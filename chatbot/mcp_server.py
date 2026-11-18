"""
MCP server: lets Claude (Desktop, Code, or claude.ai as a custom connector) look up Saravana's portfolio.

The read-only tools reuse V.E.R.A.'s index (knowledge_base/*.md, the site's records, GitHub repos, snippets)
and its hybrid search, so they cost no LLM call: Claude writes the answer from the passages itself.
`ask_vera` runs the whole chatbot pipeline instead (router + agents + OpenAI); it's on for local stdio and off
for HTTP unless asked for, so a public endpoint can't spend the OpenAI key.

Run with `python manage.py mcp_server` (stdio) or `python manage.py mcp_server --transport http`.
"""
import logging
from typing import Annotated, Literal

from django.conf import settings
from mcp.server.mcpserver import MCPServer
from mcp.server.mcpserver.exceptions import ToolError
from mcp.types import ToolAnnotations
from pydantic import Field

from chatbot.rag import index as rag_index
from chatbot.rag.pipeline import TYPE_FILTERS
from chatbot.rag.retrieve import filter_by_year, hybrid_search, list_by_type
from chatbot.rag.sources import SECTIONS

logger = logging.getLogger(__name__)

Section = Literal[TYPE_FILTERS]
MAX_MESSAGE_CHARS = 1000

INSTRUCTIONS = """\
These tools look up Saravana Perumal R's portfolio: his jobs, projects, skills, education, certifications,
publications, teaching (workshops, talks), blog posts, media and contact details. The content is the same
as on his website and in his assistant V.E.R.A.'s knowledge base.

Start with search_portfolio for a specific question, list_portfolio_records to enumerate one section
(e.g. every project), and get_portfolio_record for the full text of one result. Answer from what the
tools return, refer to him as Saravana (he/him, as the records do), and link the page_url of the
records you used. If nothing relevant comes back, say the portfolio doesn't cover it rather than guessing."""

READ_ONLY = ToolAnnotations(read_only_hint=True, idempotent_hint=True, open_world_hint=False)


def page_url(chunk):
    """Absolute site URL of the page a chunk belongs to, or None (live updates have no page)."""
    path = chunk.get("url") or (SECTIONS.get(chunk["type"]) or (None, None))[1]
    return f"{settings.SITE_URL}{path}" if path else None


def title(chunk):
    """The site's label for a record, else its heading (for FAQ chunks, the question)."""
    return chunk.get("label") or chunk["display_text"].split("\n", 1)[0].strip()


def record(chunk, *, text=None, score=None):
    out = {
        "id": chunk["chunk_id"],
        "section": chunk["type"],
        "title": title(chunk),
        "organization": None if chunk.get("organization") in (None, "none") else chunk["organization"],
        "period": None if chunk.get("period") in (None, "not specified") else chunk["period"],
        "page_url": page_url(chunk),
        "text": chunk["display_text"] if text is None else text,
    }
    if score is not None:
        out["relevance"] = score
    return out


def portfolio_overview() -> dict:
    """What the portfolio covers: the site URL and how many records each section has. Call this first if
    you're unsure which section to search or list."""
    store = rag_index.get_store()
    counts = {}
    for c in store.chunks:
        if not c["is_faq"]:
            counts[c["type"]] = counts.get(c["type"], 0) + 1
    return {
        "person": "Saravana Perumal R",
        "site_url": settings.SITE_URL,
        "sections": {s: counts.get(s, 0) for s in TYPE_FILTERS if counts.get(s)},
        "faq_entries": sum(1 for c in store.chunks if c["is_faq"]),
    }


