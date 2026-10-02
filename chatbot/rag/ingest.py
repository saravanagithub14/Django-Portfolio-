"""
Turns the Markdown knowledge base (plus GitHub repos and ContextSnippet rows) into retrieval chunks.

One `## ` section = one chunk. Each section must start with a YAML block:

    ## <heading>

    ---
    type: experience
    organization: Dexpro Innovations Pvt Ltd
    period: April 2025 to March 2026
    tags: [python, rag]
    ---

    <body>
"""
import datetime
import hashlib
import re
from pathlib import Path

import yaml
from django.conf import settings
from django.utils.text import slugify

from chatbot.rag.prompts import CONTACT_EMAIL

KB_DIR = Path(settings.BASE_DIR) / "knowledge_base"
FAQ_FILE_STEM = "faq"

# The knowledge base still carries an old address; answers must use the current one.
OUTDATED_EMAILS = ("mynamesaravanaperumal@gmail.com",)

_SECTION_RE = re.compile(r"^## ", re.M)
_YAML_RE = re.compile(r"\A\s*---[ \t]*\n(.*?)\n---[ \t]*(?:\n|\Z)", re.S)
_YEAR_RE = re.compile(r"\b(?:19|20)\d{2}\b")

# Keeps hyphenated / dotted / alphanumeric terms intact: ugc-net, llama3, qlora, pictor-v2, gpt-4o
_TOKEN_RE = re.compile(r"[a-z0-9]+(?:[-.][a-z0-9]+)*")
_STOPWORDS = frozenset(
    "a an and are as at be by did do does for from had has have he her his how i in is it its me my "
    "of on or s saravana saravana's perumal r that the their there this to was were what when where "
    "which who why will with you your".split()
)


class KnowledgeBaseError(ValueError):
    """A knowledge base section is malformed. Raised loudly so a bad file never ships."""


def tokenize(text):
    return [t for t in _TOKEN_RE.findall(text.lower()) if t not in _STOPWORDS]


def parse_period(period, current_year=None):
    """
    'April 2025 to March 2026' -> (2025, 2026); '2019' -> (2019, 2019); 'X to present' -> (X, now);
    'not specified' -> (None, None); '2024 and not specified' -> (2024, None); 'present' -> (now, now).
    """
    current_year = current_year or datetime.date.today().year
    text = str(period).strip().lower()

    def year_of(part):
        part = part.strip()
        if part == "present":
            return current_year
        match = _YEAR_RE.search(part)
        return int(match.group()) if match else None

    for sep in (" to ", " and "):
        if sep in text:
            start, end = text.split(sep, 1)
            return year_of(start), year_of(end)
    year = year_of(text)
    return year, year


def _hash(*parts):
    return hashlib.sha256("\n".join(parts).encode("utf-8")).hexdigest()


def _normalize_contact(text):
    for old in OUTDATED_EMAILS:
        text = text.replace(old, CONTACT_EMAIL)
    return text


def make_chunk(chunk_id, chunk_type, text, *, organization="none", source_file, period=None,
               tags=(), embed_text=None, raw_meta=""):
    start_year, end_year = parse_period(period) if period is not None else (None, None)
    tags = [str(t).strip() for t in tags or () if str(t).strip()]
    return {
        "chunk_id": chunk_id,
        "type": chunk_type,
        "organization": organization,
        "source_file": source_file,
        "period": str(period) if period is not None else None,
        "start_year": start_year,
        "end_year": end_year,
        "tags": tags,
        "is_faq": Path(source_file).stem == FAQ_FILE_STEM,
        # Text given to the LLM (and the reranker). For FAQ chunks this is question + answer.
        "display_text": text,
        # Text that is embedded. FAQ chunks embed only the question.
        "embed_text": embed_text or text,
        "bm25_text": " ".join([text, " ".join(tags)]).lower(),
        # Covers the metadata too, so editing a period or tag also triggers a rebuild
        "content_hash": _hash(text, raw_meta),
    }


def parse_markdown_file(path):
    path = Path(path)
    content = path.read_text(encoding="utf-8")
    sections = _SECTION_RE.split(content)[1:]  # [0] is the file's H1 preamble
    chunks = []
    for section in sections:
        heading, _, rest = section.partition("\n")
        heading = heading.strip()
        where = f"{path.name}: '## {heading}'"

        match = _YAML_RE.match(rest)
        if not match:
            raise KnowledgeBaseError(f"{where} has no YAML metadata block (--- ... ---) right after the heading")
        raw_meta = match.group(1)
        try:
            meta = yaml.safe_load(raw_meta) or {}
        except yaml.YAMLError as e:
            raise KnowledgeBaseError(f"{where} has invalid YAML: {e}") from e
        for key in ("type", "period"):
            if meta.get(key) in (None, ""):
                raise KnowledgeBaseError(f"{where} is missing '{key}' in its YAML block")

        body = rest[match.end():].strip()
        text = _normalize_contact(f"{heading}\n\n{body}")
        tags = meta.get("tags") or []
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.strip("[]").split(",")]

        is_faq = path.stem == FAQ_FILE_STEM
        chunks.append(make_chunk(
            f"{path.stem}#{slugify(heading)}",
            str(meta["type"]).strip(),
            text,
            organization=str(meta.get("organization") or "none").strip(),
            source_file=path.name,
            period=meta["period"],
            tags=tags,
            embed_text=heading if is_faq else None,
            raw_meta=raw_meta,
        ))
    return chunks


def load_knowledge_base(kb_dir=KB_DIR):
    kb_dir = Path(kb_dir)
    files = sorted(kb_dir.glob("*.md"))
    if not files:
        raise KnowledgeBaseError(f"No knowledge base files found in {kb_dir}")
    chunks = [c for f in files for c in parse_markdown_file(f)]
    seen = set()
    for c in chunks:
        if c["chunk_id"] in seen:
            raise KnowledgeBaseError(f"Duplicate chunk_id {c['chunk_id']} (two sections share a heading)")
        seen.add(c["chunk_id"])
    return chunks


def github_chunks(repos):
    """One chunk per repo: name, description, language."""
    chunks = []
    for repo in repos:
        name = repo["name"]
        text = (
            f"GitHub repository: {name}\n\n"
            f"Saravana's GitHub repository {name}. Description: {repo.get('description') or 'No description'}. "
            f"Primary language: {repo.get('language') or 'not specified'}."
        )
        chunks.append(make_chunk(f"github#{slugify(name)}", "github", text, source_file="github",
                                 tags=["github", repo.get("language") or ""]))
    return chunks


def snippet_chunks(snippets):
    """Chunks for ContextSnippet rows added through POST /update_context."""
    return [
        make_chunk(f"update#{s.pk}", "update", _normalize_contact(s.text.strip()), source_file="update")
        for s in snippets
    ]


def load_snippets():
    from chatbot.models import ContextSnippet
    try:
        return list(ContextSnippet.objects.order_by("pk"))
    except Exception:  # table not migrated yet
        return []
