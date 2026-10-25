"""
Retrieval chunks from the website's own content: the portfolio models edited in Django admin.

One record (a job, a project, a publication, a blog post, ...) = one chunk, so the index follows what
visitors see on the site, and admin edits change the manifest, which marks the index stale. Each chunk
carries the page it appears on (`url`) and a short record label (`label`) for the widget's source chips.

Chunk ids are `site:<model>#<pk>`, stable across edits, so an edited record is re-embedded alone. Text
the site writes in the first person (bio, intro, teaching) is introduced as Saravana's own words, so the
model keeps talking about him in the third person.

Projects, jobs and degrees are also described (at more length) in knowledge_base/. `link_duplicates`
pairs each such site chunk with its knowledge-base twin, and retrieval keeps only one of a pair.
"""
import html
import re
import unicodedata

from django.utils.html import strip_tags

from chatbot.rag.ingest import make_chunk, tokenize

SOURCE = "site"
NAME = "Saravana Perumal R"

PAGES = {
    "about": "/bio.html",
    "skill": "/skills.html",
    "experience": "/experience.html",
    "education": "/education.html",
    "certification": "/education.html",
    "project": "/projects.html",
    "publication": "/publications.html",
    "teaching": "/workshops.html",
    "focus": "/summary.html",
    "language": "/languages.html",
    "media": "/gallery.html",
    "blog": "/blogs.html",
    "contact": "/contact.html",
}

# "Apr 2026 – Present" -> "Apr 2026 to Present", which ingest.parse_period understands
_RANGE_DASH = re.compile(r"\s*[–—-]\s*(?=(?:\w+\s+)?(?:\d{4}|present)\b)", re.I)
_TITLE_YEARS = re.compile(r"\((\d{4}(?:\s*[–—-]\s*\d{4})?)\)\s*$")
# Containment of a site title's tokens in a knowledge-base heading needed to call them the same record
DUPLICATE_CONTAINMENT = 0.8


def _clean(text):
    text = html.unescape(strip_tags(re.sub(r"<br\s*/?>", " ", str(text or ""))))
    # Section headings can still carry emoji ("🤖 AI & Data Science"); replies are plain text
    text = "".join(ch for ch in text if unicodedata.category(ch) != "So")
    return " ".join(text.split())


def _period(text):
    text = _clean(text)
    return _RANGE_DASH.sub(" to ", text) if text else None


def _tags(raw):
    return [t.strip() for t in str(raw or "").split(",") if t.strip()]


def _lines(parts):
    """Body lines from strings (cleaned) and lists of already-formatted lines; blanks dropped."""
    lines = []
    for part in parts:
        lines += part if isinstance(part, list) else [_clean(part)]
    return "\n".join(line for line in lines if line)


def _chunk(model, pk, chunk_type, label, heading, body, *, period=None, tags=(), organization="none"):
    body = _lines(body)
    url = PAGES[chunk_type]
    chunk = make_chunk(
        f"{SOURCE}:{model}#{pk}", chunk_type, f"{heading}\n\n{body}",
        organization=organization, source_file=SOURCE, period=period, tags=tags,
        raw_meta=f"{url}|{label}|{period}|{','.join(tags)}",
    )
    chunk.update(url=url, label=_clean(label))
    return chunk


def _first_person(text):
    text = _clean(text)
    return f"In his own words on the site: \"{text}\"" if text else ""


def _bullets(items):
    return [f"- {_clean(i)}" for i in items if _clean(i)]


def profile_chunks(profile):
    from portfolio.models import BioSection
    chunks = []
    roles = ", ".join(r.name for r in profile.roles.all())
    metrics = "; ".join(f"{m.value} {m.label}" for m in profile.metrics.all())
    chunks.append(_chunk("profile", profile.pk, "about", "Overview", f"{NAME}: overview from his website", [
        f"{profile.tagline}. {profile.tagline_sub}." if profile.tagline else "",
        f"Roles: {roles}." if roles else "",
        f"At a glance: {metrics}." if metrics else "",
        f"Based in {profile.location}." if profile.location else "",
        _first_person(profile.intro),
    ]))

    # The phone / WhatsApp number is left out on purpose: V.E.R.A. never gives out a phone number
    links = [(label, value) for label, value in (
        ("Email", profile.email), ("Location", profile.location), ("GitHub", profile.github),
        ("LinkedIn", profile.linkedin), ("Medium", profile.medium), ("Instagram", profile.instagram),
        ("ResearchGate", profile.researchgate), ("ORCID", profile.orcid),
    ) if value]
    if links:
        chunks.append(_chunk("contact", profile.pk, "contact", "Contact details",
                             f"How to contact {NAME}", [f"{k}: {v}" for k, v in links]))

    bio = BioSection.objects.filter(profile=profile).first()
    if bio:
        paragraphs = [_first_person(p.text) for p in bio.paragraphs.all()]
        if any(paragraphs):
            chunks.append(_chunk("journey", bio.pk, "about", bio.journey_title or bio.journey_label,
                                 f"{NAME}'s professional journey: {_clean(bio.journey_title)}", paragraphs))
        strengths = [f"- {s.title}: {_clean(s.description)}" for s in bio.strengths.all()]
        if strengths:
            chunks.append(_chunk("strengths", bio.pk, "about", "Strengths", f"{NAME}'s strengths",
                                 [strengths]))
        if bio.teaching_description:
            chunks.append(_chunk("bio-teaching", bio.pk, "teaching", bio.teaching_label,
                                 f"{NAME}'s teaching and mentorship: {_clean(bio.teaching_title)}",
                                 [_first_person(bio.teaching_description)]))
    return chunks


