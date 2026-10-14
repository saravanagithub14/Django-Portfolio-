"""
Explainer agent: explains AI / ML / data-science concepts from general knowledge (intuition, analogy, how it
works), then bridges to Saravana's related work when the knowledge base has a strong match for the term.
"Go deeper" follow-ups reach it through the chat history, which the router resolves to the same concept.
"""
import logging

from chatbot.rag.prompts import EXPLAINER_PROMPT
from chatbot.rag.retrieve import hybrid_search

logger = logging.getLogger(__name__)

EXPLAIN_MAX_TOKENS = 350
MAX_RELATED = 2
NO_RELATED = "(none)"


def related_work(term, store, *, use_reranker, threshold, timings=None):
    """Knowledge-base chunks about the term that clear the fallback threshold (at most MAX_RELATED)."""
    try:
        results, _ = hybrid_search(store, term, use_reranker=use_reranker, timings=timings)
    except Exception as e:  # the bridge is a bonus; explain without it
        logger.warning("Explainer related-work search failed: %s", e)
        return []
    score = (lambda r: r["score"]) if use_reranker else (lambda r: r.get("dense", 0))
    return [r for r in results if score(r) is not None and score(r) >= threshold][:MAX_RELATED]


def answer(message, history, llm, related):
    """(raw_reply, provider); raw_reply is None when every provider failed."""
    related_text = "\n\n".join(r["text"] for r in related) if related else NO_RELATED
    system_prompt = EXPLAINER_PROMPT.replace("{related}", related_text)
    messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]
    return llm(messages, max_tokens=EXPLAIN_MAX_TOKENS)
