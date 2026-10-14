"""
Personal-question dodger. Questions about Saravana's private life get a fixed deflection in V.E.R.A.'s
voice, chosen by topic, with a way back to his work. No LLM call, so nothing private can leak.

`detect` catches unambiguous phrasings before routing (saving the router call); the router's "personal"
intent catches the rest, and `reply_for` then picks the line from the message's wording.
"""
import re

from chatbot.rag.prompts import PRIVACY_DEFAULT_LINE, PRIVACY_LINES

# Unambiguous phrasings only: he is a biomedical researcher who teaches, so words like "health", "children",
# "family" or "package" alone are often about his work ("health data", "model family") and go to the router.
# Location, email and LinkedIn are public on the site, so "where is he based" or "his email" aren't personal.
STRICT = (
    ("salary", r"\b(?:salary|ctc|lpa|compensation|pay\s*scale)\b|\bhow much (?:does|do|did) (?:he|you|u|saravana) (?:make|earn|get paid)\b"),
    ("contact", r"\b(?:phone|mobile|cell|whatsapp)\s*(?:number|no\b)|\b(?:home|house|residential)\s+address\b|\bwhere (?:does|do) (?:he|you|u|saravana) live\b"),
    ("age", r"\bhow old (?:is|are|r) (?:he|you|u|saravana)\b|\b(?:his|your|ur|saravana'?s) age\b|\bdate of birth\b|\b(?:his|your|ur) birthday\b"),
    ("life", r"\b(?:is|are|r) (?:he|you|u|saravana) (?:married|single|dating|in a relationship)\b|\b(?:his|your|ur) (?:wife|girlfriend|boyfriend|family|parents|kids|religion|caste)\b"),
)
# Broader wording, used only to choose the line once the router has already said "personal"
LOOSE = STRICT + (
    ("salary", r"\b(?:pay|paid|earn\w*|income|package)\b"),
    ("life", r"\b(?:married|marriage|wife|husband|partner|family|parents|children|kids|religio\w*|caste|health|illness)\b"),
    ("views", r"\b(?:politic\w*|vote\w*|election|party|government|opinion|views?)\b"),
)
_STRICT_RES = [(topic, re.compile(p, re.I)) for topic, p in STRICT]
_LOOSE_RES = [(topic, re.compile(p, re.I)) for topic, p in LOOSE]


def _first_topic(message, patterns):
    for topic, pattern in patterns:
        if pattern.search(message or ""):
            return topic
    return None


def detect(message):
    """The privacy topic if the message unambiguously asks about Saravana's private life, else None."""
    return _first_topic(message, _STRICT_RES)


def has_personal_wording(message):
    """Whether the message contains any private-life wording at all (strict or loose)."""
    return _first_topic(message, _LOOSE_RES) is not None


def reply_for(message):
    return PRIVACY_LINES.get(_first_topic(message, _LOOSE_RES), PRIVACY_DEFAULT_LINE)
