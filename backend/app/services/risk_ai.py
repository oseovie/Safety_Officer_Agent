from collections import Counter
from dataclasses import dataclass

from app.models.enums import RiskLevel


CONTROL_LIBRARY = {
    "falls": ["Install guardrails or covers", "Use certified anchor points", "Brief rescue plan before work"],
    "vehicle": ["Separate pedestrian routes", "Assign a spotter", "Enforce speed controls"],
    "chemical": ["Review SDS", "Improve ventilation", "Use compatible spill containment"],
    "fire": ["Remove combustibles", "Use hot-work permits", "Keep rated extinguishers nearby"],
    "other": ["Stop and reassess the task", "Assign supervision", "Verify PPE and method statement"],
}


@dataclass(frozen=True)
class RiskAssessment:
    risk_score: int
    risk_level: str
    category: str
    controls: dict[str, list[str]]
    narrative: str


def classify_category(text: str) -> str:
    lowered = text.lower()
    if any(word in lowered for word in ("fall", "height", "ladder", "scaffold", "edge")):
        return "falls"
    if any(word in lowered for word in ("forklift", "truck", "traffic", "vehicle", "crane")):
        return "vehicle"
    if any(word in lowered for word in ("chemical", "solvent", "spill", "fume", "acid")):
        return "chemical"
    if any(word in lowered for word in ("fire", "hot work", "welding", "spark")):
        return "fire"
    return "other"


def level_for_score(score: int) -> str:
    if score >= 20:
        return RiskLevel.CRITICAL.value
    if score >= 15:
        return RiskLevel.HIGH.value
    if score >= 8:
        return RiskLevel.MEDIUM.value
    return RiskLevel.LOW.value


def assess_risk(title: str, description: str, likelihood: int, severity: int) -> RiskAssessment:
    category = classify_category(f"{title} {description}")
    score = likelihood * severity
    controls = {
        "engineering": CONTROL_LIBRARY.get(category, CONTROL_LIBRARY["other"])[:2],
        "administrative": CONTROL_LIBRARY.get(category, CONTROL_LIBRARY["other"])[-1:],
        "ppe": ["Use task-specific PPE as the final layer of control"],
    }
    return RiskAssessment(
        risk_score=score,
        risk_level=level_for_score(score),
        category=category,
        controls=controls,
        narrative=f"{category.title()} risk scored {score}/25. Prioritize higher-order controls before PPE.",
    )


def portfolio_insights(records: list[dict[str, str | int]]) -> list[str]:
    categories = Counter(str(record.get("category", "other")) for record in records)
    locations = Counter(str(record.get("location", "unknown")) for record in records)
    insights = []
    if categories:
        category, count = categories.most_common(1)[0]
        insights.append(f"{category.title()} is the leading risk category with {count} open record(s).")
    if locations:
        location, count = locations.most_common(1)[0]
        insights.append(f"{location} is the current hotspot with {count} logged exposure(s).")
    insights.append("Review overdue corrective actions and upcoming inspections before the next shift handover.")
    return insights
