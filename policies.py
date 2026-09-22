import json
from pathlib import Path
from typing import Any


SOPS_FILE = Path(__file__).with_name("sops.json")


def load_sops() -> list[dict[str, Any]]:
    """Load the SOP rules from the JSON file."""
    try:
        with SOPS_FILE.open("r", encoding="utf-8") as file:
            sops = json.load(file)

        if not isinstance(sops, list):
            raise ValueError("sops.json must contain a JSON list.")

        return sops

    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"Could not find SOP file: {SOPS_FILE}"
        ) from exc


def evaluate_condition(
    condition: dict[str, Any],
    weather: dict[str, Any]
) -> bool:
    """Evaluate one condition against the available weather data."""
    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")

    if field not in weather:
        return False

    actual = weather[field]

    # Missing values cannot satisfy a condition.
    if actual is None:
        return False

    try:
        if operator == ">":
            return actual > expected

        if operator == "<":
            return actual < expected

        if operator == ">=":
            return actual >= expected

        if operator == "<=":
            return actual <= expected

        if operator == "==":
            return actual == expected

        if operator == "between":
            lower, upper = expected
            return lower <= actual <= upper

    except (TypeError, ValueError):
        return False

    # Unknown operators do not match.
    return False


def evaluate_conditions(
    conditions: Any,
    weather: dict[str, Any]
) -> bool:
    """Evaluate simple conditions or nested all/any condition groups."""
    if isinstance(conditions, list):
        # A list means every condition must be true.
        return all(
            evaluate_condition(condition, weather)
            for condition in conditions
        )

    if isinstance(conditions, dict):
        if "all" in conditions:
            return all(
                evaluate_condition(condition, weather)
                for condition in conditions["all"]
            )

        if "any" in conditions:
            return any(
                evaluate_condition(condition, weather)
                for condition in conditions["any"]
            )

        # A single condition represented as a dictionary.
        if "field" in conditions:
            return evaluate_condition(conditions, weather)

    return False


def find_matching_sop(
    activity: str,
    weather: dict[str, Any]
) -> dict[str, Any] | None:
    """
    Return the first SOP matching the activity and current weather.

    General outdoor SOPs can also apply when no activity-specific
    SOP matches.
    """
    sops = load_sops()
    normalized_activity = activity.strip().lower()

    # Check activity-specific rules first, followed by general outdoor rules.
    applicable_sops = [
        sop for sop in sops
        if sop.get("activity", "").lower() == normalized_activity
    ]

    if normalized_activity != "outdoor":
        applicable_sops.extend(
            sop for sop in sops
            if sop.get("activity", "").lower() == "outdoor"
        )

    for sop in applicable_sops:
        if evaluate_conditions(sop.get("conditions"), weather):
            return sop

    return None