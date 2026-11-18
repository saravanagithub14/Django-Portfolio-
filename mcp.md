# MCP server

`python manage.py mcp_server` exposes the portfolio to Claude over the Model Context Protocol
(`chatbot/mcp_server.py`, built on the `mcp` 2.x SDK's `MCPServer`).

| Tool | What it does | Cost |
| --- | --- | --- |
| `portfolio_overview` | Site URL and record counts per section | none |
| `search_portfolio(query, section?, year?)` | V.E.R.A.'s hybrid search + rerank; top 5 passages with section, period, page URL | none |
| `list_portfolio_records(section)` | Every record in a section, newest first | none |
| `get_portfolio_record(id)` | Full text of one record | none |
| `ask_vera(message)` | The whole chatbot pipeline (router, agents, guard), reply in V.E.R.A.'s voice | one or two OpenAI calls |

`ask_vera` is on by default for stdio and off for HTTP (`--ask-vera` / `--no-ask-vera` override), so a
public endpoint can't spend the OpenAI key. MCP calls aren't logged to `ChatSession`.

The index and models load in a background thread at start-up (~375MB RSS, like a web worker).

## Claude Code

```bash
claude mcp add saravana-portfolio -- python D:/Repositories/Django_portfolio/manage.py mcp_server
```

## Claude Desktop

Edit `%APPDATA%\Claude\claude_desktop_config.json` (Settings → Developer → Edit Config), then restart
Claude Desktop:

```json
{
  "mcpServers": {
    "saravana-portfolio": {
      "command": "C:\\ProgramData\\anaconda3\\python.exe",
      "args": ["D:\\Repositories\\Django_portfolio\\manage.py", "mcp_server"],
      "env": { "PYTHONIOENCODING": "utf-8" }
    }
  }
}
```

Use the full path to the Python that has the requirements installed. All paths resolve from
`BASE_DIR`, so the working directory doesn't matter.

## claude.ai (remote connector): https://www.saravanar.in/mcp

The website serves MCP itself at `/mcp` (`chatbot/mcp_http.py`): streamable HTTP, stateless, JSON
responses, inside the gunicorn worker so it shares the models the chat already loaded (a second
process would need its own ~375MB). Each POST goes through the SDK's own transport, so protocol
handling stays the SDK's. GET/DELETE get 405 (no SSE stream, no sessions).

In claude.ai: Settings → Connectors → Add custom connector → URL `https://www.saravanar.in/mcp`,
no OAuth. The tools only return what the public site already shows.

- `ask_vera` is off here; set `MCP_ASK_VERA=1` on the server to expose it (it spends the OpenAI key).
- Tool calls are rate-limited to 30/min per IP (`TOOL_CALLS_PER_MINUTE`); initialize/list are free.
- The `mcp` package is imported on the first `/mcp` request (~35MB RSS), not at start-up.
- If Cloudflare's Bot Fight Mode or a WAF challenge is on, skip it for `/mcp`: claude.ai calls the
  connector from Anthropic's servers and can't solve a challenge.

Test it from a terminal:

```bash
curl -X POST https://www.saravanar.in/mcp -H "Content-Type: application/json"   -H "Accept: application/json, text/event-stream"   -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"curl","version":"1"}}}'
```

`python manage.py mcp_server --transport http` still runs a standalone HTTP server (port 8765) for
local testing, or for a host with memory to spare for a second copy of the models.
