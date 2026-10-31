"""Conservative entity discovery for the Smart Heating setup flow.

Discovery only reads the public state machine. A role is selected automatically
only when one candidate has a unique best score; ties remain visible for manual
confirmation in the flow.
"""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

ROLE_DOMAINS = {
    "climate_entity": ("climate",),
    "heating_boolean": ("input_boolean",),
    "heating_permission": ("input_boolean",),
    "comfort_setpoint": ("input_number", "number"),
    "night_setpoint": ("input_number", "number"),
    "presence_entities": ("person", "device_tracker", "input_boolean"),
    "window_entities": ("binary_sensor", "sensor"),
    "outdoor_temperature": ("sensor",),
    "special_modes": ("input_boolean",),
}

ROLE_TOKENS = {
    "climate_entity": (("heizung", 5), ("thermostat", 4), ("heating", 3)),
    "heating_boolean": (("heizung", 5), ("heating", 3), ("zeit", 1)),
    "heating_permission": (("freigabe", 6), ("permission", 4), ("heizfreigabe", 7)),
    "comfort_setpoint": (("heiztemperatur", 7), ("comfort", 4), ("heizen", 2)),
    "night_setpoint": (("absenk", 7), ("night", 4), ("nacht", 4)),
    "presence_entities": (("zuhause", 4), ("home", 3), ("anwesen", 3)),
    "window_entities": (("fenster", 7), ("window", 5), ("kontakt", 2)),
    "outdoor_temperature": (("außen", 7), ("aussen", 7), ("outdoor", 6), ("outside", 5)),
}

SPECIAL_TOKENS = {
    "party": ("party",),
    "visit": ("besuch", "visit"),
    "return_home": ("heimweg", "return home", "rückkehr"),
    "chimney_sweep": ("schornsteinfeger", "chimney"),
    "summer": ("sommermodus", "summer mode", "sommer"),
}


def _states(hass: Any, domains: Iterable[str]) -> list[Any]:
    states = getattr(hass, "states", None)
    if states is None:
        return []
    result: list[Any] = []
    for domain in domains:
        result.extend(states.async_all(domain))
    return result


def _label(state: Any) -> str:
    name = getattr(state, "name", "") or ""
    entity_id = getattr(state, "entity_id", "") or ""
    return f"{name} {entity_id}".lower()


def _score(state: Any, role: str) -> int:
    label = _label(state)
    score = sum(weight for keyword, weight in ROLE_TOKENS.get(role, ()) if keyword in label)
    attrs = getattr(state, "attributes", {}) or {}
    device_class = str(attrs.get("device_class", "")).lower()
    if role == "window_entities" and device_class in {"window", "door", "opening"}:
        score += 8
    if role == "presence_entities" and device_class in {"occupancy", "presence"}:
        score += 8
    if role == "climate_entity" and getattr(state, "domain", "") == "climate":
        score += 1
    return score


def _role_candidates(hass: Any, role: str) -> list[dict[str, Any]]:
    candidates = []
    for state in _states(hass, ROLE_DOMAINS[role]):
        score = _score(state, role)
        if score <= 0:
            continue
        candidates.append({
            "entity_id": state.entity_id,
            "name": state.name,
            "score": score,
            "state": state.state,
        })
    return sorted(candidates, key=lambda item: (-item["score"], item["entity_id"]))


def discover_entities(hass: Any) -> dict[str, Any]:
    """Return candidates, unique selections, and ambiguity information."""
    roles: dict[str, Any] = {}
    selected: dict[str, Any] = {}
    ambiguous: list[str] = []
    missing: list[str] = []
    for role in ROLE_DOMAINS:
        candidates = _role_candidates(hass, role)
        if role in {"presence_entities", "window_entities"}:
            roles[role] = {"candidates": candidates, "selected": [item["entity_id"] for item in candidates]}
            continue
        roles[role] = {"candidates": candidates, "selected": None}
        if not candidates:
            missing.append(role)
        elif len(candidates) == 1 or candidates[0]["score"] > candidates[1]["score"]:
            selected[role] = candidates[0]["entity_id"]
            roles[role]["selected"] = candidates[0]["entity_id"]
        else:
            ambiguous.append(role)

    special_candidates: dict[str, list[dict[str, Any]]] = {}
    for mode, tokens in SPECIAL_TOKENS.items():
        items = []
        for state in _states(hass, ("input_boolean",)):
            label = _label(state)
            if any(keyword in label for keyword in tokens):
                items.append({"entity_id": state.entity_id, "name": state.name, "state": state.state})
        special_candidates[mode] = items
        if len(items) == 1:
            selected.setdefault("special_modes", {})[mode] = items[0]["entity_id"]
        elif len(items) > 1:
            ambiguous.append(f"special_modes.{mode}")
    roles["special_modes"] = {"candidates": special_candidates, "selected": selected.get("special_modes", {})}
    return {"roles": roles, "selected": selected, "ambiguous": sorted(set(ambiguous)), "missing": sorted(set(missing))}


def apply_discovery_defaults(config: dict[str, Any], report: dict[str, Any]) -> dict[str, Any]:
    """Merge only unambiguous selections into config data."""
    result = dict(config)
    selected = report.get("selected", {})
    for key in ("climate_entity", "heating_boolean", "heating_permission", "comfort_setpoint", "night_setpoint"):
        if selected.get(key):
            result[key] = selected[key]
    for key in ("presence_entities", "window_entities"):
        if report.get("roles", {}).get(key, {}).get("selected"):
            result[key] = report["roles"][key]["selected"]
    if selected.get("special_modes"):
        result["special_modes"] = selected["special_modes"]
    return result
