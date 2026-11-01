"""Pure passive backend evaluation for rooms, windows and special modes.

This module deliberately has no Home Assistant imports and no service-call
path.  It is the contract used by the management UI and by isolated tests;
the result is a preview/diagnostic, never a command.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Mapping

WINDOW_STATES = ("closed", "tilted", "open", "open_unknown", "unknown", "unavailable")
WINDOW_PRIORITY = {"closed": 0, "tilted": 1, "open_unknown": 2, "open": 3, "unknown": 4, "unavailable": 5}
WINDOW_HANDLING = {"normal", "ignore_tilted", "ignore_open", "ignore_all"}
WINDOW_STRATEGIES = {"none", "setback", "frost", "pause_demand", "custom_temperature"}
WINDOW_CONTACT_ROLES = {"unassigned", "tilt", "open"}
WINDOW_CONTACT_ROLE_LABELS = {"unassigned": "Nicht zugeordnet", "tilt": "Gekippt-Sensor", "open": "Offen-Sensor"}
MODE_PRIORITIES = {
    "chimney_sweep": 1000,
    "frost_protection": 900,
    "safety": 800,
    "party": 500,
    "visit": 490,
    "return_home": 480,
    "custom": 400,
    "summer": 300,
    "schedule": 200,
    "default": 100,
}


def normalize_window_state(value: Any, semantics: str = "binary") -> str:
    """Map a sensor value according to its declared semantics.

    A binary contact can only prove closed/open.  It never proves tilted.
    """
    raw = str(value).strip().lower()
    semantics = str(semantics or "binary").lower()
    if raw in {"unavailable", "nicht verfügbar", "missing"}:
        return "unavailable"
    if raw in {"unknown", "unbekannt", "none", ""}:
        return "unknown"
    if semantics == "tilt" and raw in {"on", "true", "1", "tilt", "tilted", "gekippt"}:
        return "tilted"
    if semantics == "open" and raw in {"on", "true", "1", "open", "opened", "offen"}:
        return "open"
    if semantics in {"multistate", "opening"}:
        if raw in {"tilt", "tilted", "gekippt"}:
            return "tilted"
        if raw in {"open", "opened", "offen", "true", "on", "1"}:
            return "open"
        if raw in {"closed", "close", "geschlossen", "false", "off", "0"}:
            return "closed"
        if raw in {"open_unknown", "offen unbekannt"}:
            return "open_unknown"
        return "unknown"
    if raw in {"closed", "close", "geschlossen", "false", "off", "0"}:
        return "closed"
    if raw in {"open", "opened", "offen", "true", "on", "1"}:
        return "open"
    return "unknown"


def aggregate_window_states(states: list[str] | tuple[str, ...]) -> str:
    """Aggregate physical-window signals conservatively and deterministically."""
    normalized = [state if state in WINDOW_STATES else "unknown" for state in states]
    if not normalized:
        return "unknown"
    if "open" in normalized:
        return "open"
    if "tilted" in normalized and "open_unknown" not in normalized:
        return "tilted"
    if "open_unknown" in normalized:
        return "open_unknown"
    if "unavailable" in normalized:
        return "unavailable"
    if "unknown" in normalized:
        return "unknown"
    return "closed"


def evaluate_window_contacts(contacts: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    """Evaluate assigned contacts while keeping technical failures visible.

    Unknown/unavailable contacts are diagnostic-only.  They never create a
    heating lock or an unknown automation state; if no valid signal remains,
    automation sees a closed room.  ``unassigned`` preserves the legacy
    semantics until a user explicitly chooses a role.
    """
    diagnostics = []
    valid_states = []
    for contact in contacts:
        if not isinstance(contact, Mapping):
            continue
        raw = str(contact.get("state", "missing") or "missing").strip().lower()
        role = str(contact.get("contact_role", contact.get("window_role", "unassigned")) or "unassigned")
        if role not in WINDOW_CONTACT_ROLES:
            role = "unassigned"
        ignored = bool(contact.get("ignored", False))
        semantics = contact.get("legacy_state_semantics") or contact.get("state_semantics") or ("tilt" if contact.get("type") == "tilt" else "binary")
        if role == "tilt":
            semantics = "tilt"
        elif role == "open":
            semantics = "open"
        normalized = normalize_window_state(raw, semantics)
        reachable = raw not in {"unknown", "unavailable", "missing", "nicht verfügbar", "none", ""}
        considered = reachable and not ignored and normalized in {"closed", "tilted", "open"}
        diagnostic_status = "unavailable" if raw in {"unavailable", "nicht verfügbar", "missing"} else "unknown" if not reachable else normalized
        derived = normalized if normalized in {"closed", "tilted", "open"} else "closed"
        if considered:
            valid_states.append(derived)
        diagnostics.append({
            "entity_id": str(contact.get("entity_id", "")),
            "name": contact.get("name") or contact.get("entity_id"),
            "role": role,
            "role_label": WINDOW_CONTACT_ROLE_LABELS[role],
            "raw_state": raw,
            "state": raw,
            "reachable": reachable,
            "available": reachable,
            "considered_for_automation": considered,
            "automation_ignored": not considered,
            "ignored": ignored,
            "diagnostic_status": diagnostic_status,
            "derived_state": derived,
            "semantics": semantics,
            "reason": "Für Heizungsautomatik ignoriert" if not considered else None,
        })
    state = "open" if "open" in valid_states else "tilted" if "tilted" in valid_states else "closed"
    return {"state": state, "contacts": diagnostics, "ignored_count": sum(not item["considered_for_automation"] for item in diagnostics), "valid_count": len(valid_states), "passive": True}


def evaluate_window_groups(groups: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> dict[str, Any]:
    """Evaluate physical windows, preserving conflict and sensor diagnostics."""
    result = []
    for index, group in enumerate(groups):
        signals = []
        for sensor in group.get("sensors", []):
            if not isinstance(sensor, Mapping):
                continue
            state = normalize_window_state(sensor.get("state"), sensor.get("semantics", "binary"))
            signals.append({"entity_id": str(sensor.get("entity_id", "")), "state": state, "semantics": sensor.get("semantics", "binary")})
        states = [item["state"] for item in signals]
        aggregate = aggregate_window_states(states)
        conflict = "open" in states and "closed" in states or "tilted" in states and "closed" in states
        result.append({"id": str(group.get("id") or f"window-{index + 1}"), "name": str(group.get("name") or f"Fenster {index + 1}"), "state": aggregate, "conflict": conflict, "sensors": signals, "warning": "Widersprüchliche Sensorsignale" if conflict else None})
    states = [item["state"] for item in result]
    return {"windows": result, "state": aggregate_window_states(states), "conflicts": [item["id"] for item in result if item["conflict"]]}


def evaluate_window_strategy(*, state: str, strategy: str = "none", tilted_delay: int = 0, open_delay: int = 0, close_delay: int = 0, elapsed_seconds: int = 0, custom_temperature: float | None = None) -> dict[str, Any]:
    """Return a deterministic passive window reaction after its delay."""
    state = state if state in WINDOW_STATES else "unknown"
    strategy = strategy if strategy in WINDOW_STRATEGIES else "none"
    delay = open_delay if state in {"open", "open_unknown"} else tilted_delay if state == "tilted" else close_delay if state == "closed" else 0
    effective = elapsed_seconds >= max(0, int(delay))
    action = "none"
    target = None
    if effective and state in {"open", "open_unknown", "tilted"}:
        action = {"none": "none", "setback": "setback", "frost": "frost", "pause_demand": "pause_demand", "custom_temperature": "custom_temperature"}[strategy]
        target = custom_temperature if action == "custom_temperature" else None
    return {"state": state, "strategy": strategy, "delay_seconds": max(0, int(delay)), "elapsed_seconds": max(0, int(elapsed_seconds)), "effective": effective, "action": action, "target_temperature": target, "passive": True}


def mode_is_active(mode: Mapping[str, Any], now: datetime | None = None) -> bool:
    """Determine activity without reviving an expired mode."""
    if not mode.get("available", False) or not mode.get("active", False):
        return False
    now = now or datetime.now(timezone.utc)
    expires = mode.get("expires_at")
    if expires:
        try:
            expiry = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            return now < expiry
        except ValueError:
            return False
    return True


def resolve_special_modes(modes: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...], *, now: datetime | None = None, zone_id: str | None = None) -> dict[str, Any]:
    """Select one deterministic winner and explain all suppressed active modes."""
    active = []
    expired = []
    for mode in modes:
        if mode_is_active(mode, now):
            if zone_id and mode.get("zone_ids") and zone_id not in mode.get("zone_ids", []):
                continue
            kind = str(mode.get("mode_type") or "custom")
            priority = int(mode.get("priority", MODE_PRIORITIES.get(kind, MODE_PRIORITIES["custom"])))
            active.append({"id": str(mode.get("id", "")), "name": mode.get("name"), "mode_type": kind, "priority": priority, "effect": mode.get("effect", {"action": "observe"}), "window_handling": mode.get("window_handling", "normal")})
        elif mode.get("active"):
            expired.append(str(mode.get("id", "")))
    active.sort(key=lambda item: (-item["priority"], item["id"]))
    winner = active[0] if active else None
    return {"active": active, "winner": winner, "suppressed": active[1:], "expired": expired, "passive": True}


def calculate_room_demand(*, room_temperature: float | None, target_temperature: float | None, windows: Mapping[str, Any], window_reaction: Mapping[str, Any], thermostats: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...], mode_result: Mapping[str, Any] | None = None, now: datetime | None = None) -> dict[str, Any]:
    """Calculate a room preview; unknown inputs never create invented demand."""
    warnings = []
    available_thermostats = [item for item in thermostats if item.get("available") is not False and item.get("state") not in {"missing", "unknown", "unavailable"}]
    if not available_thermostats:
        warnings.append("Kein verfügbares Thermostat")
    if room_temperature is None or target_temperature is None:
        warnings.append("Raum- oder Zieltemperatur unbekannt")
    if windows.get("state") in {"unknown", "unavailable", "open_unknown"}:
        warnings.append("Fensterzustand nicht eindeutig")
    action = window_reaction.get("action", "none")
    demand = None if warnings else room_temperature < target_temperature
    if action == "pause_demand" and demand is not None:
        demand = False
    mode = (mode_result or {}).get("winner")
    return {"room_temperature": room_temperature, "target_temperature": target_temperature, "heat_demand": demand, "available_thermostats": len(available_thermostats), "thermostat_count": len(thermostats), "window_state": windows.get("state", "unknown"), "window_action": action, "active_mode": mode, "warnings": warnings, "data_quality": "good" if not warnings else "partial", "computed_at": (now or datetime.now(timezone.utc)).isoformat(), "passive": True, "commands": []}
