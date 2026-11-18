import threading

from django.core.management.base import BaseCommand

from chatbot.mcp_server import build_server
from chatbot.rag.index import warm_up


class Command(BaseCommand):
    help = ("Runs an MCP server over the portfolio (search, list and read records; optionally ask V.E.R.A.). "
            "stdio for Claude Desktop / Claude Code, http (streamable HTTP at /mcp) for a remote connector.")
    # stdio: stdout carries the protocol, so nothing else may print there (checks would write to it)
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--transport", choices=("stdio", "http"), default="stdio")
        parser.add_argument("--host", default="127.0.0.1", help="http only (default 127.0.0.1)")
        parser.add_argument("--port", type=int, default=8765, help="http only (default 8765)")
        ask = parser.add_mutually_exclusive_group()
        ask.add_argument("--ask-vera", dest="ask_vera", action="store_true", default=None,
                         help="Expose ask_vera (makes OpenAI calls). Default: on for stdio, off for http.")
        ask.add_argument("--no-ask-vera", dest="ask_vera", action="store_false")

    def handle(self, *args, transport, host, port, ask_vera, **options):
        if ask_vera is None:
            ask_vera = transport == "stdio"
        server = build_server(enable_ask_vera=ask_vera)
        # Load the index and models while the client connects, so the first tool call doesn't wait ~20s
        threading.Thread(target=warm_up, name="mcp-warm-up", daemon=True).start()
        if transport == "stdio":
            server.run("stdio")
        else:
            self.stderr.write(f"MCP server on http://{host}:{port}/mcp (ask_vera {'on' if ask_vera else 'off'})")
            server.run("streamable-http", host=host, port=port)
