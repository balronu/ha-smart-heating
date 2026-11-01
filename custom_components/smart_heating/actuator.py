"""Strictly passive actuator planning for Smart Heating shadow decisions.

The records returned by this module describe what the verified legacy path
would need to do.  They are data only: this module has no Home Assistant
imports and deliberately cannot execute a service.
"""

from __future__ import annotations

from typing import Any, Mapping


KNOWN_LEGACY_SERVICES = ("climate.set_hvac_mode", "climate.set_temperature")
UNKNOWN_STATES = {"", "missing", "none", "unknown", "unavailable"}


def _value(decision: Any, key: str, default: Any = None) -> Any:
    if isinstance(decision, Mapping):
        return decision.get(key, default)
    return getattr(decision, key, default)


def _available(state: Mapping[str, Any] | None) -> bool:
    if not isinstance(state, Mapping):
        return False
    raw = str(state.get("state", "missing") or "missing").lower()
    return state.get("available") is not False and raw not in UNKNOWN_STATES


def build_passive_actor_plan(
    *,
    zone_id: str | None,
    heating_sources: Mapping[str, Any] | None,
    decision: Any,
    active_special_mode: Mapping[str, Any] | None = None,
    priority: int | None = None,
    reason: str | None = None,
    data_quality: str = "incomplete",
    missing_prerequisites: list[str] | tuple[str, ...] = (),
    actor_states: Mapping[str, Mapping[str, Any]] | None = None,
    service_evidence: Mapping[str, bool] | None = None,
    physical_heat_demand_status: str = "not_proven",
) -> dict[str, Any]:
    """Build a non-executable actor plan from a passive decision.

    Primary selection follows the proven legacy rule: use the primary Climate
    entity when available, otherwise the configured fallback.  No second
    target is added automatically.  Missing readback or capability evidence
    blocks a planned service record instead of guessing.
    """
    sources = heating_sources if isinstance(heating_sources, Mapping) else {}
    states = actor_states if isinstance(actor_states, Mapping) else {}
    evidence = service_evidence if isinstance(service_evidence, Mapping) else {}
    primary = str(sources.get("primary_climate_entity") or "") or None
    fallback = str(sources.get("fallback_climate_entity") or "") or None
    selected = None
    selection_reason = None
    if primary and _available(states.get(primary)):
        selected = primary
        selection_reason = "primary_available"
    elif fallback and _available(states.get(fallback)):
        selected = fallback
        selection_reason = "primary_unavailable_fallback_selected"

    missing = set(str(item) for item in missing_prerequisites if item)
    planned: list[dict[str, Any]] = []
    selected_state = states.get(selected) if selected else None
    desired_mode = _value(decision, "target_hvac_mode")
    desired_temperature = _value(decision, "target_temperature")
    decision_mode = _value(decision, "mode")
    decision_reason = reason or _value(decision, "reason") or "Passive Heizentscheidung"
    decision_priority = priority if priority is not None else _value(decision, "priority")
    mode_id = active_special_mode.get("id") if isinstance(active_special_mode, Mapping) else None

    if not selected:
        missing.add("actor_path" if not primary and not fallback else "actor_availability_readback")
    else:
        current_mode = selected_state.get("hvac_mode", selected_state.get("state")) if isinstance(selected_state, Mapping) else None
        current_temperature = selected_state.get("temperature") if isinstance(selected_state, Mapping) else None
        if current_mode in (None, "", "unknown", "unavailable"):
            missing.add("actor_mode_readback")
        elif desired_mode and str(current_mode) != str(desired_mode):
            if evidence.get("climate.set_hvac_mode", False):
                planned.append({
                    "zone_id": zone_id,
                    "entity_id": selected,
                    "service": "climate.set_hvac_mode",
                    "parameters": {"entity_id": selected, "hvac_mode": desired_mode},
                    "desired_temperature": desired_temperature,
                    "desired_hvac_mode": desired_mode,
                    "decision": decision_mode,
                    "special_mode": mode_id,
                    "priority": decision_priority,
                    "reason": decision_reason,
                    "data_quality": data_quality,
                    "evidence_status": "legacy_automation_service_configured",
                    "execution_status": "not_executed",
                    "passive": True,
                })
            else:
                missing.add("climate.set_hvac_mode_capability")
        if desired_temperature is not None:
            try:
                delta = abs(float(desired_temperature) - float(current_temperature))
            except (TypeError, ValueError):
                delta = None
            if delta is None:
                missing.add("actor_setpoint_readback")
            elif delta > 0.1:
                if evidence.get("climate.set_temperature", False):
                    planned.append({
                        "zone_id": zone_id,
                        "entity_id": selected,
                        "service": "climate.set_temperature",
                        "parameters": {"entity_id": selected, "temperature": float(desired_temperature)},
                        "desired_temperature": float(desired_temperature),
                        "desired_hvac_mode": desired_mode,
                        "decision": decision_mode,
                        "special_mode": mode_id,
                        "priority": decision_priority,
                        "reason": decision_reason,
                        "data_quality": data_quality,
                        "evidence_status": "legacy_automation_service_configured",
                        "execution_status": "not_executed",
                        "passive": True,
                    })
                else:
                    missing.add("climate.set_temperature_capability")

    if physical_heat_demand_status not in {"verified", "not_required"}:
        missing.add("physical_heat_demand_feedback")
    return {
        "zone_id": zone_id,
        "selected_entity": selected,
        "selection_reason": selection_reason,
        "primary_entity": primary,
        "fallback_entity": fallback,
        "desired_temperature": desired_temperature,
        "desired_hvac_mode": desired_mode,
        "decision": decision_mode,
        "special_mode": mode_id,
        "priority": decision_priority,
        "reason": decision_reason,
        "data_quality": data_quality,
        "planned_commands": planned,
        "executed_commands": [],
        "execution_status": "not_executed",
        "physical_heat_demand": {
            "requested": _value(decision, "target_hvac_mode") == "heat" and desired_temperature is not None,
            "status": physical_heat_demand_status,
            "evidence": "independent boiler/burner feedback required",
        },
        "missing_prerequisites": sorted(missing),
        "passive": True,
        "supported_services": [service for service in KNOWN_LEGACY_SERVICES if evidence.get(service, False)],
    }
