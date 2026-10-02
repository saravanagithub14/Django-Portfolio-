import json

import pytest
from django.core.cache import cache
from django.urls import reverse

from chatbot import views
from chatbot.models import ChatMessage

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clear_rate_limit():
    cache.clear()
    yield
    cache.clear()


@pytest.fixture
def fake_generate(monkeypatch):
    calls = []

    def generate(user_message, profile, session, model_cfg):
        calls.append(user_message)
        return f"I heard: {user_message}", {"intent": "lookup", "chunks": [], "fallback": False, "provider": "fake"}

    monkeypatch.setattr(views, "generate_llm_response", generate)
    monkeypatch.delenv("CHATBOT_PROVIDER", raising=False)
    return calls


def post(client, body, **extra):
    return client.post(reverse("chat_api"), data=json.dumps(body), content_type="application/json", **extra)


def test_chat_contract_and_logging(client, fake_generate):
    response = post(client, {"message": "what did you do at SCTIMST"})
    assert response.status_code == 200
    assert response.json() == {"response": "I heard: what did you do at SCTIMST"}

    user_msg, bot_msg = ChatMessage.objects.order_by("timestamp", "pk")
    assert (user_msg.role, user_msg.content, user_msg.retrieval_meta) == ("user", "what did you do at SCTIMST", None)
    assert bot_msg.role == "assistant"
    assert bot_msg.retrieval_meta["provider"] == "fake"


def test_message_length_limit(client, fake_generate):
    assert post(client, {"message": "x" * 500}).status_code == 200
    response = post(client, {"message": "x" * 501})
    assert response.status_code == 400
    assert "500" in response.json()["error"]


def test_bad_requests(client, fake_generate):
    assert client.get(reverse("chat_api")).status_code == 405
    assert post(client, {"message": "   "}).status_code == 400
    bad_json = client.post(reverse("chat_api"), data="{not json", content_type="application/json")
    assert bad_json.status_code == 400


def test_rate_limit_is_ten_per_minute(client, fake_generate):
    codes = [post(client, {"message": f"hi {i}"}, REMOTE_ADDR="10.0.0.9").status_code for i in range(11)]
    assert codes[:10] == [200] * 10
    assert codes[10] == 429


def test_keyword_fallback_when_llm_chain_fails(client, monkeypatch):
    monkeypatch.setattr(views, "generate_llm_response", lambda *a: (None, {"fallback": False}))
    response = post(client, {"message": "what is machine learning"})
    assert response.status_code == 200
    assert response.json()["response"] == views.CONCEPT_ANSWERS["machine learning"]


def test_update_context_requires_token(client, monkeypatch):
    monkeypatch.setenv("UPDATE_TOKEN", "secret")
    response = client.post("/update_context", data=json.dumps({"text": "x"}), content_type="application/json",
                           HTTP_X_UPDATE_TOKEN="wrong")
    assert response.status_code == 401


def test_update_context_saves_snippet_and_updates_live_index(client, monkeypatch):
    from chatbot import rag_service
    from chatbot.models import ContextSnippet
    added = []
    monkeypatch.setenv("UPDATE_TOKEN", "secret")
    monkeypatch.setattr(rag_service, "add_snippet_to_live_index",
                        lambda s: added.append(s) or {"chunk_id": f"update#{s.pk}"})
    response = client.post("/update_context", data=json.dumps({"text": "Gave a RAG talk in 2026."}),
                           content_type="application/json", HTTP_X_UPDATE_TOKEN="secret")
    assert response.status_code == 200
    snippet = ContextSnippet.objects.get()
    assert snippet.text == "Gave a RAG talk in 2026."
    assert response.json()["chunk_id"] == f"update#{snippet.pk}"
    assert added == [snippet]


def test_mock_provider_skips_the_pipeline(client, monkeypatch, fake_generate):
    monkeypatch.setenv("CHATBOT_PROVIDER", "mock")
    response = post(client, {"message": "what is deep learning"})
    assert response.json()["response"] == views.CONCEPT_ANSWERS["deep learning"]
    assert fake_generate == []
