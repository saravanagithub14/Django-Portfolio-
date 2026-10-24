"""
Source chips for the chat widget: which parts of the site an answer came from.

Each source is {"section", "url", "item"}: the site page the chunk belongs to and a short label
for the specific record ("Gen AI Engineer", "Hybrid Search RAG with Pinecone"). FAQ chunks have no
record of their own, so they only contribute their section. Website chunks carry their own page and
record label; knowledge-base chunks get theirs from their type and heading.
"""
import re

from . import index as rag_index

# Chunk type -> (section label, site page). GitHub repos are shown on the Projects page.
SECTIONS = {
    "experience": ("Experience", "/experience.html"),
    "project": ("Projects", "/projects.html"),
    "github": ("Projects", "/projects.html"),
    "skill": ("Skills", "/skills.html"),
    "education": ("Education", "/education.html"),
    "certification": ("Education", "/education.html"),
    "teaching": ("Workshops", "/workshops.html"),
    "about": ("Bio", "/bio.html"),
    "publication": ("Publications", "/publications.html"),
    "focus": ("Current Focus", "/summary.html"),
    "language": ("Languages", "/languages.html"),
    "media": ("Gallery", "/gallery.html"),
    "blog": ("Blog", "/blogs.html"),
    "contact": ("Contact", "/contact.html"),
}
SECTION_FOR_PAGE = {url: label for label, url in SECTIONS.values()}

MAX_SOURCES = 3
MAX_LABEL = 38
# Rerank logits: only chunks within this distance of the best one become chips (weaker ones are
# usually incidental matches, e.g. a random repo for "who are you?")
RELATIVE_WINDOW = 3.0

_PREFIXES = re.compile(
    r"^(Saravana Perumal R's (research )?project: |Saravana Perumal R, |Saravana Perumal R's |GitHub repository: )"
)
_TRAILING_DATES = re.compile(r"\s*\([^)]*\d{4}[^)]*\)\s*$")


def _shorten(label):
    if len(label) <= MAX_LABEL:
        return label
    cut = label[:MAX_LABEL].rsplit(" ", 1)[0].rstrip(" ,;:-&")  # whole words only
    return cut + "…"


def item_label(chunk):
    """A short label for one record, from its site label or its heading. None for FAQ chunks."""
    if chunk.get("is_faq"):
        return None
    if chunk.get("label"):
        return _shorten(chunk["label"])
    heading = chunk["display_text"].split("\n", 1)[0].strip()
    heading = _TRAILING_DATES.sub("", _PREFIXES.sub("", heading))
    if chunk["type"] == "experience" and " at " in heading:
        heading = heading.split(" at ", 1)[0]  # "Gen AI Engineer at Blackbox Learning" -> "Gen AI Engineer"
    heading = heading.replace("Professional summary of Saravana Perumal R", "Professional summary")
    return _shorten(heading[:1].upper() + heading[1:])


def chunk_section(chunk):
    """(section label, page url) for a chunk, or None if it has no page (live updates)."""
    if chunk.get("url"):
        return SECTION_FOR_PAGE.get(chunk["url"], "Site"), chunk["url"]
    return SECTIONS.get(chunk["type"])


def answer_sources(results, meta, *, threshold, store=None, use_reranker=True):
    """
    Sources worth showing for an answer: the top retrieved chunks that cleared the fallback threshold
    (so weak matches that the model probably ignored don't become chips). Empty for fallbacks and
    for chitchat / out-of-scope turns.
    """
    if not results or meta.get("fallback") or meta.get("intent") in ("chitchat", "out_of_scope"):
        return []
    store = store if store is not None else rag_index.get_store()

    if meta.get("intent") == "list":
        section = SECTIONS.get(meta.get("type_filter"))
        return [{"section": section[0], "url": section[1], "item": None}] if section else []

    scored = [r["score"] if use_reranker else r.get("dense", 0) for r in results]
    best = max((s for s in scored if s is not None), default=None)
    if best is None:
        return []
    floor = max(threshold, best - RELATIVE_WINDOW) if use_reranker else threshold

    sources, seen = [], set()
    for r, score in zip(results, scored):
        strong = score is not None and score >= floor
        if not strong:
            continue
        chunk = store.chunks[r["pos"]]
        section = chunk_section(chunk)
        if not section:
            continue
        item = item_label(chunk)
        key = (section[0], item)
        if key in seen:
            continue
        seen.add(key)
        sources.append({"section": section[0], "url": section[1], "item": item})
        if len(sources) >= MAX_SOURCES:
            break
    # Specific records first, so the "See …" link points at the page holding the record itself
    # (an FAQ about his current role is filed under Bio, but the role lives on Experience)
    return sorted(sources, key=lambda s: s["item"] is None)
