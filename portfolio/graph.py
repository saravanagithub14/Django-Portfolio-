"""
Builds the 3D knowledge-graph data from the site's content models, so anything edited in the admin
(jobs, projects, skills, degrees, publications, talks, focus cards, contact details) shows up in the
graph on the next page load. There is nothing graph-specific to maintain.

Shape (consumed by static/js/graph.js):
    {"id", "name", "type", "navigateTo"?, "description"?, "children"?: [...]}
Top-level ids match each page's `active_page`, which is how graph.js highlights "You are here".
"""
import re

from portfolio.models import (
    BookChapter, Certification, Degree, ExperienceSection, FocusCard, Project, ProjectCategory,
    ResearchArticle, SeminarItem, SkillCategory, UserProfile, WorkshopItem,
)

MAX_LABEL = 48
_LEADING_SYMBOLS = re.compile(r"^[^\w(]+", re.UNICODE)  # emoji / punctuation prefixes like "🤖 " or "⭐ "
_TAGS = re.compile(r"<[^>]+>")


def _clean(text):
    return _LEADING_SYMBOLS.sub("", (text or "").strip()).strip()


def _label(text, limit=MAX_LABEL):
    text = " ".join(_clean(text).split())
    return text if len(text) <= limit else text[:limit - 1].rstrip(" ,;:-–") + "…"


def _node(node_id, name, description="", navigate_to="", children=None, node_type="leaf"):
    node = {"id": node_id, "name": name, "type": node_type}
    if navigate_to:
        node["navigateTo"] = navigate_to
    description = " ".join(_TAGS.sub(" ", description or "").split())
    if description:
        node["description"] = description
    if children:
        node["children"] = children
    return node


def _section(node_id, name, page, description, children):
    """A top-level branch. Kept even when empty so the graph shape stays stable."""
    return _node(node_id, name, description, page, children, node_type="category")


def build_graph():
    profile = UserProfile.objects.prefetch_related("roles").first()
    if profile is None:
        return None

    # Experience: section -> job
    experience = [
        _node(f"exp-section-{s.pk}", _label(s.heading), children=[
            _node(f"job-{j.pk}", _label(f"{j.title} – {j.company}"),
                  " · ".join(filter(None, [j.period, j.tags])))
            for j in s.jobs.all()
        ])
        for s in ExperienceSection.objects.prefetch_related("jobs")
    ]

    # Projects: featured group + one group per category
    def project_node(p):
        return _node(f"project-{p.pk}", _label(p.title), p.tags or p.description[:140])

    featured = [project_node(p) for p in Project.objects.filter(featured=True)]
    projects = ([_node("projects-featured", "Featured Projects", children=featured)] if featured else []) + [
        _node(f"project-cat-{c.pk}", _label(c.heading), children=[project_node(p) for p in c.projects.all()])
        for c in ProjectCategory.objects.prefetch_related("projects")
    ]

    # Skills: category -> skill
    skills = [
        _node(f"skill-cat-{c.pk}", _label(c.name), children=[
            _node(f"skill-{s.pk}", _label(s.name), s.context) for s in c.skills.all()
        ])
        for c in SkillCategory.objects.prefetch_related("skills")
    ]

    # Education: degrees + certifications
    education = [
        _node(f"degree-{d.pk}", _label(d.degree), f"{d.school} ({d.year})") for d in Degree.objects.all()
    ] + [
        _node(f"cert-{c.pk}", _label(c.name), c.detail) for c in Certification.objects.all()
    ]

    # Publications: book chapters + research articles
    publications = [
        _node(f"book-{b.pk}", _label(b.title), f"Book chapter · {b.title}") for b in BookChapter.objects.all()
    ] + [
        _node(f"article-{a.pk}", _label(a.title), f"Research article · {a.title}") for a in ResearchArticle.objects.all()
    ]

    # Workshops & talks
    talks = [
        _node(f"workshop-{w.pk}", _label(w.title), "Workshop") for w in WorkshopItem.objects.all()
    ] + [
        _node(f"seminar-{s.pk}", _label(s.title), "Seminar") for s in SeminarItem.objects.all()
    ]

    # Current focus
    focus = [_node(f"focus-{f.pk}", _label(f.title), f.description[:160]) for f in FocusCard.objects.all()]

    # Contact: only the channels that are filled in
    contact = [
        _node(f"contact-{key}", label)
        for key, label in (
            ("email", profile.email),
            ("github", profile.github.replace("https://", "").replace("www.", "") if profile.github else ""),
            ("linkedin", profile.linkedin.replace("https://", "").replace("www.", "") if profile.linkedin else ""),
            ("medium", f"Medium: {profile.medium_handle}" if profile.medium_handle else ""),
            ("location", profile.location),
        )
        if label
    ]

    sections = [
        _section("experience", "Experience", "experience.html", "Career history across AI, data science, and research", experience),
        _section("projects", "Projects", "projects.html", "AI, ML, and biomedical research projects", projects),
        _section("skills", "Skills", "skills.html", "Technical and research skills", skills),
        _section("education", "Education", "education.html", "Degrees and certifications", education),
        _section("publications", "Publications", "publications.html", "Book chapters and research articles", publications),
        _section("workshops", "Workshops & Talks", "workshops.html", "Workshops and seminars delivered", talks),
        _section("summary", "Current Focus", "summary.html", "What I'm building and thinking about right now", focus),
        _section("contact", "Contact", "contact.html", "Let's connect", contact),
    ]
    roles = " | ".join(r.name for r in profile.roles.all())
    return _node("root", profile.site_title, roles, "#bio-section", sections, node_type="root")
