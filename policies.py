import json
from pathlib import Path
from typing import Optional


SOPS_FILE = Path(__file__).with_name("sops.json")


def load_sops() -> list[dict]:
    """Load SOPs from sops.json."""
    with SOPS_FILE.open("r", encoding="utf-8") as file:
        sops = json.load(file)

    if not isinstance(sops, list):
        raise ValueError("sops.json must contain a list of SOPs.")

    return sops


def matches_simple_condition(condition: dict, weather: dict) -> bool:
    """Evaluate one weather condition."""

    field = condition.get("field")
    operator = condition.get("operator")
    actual = weather.get(field)

    if actual is None:
        return False

    try:
        if operator == ">":
            return actual > condition.get("value")

        if operator == "<":
            return actual < condition.get("value")

        if operator == ">=":
            return actual >= condition.get("value")

        if operator == "<=":
            return actual <= condition.get("value")

        if operator == "==":
            return actual == condition.get("value")

        if operator == "between":
            limits = condition.get("value")

            if isinstance(limits, list) and len(limits) == 2:
                return limits[0] <= actual <= limits[1]

            minimum = condition.get("min")
            maximum = condition.get("max")

            if minimum is not None and maximum is not None:
                return minimum <= actual <= maximum

    except (TypeError, ValueError):
        return False

    return False


def matches_conditions(conditions, weather: dict) -> bool:
    """Evaluate a list of conditions or an all/any condition group."""

    # A direct list means all conditions must match.
    if isinstance(conditions, list):
        return bool(conditions) and all(
            matches_simple_condition(condition, weather)
            for condition in conditions
        )

    if not isinstance(conditions, dict):
        return False

    # Support {"all": [...]} and {"any": [...]}.
    if "all" in conditions:
        rules = conditions["all"]
        return bool(rules) and all(
            matches_simple_condition(rule, weather)
            for rule in rules
        )

    if "any" in conditions:
        rules = conditions["any"]
        return bool(rules) and any(
            matches_simple_condition(rule, weather)
            for rule in rules
        )

    # Support an individual condition object.
    if "field" in conditions:
        return matches_simple_condition(conditions, weather)

    return False


def get_weather_value(weather: dict, *field_names):
    """Read a weather value using any supported field name."""

    for field in field_names:
        value = weather.get(field)
        if value is not None:
            return value

    return None


def matches_severe_weather_condition(condition: dict, weather: dict) -> bool:
    """Evaluate severe-weather thresholds if an SOP uses that format."""

    thresholds = condition.get("thresholds", {})
    combination = condition.get("combination", {})

    temperature = get_weather_value(
        weather, "temperature", "temperature_2m"
    )
    wind = get_weather_value(
        weather, "wind_speed", "wind_speed_10m"
    )
    rain = get_weather_value(
        weather, "precipitation_probability"
    )

    extreme_heat = (
        temperature is not None
        and temperature >= thresholds.get("extreme_heat", float("inf"))
    )

    extreme_cold = (
        temperature is not None
        and temperature <= thresholds.get("extreme_cold", float("-inf"))
    )

    severe_wind = (
        wind is not None
        and wind >= thresholds.get("severe_wind", float("inf"))
    )

    certain_rain = (
        rain is not None
        and rain >= thresholds.get("certain_rain", float("inf"))
    )

    rain_threshold = combination.get(
        "rain_probability", float("inf")
    )
    wind_threshold = combination.get(
        "wind_speed", float("inf")
    )

    heavy_rain_and_wind = (
        rain is not None
        and wind is not None
        and rain >= rain_threshold
        and wind >= wind_threshold
    )

    check_type = condition.get("check_type", "any")

    if check_type == "any":
        return any([
            extreme_heat,
            extreme_cold,
            severe_wind,
            certain_rain
        ])

    if check_type == "combination":
        return any([
            heavy_rain_and_wind,
            extreme_heat,
            extreme_cold
        ])

    return False


def sop_matches(sop: dict, requested_activity: str, weather: dict) -> bool:
    """Check whether one SOP applies to the requested activity and weather."""

    # Support both activity field names.
    sop_activity = sop.get(
        "activity", sop.get("activity_type", "")
    )

    if not isinstance(sop_activity, str):
        return False

    sop_activity = sop_activity.strip().lower()

    # Check activity-specific policies and general outdoor policies.
    if sop_activity not in (requested_activity, "outdoor"):
        return False

    # Latest SOP format: {"conditions": ...}
    if "conditions" in sop:
        return matches_conditions(sop["conditions"], weather)

    # Also support the older {"condition": {...}} format.
    condition = sop.get("condition", {})
    condition_type = condition.get("type")

    if condition_type == "simple":
        return matches_simple_condition(condition, weather)

    if condition_type == "fuzzy":
        return matches_conditions(
            {
                condition.get("logic", "all"): condition.get("conditions", [])
            },
            weather
        )

    if condition_type == "severe_weather":
        return matches_severe_weather_condition(condition, weather)

    return False


def find_matching_sop(
    activity_type: str,
    weather: dict,
    location: str = ""
) -> Optional[dict]:
    """Return the highest-severity SOP that matches."""

    requested_activity = activity_type.strip().lower()
    matching_sops = []

    for sop in load_sops():
        if sop_matches(sop, requested_activity, weather):
            matching_sops.append(sop)

    if not matching_sops:
        return None

    severity_order = {
        "high": 3,
        "moderate": 2,
        "low": 1
    }

    # Highest severity first; preserve JSON order for equal severities.
    matching_sops.sort(
        key=lambda sop: severity_order.get(
            str(sop.get("severity", "low")).lower(), 0
        ),
        reverse=True
    )

    return matching_sops[0]