def skill_chunks(profile):
    chunks = []
    for category in profile.skill_categories.prefetch_related("skills"):
        lines = [f"- {s.name}" + (f" ({s.context})" if s.context else "") for s in category.skills.all()]
        if lines:
            chunks.append(_chunk("skillcategory", category.pk, "skill", f"Skills: {category.name}",
                                 f"{NAME}'s skills in {_clean(category.name)}", [lines],
                                 tags=[s.name for s in category.skills.all()]))
    return chunks


def experience_chunks(page):
    chunks = []
    for section in page.sections.prefetch_related("jobs"):
        for job in section.jobs.all():
            chunks.append(_chunk("job", job.pk, "experience", job.title,
                                 f"{NAME}, {job.title} at {job.company} ({_period(job.period)})",
                                 [job.description, f"Section: {section.heading}.",
                                  f"Skills: {', '.join(job.tag_list)}." if job.tag_list else ""],
                                 period=_period(job.period), tags=job.tag_list, organization=job.company))
    return chunks


def project_chunks(page):
    chunks = []
    for project in page.projects.select_related("category"):
        years = _TITLE_YEARS.search(project.title)
        links = [f"{k}: {v}" for k, v in (("Code", project.github_url), ("Demo", project.demo_url))
                 if v and v != "#"]
        chunks.append(_chunk("project", project.pk, "project", _TITLE_YEARS.sub("", project.title).strip(),
                             f"{NAME}'s project: {project.title}", [
                                 project.description,
                                 "Featured project." if project.featured else
                                 f"Category: {project.category.heading}." if project.category else "",
                                 f"Tools and topics: {', '.join(project.tag_list)}." if project.tag_list else "",
                                 *links,
                             ], period=_period(years.group(1)) if years else "not specified",
                             tags=project.tag_list))
    return chunks


def education_chunks(page):
    chunks = [
        _chunk("degree", d.pk, "education", d.degree, f"{NAME}'s {d.degree} from {d.school} ({_period(d.year)})",
               [d.detail], period=_period(d.year), organization=d.school)
        for d in page.degrees.all()
    ]
    chunks += [_chunk("certification", c.pk, "certification", c.name, f"{NAME}'s certification: {c.name}",
                      [c.detail]) for c in page.certifications.all()]
    return chunks


def publication_chunks(page):
    chunks = []
    for model, kind, items in (("article", "Research article", page.research_articles.all()),
                               ("chapter", "Book chapter", page.book_chapters.all())):
        for item in items:
            chunks.append(_chunk(model, item.pk, "publication", item.title,
                                 f"{NAME}'s publication: {item.title}" + (f" ({item.year})" if item.year else ""), [
                                     f"{item.label or kind}.", item.summary, item.meta,
                                     f"Topics: {', '.join(item.tag_list)}." if item.tag_list else "",
                                     f"DOI: {item.doi}" if item.doi else "",
                                 ], period=str(item.year) if item.year else "not specified", tags=item.tag_list))
    chunks += [_chunk("achievement", a.pk, "publication", a.title, f"{NAME}'s achievement: {a.title}",
                      [a.description]) for a in page.achievements.all()]
    return chunks


def workshop_chunks(page):
    return [
        _chunk(model, item.pk, "teaching", item.title, f"{kind} by {NAME}: {item.title}", [item.description])
        for model, kind, items in (("workshop", "Workshop", page.workshops.all()),
                                   ("seminar", "Talk", page.seminars.all()))
        for item in items
    ]


def focus_chunks(page):
    chunks = [_chunk("focus", c.pk, "focus", c.title, f"{NAME}'s current focus: {c.title}", [c.description])
              for c in page.cards.all()]
    entries = _bullets(e.text for e in page.positioning_entries.all())
    if entries or page.positioning_tagline:
        chunks.append(_chunk("positioning", page.pk, "focus", "Positioning", f"How {NAME} positions his work",
                             [entries, page.positioning_tagline]))
    return chunks


