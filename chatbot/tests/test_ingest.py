import re

import pytest

from chatbot.rag import ingest
from chatbot.rag.prompts import CONTACT_EMAIL


def test_chunk_count_matches_h2_sections(kb_chunks):
    h2_count = sum(
        len(re.findall(r"^## ", path.read_text(encoding="utf-8"), re.M))
        for path in ingest.KB_DIR.glob("*.md")
    )
    assert h2_count > 0
    assert len(kb_chunks) == h2_count


def test_every_chunk_has_required_metadata(kb_chunks):
    for c in kb_chunks:
        assert c["chunk_id"].startswith(c["source_file"].removesuffix(".md") + "#")
        assert c["type"]
        assert c["organization"]
        assert c["period"]
        assert isinstance(c["tags"], list)
        assert len(c["content_hash"]) == 64
        assert "---" not in c["display_text"].split("\n", 3)[:3], "YAML block must be stripped"


def test_chunk_ids_are_unique(kb_chunks):
    ids = [c["chunk_id"] for c in kb_chunks]
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("period, expected", [
    ("April 2025 to March 2026", (2025, 2026)),
    ("2019 to November 2023", (2019, 2023)),
    ("2019", (2019, 2019)),
    ("July 2019 to present", (2019, 2030)),
    ("present", (2030, 2030)),
    ("not specified", (None, None)),
    ("not specified to present", (None, 2030)),
    ("2024 and not specified", (2024, None)),
])
def test_parse_period(period, expected):
    assert ingest.parse_period(period, current_year=2030) == expected


def test_faq_chunks_embed_only_the_question(kb_chunks):
    faq = [c for c in kb_chunks if c["is_faq"]]
    assert faq
    for c in faq:
        question = c["display_text"].split("\n", 1)[0]
        assert c["embed_text"] == question
        assert len(c["display_text"]) > len(question)  # answer is kept for the LLM


def test_outdated_email_is_replaced(kb_chunks):
    text = " ".join(c["display_text"] for c in kb_chunks)
    assert "mynamesaravanaperumal@gmail.com" not in text
    assert CONTACT_EMAIL in text


def test_tokenizer_keeps_compound_terms():
    tokens = ingest.tokenize("UGC-NET, Llama3 + QLoRA tuning of Pictor-v2; Saravana's work")
    for term in ("ugc-net", "llama3", "qlora", "pictor-v2"):
        assert term in tokens


def _write(tmp_path, body):
    path = tmp_path / "broken.md"
    path.write_text(f"# Title\n\n## Some heading\n\n{body}\n", encoding="utf-8")
    return path


def test_section_without_yaml_fails_loudly(tmp_path):
    with pytest.raises(ingest.KnowledgeBaseError, match="no YAML"):
        ingest.parse_markdown_file(_write(tmp_path, "Just prose, no metadata."))


@pytest.mark.parametrize("missing", ["type", "period"])
def test_yaml_missing_required_key_fails_loudly(tmp_path, missing):
    fields = {"type": "project", "organization": "none", "period": "2021", "tags": "[a, b]"}
    del fields[missing]
    yaml_block = "\n".join(f"{k}: {v}" for k, v in fields.items())
    with pytest.raises(ingest.KnowledgeBaseError, match=f"missing '{missing}'"):
        ingest.parse_markdown_file(_write(tmp_path, f"---\n{yaml_block}\n---\n\nBody."))
