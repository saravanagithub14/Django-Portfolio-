"""
Tutor agent: teaches any topic from general knowledge (science, history, maths, programming, AI, languages,
...) with one method: core intuition, an everyday analogy, how it actually works, then an offer to go
further. When the index has a strong match for the topic, it ends with a bridge to Saravana's related work.
Follow-ups ("go deeper", "give me an example", "quiz me") reach it through the chat history, which the
router resolves to the same topic.
"""
import logging

from chatbot.rag.prompts import TUTOR_PROMPT
from chatbot.rag.retrieve import hybrid_search

logger = logging.getLogger(__name__)

TEACH_MAX_TOKENS = 500
MAX_RELATED = 2
NO_RELATED = "(none)"


def related_work(topic, store, *, use_reranker, threshold, timings=None):
    """Indexed chunks about the topic that clear the fallback threshold (at most MAX_RELATED)."""
    try:
        results, _ = hybrid_search(store, topic, use_reranker=use_reranker, timings=timings)
    except Exception as e:  # the bridge is a bonus; teach without it
        logger.warning("Tutor related-work search failed: %s", e)
        return []
    score = (lambda r: r["score"]) if use_reranker else (lambda r: r.get("dense", 0))
    return [r for r in results if score(r) is not None and score(r) >= threshold][:MAX_RELATED]


def answer(message, history, llm, related):
    """(raw_reply, provider); raw_reply is None when every provider failed."""
    related_text = "\n\n".join(r["text"] for r in related) if related else NO_RELATED
    system_prompt = TUTOR_PROMPT.replace("{related}", related_text)
    messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]
    return llm(messages, max_tokens=TEACH_MAX_TOKENS)