def language_chunks(page):
    spoken = [f"- {s.name}: {s.proficiency}" for s in page.spoken.all()]
    programming = [f"- {p.name}: {p.proficiency}" for p in page.programming.all()]
    if not (spoken or programming):
        return []
    return [_chunk("languages", page.pk, "language", "Languages", f"Languages {NAME} speaks and programs in", [
        "Spoken languages:" if spoken else "", spoken, "Programming languages:" if programming else "", programming,
    ])]


def gallery_chunks(page):
    chunks = [_chunk("video", v.pk, "media", v.title, f"Video by {NAME}: {v.title}",
                     [f"{v.category}, {v.duration}." if v.duration else f"{v.category}.", v.description])
              for v in page.videos.all()]
    reels = _bullets(r.title for r in page.reels.all())
    if reels:
        chunks.append(_chunk("reels", page.pk, "media", "Instagram reels", f"{NAME}'s Instagram reels",
                             ["Short videos on the gallery page:", reels]))
    return chunks


def blog_chunks(page):
    posts = list(page.posts.all())
    if not posts:
        return []
    stats = "; ".join(f"{k}: {_clean(v)}" for k, v in (
        ("Posts", page.stats_total_posts), ("Platform", page.stats_platform), ("Topics", page.stats_topics)) if v)
    # So "does he write a blog?" finds the blog itself, not only one post that happens to match
    overview = _chunk("blogpage", page.pk, "blog", "Blog", f"{NAME}'s blog: the articles he writes", [
        page.page_sub, f"{stats}." if stats else "", "Posts:", _bullets(f"{p.title} ({p.date})" for p in posts),
    ], tags=["blog", "blog posts", "articles", "writing", page.stats_platform])
    return [overview] + [
        _chunk("blogpost", p.pk, "blog", p.title, f"Blog post by {NAME}: {p.title} ({p.date})", [
            f"{p.category}, {p.read_time}.", p.excerpt,
            f"Tags: {', '.join(p.tag_list)}." if p.tag_list else "", f"Read on Medium: {p.medium_url}",
        ], period=_clean(p.date) or "not specified", tags=p.tag_list)
        for p in posts
    ]


PAGE_BUILDERS = (
    ("experience_page", experience_chunks), ("project_page", project_chunks),
    ("education_page", education_chunks), ("publications_page", publication_chunks),
    ("workshops_page", workshop_chunks), ("focus_page", focus_chunks), ("languages_page", language_chunks),
    ("gallery_page", gallery_chunks), ("blog_page", blog_chunks),
)


def site_chunks():
    """Chunks for every page's content in the database. Empty when there is no profile or no tables yet."""
    from portfolio.models import UserProfile
    try:
        profile = UserProfile.objects.first()
        if profile is None:
            return []
        chunks = profile_chunks(profile) + skill_chunks(profile)
        for attr, build in PAGE_BUILDERS:
            page = getattr(profile, attr, None)  # a missing page raises RelatedObjectDoesNotExist
            if page is not None:
                chunks += build(page)
    except Exception:  # tables not migrated yet, or no database access (tests)
        return []
    return chunks


# ─── Duplicates of knowledge-base records ───────────────────────────

# The site abbreviates degree names that the knowledge base spells out
_ABBREVIATIONS = {"m.sc": "master science", "b.sc": "bachelor science"}


def _title_tokens(text):
    tokens = tokenize(re.sub(r"[^\w\s.-]", " ", text))
    return set(" ".join(_ABBREVIATIONS.get(t, t) for t in tokens).split())


def link_duplicates(site, kb):
    """
    Set `same_as` on each site project / job / degree to the knowledge-base chunk describing the same
    record: the one whose heading contains most of the site title's words (ties go to the closer heading).
    """
    headings = [(c, _title_tokens(c["display_text"].split("\n", 1)[0])) for c in kb
                if c["type"] in ("project", "experience", "education") and not c["is_faq"]]
    for chunk in site:
        if chunk["type"] not in ("project", "experience", "education"):
            continue
        title = _title_tokens(chunk["label"])
        if not title:
            continue
        best, best_key = None, (0, 0)
        for candidate, heading in headings:
            if candidate["type"] != chunk["type"]:
                continue
            key = (len(title & heading) / len(title), len(title & heading) / len(title | heading))
            if key > best_key:
                best, best_key = candidate, key
        if best is not None and best_key[0] >= DUPLICATE_CONTAINMENT:
            chunk["same_as"] = best["chunk_id"]
    return site
