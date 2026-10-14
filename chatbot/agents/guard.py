"""
Prompt-injection guard. Inbound: obvious attempts to override the rules get the brand kit's trick line
without any LLM call (the router's "injection" intent catches subtler ones). Outbound: a reply that repeats
a system-prompt heading, or contains a phone number, is replaced.
"""
import re

from chatbot.rag.prompts import PRIVACY_LINES, PROMPT_MARKERS, TRICK_LINE

INJECTION_RE = re.compile(
    r"\b(?:ignore|disregard|forget|override|bypass)\b.{0,40}\b(?:instructions?|rules|prompts?|guidelines|guardrails)\b"
    r"|\b(?:reveal|show|print|repeat|output|leak|give)\b.{0,30}\b(?:system|initial|hidden|original)\s+(?:prompt|instructions?|message)\b"
    r"|\b(?:what(?:'s| is| are)|tell me)\s+your\s+(?:system\s+)?(?:prompt|instructions)\b"
    r"|\byou\s+are\s+now\b|\bfrom\s+now\s+on\s+you\b|\bpretend\s+(?:to\s+be|you\s+are)\b"
    r"|\b(?:jailbreak|developer\s+mode|DAN\s+mode|do\s+anything\s+now)\b"
    r"|<\|[a-z_]+\|>|^\s*(?:system|assistant)\s*:|\[\s*system\s*\]",
    re.I | re.M,
)
# Phone-length digit runs (10-13 digits, spaces or dashes allowed). Years, year ranges and DOIs don't match:
# a run touching a "." plus digits is part of a DOI or decimal.
PHONE_RE = re.compile(r"(?<![\d.])(?:\+?\d{1,3}[\s-]?)?(?:\d[\s-]?){9,12}\d(?!\d|\.\d)")


def is_injection(message):
    return bool(INJECTION_RE.search(message or ""))


def check_reply(reply):
    """(safe_reply, problem): problem is "prompt_leak", "phone_number" or None."""
    if not reply:
        return reply, None
    if any(marker.lower() in reply.lower() for marker in PROMPT_MARKERS):
        return TRICK_LINE, "prompt_leak"
    if PHONE_RE.search(reply):
        return PRIVACY_LINES["contact"], "phone_number"
    return reply, None
