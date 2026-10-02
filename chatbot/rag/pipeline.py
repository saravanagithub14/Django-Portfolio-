"""
Query pipeline: condense + route (one LLM call) -> retrieve by intent -> fallback check -> generate.

The LLM is passed in as a callable so this module stays independent of provider plumbing:

    llm(messages, *, temperature=None, max_tokens=..., json_mode=False) -> (text | None, provider | None)

`temperature=None` means "use the provider's configured temperature".
"""
import json
import logging
import os
import re
import time

from chatbot.formatting import strip_markdown
from chatbot.rag import index as rag_index
from chatbot.rag.prompts import (
    CONDENSE_ROUTE_PROMPT, FALLBACK_MESSAGE, FIXED_LINES, NO_SOURCES_CONTEXT, SYSTEM_PROMPT_TEMPLATE,
)
from chatbot.rag.retrieve import filter_by_year, hybrid_search, list_by_type
from chatbot.rag.sources import answer_sources

logger = logging.getLogger(__name__)

INTENTS = ("lookup", "list", "timeframe", "out_of_scope", "chitchat")
TYPE_FILTERS = ("experience", "project", "skill", "teaching", "education", "certification", "about", "github")
NO_RETRIEVAL_INTENTS = ("out_of_scope", "chitchat")
FALLBACK_INTENTS = ("lookup", "timeframe")

# Defaults picked from the eval's in-scope vs out-of-scope score distributions (see CLAUDE.md).
# Reranker scores are ms-marco logits; dense scores are cosine similarities, so each needs its own default.
# Rerank: in-scope min 2.63 vs off-topic max 1.45 (salary, coding help, politics, family) -> 2.0.
DEFAULT_THRESHOLD_RERANK = 2.0
# Dense cosine doesn't separate them (in-scope 0.72-0.98, off-topic 0.73-0.90), so with the reranker
# off this only catches near-nonsense; refusals then rely on routing and the system prompt.
DEFAULT_THRESHOLD_DENSE = 0.70
# Rerank score at which a question the router called chitchat/out_of_scope is answered as a lookup.
# Misrouted in-scope questions scored 5.5-10.9; true off-topic questions scored <= 1.45.
ROUTE_RESCUE_SCORE = 5.0

CONDENSE_MAX_TOKENS = 300
ANSWER_MAX_TOKENS = 400
LIST_ANSWER_MAX_TOKENS = 800


def default_route(message):
    return {"standalone_question": message, "intent": "lookup", "type_filter": None, "year": None}


def parse_route(raw, message):
    """Parse the condense/route JSON defensively; anything malformed falls back to a plain lookup."""
    try:
        match = re.search(r"\{.*\}", raw or "", re.S)  # tolerate code fences or chatter around the JSON
        data = json.loads(match.group(0))
        if not isinstance(data, dict):
            raise ValueError("route is not a JSON object")
    except (AttributeError, TypeError, ValueError):
        return default_route(message)

    question = data.get("standalone_question")
    intent = data.get("intent")
    type_filter = data.get("type_filter")
    year = data.get("year")
    try:
        year = int(year) if year not in (None, "", "null") else None
    except (TypeError, ValueError):
        year = None
    return {
        "standalone_question": question.strip() if isinstance(question, str) and question.strip() else message,
        "intent": intent if intent in INTENTS else "lookup",
        "type_filter": type_filter if type_filter in TYPE_FILTERS else None,
        "year": year if year is not None and 1950 <= year <= 2100 else None,
    }


def format_history(history):
    if not history:
        return "(none)"
    return "\n".join(
        f"{'Visitor' if m['role'] == 'user' else 'Assistant'}: {m['content']}" for m in history
    )


def condense_and_route(message, history, llm):
    prompt = CONDENSE_ROUTE_PROMPT.format(history=format_history(history), question=message)
    text, provider = llm([{"role": "user", "content": prompt}], temperature=0,
                         max_tokens=CONDENSE_MAX_TOKENS, json_mode=True)
    return parse_route(text, message), provider


def fallback_threshold(use_reranker):
    raw = os.getenv("RAG_FALLBACK_THRESHOLD")
    if raw not in (None, ""):
        try:
            return float(raw)
        except ValueError:
            logger.warning("Ignoring non-numeric RAG_FALLBACK_THRESHOLD=%r", raw)
    return DEFAULT_THRESHOLD_RERANK if use_reranker else DEFAULT_THRESHOLD_DENSE


