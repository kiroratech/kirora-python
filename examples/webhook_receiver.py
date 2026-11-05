"""A webhook endpoint using only the standard library.

    KIRORA_WEBHOOK_SECRET=whsec_... python examples/webhook_server.py

It verifies each delivery against the raw body, skips events it has already handled,
and answers 2xx only once an event's work has succeeded, so a failure is delivered again.
Point a Kirora webhook at http://<host>:8000/webhooks/kirora, or send a test event.
"""

from __future__ import annotations

import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Set

import kirora

SECRET = os.environ["KIRORA_WEBHOOK_SECRET"]
# Use your database in production, so deduplication survives restarts.
handled: Set[str] = set()


def handle(event_type: str, payload: dict) -> None:  # type: ignore[type-arg]
    print("Handling", event_type, payload.get("eventId"))


class Handler(BaseHTTPRequestHandler):
    def do_POST(self) -> None:
        if self.path != "/webhooks/kirora":
            self.send_error(404)
            return
        raw_body = self.rfile.read(int(self.headers.get("content-length") or 0))
        verified = kirora.Webhooks.verify(SECRET, raw_body, self.headers)
        if verified is None:
            self.send_error(400, "Invalid webhook")
            return
        event_id = verified.headers.event_id
        if event_id not in handled:
            try:
                handle(verified.headers.event, verified.payload)
            except Exception:
                self.send_error(500)  # Kirora delivers it again.
                return
            handled.add(event_id)
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    print("Listening on http://localhost:8000/webhooks/kirora")
    HTTPServer(("", 8000), Handler).serve_forever()
