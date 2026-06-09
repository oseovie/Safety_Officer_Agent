from app.services.weather import assess_weather_safety


def test_assess_weather_safety_flags_extreme_weather():
    result = assess_weather_safety(
        {
            "temperature_2m": 42,
            "wind_speed_10m": 26,
            "precipitation": 4.5,
            "weather_code": 95,
        }
    )

    assert result["safe_to_work"] is False
    assert result["risk_level"] == "high"
    assert any("heat" in reason.lower() or "wind" in reason.lower() for reason in result["reasons"])


def test_assess_weather_safety_allows_mild_weather():
    result = assess_weather_safety(
        {
            "temperature_2m": 18,
            "wind_speed_10m": 8,
            "precipitation": 0.2,
            "weather_code": 1,
        }
    )

    assert result["safe_to_work"] is True
    assert result["risk_level"] == "low"
