"""WhatsApp adapter for the worksite safety agent."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from safety_agent import CHECKLIST, Hazard, suggest_controls
from risk_engine import RiskInput, log_hazard, overdue_open_risks, update_status


GRAPH_VERSION = os.getenv("WHATSAPP_GRAPH_VERSION", "v20.0")


def build_whatsapp_reply(message: str) -> str:
    text = message.strip()
    lowered = text.lower()

    if not text or lowered in {"help", "menu", "start"}:
        return (
            "Safety Agent commands:\n"
            "1. checklist\n"
            "2. toolbox <topic>\n"
            "3. assess <task> | <hazard> | <people> | <location> | <owner> | <deadline hours>\n"
            "4. close <risk id> | <verification note>\n"
            "5. overdue"
        )

    if lowered == "checklist":
        return "Pre-task checklist:\n" + "\n".join(f"- {item}" for item in CHECKLIST)

    if lowered.startswith("toolbox "):
        topic = text[8:].strip()
        if not topic:
            return "Please send: toolbox <topic>"
        controls = suggest_controls(topic)
        points = [
            f"Toolbox talk: {topic}",
            "What can hurt someone during this task?",
            "Who is exposed and how will controls protect them?",
            *controls[:4],
            "Stop work and report unsafe changes immediately.",
        ]
        return "\n".join(f"- {point}" for point in points)

    if lowered.startswith("assess "):
        return assess_from_message(text[7:].strip())

    if lowered.startswith("close "):
        return close_from_message(text[6:].strip())

    if lowered == "overdue":
        risks = overdue_open_risks()
        if not risks:
            return "No hazards are overdue right now."
        lines = ["Overdue open hazards:"]
        for risk in risks[:8]:
            lines.append(f"- {risk['id']}: {risk['hazard']} at {risk['location']} owner {risk['owner']}")
        return "\n".join(lines)

    return (
        "I can help with site safety. Send 'help', 'checklist', "
        "'toolbox <topic>', 'assess <task> | <hazard> | <people> | <location> | <owner> | <deadline hours>', "
        "or 'close <risk id> | <verification note>'."
    )


def assess_from_message(details: str) -> str:
    parts = [part.strip() for part in details.split("|")]
    if len(parts) != 6:
        return (
            "Use this format:\n"
            "assess <task> | <hazard> | <people at risk> | <location> | <owner> | <deadline hours>"
        )

    task, hazard_text, people, location, owner, deadline_text = parts
    try:
        deadline_hours = int(deadline_text)
    except ValueError:
        return "Deadline must be a whole number of hours."

    if not task or not hazard_text or not people or not location or not owner:
        return "Task, hazard, people at risk, location, and owner are required."

    if deadline_hours < 1:
        return "Deadline must be at least 1 hour."

    risk = log_hazard(
        RiskInput(
            task=task,
            hazard=hazard_text,
            people_at_risk=people,
            location=location,
            owner=owner,
            deadline_hours=deadline_hours,
        )
    )

    controls = "\n".join(
        f"- {control}"
        for control in risk["hierarchy_of_controls"]["engineering"] + risk["hierarchy_of_controls"]["administrative"]
    )
    return (
        f"Risk logged: {risk['id']}\n"
        f"Hazard: {risk['hazard']}\n"
        f"Location: {risk['location']}\n"
        f"Owner: {risk['owner']} due in {risk['deadline_hours']}h\n"
        f"Initial score: {risk['initial_score']} ({risk['initial_level']})\n"
        f"Residual score: {risk['residual_score']} ({risk['residual_level']})\n"
        f"Controls:\n{controls}\n"
        f"Close with: close {risk['id']} | <verification note or photo reference>"
    )


def close_from_message(details: str) -> str:
    parts = [part.strip() for part in details.split("|", 1)]
    if len(parts) != 2:
        return "Use this format: close <risk id> | <verification note or photo reference>"
    risk_id, note = parts
    if not note:
        return "A verification note or photo reference is required to close a hazard."
    updated = update_status(risk_id, "Closed", note)
    if updated is None:
        return "Risk not found. Check the risk id and try again."
    return f"Risk {risk_id} closed. Verification recorded: {note}"


def extract_text_messages(payload: dict[str, object]) -> list[dict[str, str]]:
    messages: list[dict[str, str]] = []

    for entry in payload.get("entry", []):
        for change in entry.get("changes", []):
            value = change.get("value", {})
            for message in value.get("messages", []):
                if message.get("type") != "text":
                    continue
                from_number = str(message.get("from", "")).strip()
                body = str(message.get("text", {}).get("body", "")).strip()
                message_id = str(message.get("id", "")).strip()
                if from_number and body:
                    messages.append({"from": from_number, "body": body, "id": message_id})

    return messages


def send_whatsapp_text(to_number: str, message: str) -> tuple[bool, str]:
    token = os.getenv("WHATSAPP_ACCESS_TOKEN", "").strip()
    phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "").strip()

    if not token or not phone_number_id:
        return False, "WhatsApp credentials are not configured. Reply was generated in dry-run mode."

    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{phone_number_id}/messages"
    body = json.dumps(
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to_number,
            "type": "text",
            "text": {"preview_url": False, "body": message[:4096]},
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 300, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return False, error.read().decode("utf-8")
    except urllib.error.URLError as error:
        return False, str(error)
