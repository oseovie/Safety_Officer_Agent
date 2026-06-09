"""Weather safety assessment helpers for site operations."""

from __future__ import annotations


def assess_weather_safety(weather_data: dict[str, float | int]) -> dict[str, object]:
    """Evaluate whether site work is safe under current weather conditions.

    The assessment is intentionally lightweight so it can be used in the
    existing safety dashboard and future weather-aware workflows.
    """

    temperature = float(weather_data.get("temperature_2m", 0))
    wind_speed = float(weather_data.get("wind_speed_10m", 0))
    precipitation = float(weather_data.get("precipitation", 0))
    weather_code = int(weather_data.get("weather_code", 0))

    reasons: list[str] = []
    risk_score = 0

    if temperature >= 35:
        reasons.append("Extreme heat may increase heat stress and dehydration risk.")
        risk_score += 3
    elif temperature <= 0:
        reasons.append("Freezing conditions may increase slip and cold-exposure risk.")
        risk_score += 2

    if wind_speed >= 20:
        reasons.append("High wind may make lifting, access, and crane operations unsafe.")
        risk_score += 3
    elif wind_speed >= 12:
        reasons.append("Moderate wind may affect stability and visibility on site.")
        risk_score += 1

    if precipitation >= 5:
        reasons.append("Heavy rain may create slip, visibility, and access hazards.")
        risk_score += 2
    elif precipitation >= 1:
        reasons.append("Rainfall may increase slip and grounding risks.")
        risk_score += 1

    if weather_code in {95, 96, 99}:
        reasons.append("Thunderstorm activity is unsafe for exposed work.")
        risk_score += 4
    elif weather_code in {61, 63, 65, 80, 81, 82}:
        reasons.append("Showers or storm cells may affect access and footing.")
        risk_score += 1

    if risk_score >= 5:
        risk_level = "high"
    elif risk_score >= 2:
        risk_level = "medium"
    else:
        risk_level = "low"

    display_reasons = reasons or ["Weather conditions are within normal safe working limits."]

    return {
        "safe_to_work": risk_level in {"low", "medium"} and risk_score < 5,
        "risk_level": risk_level,
        "reasons": display_reasons,
        "temperature_2m": temperature,
        "wind_speed_10m": wind_speed,
        "precipitation": precipitation,
        "weather_code": weather_code,
    }
