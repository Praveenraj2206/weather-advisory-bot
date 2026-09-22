import json
from pathlib import Path
from typing import Any


SOPS_FILE = Path(__file__).with_name("sops.json")


def load_sops() -> list[dict[str, Any]]:
    """Load SOP rules from the JSON file."""
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
    """Check whether one weather condition matches."""
    field = condition.get("field")
    operator = condition.get("operator")
    expected = condition.get("value")

    if field not in weather or weather[field] is None:
        return False

    actual = weather[field]

    try:
        if operator == ">":
            return actual > expected

        elif operator == "<":
            return actual < expected

        elif operator == ">=":
            return actual >= expected

        elif operator == "<=":
            return actual <= expected

        elif operator == "==":
            return actual == expected

        elif operator == "between":
            lower, upper = expected
            return lower <= actual <= upper

    except (TypeError, ValueError, IndexError):
        return False

    return False


def evaluate_conditions(
    conditions: Any,
    weather: dict[str, Any]
) -> bool:
    """Evaluate individual conditions or all/any groups."""

    if isinstance(conditions, list):
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

        if "field" in conditions:
            return evaluate_condition(conditions, weather)

    return False


def find_matching_sop(
    activity: str,
    weather: dict[str, Any]
) -> dict[str, Any] | None:
    """
    Find the first matching SOP.

    Activity-specific SOPs are checked first.
    General outdoor SOPs are checked afterward.
    """

    sops = load_sops()
    normalized_activity = activity.strip().lower()

    # First, check rules for the requested activity.
    activity_sops = [
        sop for sop in sops
        if sop.get("activity", "").strip().lower()
        == normalized_activity
    ]

    # Then, check general outdoor rules as a fallback.
    general_sops = []

    if normalized_activity != "outdoor":
        general_sops = [
            sop for sop in sops
            if sop.get("activity", "").strip().lower() == "outdoor"
        ]

    # Return the first rule whose conditions match.
    for sop in activity_sops + general_sops:
        if evaluate_conditions(sop.get("conditions"), weather):
            return sop

    # No matching policy was found.
    return None