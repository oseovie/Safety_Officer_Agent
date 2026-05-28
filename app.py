"""Local web app for the worksite safety officer agent.

Run it with:
    python app.py

Then open:
    http://localhost:8000
"""

from __future__ import annotations

import json
import os
from csv import DictWriter
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from pdf_export import build_pdf
from safety_agent import CHECKLIST, suggest_controls
from risk_engine import (
    RiskInput,
    analytics,
    load_risks,
    log_hazard,
    overdue_open_risks,
    parse_score,
    predictive_jha,
    update_status,
)
from whatsapp_agent import build_whatsapp_reply, extract_text_messages, send_whatsapp_text


ROOT = Path(__file__).parent
STATIC_DIR = ROOT / "static"
HOST = "127.0.0.1"
PORT = 8000
ERROR_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Safety Agent Error</title>
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <main class="error-page">
      <section class="panel error-panel">
        <p class="eyebrow">Safety Agent</p>
        <h1>{title}</h1>
        <p>{message}</p>
        <a class="home-link" href="/">Return to dashboard</a>
      </section>
    </main>
  </body>
</html>
"""
REPORT_PAGE = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Safety Risk Register</title>
    <link rel="stylesheet" href="/styles.css">
  </head>
  <body>
    <main class="print-report">
      <header class="print-header">
        <p class="eyebrow">Risk Management Engine</p>
        <h1>Safety Risk Register</h1>
        <p>Generated from the local safety documentation log.</p>
      </header>
      {rows}
    </main>
  </body>
</html>
"""


def read_json(handler: BaseHTTPRequestHandler) -> dict[str, object]:
    length = int(handler.headers.get("Content-Length", "0"))
    raw_body = handler.rfile.read(length).decode("utf-8")
    if not raw_body:
        return {}
    return json.loads(raw_body)


def html_escape(value: object) -> str:
    return (
        str(value)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#039;")
    )


class SafetyRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/whatsapp/webhook":
            self.verify_whatsapp_webhook()
            return

        if path == "/api/checklist":
            self.send_json({"items": CHECKLIST})
            return

        if path == "/api/risks":
            self.send_json({"risks": load_risks()})
            return

        if path == "/api/analytics":
            self.send_json(analytics())
            return

        if path == "/api/predictive-jha":
            self.send_json({"items": predictive_jha()})
            return

        if path == "/api/capa/overdue":
            self.send_json({"risks": overdue_open_risks()})
            return

        if path == "/export/risks.csv":
            self.send_csv_export()
            return

        if path == "/export/report":
            self.send_print_report()
            return

        if path == "/export/risks.pdf":
            self.send_pdf_export()
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

        if path == "/api/risks":
            self.handle_assessment()
            return

        if path == "/api/risks/status":
            self.handle_status_update()
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
            location = str(payload.get("location", "Unassigned")).strip() or "Unassigned"
            owner = str(payload.get("owner", "Unassigned")).strip() or "Unassigned"
            deadline_hours = payload.get("deadline_hours", 24)
            likelihood = parse_score(payload.get("likelihood"))
            severity = parse_score(payload.get("severity"))

            if not task or not hazard_text or not people:
                self.send_json({"error": "Task, hazard, and people at risk are required."}, 400)
                return

            if "likelihood" in payload and likelihood is None:
                self.send_json({"error": "Likelihood must be a whole number from 1 to 5."}, 400)
                return

            if "severity" in payload and severity is None:
                self.send_json({"error": "Severity must be a whole number from 1 to 5."}, 400)
                return

            if isinstance(deadline_hours, bool) or not isinstance(deadline_hours, int) or deadline_hours < 1:
                self.send_json({"error": "Deadline must be a whole number of hours."}, 400)
                return

            if likelihood is None and severity is not None or likelihood is not None and severity is None:
                self.send_json({"error": "Likelihood and severity must be whole numbers from 1 to 5."}, 400)
                return

            record = log_hazard(
                RiskInput(
                    task=task,
                    hazard=hazard_text,
                    people_at_risk=people,
                    location=location,
                    owner=owner,
                    deadline_hours=deadline_hours,
                    likelihood=likelihood,
                    severity=severity,
                )
            )

            self.send_json(record)
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid assessment data."}, 400)
        except OSError:
            self.send_json({"error": "Risk log storage is unavailable. Try again after file sync completes."}, 500)

    def handle_status_update(self) -> None:
        try:
            payload = read_json(self)
            risk_id = str(payload.get("id", "")).strip()
            status = str(payload.get("status", "")).strip()
            note = str(payload.get("verification_note", "")).strip()
            if not risk_id or not status:
                self.send_json({"error": "Risk id and status are required."}, 400)
                return
            updated = update_status(risk_id, status, note)
            if updated is None:
                self.send_json({"error": "Risk not found or status is invalid."}, 400)
                return
            self.send_json({"risk": updated})
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid status update data."}, 400)
        except OSError:
            self.send_json({"error": "Risk log storage is unavailable. Try again after file sync completes."}, 500)

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
        except OSError:
            self.send_json({"error": "Risk log storage is unavailable. Try again after file sync completes."}, 500)

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
        except OSError:
            self.send_json({"error": "Risk log storage is unavailable. Try again after file sync completes."}, 500)

    def send_json(self, data: dict[str, object], status: int = 200) -> None:
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_csv_export(self) -> None:
        risks = load_risks()
        output = StringIO()
        fields = [
            "id",
            "created_at",
            "status",
            "task",
            "hazard",
            "people_at_risk",
            "location",
            "category",
            "initial_likelihood",
            "initial_severity",
            "initial_score",
            "initial_level",
            "residual_likelihood",
            "residual_severity",
            "residual_score",
            "residual_level",
            "owner",
            "due_at",
            "verification_required",
            "verification_note",
            "closed_at",
        ]
        writer = DictWriter(output, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for risk in risks:
            writer.writerow(risk)
        body = output.getvalue().encode("utf-8-sig")
        self.send_response(200)
        self.send_header("Content-Type", "text/csv; charset=utf-8")
        self.send_header("Content-Disposition", 'attachment; filename="safety-risk-register.csv"')
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_print_report(self) -> None:
        rows = []
        for risk in load_risks():
            rows.append(
                f"""
                <article class="print-risk">
                  <div class="print-risk-head">
                    <h2>{html_escape(risk.get("task", ""))}</h2>
                    <span>{html_escape(risk.get("initial_level", ""))} - {html_escape(risk.get("initial_score", ""))}/25</span>
                  </div>
                  <p><strong>ID:</strong> {html_escape(risk.get("id", ""))}</p>
                  <p><strong>Status:</strong> {html_escape(risk.get("status", ""))}</p>
                  <p><strong>Hazard:</strong> {html_escape(risk.get("hazard", ""))}</p>
                  <p><strong>People at risk:</strong> {html_escape(risk.get("people_at_risk", ""))}</p>
                  <p><strong>Location:</strong> {html_escape(risk.get("location", ""))}</p>
                  <p><strong>Category:</strong> {html_escape(risk.get("category", ""))}</p>
                  <p><strong>Residual risk:</strong> {html_escape(risk.get("residual_score", ""))}/25 ({html_escape(risk.get("residual_level", ""))})</p>
                  <p><strong>Owner:</strong> {html_escape(risk.get("owner", ""))}</p>
                  <p><strong>Due:</strong> {html_escape(risk.get("due_at", ""))}</p>
                  <p><strong>Verification:</strong> {html_escape(risk.get("verification_note", risk.get("verification_required", "")))}</p>
                </article>
                """
            )
        body = REPORT_PAGE.format(rows="\n".join(rows) or "<p>No risks logged.</p>").encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_pdf_export(self) -> None:
        body = build_pdf(load_risks())
        self.send_response(200)
        self.send_header("Content-Type", "application/pdf")
        self.send_header("Content-Disposition", 'attachment; filename="safety-risk-register.pdf"')
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
    main()
