import pytest

from chatbot.rag import pipeline
from chatbot.rag.prompts import FALLBACK_MESSAGE
from chatbot.tests.conftest import make_fake_store

MESSAGE = "u used agents?"
DEFAULT = {"standalone_question": MESSAGE, "intent": "lookup", "type_filter": None, "year": None,
           "concept_term": None}


@pytest.mark.parametrize("raw", [
    None,
    "",
    "not json at all",
    "{\"standalone_question\": \"x\", ",   # truncated
    "[1, 2, 3]",
    "{bad json}",
])
def test_malformed_route_falls_back_to_lookup(raw):
    assert pipeline.parse_route(raw, MESSAGE) == DEFAULT


def test_route_with_invalid_values_is_sanitized():
    raw = '{"standalone_question": "", "intent": "dance", "type_filter": "hobby", "year": "next year"}'
    assert pipeline.parse_route(raw, MESSAGE) == DEFAULT


def test_route_inside_code_fence_is_parsed():
    raw = '```json\n{"standalone_question": "Has Saravana built AI agents?", "intent": "lookup", ' \
          '"type_filter": "project", "year": "2024"}\n```'
    assert pipeline.parse_route(raw, MESSAGE) == {
        "standalone_question": "Has Saravana built AI agents?", "intent": "lookup",
        "type_filter": "project", "year": 2024, "concept_term": None,
    }


def test_condense_uses_default_when_every_provider_fails():
    route, provider = pipeline.condense_and_route(MESSAGE, [], lambda *a, **k: (None, None))
    assert route == DEFAULT and provider is None


def test_fallback_skips_generation_when_scores_are_low(kb_chunks, monkeypatch):
    monkeypatch.setenv("RAG_FALLBACK_THRESHOLD", "0")
    store = make_fake_store(kb_chunks, rerank_fn=lambda q, texts: [-5.0] * len(texts))
    calls = []

    def llm(messages, **kwargs):
        calls.append(kwargs)
        if kwargs.get("json_mode"):
            return '{"standalone_question": "Q", "intent": "lookup", "type_filter": null, "year": null}', "fake"
        return "should not be called", "fake"

    result = pipeline.run("what is your favourite colour", [], llm, store=store, use_reranker=True)
    assert result["reply"] == FALLBACK_MESSAGE
    assert result["meta"]["fallback"] is True
    assert len(calls) == 1, "only the condense call; no generation"


def test_generation_gets_sources_and_reply_is_plain_text(kb_chunks, monkeypatch):
    monkeypatch.setenv("RAG_FALLBACK_THRESHOLD", "-100")
    store = make_fake_store(kb_chunks)
    seen = {}

    def llm(messages, **kwargs):
        if kwargs.get("json_mode"):
            return '{"standalone_question": "Q", "intent": "lookup", "type_filter": null, "year": null}', "fake"
        seen["system"] = messages[0]["content"]
        return "**I** worked at *SCTIMST*.", "fake"

    result = pipeline.run("where did you work", [], llm, store=store, use_reranker=True)
    assert result["reply"] == "I worked at SCTIMST."
    assert "[source: " in seen["system"]
    assert result["meta"]["provider"] == "fake"
    assert len(result["meta"]["chunks"]) == 5
    assert set(result["meta"]["latency_ms"]) >= {"condense_ms", "retrieve_ms", "generate_ms", "total_ms"}


def test_threshold_env_overrides_default(monkeypatch):
    monkeypatch.delenv("RAG_FALLBACK_THRESHOLD", raising=False)
    assert pipeline.fallback_threshold(True) == pipeline.DEFAULT_THRESHOLD_RERANK
    assert pipeline.fallback_threshold(False) == pipeline.DEFAULT_THRESHOLD_DENSE
    monkeypatch.setenv("RAG_FALLBACK_THRESHOLD", "1.5")
    assert pipeline.fallback_threshold(True) == 1.5
