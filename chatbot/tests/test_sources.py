from types import SimpleNamespace

import pytest

from chatbot.rag.sources import answer_sources, item_label


def chunk(type_, heading, is_faq=False):
    return {"type": type_, "is_faq": is_faq, "display_text": f"{heading}\n\nBody text."}


@pytest.mark.parametrize("type_, heading, expected", [
    ("experience", "Saravana Perumal R, Gen AI Engineer at Blackbox Learning (April 2026 to present)", "Gen AI Engineer"),
    ("project", "Saravana Perumal R's project: Hybrid Search RAG with Pinecone", "Hybrid Search RAG with Pinecone"),
    ("education", "Saravana Perumal R's Diploma in Data Science from Edure (2023 to 2024)",
     "Diploma in Data Science from Edure"),
    ("skill", "Saravana Perumal R's skills in RAG and vector databases", "Skills in RAG and vector databases"),
    ("github", "GitHub repository: ai-agent-for-bbx", "Ai-agent-for-bbx"),
    ("about", "Professional summary of Saravana Perumal R", "Professional summary"),
])
def test_item_label_strips_names_and_dates(type_, heading, expected):
    assert item_label(chunk(type_, heading)) == expected


def test_item_label_is_none_for_faq_and_truncates_long_headings():
    assert item_label(chunk("skill", "Has Saravana built RAG systems?", is_faq=True)) is None
    label = item_label(chunk("project", "Saravana Perumal R's project: " + "A very long project title " * 4))
    assert len(label) <= 39 and label.endswith("…") and not label[:-1].endswith(" ")
    long_heading = chunk("about", "Saravana Perumal R's current role, location, and contact details")
    assert item_label(long_heading) == "Current role, location, and contact…"


STORE = SimpleNamespace(chunks=[
    chunk("experience", "Saravana Perumal R, Gen AI Engineer at Blackbox Learning (April 2026 to present)"),
    chunk("experience", "What does Saravana do right now?", is_faq=True),
    chunk("project", "Saravana Perumal R's project: Hybrid Search RAG with Pinecone"),
    chunk("update", "Live update"),
])


def results(*scores):
    return [{"pos": i, "chunk_id": f"c{i}", "score": s, "dense": 0.0} for i, s in enumerate(scores)]


def test_sources_keep_strong_known_chunks_records_first():
    sources = answer_sources(results(4.0, 6.0, 5.0, 1.0), {"intent": "lookup", "fallback": False},
                             threshold=2.0, store=STORE)
    assert sources == [
        {"section": "Experience", "url": "/experience.html", "item": "Gen AI Engineer"},
        {"section": "Projects", "url": "/projects.html", "item": "Hybrid Search RAG with Pinecone"},
        {"section": "Experience", "url": "/experience.html", "item": None},  # the FAQ: section only, last
    ]


def test_sources_drop_chunks_far_below_the_best_match():
    # best is 9.0 (the "update" chunk, which has no page); only scores >= 6.0 survive
    sources = answer_sources(results(6.0, 4.0, 1.0, 9.0), {"intent": "lookup", "fallback": False},
                             threshold=2.0, store=STORE)
    assert sources == [{"section": "Experience", "url": "/experience.html", "item": "Gen AI Engineer"}]


def test_sources_empty_for_fallback_and_chitchat_and_section_only_for_lists():
    meta = {"intent": "lookup", "fallback": True}
    assert answer_sources(results(9.0), meta, threshold=2.0, store=STORE) == []
    assert answer_sources(results(9.0), {"intent": "chitchat"}, threshold=2.0, store=STORE) == []
    listed = answer_sources(results(None, None), {"intent": "list", "type_filter": "project"}, threshold=2.0,
                            store=STORE)
    assert listed == [{"section": "Projects", "url": "/projects.html", "item": None}]
