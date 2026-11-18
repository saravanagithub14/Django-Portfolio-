"""
The MCP server at /mcp on the website itself (streamable HTTP, stateless, JSON responses), for claude.ai's
custom connectors and any other remote MCP client.

It runs inside the Django worker rather than as a second process: a second process would load its own
copy of the models (~375MB), which doesn't fit beside the site in Render's 512MB. Each POST is handed to
the SDK's own transport (StreamableHTTPSessionManager, stateless) as a one-off ASGI request, so protocol
handling (the initialize handshake, the 2026-07-28 single-exchange revision, header checks, errors) stays
the SDK's. The SDK is imported on the first /mcp request, so the site doesn't carry its ~35MB until then.

ask_vera spends the OpenAI key, so it's off here unless MCP_ASK_VERA=1.
"""
import asyncio
import json
import logging
import threading

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from chatbot.rag.index import env_flag
from chatbot.views import client_ip, is_rate_limited

logger = logging.getLogger(__name__)

PATH = "/mcp"
# Tool calls run the embedder + reranker on a shared CPU; protocol chatter (initialize, tools/list) is free
TOOL_CALLS_PER_MINUTE = 30
REQUEST_TIMEOUT_SECONDS = 100  # under gunicorn's 120s
MAX_BODY_BYTES = 64 * 1024
# Hop-by-hop / length headers that Django sets itself
SKIP_HEADERS = {"content-length", "transfer-encoding", "connection"}

_server = None
_server_lock = threading.Lock()


def get_server():
    global _server
    if _server is None:
        with _server_lock:
            if _server is None:
                from chatbot.mcp_server import build_server
                _server = build_server(enable_ask_vera=env_flag("MCP_ASK_VERA", default=False))
    return _server


def json_rpc_error(code, message, status, request_id=None):
    body = {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}
    return HttpResponse(json.dumps(body), status=status, content_type="application/json")


def tool_call_count(body):
    """How many tools/call requests a POST body carries (0 if it isn't valid JSON: the SDK reports that)."""
    try:
        message = json.loads(body)
    except ValueError:
        return 0
    messages = message if isinstance(message, list) else [message]
    return sum(1 for m in messages if isinstance(m, dict) and m.get("method") == "tools/call")


def asgi_scope(request):
    host = request.get_host()  # validated against ALLOWED_HOSTS
    return {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": request.method,
        "scheme": request.scheme,
        "path": PATH,
        "raw_path": PATH.encode(),
        "root_path": "",
        "query_string": request.META.get("QUERY_STRING", "").encode("latin-1", "replace"),
        "headers": [(k.lower().encode("latin-1", "replace"), v.encode("latin-1", "replace"))
                    for k, v in request.headers.items()],
        "client": (client_ip(request) or "", 0),
        "server": (host.split(":", 1)[0], 443 if request.is_secure() else 80),
    }


async def run_asgi(scope, body):
    """Run one request through the SDK's stateless transport and return (status, headers, body)."""
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.server.transport_security import TransportSecuritySettings

    # Django already checked the Host header; the SDK's own check only knows localhost names
    manager = StreamableHTTPSessionManager(
        app=get_server()._lowlevel_server, stateless=True, json_response=True,
        security_settings=TransportSecuritySettings(enable_dns_rebinding_protection=False),
        max_request_body_size=MAX_BODY_BYTES,
    )
    response = {"status": 500, "headers": [], "body": []}
    done = asyncio.Event()
    sent_body = False

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": body, "more_body": False}
        await done.wait()  # the client "disconnects" only once the response is complete
        return {"type": "http.disconnect"}

    async def send(message):
        if message["type"] == "http.response.start":
            response["status"] = message["status"]
            response["headers"] = message.get("headers", [])
        elif message["type"] == "http.response.body":
            response["body"].append(message.get("body", b""))
            if not message.get("more_body"):
                done.set()

    async with manager.run():
        await asyncio.wait_for(manager.handle_request(scope, receive, send), REQUEST_TIMEOUT_SECONDS)
    return response["status"], response["headers"], b"".join(response["body"])


@csrf_exempt
def mcp_endpoint(request):
    # Stateless and JSON-only: no standalone SSE stream (GET) and no sessions to end (DELETE)
    if request.method != "POST":
        response = HttpResponse(status=405)
        response["Allow"] = "POST"
        return response
    body = request.body
    if len(body) > MAX_BODY_BYTES:
        return json_rpc_error(-32600, "Request body too large", 413)

    calls = tool_call_count(body)
    if calls and any(is_rate_limited(client_ip(request), prefix="mcp_rate", limit=TOOL_CALLS_PER_MINUTE)
                     for _ in range(calls)):
        return json_rpc_error(-32000, "Rate limit exceeded. Please try again in a minute.", 429)

    try:
        status, headers, content = asyncio.run(run_asgi(asgi_scope(request), body))
    except asyncio.TimeoutError:
        return json_rpc_error(-32000, "The request took too long.", 504)
    except Exception as e:
        logger.error("MCP request failed: %s", e, exc_info=True)
        return json_rpc_error(-32603, "Internal error", 500)

    response = HttpResponse(content, status=status)
    for name, value in headers:
        name = name.decode("latin-1")
        if name.lower() not in SKIP_HEADERS:
            response[name] = value.decode("latin-1")
    if not content:
        del response["Content-Type"]
    return response
