import numpy as np
import pytest
from django.contrib.auth.models import User

from chatbot.rag import index as rag_index
from chatbot.rag import site_content
from chatbot.rag.retrieve import cap_faq, list_by_type
from chatbot.rag.sources import answer_sources
from chatbot.tests.conftest import make_fake_store
from portfolio.models import (
    BlogPage, BlogPost, ExperiencePage, ExperienceSection, Job, Project, ProjectPage, PublicationsPage,
    ResearchArticle, UserProfile,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def content():
    user = User.objects.create_user("owner", "owner@example.com", "pw")
    profile = UserProfile.objects.create(user=user, email="me@example.com", location="Thiruvananthapuram",
                                         whatsapp_number="+91 98765 43210", intro="I build RAG systems.")
    section = ExperienceSection.objects.create(
        experience_page=ExperiencePage.objects.create(profile=profile), heading="🤖 AI & Data Science")
    job = Job.objects.create(section=section, title="Gen AI Engineer", company="Blackbox Learning",
                             period="Apr 2026 – Present", description="Builds agents.", tags="GenAI, RAG")
    page = ProjectPage.objects.create(profile=profile)
    project = Project.objects.create(project_page=page, title="Hybrid Search RAG with Pinecone",
                                     description="Semantic plus keyword search.", featured=True)
    ResearchArticle.objects.create(publications_page=PublicationsPage.objects.create(profile=profile),
                                   title="A wound dressing", meta="A, B<br><em>Journal</em> &middot; 2022",
                                   year=2022)
    BlogPost.objects.create(blog_page=BlogPage.objects.create(profile=profile), title="AI PCs", excerpt="On NPUs.",
                            category="Hardware", date="2024", read_time="4 min", medium_url="https://medium.com/x")
    return {"job": job, "project": project}


def by_id(chunks):
    return {c["chunk_id"]: c for c in chunks}


def test_site_chunks_cover_every_page_with_their_urls(content):
    chunks = by_id(site_content.site_chunks())
    job = chunks[f"site:job#{content['job'].pk}"]
    assert job["type"] == "experience" and job["url"] == "/experience.html" and job["label"] == "Gen AI Engineer"
    assert (job["start_year"], job["end_year"]) == (2026, rag_index.datetime.date.today().year)
    assert "🤖" not in job["display_text"] and "AI & Data Science" in job["display_text"]

    article = next(c for c in chunks.values() if c["type"] == "publication")
    assert "B Journal · 2022" in article["display_text"] and article["start_year"] == 2022
    assert next(c for c in chunks.values() if c["type"] == "blog")["url"] == "/blogs.html"

    about = next(c for c in chunks.values() if c["type"] == "about")
    assert 'In his own words on the site: "I build RAG systems."' in about["display_text"]
    contact = next(c for c in chunks.values() if c["type"] == "contact")["display_text"]
    assert "me@example.com" in contact and "98765" not in contact


def test_site_chunks_are_empty_without_a_profile():
    assert site_content.site_chunks() == []


def test_duplicates_link_to_their_knowledge_base_twin(content, kb_chunks):
    chunks = by_id(site_content.link_duplicates(site_content.site_chunks(), kb_chunks))
    assert chunks[f"site:job#{content['job'].pk}"]["same_as"].startswith("experience#saravana-perumal-r-gen-ai-engineer")
    assert chunks[f"site:project#{content['project'].pk}"]["same_as"] == \
        "projects#saravana-perumal-rs-project-hybrid-search-rag-with-pinecone"
    assert "same_as" not in next(c for c in chunks.values() if c["type"] == "blog")


def test_retrieval_and_lists_keep_one_chunk_per_record(content, kb_chunks):
    store = make_fake_store(rag_index.local_chunks())
    project = f"site:project#{content['project'].pk}"
    twin = store.chunks[[c["chunk_id"] for c in store.chunks].index(project)]["same_as"]
    ids = [c["chunk_id"] for c in store.chunks]
    picked = [store.chunks[p]["chunk_id"] for p in cap_faq([ids.index(twin), ids.index(project)] + list(range(6)), store)]
    assert twin in picked and project not in picked

    listed = [r["chunk_id"] for r in list_by_type(store, "project")]
    assert project in listed and twin not in listed
    assert len(listed) == len({store.chunks[ids.index(i)].get("same_as") or i for i in listed})


def test_sources_use_the_site_chunk_page_and_label(content):
    store = make_fake_store(site_content.site_chunks())
    pos = next(i for i, c in enumerate(store.chunks) if c["chunk_id"].startswith("site:blogpost#"))
    sources = answer_sources([{"pos": pos, "chunk_id": "x", "score": 6.0, "dense": 0.0}],
                             {"intent": "lookup", "fallback": False}, threshold=2.0, store=store)
    assert sources == [{"section": "Blog", "url": "/blogs.html", "item": "AI PCs"}]


def test_admin_edit_refreshes_the_live_index_embedding_only_changed_chunks(content, monkeypatch, tmp_path):
    embedded = []

    def fake_embed(texts):
        embedded.extend(texts)
        return np.ones((len(texts), 8), dtype="float32")

    monkeypatch.setattr(rag_index, "embed_documents", fake_embed)
    monkeypatch.setattr(rag_index, "INDEX_DIR", tmp_path)
    monkeypatch.setattr(rag_index, "save_index", lambda store, index_dir=None: None)
    rag_index.reset_store()
    try:
        rag_index._store = rag_index.build_store(rag_index.local_chunks())
        rag_index._checked_at = rag_index.time.monotonic()
        embedded.clear()

        job = content["job"]
        job.title = "Lead Gen AI Engineer"
        job.save()  # the post_save signal makes the next get_store() re-check
        store = rag_index.get_store()

        assert by_id(store.chunks)[f"site:job#{job.pk}"]["label"] == "Lead Gen AI Engineer"
        assert len(embedded) == 1 and embedded[0].startswith("Saravana Perumal R, Lead Gen AI Engineer")
    finally:
        rag_index.reset_store()
