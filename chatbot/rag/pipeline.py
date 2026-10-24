"""
V.E.R.A.'s orchestrator: guard -> condense + route (one LLM call) -> one specialist agent -> output check.

    injection   guard: the brand kit's trick line, no LLM call (obvious attempts never reach the router)
    personal    privacy agent: a fixed deflection, no LLM call (unambiguous ones never reach the router)
    concept     tutor agent: teaches any topic, bridging to Saravana's related work when there is some
    lookup, list, timeframe, chitchat, out_of_scope
                portfolio agent: retrieve by intent -> fallback check -> answer from the knowledge base

The LLM is passed in as a callable so this module stays independent of provider plumbing:

    llm(messages, *, temperature=None, max_tokens=..., json_mode=False) -> (text | None, provider | None)

`temperature=None` means "use the provider's configured temperature".
"""
import json
import logging
import os
import re
import time

from chatbot.agents import guard, portfolio, privacy, tutor
from chatbot.agents.portfolio import format_context  # noqa: F401  (kept importable from here)
from chatbot.formatting import strip_markdown
from chatbot.rag import index as rag_index
from chatbot.rag.prompts import CONDENSE_ROUTE_PROMPT, FALLBACK_MESSAGE, FIXED_LINES, OFF_TOPIC_LINES
from chatbot.rag.retrieve import filter_by_year, hybrid_search, list_by_type
from chatbot.rag.sources import answer_sources

logger = logging.getLogger(__name__)

INTENTS = ("lookup", "list", "timeframe", "concept", "personal", "injection", "out_of_scope", "chitchat")
# Which agent answers each intent; anything else goes to the portfolio agent
AGENT_FOR_INTENT = {"injection": "guard", "personal": "privacy", "concept": "tutor"}
TYPE_FILTERS = ("experience", "project", "skill", "teaching", "education", "certification", "publication", "blog",
                "media", "focus", "language", "contact", "about", "github")
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


