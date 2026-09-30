import json
from pathlib import Path
from typing import Optional

SOPS_FILE = Path(__file__).with_name("sops.json")
UNIVERSAL = "any"  # SOPs with this activity apply to every question
SEVERITY_RANK = {"high": 3, "moderate": 2, "low": 1}

OPERATORS = {
    ">": lambda a, v: a > v,
    "<": lambda a, v: a < v,
    ">=": lambda a, v: a >= v,
    "<=": lambda a, v: a <= v,
    "==": lambda a, v: a == v,
    "in": lambda a, v: a in v,
    "between": lambda a, v: v[0] <= a <= v[1],
}


def load_sops() -> list[dict]:
    """Load SOPs from sops.json."""
    with SOPS_FILE.open("r", encoding="utf-8") as file:
        sops = json.load(file)
    if not isinstance(sops, list):
        raise ValueError("sops.json must contain a list of SOPs.")
    return sops


def get_categories() -> list[str]:
    """Activity categories defined by the SOPs (read from the data, not hardcoded)."""
    return sorted({str(s.get("activity", "")).strip().lower() for s in load_sops()} - {UNIVERSAL, ""})


def evaluate_condition(condition: dict, weather: dict) -> bool:
    """Evaluate one {field, operator, value} condition. Missing data never matches."""
    actual = weather.get(condition.get("field"))
    operator = OPERATORS.get(condition.get("operator"))
    if actual is None or operator is None:
        return False
    try:
        return bool(operator(actual, condition.get("value")))
    except (TypeError, ValueError, IndexError):
        return False


def evaluate_conditions(conditions, weather: dict) -> bool:
    """Evaluate a list (all), {"all": [...]}, {"any": [...]}, {"at_least": n, "of": [...]}, or one condition."""
    if isinstance(conditions, list):
        return bool(conditions) and all(evaluate_condition(c, weather) for c in conditions)

    if not isinstance(conditions, dict):
        return False

    if "all" in conditions:
        rules = conditions["all"]
        return bool(rules) and all(evaluate_condition(r, weather) for r in rules)

    if "any" in conditions:
        rules = conditions["any"]
        return bool(rules) and any(evaluate_condition(r, weather) for r in rules)

    if "at_least" in conditions:  # fuzzy rule: enough soft signals hold
        rules = conditions.get("of", [])
        hits = sum(evaluate_condition(r, weather) for r in rules)
        return bool(rules) and hits >= conditions["at_least"]

    if "field" in conditions:
        return evaluate_condition(conditions, weather)

    return False


def find_matching_sops(activity_type: str, weather: dict) -> list[dict]:
    """All matching SOPs, best first.

    Ranking: highest severity first. On equal severity, universal ("any") SOPs
    come before activity-specific ones, because a situational rule (e.g. heavy
    rain) should lead. Remaining ties keep sops.json order.
    """
    activity = activity_type.strip().lower()
    matches = [
        sop for sop in load_sops()
        if str(sop.get("activity", "")).strip().lower() in (activity, UNIVERSAL)
        and evaluate_conditions(sop.get("conditions"), weather)
    ]
    matches.sort(key=lambda s: (
        -SEVERITY_RANK.get(str(s.get("severity", "low")).lower(), 0),
        str(s.get("activity", "")).strip().lower() != UNIVERSAL,
    ))
    return matches


def find_matching_sop(activity_type: str, weather: dict) -> Optional[dict]:
    """The single highest-ranked matching SOP, or None."""
    matches = find_matching_sops(activity_type, weather)
    return matches[0] if matches else None