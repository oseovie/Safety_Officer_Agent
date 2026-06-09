"""Core risk management engine.

The engine stores hazards locally in JSON so the app can track CAPA status
without requiring a database server.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from threading import RLock
from uuid import uuid4


ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
RISK_LOG = DATA_DIR / "risk_log.json"
SCHEDULE_FILE = DATA_DIR / "schedule.json"
CRITICAL_THRESHOLD = 15
DATA_LOCK = RLock()

FATAL_FOUR_KEYWORDS = {
    "Falls": ("fall", "height", "ladder", "roof", "scaffold", "edge", "opening"),
    "Struck-By": ("struck", "dropped", "falling object", "crane", "lift", "suspended", "traffic"),
    "Caught-In/Between": ("caught", "trench", "excavation", "collapse", "pinch", "crush", "shoring"),
    "Electrocution": ("electric", "electrical", "power", "panel", "cable", "energized", "shock"),
}

OTHER_CATEGORIES = {
    "Fire": ("fire", "hot work", "welding", "spark", "combustible"),
    "Chemical": ("chemical", "solvent", "fume", "toxic", "spill", "acid"),
    "Vehicle/Plant": ("vehicle", "forklift", "loader", "excavator", "plant", "reversing"),
    "Ergonomic": ("manual handling", "lifting", "strain", "repetitive"),
    "Housekeeping": ("slip", "trip", "housekeeping", "spill", "debris", "cable"),
}

CONTROL_LIBRARY = {
    "Falls": {
        "elimination": ["Perform the work from ground level where practicable."],
        "substitution": ["Use extendable tools or prefabricated assemblies to reduce work at height."],
        "engineering": ["Install guardrails, covers, toe boards, or certified work platforms."],
        "administrative": ["Use a work-at-height permit, exclusion zone, rescue plan, and competent supervision."],
        "ppe": ["Use inspected harnesses, lanyards, anchor points, helmets, and non-slip footwear."],
    },
    "Struck-By": {
        "elimination": ["Remove overhead work while crews are below."],
        "substitution": ["Use lighter materials or tool tether systems where possible."],
        "engineering": ["Install debris nets, barricades, physical exclusion zones, and lifting restraints."],
        "administrative": ["Sequence work to separate trades and assign a spotter or banksman."],
        "ppe": ["Use hard hats, high-visibility clothing, eye protection, and safety boots."],
    },
    "Caught-In/Between": {
        "elimination": ["Avoid entry into unstable trenches or pinch-point zones until made safe."],
        "substitution": ["Use remote equipment or prefabrication to reduce worker exposure."],
        "engineering": ["Install trench boxes, shoring, machine guards, lockout devices, or barriers."],
        "administrative": ["Use permits, competent-person inspections, and controlled access."],
        "ppe": ["Use helmets, gloves, boots, and task-specific protective clothing."],
    },
    "Electrocution": {
        "elimination": ["De-energize and remove temporary power exposure before work starts."],
        "substitution": ["Use battery-powered tools or lower-voltage systems where suitable."],
        "engineering": ["Install GFCI/RCD protection, covers, cable supports, and physical barriers."],
        "administrative": ["Use lockout/tagout, permits, signage, and authorized electrical workers only."],
        "ppe": ["Use arc-rated PPE, insulated gloves, eye protection, and dielectric footwear as required."],
    },
    "Fire": {
        "elimination": ["Remove ignition sources or combustible materials from the area."],
        "substitution": ["Use cold-work methods or less flammable materials where possible."],
        "engineering": ["Provide fire blankets, spark containment, ventilation, and suitable extinguishers."],
        "administrative": ["Use hot-work permits, fire watch, gas testing, and post-work monitoring."],
        "ppe": ["Use flame-resistant clothing, gloves, eye protection, and respiratory protection if needed."],
    },
    "Chemical": {
        "elimination": ["Remove unnecessary chemicals from the work area."],
        "substitution": ["Choose a less hazardous product or lower-toxicity process."],
        "engineering": ["Use ventilation, closed transfer, bunding, eyewash, and spill containment."],
        "administrative": ["Review SDS, label containers, train workers, and restrict access."],
        "ppe": ["Use chemical gloves, goggles, face shields, coveralls, and respirators as required."],
    },
    "Vehicle/Plant": {
        "elimination": ["Remove pedestrian access from active plant routes."],
        "substitution": ["Use smaller or lower-risk equipment where suitable."],
        "engineering": ["Install barriers, wheel stops, alarms, cameras, and separated walkways."],
        "administrative": ["Set traffic plans, speed limits, spotters, and one-way routes."],
        "ppe": ["Use high-visibility clothing, helmets, and safety boots."],
    },
    "Ergonomic": {
        "elimination": ["Remove unnecessary manual handling."],
        "substitution": ["Use lighter components or preassembled materials."],
        "engineering": ["Use hoists, trolleys, adjustable benches, or mechanical aids."],
        "administrative": ["Rotate tasks, limit lift weights, and train workers in safe handling."],
        "ppe": ["Use grip gloves and supportive footwear where useful."],
    },
    "Housekeeping": {
        "elimination": ["Remove debris, spills, and trailing cables immediately."],
        "substitution": ["Use cordless tools or covered cable routes where possible."],
        "engineering": ["Install cable ramps, drainage, lighting, and stable access surfaces."],
        "administrative": ["Assign cleanup ownership, inspection frequency, and clear access routes."],
        "ppe": ["Use slip-resistant footwear and gloves for cleanup tasks."],
    },
    "Other": {
        "elimination": ["Stop the task until the hazard is clearly understood."],
        "substitution": ["Choose a safer method or material where practicable."],
        "engineering": ["Physically isolate workers from the hazard."],
        "administrative": ["Brief workers, control access, and assign supervision."],
        "ppe": ["Use PPE matched to the hazard as the final layer of protection."],
    },
}


@dataclass(frozen=True)
class RiskInput:
    task: str
    hazard: str
    people_at_risk: str
    location: str
    owner: str
    deadline_hours: int
    likelihood: int | None = None
    severity: int | None = None


def utc_now() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def ensure_data_files() -> None:
    with DATA_LOCK:
        DATA_DIR.mkdir(exist_ok=True)
        if not RISK_LOG.exists():
            RISK_LOG.write_text("[]", encoding="utf-8")
        if not SCHEDULE_FILE.exists():
            SCHEDULE_FILE.write_text(
                json.dumps(
                    [
                        {
                            "date": "tomorrow",
                            "location": "Sector 4",
                            "task": "Steel erection above plumbing trench work",
                            "crew": "Structural / Plumbing",
                        }
                    ],
                    indent=2,
                ),
                encoding="utf-8",
            )


def _read_json_file(filepath: Path) -> list[dict[str, object]]:
    """Read JSON file with thread-safe locking."""
    ensure_data_files()
    with DATA_LOCK:
        return json.loads(filepath.read_text(encoding="utf-8"))


def _write_json_file(filepath: Path, data: list[dict[str, object]]) -> None:
    """Write JSON file with atomic replacement and fallback, thread-safe."""
    ensure_data_files()
    with DATA_LOCK:
        temp_file = filepath.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
        try:
            temp_file.replace(filepath)
        except PermissionError:
            filepath.write_text(json.dumps(data, indent=2), encoding="utf-8")
            try:
                temp_file.unlink()
            except OSError:
                pass


def load_risks() -> list[dict[str, object]]:
    return _read_json_file(RISK_LOG)


def save_risks(risks: list[dict[str, object]]) -> None:
    _write_json_file(RISK_LOG, risks)


def parse_score(value: object) -> int | None:
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    if value not in range(1, 6):
        return None
    return value


def categorize(text: str) -> str:
    lowered = text.lower()
    for category, keywords in FATAL_FOUR_KEYWORDS.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    for category, keywords in OTHER_CATEGORIES.items():
        if any(keyword in lowered for keyword in keywords):
            return category
    return "Other"


def estimate_scores(category: str, text: str) -> tuple[int, int]:
    lowered = text.lower()
    severity = 5 if category in {"Falls", "Electrocution", "Caught-In/Between"} else 4
    likelihood = 3

    if any(word in lowered for word in ("leaking", "exposed", "open", "unprotected", "overhead", "energized")):
        likelihood += 1
    if any(word in lowered for word in ("near miss", "injury", "collapse", "fatal", "serious")):
        severity = 5
    if any(word in lowered for word in ("temporary", "night", "rain", "crowded", "multiple crews")):
        likelihood += 1

    return min(likelihood, 5), min(severity, 5)


def risk_level(score: int) -> str:
    if score >= 20:
        return "Critical"
    if score >= CRITICAL_THRESHOLD:
        return "High"
    if score >= 8:
        return "Medium"
    return "Low"


def calculate_residual(likelihood: int, severity: int, category: str) -> tuple[int, int]:
    reduction = 2 if category in CONTROL_LIBRARY else 1
    residual_likelihood = max(1, likelihood - reduction)
    residual_severity = max(1, severity - 1)
    return residual_likelihood, residual_severity


def build_hazard_record(risk_input: RiskInput) -> dict[str, object]:
    text = f"{risk_input.task} {risk_input.hazard} {risk_input.location}"
    category = categorize(text)
    likelihood, severity = estimate_scores(category, text)

    if risk_input.likelihood is not None:
        likelihood = risk_input.likelihood
    if risk_input.severity is not None:
        severity = risk_input.severity

    residual_likelihood, residual_severity = calculate_residual(likelihood, severity, category)
    initial_score = likelihood * severity
    residual_score = residual_likelihood * residual_severity
    due_at = datetime.utcnow() + timedelta(hours=risk_input.deadline_hours)

    return {
        "id": uuid4().hex[:10],
        "created_at": utc_now(),
        "status": "Open",
        "task": risk_input.task,
        "hazard": risk_input.hazard,
        "people_at_risk": risk_input.people_at_risk,
        "location": risk_input.location,
        "category": category,
        "initial_likelihood": likelihood,
        "initial_severity": severity,
        "initial_score": initial_score,
        "initial_level": risk_level(initial_score),
        "hierarchy_of_controls": CONTROL_LIBRARY[category],
        "residual_likelihood": residual_likelihood,
        "residual_severity": residual_severity,
        "residual_score": residual_score,
        "residual_level": risk_level(residual_score),
        "owner": risk_input.owner,
        "deadline_hours": risk_input.deadline_hours,
        "due_at": due_at.replace(microsecond=0).isoformat() + "Z",
        "critical": initial_score >= CRITICAL_THRESHOLD,
        "verification_required": "Photo, supervisor sign-off, or inspection record is required to close.",
        "reminders_sent": 0,
    }


def log_hazard(risk_input: RiskInput) -> dict[str, object]:
    record = build_hazard_record(risk_input)
    with DATA_LOCK:
        risks = load_risks()
        risks.insert(0, record)
        save_risks(risks)
    if record["critical"]:
        trigger_escalation(record)
    return record


def update_status(risk_id: str, status: str, verification_note: str = "") -> dict[str, object] | None:
    normalized = status.strip().title()
    if normalized not in {"Open", "In Progress", "Closed"}:
        return None
    with DATA_LOCK:
        risks = load_risks()
        for risk in risks:
            if risk["id"] == risk_id:
                risk["status"] = normalized
                risk["verification_note"] = verification_note.strip()
                risk["updated_at"] = utc_now()
                if normalized == "Closed":
                    risk["closed_at"] = utc_now()
                save_risks(risks)
                return risk
    return None


def trigger_escalation(record: dict[str, object]) -> tuple[bool, str]:
    webhook = os.getenv("SAFETY_ESCALATION_WEBHOOK", "").strip()
    payload = {
        "type": "critical_risk",
        "message": (
            f"Critical safety risk at {record['location']}: {record['hazard']} "
            f"({record['initial_score']}/25). Owner: {record['owner']}."
        ),
        "risk": record,
    }

    if not webhook:
        return False, "SAFETY_ESCALATION_WEBHOOK is not configured."

    request = urllib.request.Request(
        webhook,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return 200 <= response.status < 300, response.read().decode("utf-8")
    except urllib.error.HTTPError as error:
        return False, error.read().decode("utf-8")
    except urllib.error.URLError as error:
        return False, str(error)


def analytics() -> dict[str, object]:
    risks = load_risks()
    by_category: dict[str, int] = {}
    by_location: dict[str, int] = {}
    open_critical = 0

    for risk in risks:
        by_category[str(risk["category"])] = by_category.get(str(risk["category"]), 0) + 1
        by_location[str(risk["location"])] = by_location.get(str(risk["location"]), 0) + 1
        if risk["status"] != "Closed" and risk["critical"]:
            open_critical += 1

    hot_locations = [
        {"location": location, "count": count}
        for location, count in sorted(by_location.items(), key=lambda item: item[1], reverse=True)
        if count >= 3
    ]

    return {
        "total": len(risks),
        "open": sum(1 for risk in risks if risk["status"] != "Closed"),
        "open_critical": open_critical,
        "by_category": by_category,
        "by_location": by_location,
        "hot_locations": hot_locations,
    }


def overdue_open_risks(hours_open: int = 24) -> list[dict[str, object]]:
    cutoff = datetime.utcnow() - timedelta(hours=hours_open)
    overdue: list[dict[str, object]] = []
    for risk in load_risks():
        created = datetime.fromisoformat(str(risk["created_at"]).replace("Z", ""))
        if risk["status"] != "Closed" and created <= cutoff:
            overdue.append(risk)
    return overdue


def predictive_jha() -> list[dict[str, object]]:
    schedule = _read_json_file(SCHEDULE_FILE)
    predictions: list[dict[str, object]] = []

    for item in schedule:
        text = f"{item.get('task', '')} {item.get('location', '')}"
        category = categorize(text)
        if category == "Other" and "above" in text.lower():
            category = "Struck-By"
        if category == "Other":
            continue
        likelihood, severity = estimate_scores(category, text)
        residual_likelihood, residual_severity = calculate_residual(likelihood, severity, category)
        predictions.append(
            {
                "date": item.get("date", "tomorrow"),
                "location": item.get("location", "Unknown"),
                "task": item.get("task", "Scheduled work"),
                "crew": item.get("crew", "Unknown"),
                "category": category,
                "initial_score": likelihood * severity,
                "initial_level": risk_level(likelihood * severity),
                "residual_score": residual_likelihood * residual_severity,
                "controls": CONTROL_LIBRARY[category],
            }
        )

    return predictions