def default_route(message):
    return {"standalone_question": message, "intent": "lookup", "type_filter": None, "year": None,
            "concept_term": None}


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
    term = data.get("concept_term")
    try:
        year = int(year) if year not in (None, "", "null") else None
    except (TypeError, ValueError):
        year = None
    return {
        "standalone_question": question.strip() if isinstance(question, str) and question.strip() else message,
        "intent": intent if intent in INTENTS else "lookup",
        "type_filter": type_filter if type_filter in TYPE_FILTERS else None,
        "year": year if year is not None and 1950 <= year <= 2100 else None,
        "concept_term": term.strip() if isinstance(term, str) and term.strip() else None,
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


def _elapsed_ms(start):
    return round((time.perf_counter() - start) * 1000, 1)


def step(agent, stage):
    """A progress event: which agent is working and what it is doing (routing, checking, searching, writing)."""
    return {"agent": agent, "stage": stage}


def run(message, history, llm, *, store=None, use_reranker=None):
    """The pipeline without progress events: returns run_steps' result dict."""
    steps = run_steps(message, history, llm, store=store, use_reranker=use_reranker)
    while True:
        try:
            next(steps)
        except StopIteration as done:
            return done.value


def run_steps(message, history, llm, *, store=None, use_reranker=None):
    """
    Full pipeline for one visitor message, as a generator: it yields step() events as agents start work (the
    chat widget shows them while it waits), and returns a dict:
        reply       final plain-text reply, or None if every LLM provider failed
        raw_reply   the model's text before strip_markdown (for evals)
        results     retrieved chunks (for concept questions, the tutor's related work)
        sources     site sections / records the answer drew on, for the widget's source chips
        meta        what gets logged to ChatMessage.retrieval_meta, including which agent answered
    """
    started = time.perf_counter()
    timings = {}
    reranked = rag_index.reranker_enabled() if use_reranker is None else use_reranker

    def finish(route, agent, raw_reply, *, results=(), sources=(), provider=None, condense_provider=None,
               top_score=None, fallback=False):
        meta = {
            **route,
            "agent": agent,
            "chunks": [{"chunk_id": r["chunk_id"], "score": r["score"]} for r in results],
            "top_score": None if top_score is None else round(top_score, 4),
            "fallback": fallback,
            "condense_provider": condense_provider,
            "provider": provider,
            "latency_ms": timings,
        }
        reply, problem = guard.check_reply(strip_markdown(raw_reply) if raw_reply else None)
        if problem:
            logger.warning("Output guard replaced a %s reply (%s): %r", agent, problem, raw_reply)
            meta["output_guard"] = problem
            sources = ()
        timings["total_ms"] = _elapsed_ms(started)
        return {"reply": reply, "raw_reply": raw_reply, "results": list(results), "sources": list(sources),
                "meta": meta}

    # 1. Before any LLM call: obvious injection attempts and unambiguous personal questions
    if guard.is_injection(message):
        yield step("guard", "checking")
        return finish({**default_route(message), "intent": "injection"}, "guard", guard.injection_reply(history))
    if privacy.detect(message):
        yield step("privacy", "checking")
        return finish({**default_route(message), "intent": "personal"}, "privacy", privacy.reply_for(message))

    # 2. Condense + route
    yield step("router", "routing")
    t = time.perf_counter()
    route, condense_provider = condense_and_route(message, history, llm)
    timings["condense_ms"] = _elapsed_ms(t)
    agent = AGENT_FOR_INTENT.get(route["intent"], "portfolio")

    if agent == "guard":
        yield step("guard", "checking")
        return finish(route, agent, guard.injection_reply(history), condense_provider=condense_provider)
    if agent == "privacy":
        yield step("privacy", "checking")
        wording = f"{message} {route['standalone_question']}"
        # The router sometimes calls work questions personal ("do u teach students", "r u open to
        # freelance"). With no private-life wording, a strong knowledge-base match sends it to the portfolio.
        if not privacy.has_personal_wording(wording) and reranked:
            store = store if store is not None else rag_index.get_store()
            results, top_score = hybrid_search(store, route["standalone_question"], use_reranker=True,
                                               timings=timings)
            if top_score is not None and top_score >= ROUTE_RESCUE_SCORE:
                route["rerouted_from"] = route["intent"]
                route["intent"] = "lookup"
                yield step("portfolio", "writing")
                return _answer_portfolio(message, history, llm, route, results, top_score, store, reranked,
                                         timings, finish, condense_provider)
        return finish(route, agent, privacy.reply_for(wording), condense_provider=condense_provider)

    store = store if store is not None else rag_index.get_store()

    if agent == "tutor":
        yield step("tutor", "searching")
        t = time.perf_counter()
        related = tutor.related_work(route["concept_term"] or route["standalone_question"], store,
                                         use_reranker=reranked, threshold=fallback_threshold(reranked),
                                         timings=timings)
        timings["retrieve_ms"] = _elapsed_ms(t)
        yield step("tutor", "writing")
        t = time.perf_counter()
        raw_reply, provider = tutor.answer(message, history, llm, related)
        timings["generate_ms"] = _elapsed_ms(t)
        return finish(route, agent, raw_reply, results=related, provider=provider,
                      condense_provider=condense_provider,
                      sources=_sources(raw_reply, related, route, store, reranked))

    # 3. Portfolio agent: retrieve by intent; fall back without generating if nothing scores well enough
    yield step("portfolio", "searching")
    t = time.perf_counter()
    results, top_score, fallback = retrieve(route, store, use_reranker=reranked, timings=timings)
    timings["retrieve_ms"] = _elapsed_ms(t)
    if fallback:
        return finish(route, agent, FALLBACK_MESSAGE, results=results, condense_provider=condense_provider,
                      top_score=top_score, fallback=True)
    if route["intent"] == "out_of_scope":  # not rescued to a lookup: a fixed line, no answer call
        return finish(route, agent, guard.next_line(OFF_TOPIC_LINES, history), condense_provider=condense_provider)

    yield step("portfolio", "writing")
    return _answer_portfolio(message, history, llm, route, results, top_score, store, reranked, timings,
                             finish, condense_provider)


def _answer_portfolio(message, history, llm, route, results, top_score, store, reranked, timings, finish,
                      condense_provider):
    t = time.perf_counter()
    raw_reply, provider = portfolio.answer(message, history, llm, results, route["intent"])
    timings["generate_ms"] = _elapsed_ms(t)
    return finish(route, "portfolio", raw_reply, results=results, provider=provider,
                  condense_provider=condense_provider, top_score=top_score,
                  sources=_sources(raw_reply, results, route, store, reranked))


def _sources(raw_reply, results, route, store, reranked):
    """Source chips for an answer; none for fixed lines, which didn't use the retrieved chunks."""
    if not raw_reply or raw_reply.strip().strip('"') in FIXED_LINES:
        return []
    try:
        return answer_sources(results, route, threshold=fallback_threshold(reranked), store=store,
                              use_reranker=reranked)
    except Exception as e:  # chips are decoration; never fail an answer over them
        logger.warning("Could not build answer sources: %s", e)
        return []
