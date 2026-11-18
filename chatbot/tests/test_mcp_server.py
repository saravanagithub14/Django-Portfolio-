import asyncio
import json

import pytest
from mcp.server.mcpserver.exceptions import ToolError

from chatbot import mcp_server
from chatbot.rag import index as rag_index

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def use_fake_store(monkeypatch, fake_store):
    monkeypatch.setattr(rag_index, "get_store", lambda: fake_store)
    monkeypatch.setenv("RAG_RERANKER", "1")
    return fake_store


def tool_names(server):
    return {t.name for t in asyncio.run(server.list_tools())}


def test_ask_vera_is_optional():
    read_only = {"portfolio_overview", "search_portfolio", "list_portfolio_records", "get_portfolio_record"}
    assert tool_names(mcp_server.build_server(enable_ask_vera=False)) == read_only
    assert tool_names(mcp_server.build_server()) == read_only | {"ask_vera"}


def test_overview_counts_sections_without_faq(fake_store):
    overview = mcp_server.portfolio_overview()
    assert overview["sections"]["project"] == sum(
        1 for c in fake_store.chunks if c["type"] == "project" and not c["is_faq"])
    assert overview["faq_entries"] == sum(1 for c in fake_store.chunks if c["is_faq"])


def test_search_filters_by_section_and_year(fake_store):
    results = mcp_server.search_portfolio("teaching", section="teaching", year=2019)["results"]
    assert results and all(r["section"] == "teaching" for r in results)
    for r in results:
        c = next(c for c in fake_store.chunks if c["chunk_id"] == r["id"])
        assert c["start_year"] <= 2019 <= (c["end_year"] or c["start_year"])
        assert r["page_url"].endswith("/workshops.html") and r["page_url"].startswith("http")
    assert mcp_server.search_portfolio("   ")["results"] == []


def test_list_and_get_record():
    listed = mcp_server.list_portfolio_records("project")
    assert listed["count"] == len(listed["records"]) > 0
    first = listed["records"][0]
    full = mcp_server.get_portfolio_record(first["id"])
    assert full["id"] == first["id"] and len(full["text"]) >= len(first["text"])
    assert "…" not in full["title"]
    with pytest.raises(ToolError, match="No portfolio record"):
        mcp_server.get_portfolio_record("missing#id")


def test_ask_vera_rejects_bad_messages():
    with pytest.raises(ToolError):
        mcp_server.ask_vera("  ")
    with pytest.raises(ToolError):
        mcp_server.ask_vera("x" * (mcp_server.MAX_MESSAGE_CHARS + 1))


# ─── /mcp on the website (streamable HTTP through Django) ───────────────

MCP_HEADERS = {"HTTP_ACCEPT": "application/json, text/event-stream", "HTTP_MCP_PROTOCOL_VERSION": "2025-06-18"}


@pytest.fixture
def mcp_client(client, monkeypatch):
    from django.core.cache import cache

    from chatbot import mcp_http
    monkeypatch.setattr(mcp_http, "_server", None)
    monkeypatch.delenv("MCP_ASK_VERA", raising=False)
    cache.clear()

    def rpc(method, params=None, request_id=1, **extra):
        body = {"jsonrpc": "2.0", "method": method, **({"params": params} if params is not None else {})}
        if request_id is not None:
            body["id"] = request_id
        return client.post("/mcp", data=json.dumps(body), content_type="application/json", **MCP_HEADERS, **extra)
    yield rpc
    cache.clear()


def test_http_handshake_and_tools_without_ask_vera(mcp_client):
    init = mcp_client("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                     "clientInfo": {"name": "test", "version": "1"}})
    assert init.status_code == 200
    assert init.json()["result"]["serverInfo"]["name"] == "saravana-portfolio"
    assert mcp_client("notifications/initialized", request_id=None).status_code == 202
    tools = {t["name"] for t in mcp_client("tools/list").json()["result"]["tools"]}
    assert "search_portfolio" in tools and "ask_vera" not in tools


def test_http_tool_call_and_rate_limit(mcp_client, monkeypatch):
    from chatbot import mcp_http
    monkeypatch.setattr(mcp_http, "TOOL_CALLS_PER_MINUTE", 2)
    call = {"name": "search_portfolio", "arguments": {"query": "teaching", "section": "teaching"}}
    first = mcp_client("tools/call", call).json()["result"]
    assert not first.get("isError") and "workshops" in first["content"][0]["text"]
    assert mcp_client("tools/call", call).status_code == 200
    assert mcp_client("tools/call", call).status_code == 429
    assert mcp_client("tools/list").status_code == 200  # only tool calls count


def test_http_rejects_get_and_bad_json(client):
    assert client.get("/mcp").status_code == 405
    bad = client.post("/mcp", data="not json", content_type="application/json", **MCP_HEADERS)
    assert bad.status_code == 400 and bad.json()["error"]["code"] == -32700
