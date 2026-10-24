"""Serve the static frontend and proxy API requests to the local Flask app."""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


ROOT = Path(__file__).resolve().parent / "frontend1"
API_ORIGIN = os.getenv(
    "FITNESS_API_ORIGIN",
    f"http://127.0.0.1:{os.getenv('PORT', '5000')}",
).rstrip("/")
FRONTEND_PORT = int(os.getenv("FITNESS_FRONTEND_PORT", "8080"))
PROXY_PATHS = ("/api/", "/session", "/logout")


class FrontendHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def end_headers(self):
        # Avoid stale frontend configuration during local development. This
        # is especially important when API proxy settings change.
        if urlsplit(self.path).path.endswith(".js"):
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def _is_api_request(self):
        path = urlsplit(self.path).path
        return path == "/api" or any(path.startswith(prefix) for prefix in PROXY_PATHS)

    def _proxy(self):
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length else None
        headers = {
            name: self.headers[name]
            for name in (
                "Accept", "Content-Type", "Cookie", "Origin",
                "X-Requested-With", "X-Portal-Role", "X-CSRFToken",
            )
            if self.headers.get(name)
        }
        request = Request(
            API_ORIGIN + self.path,
            data=body,
            headers=headers,
            method=self.command,
        )

        try:
            response = urlopen(request, timeout=30)
        except HTTPError as error:
            response = error
        except URLError as error:
            payload = b'{"success":false,"message":"The API server is unavailable."}'
            self.send_response(502)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            self.log_error("API proxy failed: %s", error.reason)
            return

        with response:
            payload = response.read()
            self.send_response(response.status)
            for name in ("Content-Type", "Content-Length", "Set-Cookie", "Cache-Control"):
                value = response.headers.get(name)
                if value:
                    self.send_header(name, value)
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(payload)

    def do_GET(self):
        self._proxy() if self._is_api_request() else super().do_GET()

    def do_HEAD(self):
        self._proxy() if self._is_api_request() else super().do_HEAD()

    def do_POST(self):
        self._proxy() if self._is_api_request() else self.send_error(405, "Method not allowed")

    def do_PUT(self):
        self._proxy() if self._is_api_request() else self.send_error(405, "Method not allowed")

    def do_PATCH(self):
        self._proxy() if self._is_api_request() else self.send_error(405, "Method not allowed")

    def do_DELETE(self):
        self._proxy() if self._is_api_request() else self.send_error(405, "Method not allowed")

    def do_OPTIONS(self):
        if self._is_api_request():
            self._proxy()
        else:
            self.send_response(204)
            self.end_headers()


if __name__ == "__main__":
    server = ThreadingHTTPServer(("127.0.0.1", FRONTEND_PORT), FrontendHandler)
    print(f"Frontend with API proxy: http://localhost:{FRONTEND_PORT}", flush=True)
    print("Flask API target: http://127.0.0.1:5000", flush=True)
    server.serve_forever()
