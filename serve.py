#!/usr/bin/env python3
"""Local test server for the portfolio.

Why not just double-click index.html? Several pages fetch() the CSVs in data/,
and browsers block fetch() on file:// URLs. Serving over http://localhost
mimics GitHub Pages closely enough to test them.

Usage:  python3 serve.py [port]        (default 8000)
"""
import http.server
import os
import socketserver
import sys

PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
ROOT = os.path.dirname(os.path.abspath(__file__))


class Handler(http.server.SimpleHTTPRequestHandler):
    extensions_map = {
        **http.server.SimpleHTTPRequestHandler.extensions_map,
        ".csv": "text/csv",
        ".svg": "image/svg+xml",
        ".js": "text/javascript",
    }

    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def end_headers(self):
        # No caching, so edits show up on a normal refresh.
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        code = str(args[1]) if len(args) > 1 else ""
        flag = "  <-- MISSING" if code.startswith("4") else ""
        sys.stderr.write("%s %s%s\n" % (self.command, self.path, flag) if not args
                         else "[%s] %s%s\n" % (code, self.path, flag))


class Server(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


if __name__ == "__main__":
    with Server(("127.0.0.1", PORT), Handler) as srv:
        print(f"Serving {ROOT}\nOpen http://localhost:{PORT}/   (Ctrl+C to stop)")
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print("\nStopped.")
