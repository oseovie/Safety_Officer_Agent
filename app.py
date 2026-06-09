"""Local web app for the worksite safety officer agent.

Run it with:
    python app.py

Then open:
    http://localhost:8000
"""

from __future__ import annotations

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from safety_agent import CHECKLIST, Hazard, suggest_controls
from whatsapp_agent import build_whatsapp_reply, extract_text_messages, send_whatsapp_text


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
HOST = "127.0.0.1"
PORT = 8000


def html_page(title: str, content: str, css_class: str = "") -> str:
    """Helper to generate HTML page template with consistent boilerplate."""
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>{title}</title>
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <main class="{css_class}">
      {content}
    </main>
  </body>
</html>
"""


ERROR_PAGE = html_page(
    "Safety Agent Error",
    """<section class="panel error-panel">
        <p class="eyebrow">Safety Agent</p>
        <h1>{title}</h1>
        <p>{message}</p>
        <a class="home-link" href="/">Return to dashboard</a>
      </section>""",
    "error-page"
)


def hazard_to_dict(hazard: Hazard) -> dict[str, object]:
    return {
        "task": hazard.task,
        "hazard": hazard.hazard,
        "people_at_risk": hazard.people_at_risk,
        "likelihood": hazard.likelihood,
        "severity": hazard.severity,
        "score": hazard.score,
        "level": hazard.level,
        "action": hazard.action,
        "controls": hazard.controls,
    }


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(length).decode("utf-8")
    if not raw_body:
        return {}
    return json.loads(raw_body)


def parse_score(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value not in range(1, 6):
        return None
    return value


class SafetyRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/whatsapp/webhook":
            self.verify_whatsapp_webhook()
            return

        if path == "/api/checklist":
            self.send_json({"items": CHECKLIST})
            return

        if path == "/":
            self.send_file(STATIC_DIR / "index.html", "text/html; charset=utf-8")
            return

        requested = (STATIC_DIR / path.lstrip("/")).resolve()
        if requested.is_file() and STATIC_DIR.resolve() in requested.parents:
            self.send_file(requested, self.content_type(requested))
            return

        self.send_not_found()

    def do_POST(self) -> None:
        path = urlparse(self.path).path

        if path == "/api/assess":
            self.handle_assessment()
            return

        if path == "/api/toolbox":
            self.handle_toolbox()
            return

        if path == "/api/whatsapp/test":
            self.handle_whatsapp_test()
            return

        if path == "/whatsapp/webhook":
            self.handle_whatsapp_webhook()
            return

        self.send_not_found()

    def do_PUT(self) -> None:
        self.send_method_not_allowed()

    def do_PATCH(self) -> None:
        self.send_method_not_allowed()

    def do_DELETE(self) -> None:
        self.send_method_not_allowed()

    def handle_assessment(self) -> None:
        try:
            payload = read_json(self)
            task = str(payload.get("task", "")).strip()
            hazard_text = str(payload.get("hazard", "")).strip()
            people = str(payload.get("people_at_risk", "")).strip()
            likelihood = parse_score(payload.get("likelihood"))
            severity = parse_score(payload.get("severity"))

            if not task or not hazard_text or not people:
                self.send_json({"error": "Task, hazard, and people at risk are required."}, 400)
                return

            if likelihood is None or severity is None:
                self.send_json({"error": "Likelihood and severity must be whole numbers from 1 to 5."}, 400)
                return

            hazard = Hazard(
                task=task,
                hazard=hazard_text,
                people_at_risk=people,
                likelihood=likelihood,
                severity=severity,
                controls=suggest_controls(f"{task} {hazard_text}"),
            )
            self.send_json(hazard_to_dict(hazard))
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid assessment data."}, 400)

    def handle_toolbox(self) -> None:
        try:
            payload = read_json(self)
            topic = str(payload.get("topic", "")).strip()
            if not topic:
                self.send_json({"error": "Topic is required."}, 400)
                return

            controls = suggest_controls(topic)
            points = [
                f"Today we are discussing: {topic}.",
                "What can hurt someone during this task?",
                "Who is exposed and how will we separate them from the hazard?",
                *controls[:4],
                "Stop work and report changes, near misses, or unsafe conditions immediately.",
            ]
            self.send_json({"topic": topic, "points": points})
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid toolbox data."}, 400)

    def verify_whatsapp_webhook(self) -> None:
        query = parse_qs(urlparse(self.path).query)
        mode = query.get("hub.mode", [""])[0]
        token = query.get("hub.verify_token", [""])[0]
        challenge = query.get("hub.challenge", [""])[0]
        expected_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "").strip()

        if mode == "subscribe" and expected_token and token == expected_token:
            body = challenge.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        self.send_json({"error": "Webhook verification failed."}, 403)

    def handle_whatsapp_webhook(self) -> None:
        try:
            payload = read_json(self)
            replies: list[dict[str, object]] = []

            for message in extract_text_messages(payload):
                reply = build_whatsapp_reply(message["body"])
                sent, result = send_whatsapp_text(message["from"], reply)
                replies.append(
                    {
                        "to": message["from"],
                        "message_id": message["id"],
                        "reply": reply,
                        "sent": sent,
                        "result": result,
                    }
                )

            self.send_json({"status": "received", "processed": len(replies), "replies": replies})
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid WhatsApp webhook data."}, 400)

    def handle_whatsapp_test(self) -> None:
        try:
            payload = read_json(self)
            message = str(payload.get("message", "")).strip()
            if not message:
                self.send_json({"error": "Message is required."}, 400)
                return
            self.send_json({"reply": build_whatsapp_reply(message)})
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid WhatsApp test data."}, 400)

    def send_json(self, data: dict[str, object], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_not_found(self) -> None:
        if urlparse(self.path).path.startswith("/api/"):
            self.send_json({"error": "Endpoint not found."}, 404)
            return
        self.send_error_page(404, "Page not found", "The requested page does not exist.")

    def send_method_not_allowed(self) -> None:
        self.send_json({"error": "Method not allowed. Use GET or POST for this app."}, 405)

    def send_error_page(self, status: int, title: str, message: str) -> None:
        body = ERROR_PAGE.format(title=title, message=message).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_file(self, path: Path, content_type: str) -> None:
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        print(f"{self.address_string()} - {format % args}")

    @staticmethod
    def content_type(path: Path) -> str:
        if path.suffix == ".css":
            return "text/css; charset=utf-8"
        if path.suffix == ".js":
            return "application/javascript; charset=utf-8"
        if path.suffix == ".html":
            return "text/html; charset=utf-8"
        return "application/octet-stream"


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


def main() -> None:
    server = ReusableThreadingHTTPServer((HOST, PORT), SafetyRequestHandler)
    print(f"Safety web app running at http://localhost:{PORT}")
    print("Press Ctrl+C to stop.")
    server.serve_forever()


if __name__ == "__main__":
    main