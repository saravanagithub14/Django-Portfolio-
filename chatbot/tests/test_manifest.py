import shutil

import pytest

from chatbot.rag import index as rag_index
from chatbot.rag import ingest


@pytest.fixture
def kb_copy(tmp_path):
    target = tmp_path / "knowledge_base"
    shutil.copytree(ingest.KB_DIR, target)
    return target


@pytest.mark.django_db
def test_matching_manifest_is_fresh(kb_copy):
    manifest = rag_index.build_manifest(rag_index.local_chunks(kb_copy))
    assert rag_index.check_freshness(manifest, kb_copy, with_github=False) == (True, [])


@pytest.mark.django_db
def test_editing_one_file_marks_index_stale(kb_copy):
    manifest = rag_index.build_manifest(rag_index.local_chunks(kb_copy))
    path = kb_copy / "teaching.md"
    # Appending lands in the last section's body (the H1 title above the first section isn't indexed)
    path.write_text(path.read_text(encoding="utf-8") + "\nSaravana also ran a weekend study group.\n",
                    encoding="utf-8")

    fresh, reasons = rag_index.check_freshness(manifest, kb_copy, with_github=False)
    assert not fresh
    assert any("changed" in r for r in reasons)


@pytest.mark.django_db
def test_changing_metadata_only_marks_index_stale(kb_copy):
    manifest = rag_index.build_manifest(rag_index.local_chunks(kb_copy))
    path = kb_copy / "education.md"
    text = path.read_text(encoding="utf-8")
    path.write_text(text.replace("period: 2019\n", "period: 2020\n", 1), encoding="utf-8")
    assert not rag_index.check_freshness(manifest, kb_copy, with_github=False)[0]


@pytest.mark.django_db
def test_new_embedding_model_marks_index_stale(kb_copy):
    manifest = rag_index.build_manifest(rag_index.local_chunks(kb_copy), embedding_model="old/model")
    fresh, reasons = rag_index.check_freshness(manifest, kb_copy, with_github=False)
    assert not fresh and "embedding model changed" in reasons[0]


@pytest.mark.django_db
def test_github_chunks_do_not_make_index_stale(kb_copy):
    chunks = rag_index.local_chunks(kb_copy) + ingest.github_chunks([{"name": "repo", "language": "Python"}])
    manifest = rag_index.build_manifest(chunks)
    assert rag_index.check_freshness(manifest, kb_copy, with_github=True)[0]
    assert not rag_index.check_freshness(manifest, kb_copy, with_github=False)[0]


@pytest.mark.django_db
def test_context_snippets_are_part_of_the_manifest(kb_copy):
    from chatbot.models import ContextSnippet
    manifest = rag_index.build_manifest(rag_index.local_chunks(kb_copy))
    ContextSnippet.objects.create(text="Saravana gave a talk on agentic RAG in 2026.")
    fresh, reasons = rag_index.check_freshness(manifest, kb_copy, with_github=False)
    assert not fresh and any("added" in r for r in reasons)


def test_diff_manifest_counts():
    old = {"chunks": {"a": "1", "b": "2", "c": "3"}}
    new = {"chunks": {"a": "1", "b": "X", "d": "4"}}
    assert rag_index.diff_manifest(old, new) == {
        "added": ["d"], "removed": ["c"], "changed": ["b"], "unchanged": ["a"],
    }
