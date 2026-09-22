import json
from pathlib import Path
from typing import Optional


# Load SOPs from the same directory as this Python file
SOPS_FILE = Path(__file__).with_name("sops.json")


def load_sops() -> list[dict]:
    """Load SOPs from sops.json."""
    with SOPS_FILE.open("r", encoding="utf-8") as file:
        sops = json.load(file)

    if not isinstance(sops, list):
        raise ValueError("sops.json must contain a list of SOPs.")

    return sops


def matches_simple_condition(condition: dict, weather: dict) -> bool:
    """Check whether a weather value satisfies a simple condition."""

    field = condition.get("field")
    operator = condition.get("operator")
    value = condition.get("value")

    actual = weather.get(field)

    if actual is None:
        return False

    try:
        if operator == ">":
            return actual > value

        elif operator == "<":
            return actual < value

        elif operator == ">=":
            return actual >= value

        elif operator == "<=":
            return actual <= value

        elif operator == "==":
            return actual == value

        elif operator == "between":
            minimum = condition.get("min")
            maximum = condition.get("max")

            if minimum is None or maximum is None:
                return False

            return minimum <= actual <= maximum

    except (TypeError, ValueError):
        return False

    return False


def matches_fuzzy_condition(condition: dict, weather: dict) -> bool:
    """Evaluate multiple conditions using all or any logic."""

    conditions = condition.get("conditions", [])
    logic = condition.get("logic", "all")

    if not conditions:
        return False

    results = [
        matches_simple_condition(cond, weather)
        for cond in conditions
    ]

    if logic == "all":
        return all(results)

    elif logic == "any":
        return any(results)

    return False


def matches_severe_weather_condition(
    condition: dict,
    weather: dict
) -> bool:
    """Evaluate severe-weather thresholds defined in the SOP JSON."""

    thresholds = condition.get("thresholds", {})

    temperature = weather.get("temperature_2m")
    wind = weather.get("wind_speed_10m")
    rain_probability = weather.get("precipitation_probability")

    # Individual severe-weather conditions
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
        rain_probability is not None
        and rain_probability >= thresholds.get("certain_rain", float("inf"))
    )

    # Combination thresholds are also configurable in sops.json.
    combination = condition.get("combination", {})

    rain_threshold = combination.get("rain_probability", float("inf"))
    wind_threshold = combination.get("wind_speed", float("inf"))

    high_rain_and_wind = (
        rain_probability is not None
        and wind is not None
        and rain_probability >= rain_threshold
        and wind >= wind_threshold
    )

    check_type = condition.get("check_type", "any")

    if check_type == "any":
        return (
            extreme_heat
            or extreme_cold
            or severe_wind
            or certain_rain
        )

    elif check_type == "combination":
        return (
            high_rain_and_wind
            or extreme_heat
            or extreme_cold
        )

    return False


def matches_condition(condition: dict, weather: dict) -> bool:
    """Choose the correct evaluator based on the condition type."""

    condition_type = condition.get("type")

    if condition_type == "simple":
        return matches_simple_condition(condition, weather)

    elif condition_type == "fuzzy":
        return matches_fuzzy_condition(condition, weather)

    elif condition_type == "severe_weather":
        return matches_severe_weather_condition(condition, weather)

    return False


def find_matching_sop(
    activity_type: str,
    weather: dict,
    location: str = ""
) -> Optional[dict]:
    """
    Find the matching SOP.

    Resolution strategy:
    1. Check SOPs for the requested activity.
    2. Also check general outdoor SOPs.
    3. Select the matching SOP with the highest severity.
    4. For equal severity, retain the first matching SOP in sops.json.
    """

    sops = load_sops()

    requested_activity = activity_type.strip().lower()

    matching_sops = []

    for sop in sops:
        sop_activity = sop.get("activity_type", "").strip().lower()

        # Check the requested activity and general outdoor policies.
        if sop_activity not in (requested_activity, "outdoor"):
            continue

        condition = sop.get("condition", {})

        if matches_condition(condition, weather):
            matching_sops.append(sop)

    if not matching_sops:
        return None

    # Severity priority: high > moderate > low
    severity_order = {
        "high": 3,
        "moderate": 2,
        "low": 1
    }

    matching_sops.sort(
        key=lambda sop: severity_order.get(
            sop.get("severity", "").lower(),
            0
        ),
        reverse=True
    )

    return matching_sops[0]