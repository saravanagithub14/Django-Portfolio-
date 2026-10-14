"""
Portfolio agent: answers questions about Saravana from the retrieved knowledge-base chunks, using the
brand-kit system prompt. Retrieval itself (and the fallback check) happens in the orchestrator, so this is
only the answer step. Also handles chitchat and off-topic turns, which the prompt answers with fixed lines.
"""
from chatbot.rag.prompts import NO_SOURCES_CONTEXT, SYSTEM_PROMPT_TEMPLATE

ANSWER_MAX_TOKENS = 400
LIST_ANSWER_MAX_TOKENS = 800


def format_context(results):
    if not results:
        return NO_SOURCES_CONTEXT
    return "\n\n".join(f"[source: {r['chunk_id']}]\n{r['text']}" for r in results)


def answer(message, history, llm, results, intent):
    """(raw_reply, provider); raw_reply is None when every provider failed."""
    system_prompt = SYSTEM_PROMPT_TEMPLATE.replace("{context}", format_context(results))
    messages = [{"role": "system", "content": system_prompt}, *history, {"role": "user", "content": message}]
    return llm(messages, max_tokens=LIST_ANSWER_MAX_TOKENS if intent == "list" else ANSWER_MAX_TOKENS)