def search_portfolio(
    query: Annotated[str, Field(description="What to look for, as a question or keywords, e.g. "
                                            "'experience with RAG pipelines' or 'where did he study'.")],
    section: Annotated[Section | None, Field(description="Only search this section.")] = None,
    year: Annotated[int | None, Field(description="Only records active in this year, e.g. 2021.")] = None,
) -> dict:
    """Search Saravana's portfolio (hybrid semantic + keyword search with reranking) and return the five most
    relevant passages with their section, period and page URL. Higher relevance is better; below about 2
    the match is probably incidental."""
    store = rag_index.get_store()
    query = query.strip()
    if not query:
        return {"results": [], "note": "Empty query."}
    subset = None
    if section or year:
        allowed = set(range(len(store)))
        if section:
            allowed &= {p for p, c in enumerate(store.chunks) if c["type"] == section}
        if year:
            allowed &= set(filter_by_year(store, year))
        subset = sorted(allowed)
    results, _ = hybrid_search(store, query, subset=subset, use_reranker=rag_index.reranker_enabled())
    return {"results": [record(store.chunks[r["pos"]], score=r["score"]) for r in results]}


def list_portfolio_records(
    section: Annotated[Section, Field(description="The section to list.")],
) -> dict:
    """List every record in one section of the portfolio, newest first, as title + one-line summary.
    Use get_portfolio_record with an id for the full text."""
    store = rag_index.get_store()
    rows = list_by_type(store, section)
    return {
        "section": section,
        "count": len(rows),
        "records": [record(store.chunks[r["pos"]], text=r["text"].split("\n", 1)[-1]) for r in rows],
    }


def get_portfolio_record(
    id: Annotated[str, Field(description="A record id from search_portfolio or list_portfolio_records.")],
) -> dict:
    """The full text and details of one portfolio record."""
    store = rag_index.get_store()
    for c in store.chunks:
        if c["chunk_id"] == id:
            return {**record(c), "tags": c.get("tags", [])}
    raise ToolError(f"No portfolio record with id {id!r}. Use search_portfolio to find ids.")


def ask_vera(
    message: Annotated[str, Field(description="A visitor-style question for V.E.R.A., e.g. "
                                              "'What has Saravana built with LLMs?'")],
) -> dict:
    """Ask V.E.R.A., the chatbot on Saravana's website, and get its reply exactly as a visitor would (plain
    text, its own voice), with the agent that answered and the site sections it drew on. It makes an OpenAI
    call, so prefer search_portfolio when you only need the facts."""
    from chatbot.fallback import get_keyword_fallback_response
    from chatbot.llm import is_mock_provider, make_llm
    from chatbot.rag import pipeline
    from chatbot.views import get_active_bot
    from portfolio.models import UserProfile

    message = message.strip()
    if not message:
        raise ToolError("Message is empty.")
    if len(message) > MAX_MESSAGE_CHARS:
        raise ToolError(f"Message is longer than {MAX_MESSAGE_CHARS} characters.")

    bot = get_active_bot()
    model_cfg = bot.model_config if bot else None
    if model_cfg and not is_mock_provider(model_cfg):
        try:
            result = pipeline.run(message, [], make_llm(model_cfg))
        except Exception as e:
            logger.error("ask_vera pipeline error: %s", e, exc_info=True)
            result = None
        if result and result.get("reply"):
            return {"reply": result["reply"], "agent": result["meta"].get("agent"),
                    "sources": result.get("sources", [])}
    # Same as the website: mock provider, or every provider failed
    return {"reply": get_keyword_fallback_response(message, UserProfile.objects.first()),
            "agent": "keyword_fallback", "sources": []}


def build_server(*, enable_ask_vera=True):
    server = MCPServer(
        name="saravana-portfolio",
        title="Saravana Perumal R — Portfolio",
        instructions=INSTRUCTIONS,
        website_url=settings.SITE_URL,
    )
    server.tool(title="Portfolio overview", annotations=READ_ONLY)(portfolio_overview)
    server.tool(title="Search the portfolio", annotations=READ_ONLY)(search_portfolio)
    server.tool(title="List a portfolio section", annotations=READ_ONLY)(list_portfolio_records)
    server.tool(title="Get a portfolio record", annotations=READ_ONLY)(get_portfolio_record)
    if enable_ask_vera:
        server.tool(title="Ask V.E.R.A.", annotations=ToolAnnotations(
            read_only_hint=True, idempotent_hint=False, open_world_hint=True))(ask_vera)
    return server