def format_context(results):
    if not results:
        return NO_SOURCES_CONTEXT
    return "\n\n".join(f"[source: {r['chunk_id']}]\n{r['text']}" for r in results)


def retrieve(route, store=None, *, use_reranker=None, timings=None):
    """Retrieve for a routed question. Returns (results, top_score, fallback_fired)."""
    store = store if store is not None else rag_index.get_store()
    use_reranker = rag_index.reranker_enabled() if use_reranker is None else use_reranker
    timings = timings if timings is not None else {}
    intent, question = route["intent"], route["standalone_question"]

    if intent in NO_RETRIEVAL_INTENTS:
        # The router often labels short in-scope questions ("where r u based", "do u teach students")
        # as chitchat/out_of_scope. If the reranker is confident the KB answers it, treat it as a lookup.
        if use_reranker:
            results, top_score = hybrid_search(store, question, use_reranker=True, timings=timings)
            if top_score is not None and top_score >= ROUTE_RESCUE_SCORE:
                route["rerouted_from"] = intent
                route["intent"] = "lookup"
                return results, top_score, False
        return [], None, False
    if intent == "list" and route["type_filter"]:
        return list_by_type(store, route["type_filter"]), None, False

    subset = filter_by_year(store, route["year"]) if intent == "timeframe" and route["year"] else None
    results, top_score = hybrid_search(store, question, subset=subset, use_reranker=use_reranker, timings=timings)
    fallback = intent in FALLBACK_INTENTS and (top_score is None or top_score < fallback_threshold(use_reranker))
    return results, top_score, fallback


def run(message, history, llm, *, store=None, use_reranker=None):
    """
    Full pipeline for one visitor message. Returns a dict:
        reply       final plain-text reply, or None if every LLM provider failed
        raw_reply   the model's text before strip_markdown (for evals)
        results     retrieved chunks
        sources     site sections / records the answer drew on, for the widget's source chips
        meta        what gets logged to ChatMessage.retrieval_meta
    """
    started = time.perf_counter()
    timings = {}

    t = time.perf_counter()
    route, condense_provider = condense_and_route(message, history, llm)
    timings["condense_ms"] = round((time.perf_counter() - t) * 1000, 1)

    t = time.perf_counter()
    results, top_score, fallback = retrieve(route, store, use_reranker=use_reranker, timings=timings)
    timings["retrieve_ms"] = round((time.perf_counter() - t) * 1000, 1)

    meta = {
        **route,
        "chunks": [{"chunk_id": r["chunk_id"], "score": r["score"]} for r in results],
        "top_score": None if top_score is None else round(top_score, 4),
        "fallback": fallback,
        "condense_provider": condense_provider,
        "provider": None,
        "latency_ms": timings,
    }

    if fallback:
        timings["total_ms"] = round((time.perf_counter() - started) * 1000, 1)
        return {"reply": FALLBACK_MESSAGE, "raw_reply": FALLBACK_MESSAGE, "results": results, "sources": [],
                "meta": meta}

    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{context}", format_context(results))
    messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]
    t = time.perf_counter()
    raw_reply, provider = llm(
        messages, max_tokens=LIST_ANSWER_MAX_TOKENS if route["intent"] == "list" else ANSWER_MAX_TOKENS,
    )
    timings["generate_ms"] = round((time.perf_counter() - t) * 1000, 1)
    timings["total_ms"] = round((time.perf_counter() - started) * 1000, 1)
    meta["provider"] = provider
    reranked = rag_index.reranker_enabled() if use_reranker is None else use_reranker
    try:
        # A fixed line (greeting, off topic, ...) didn't use the retrieved chunks, so it gets no chips
        is_fixed_line = (raw_reply or "").strip().strip('"') in FIXED_LINES
        sources = [] if is_fixed_line else answer_sources(
            results, meta, threshold=fallback_threshold(reranked), store=store, use_reranker=reranked)
    except Exception as e:  # chips are decoration; never fail an answer over them
        logger.warning("Could not build answer sources: %s", e)
        sources = []
    return {
        "reply": strip_markdown(raw_reply) if raw_reply else None,
        "raw_reply": raw_reply,
        "results": results,
        "sources": sources,
        "meta": meta,
    }
