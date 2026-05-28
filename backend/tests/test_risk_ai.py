from app.services.risk_ai import assess_risk, classify_category, level_for_score


def test_classifies_fall_hazard():
    assert classify_category("worker exposed to scaffold edge") == "falls"


def test_scores_high_risk():
    assessment = assess_risk("Open edge", "work at height without guardrail", 4, 5)
    assert assessment.risk_score == 20
    assert assessment.risk_level == "critical"
    assert "engineering" in assessment.controls


def test_level_boundaries():
    assert level_for_score(4) == "low"
    assert level_for_score(9) == "medium"
    assert level_for_score(16) == "high"
    assert level_for_score(20) == "critical"
