import json

import pytest
from django.contrib.auth.models import User

from portfolio.graph import build_graph
from portfolio.models import (
    ExperiencePage, ExperienceSection, Job, Project, ProjectCategory, ProjectPage, Skill, SkillCategory,
    UserProfile,
)

pytestmark = pytest.mark.django_db


@pytest.fixture
def content():
    user = User.objects.create_superuser("owner", "owner@example.com", "a-strong-test-password")
    profile = UserProfile.objects.create(user=user, site_title="Saravana Perumal R.", email="me@example.com",
                                         location="Thiruvananthapuram")
    section = ExperienceSection.objects.create(
        experience_page=ExperiencePage.objects.create(profile=profile), heading="🤖 AI & Data Science")
    job = Job.objects.create(section=section, title="Gen AI Engineer", company="Blackbox Learning",
                             period="Apr 2026 – Present", description="…", tags="GenAI")
    page = ProjectPage.objects.create(profile=profile)
    category = ProjectCategory.objects.create(project_page=page, heading="🔮 Generative AI")
    Project.objects.create(project_page=page, category=category, title="Hybrid Search RAG", description="d")
    Skill.objects.create(category=SkillCategory.objects.create(profile=profile, name="Deep Learning"), name="TensorFlow")
    return {"user": user, "job": job, "page": page}


def flatten(node):
    yield node
    for child in node.get("children", []):
        yield from flatten(child)


def names(graph):
    return {n["name"] for n in flatten(graph)}


def test_graph_is_built_from_content(content):
    graph = build_graph()
    sections = {s["id"]: s for s in graph["children"]}
    assert set(sections) == {"experience", "projects", "skills", "education", "publications", "workshops",
                             "summary", "contact"}
    assert sections["summary"]["navigateTo"] == "summary.html"
    assert {"AI & Data Science", "Gen AI Engineer – Blackbox Learning", "Hybrid Search RAG", "TensorFlow",
            "me@example.com"} <= names(graph)
    ids = [n["id"] for n in flatten(graph)]
    assert len(ids) == len(set(ids)), "node ids must be unique for the 3D graph"


def test_long_labels_are_shortened(content):
    Project.objects.create(project_page=content["page"], featured=True, description="d",
                           title="An extremely long project title that keeps going and going forever")
    label = next(n["name"] for n in flatten(build_graph()) if n["name"].startswith("An extremely"))
    assert len(label) <= 48 and label.endswith("…")


def test_admin_edits_show_up_in_graph(client, content):
    assert client.login(username="owner", password="a-strong-test-password")

    # Edit a job through the admin change form
    job = content["job"]
    response = client.post(f"/admin/portfolio/job/{job.pk}/change/", {
        "section": job.section_id, "title": "Lead Gen AI Engineer", "company": "Blackbox Learning",
        "period": job.period, "description": job.description, "tags": job.tags, "order": 0,
    })
    assert response.status_code == 302, response.content[:500]

    # Add a featured project through the admin add form
    response = client.post("/admin/portfolio/project/add/", {
        "project_page": content["page"].pk, "emoji": "🧠", "title": "Agentic Tutor", "category": "",
        "description": "New project", "tags": "", "github_url": "#", "demo_url": "#", "featured": "on", "order": 0,
    })
    assert response.status_code == 302, response.content[:500]

    graph_names = names(build_graph())
    assert "Lead Gen AI Engineer – Blackbox Learning" in graph_names
    assert "Gen AI Engineer – Blackbox Learning" not in graph_names
    assert "Agentic Tutor" in graph_names


def test_graph_on_pages_reflects_edits(client, content):
    Job.objects.filter(pk=content["job"].pk).update(title="Principal Engineer")
    html = client.get("/experience/").content.decode()
    data = json.loads(html.split("const resumeData = ", 1)[1].split(";\n", 1)[0])
    assert "Principal Engineer – Blackbox Learning" in names(data)


def test_login_shortcut_and_admin_require_auth(client, content):
    assert client.get("/login/")["Location"] == "/admin/"
    response = client.get("/admin/")
    assert response.status_code == 302 and "/admin/login/" in response["Location"]
    assert client.get("/admin/login/").status_code == 200
