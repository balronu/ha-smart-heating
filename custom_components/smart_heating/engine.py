"""Server-side calculations for the passive Smart Heating coordinator."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any, Mapping

from .models import WeeklySchedule, evaluate_decision
from .backend_engine import calculate_room_demand, evaluate_window_groups, evaluate_window_strategy, resolve_passive_decision, resolve_special_modes
from .actuator import build_passive_actor_plan
from .shadow_compare import compare_shadow_decision


def calculate_status(
    schedule: WeeklySchedule,
    *,
    now: datetime,
    timezone: str,
    overrides: Mapping[str, bool] | None = None,
    context: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    context = context or {}
    active = schedule.active_at(now, timezone)
    next_switch, next_state = schedule.next_switch(now, timezone)
    active_window = schedule.active_window_at(now, timezone)
    # Legacy summer comfort override depends on measured room temperature.
    # This remains a passive calculation; no climate services are called.
    effective_overrides = dict(overrides or {})
    measured = context.get("room_temperature")
    comfort = context.get("comfort_temperature")
    if measured is not None and comfort is not None:
        try:
            effective_overrides["need_heat_now"] = float(measured) < float(comfort) - 0.4
        except (TypeError, ValueError):
            pass
    decision = evaluate_decision(
        schedule_active=active,
        overrides=effective_overrides,
        comfort_temperature=context.get("comfort_temperature"),
        night_temperature=context.get("night_temperature"),
        chimney_temperature=context.get("chimney_temperature", 25.0),
        summer_mode=context.get("summer_mode", "compatibility"),
        frost_temperature=context.get("frost_temperature", 5.0),
        hvac_supports_off=context.get("hvac_supports_off", True),
    )
    if decision.mode == "comfort" and active_window is not None and active_window.target_temperature is not None:
        decision = replace(decision, target_temperature=active_window.target_temperature)
    presence = context.get("presence", {}) if isinstance(context.get("presence", {}), Mapping) else {}
    window_result = evaluate_window_groups(context.get("window_groups", ()))
    mode_result = resolve_special_modes(
        context.get("special_modes", ()),
        now=now,
        zone_id=context.get("zone_id"),
        presence_status=presence.get("status"),
        window_state=window_result["state"],
    )
    passive_decision = resolve_passive_decision(
        decision,
        mode_result,
        comfort_temperature=context.get("comfort_temperature"),
        setback_temperature=context.get("night_temperature"),
        chimney_temperature=context.get("chimney_temperature", 25.0),
        frost_temperature=context.get("frost_temperature", 5.0),
        window_state=window_result["state"],
        presence_status=presence.get("status"),
    )
    effective_windows = window_result
    if passive_decision["window_override"]:
        effective_windows = {**window_result, "original_state": window_result["state"], "state": "closed"}
    window_reaction = evaluate_window_strategy(
        state=effective_windows["state"],
        strategy=context.get("window_strategy", "none"),
        tilted_delay=context.get("window_delays", {}).get("tilted", 0),
        open_delay=context.get("window_delays", {}).get("open", 0),
        close_delay=context.get("window_delays", {}).get("closed", 0),
        elapsed_seconds=context.get("window_elapsed_seconds", 0),
        custom_temperature=context.get("window_custom_temperature"),
    )
    room_demand = calculate_room_demand(
        room_temperature=context.get("room_temperature"),
        target_temperature=decision.target_temperature,
        windows=effective_windows,
        window_reaction=window_reaction,
        thermostats=context.get("thermostats", ()),
        mode_result=mode_result,
        demand_override=passive_decision["heat_demand_override"],
        now=now,
    )
    missing_prerequisites = list(passive_decision["missing_prerequisites"])
    sources = context.get("heating_sources", {}) if isinstance(context.get("heating_sources", {}), Mapping) else {}
    if not sources.get("primary_climate_entity") and not sources.get("fallback_climate_entity"):
        missing_prerequisites.append("actor_path")
    if not context.get("schedule_source_verified", False):
        missing_prerequisites.append("scheduler_or_schedule_source")
    data_quality = "complete" if not missing_prerequisites else "incomplete"
    actor_plan = build_passive_actor_plan(
        zone_id=context.get("zone_id"),
        heating_sources=sources,
        decision=passive_decision,
        active_special_mode=mode_result.get("winner"),
        priority=passive_decision.get("priority"),
        reason=passive_decision.get("reason"),
        data_quality=data_quality,
        missing_prerequisites=missing_prerequisites,
        actor_states=context.get("actor_states", {}),
        service_evidence=context.get("actor_service_evidence", {}),
        physical_heat_demand_status=context.get("physical_heat_demand_status", "not_proven"),
    )
    missing_prerequisites = sorted(set(missing_prerequisites) | set(actor_plan["missing_prerequisites"]))
    data_quality = "complete" if not missing_prerequisites else "incomplete"
    selected_state = actor_plan.get("selected_entity") and context.get("actor_states", {}).get(actor_plan["selected_entity"], {})
    comparison = compare_shadow_decision(
        timestamp=now,
        zone_id=context.get("zone_id"),
        observed_thermostat=selected_state,
        legacy_decision=context.get("legacy_decision"),
        smart_decision=passive_decision,
        planned_actor_action=(actor_plan.get("planned_commands") or [None])[0],
        active_special_mode=mode_result.get("winner"),
        priority=passive_decision.get("priority"),
        schedule_decision={"active": active, "next_switch": next_switch.isoformat() if next_switch else None, "source_verified": bool(context.get("schedule_source_verified", False))},
        window_state=window_result.get("state"),
        presence=presence,
        data_quality=data_quality,
    )
    return {
        "schedule_active": active,
        "next_switch": next_switch.isoformat() if next_switch else None,
        "next_state": next_state,
        "mode": passive_decision["mode"],
        "actual_mode": decision.mode,
        "mode_source": passive_decision["source"],
        "reason": passive_decision["reason"],
        "target_temperature": passive_decision["target_temperature"],
        "target_hvac_mode": passive_decision["target_hvac_mode"],
        "base_decision": {"mode": decision.mode, "reason": decision.reason, "target_temperature": decision.target_temperature, "target_hvac_mode": decision.target_hvac_mode, "source": decision.source},
        "passive_decision": passive_decision,
        "control_enabled": False,
        "control_state": "locked",
        "operation_mode": context.get("operation_mode", "compatibility"),
        "control_plane": dict(context.get("control_plane", {
            "operating_state": "LEGACY",
            "confirmed_control_ownership": "legacy",
            "switch_ready": False,
            "rollback_ready": True,
            "error": None,
            "blocked_reason": "Smart Heating ist passiv; eine Umschaltung ist nicht freigegeben.",
        })),
        "heat_demand_verified": False,
        "heat_demand_status": "not_measured",
        "special_modes": {key: bool(value) for key, value in (overrides or {}).items() if key in {"party", "visit", "return_home", "chimney_sweep", "summer"}},
        "simulated": True,
        "window_evaluation": window_result,
        "window_reaction": window_reaction,
        "special_mode_evaluation": mode_result,
        "room_demand": room_demand,
        "shadow": {
            "zone_id": context.get("zone_id"),
            "active_special_mode": mode_result.get("winner"),
            "suppressed_special_modes": mode_result.get("suppressed", []),
            "schedule_decision": {
                "active": active,
                "source_verified": bool(context.get("schedule_source_verified", False)),
                "next_switch": next_switch.isoformat() if next_switch else None,
                "next_state": next_state,
                "window_target_temperature": active_window.target_temperature if active_window else None,
                "timezone": timezone,
            },
            "window_state": window_result.get("state"),
            "presence": presence,
            "actor_path": {"primary": sources.get("primary_climate_entity"), "fallback": sources.get("fallback_climate_entity")},
            "data_quality": data_quality,
            "missing_prerequisites": sorted(set(missing_prerequisites)),
            "passive": True,
            "commands": [],
            "planned_actor_actions": actor_plan,
            "comparison": comparison,
            "data_sources": context.get("shadow_data_sources", {}),
        },
    }


def calculate_zone_target_previews(
    schedule: WeeklySchedule,
    *,
    now: datetime,
    timezone: str,
    zones: list[Mapping[str, Any]],
    internal: Mapping[str, Any],
    zone_diagnostics: list[Mapping[str, Any]] | None = None,
    overrides: Mapping[str, bool] | None = None,
    context: Mapping[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Calculate independent per-zone targets, without reading or actuating devices.

    This is a target-only shadow preview, not a room demand or actuator plan.
    It intentionally uses the same safety and schedule decision as the global
    preview and does not claim independent physical boiler control.
    """
    if not internal.get("internal_only", False):
        return []
    active = schedule.active_at(now, timezone)
    window = schedule.active_window_at(now, timezone)
    base_context = dict(context or {})
    zone_targets = internal.get("zones", {})
    if not isinstance(zone_targets, Mapping):
        zone_targets = {}
    diagnostics_by_id = {str(item.get("zone_id")): item for item in (zone_diagnostics or [])}
    result = []
    for zone in zones:
        zone_id = str(zone.get("id") or "")
        if not zone_id or zone.get("enabled") is False:
            continue
        settings = zone_targets.get(zone_id, {})
        if not isinstance(settings, Mapping):
            settings = {}
        comfort = settings.get("comfort_temperature", internal.get("comfort_temperature", 21.0))
        night = settings.get("night_temperature", internal.get("night_temperature", 18.0))
        diagnostic = diagnostics_by_id.get(zone_id, {})
        window_state = diagnostic.get("window_state", "unknown")
        zone_overrides = {key: value for key, value in (overrides or {}).items() if key not in {"window_open", "window_tilted", "window_unknown"}}
        if window_state in {"open", "open_or_tilted"}:
            zone_overrides["window_open"] = True
        elif window_state == "tilted":
            zone_overrides["window_tilted"] = True
        elif window_state not in {"closed", "closed_or_clear"}:
            zone_overrides["window_unknown"] = True
        decision = evaluate_decision(
            schedule_active=active,
            overrides=zone_overrides,
            comfort_temperature=float(comfort),
            night_temperature=float(night),
            chimney_temperature=base_context.get("chimney_temperature", 25.0),
            summer_mode=base_context.get("summer_mode", "compatibility"),
            frost_temperature=base_context.get("frost_temperature", 5.0),
            hvac_supports_off=base_context.get("hvac_supports_off", True),
        )
        if decision.mode == "comfort" and window is not None and window.target_temperature is not None:
            decision = replace(decision, target_temperature=window.target_temperature)
        measured = diagnostic.get("room_temperature")
        thermostat_count = diagnostic.get("thermostat_count", 0)
        unavailable_count = diagnostic.get("unavailable_thermostats", 0)
        thermostats_unavailable = thermostat_count > 0 and unavailable_count >= thermostat_count
        target = decision.target_temperature
        # Unknown measurements, unsafe window states and disabled HVAC are
        # not evidence of heat demand.
        if measured is None or target is None or thermostats_unavailable or window_state not in {"closed", "closed_or_clear"} or decision.target_hvac_mode == "off":
            heat_demand = None
        else:
            heat_demand = float(measured) < float(target)
        result.append({
            "room_temperature": measured,
            "temperature_source": diagnostic.get("temperature_source"),
            "heat_demand": heat_demand,
            "zone_id": zone_id,
            "name": str(zone.get("name") or zone_id),
            "mode": decision.mode,
            "target_temperature": decision.target_temperature,
            "target_hvac_mode": decision.target_hvac_mode,
            "reason": decision.reason,
            "window_state": window_state,
            "thermostat_count": thermostat_count,
            "unavailable_thermostats": unavailable_count,
            "thermostats_unavailable": thermostats_unavailable,
            "passive": True,
            "scope": "target_and_window_safety_preview",
            "commands": [],
        })
    return result


def summarize_zone_heat_demand(previews: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize passive room demand; never authorize boiler operation.

    A single requesting room does not grant ownership of the shared boiler.
    Unknown or missing room measurements remain visible and cannot be treated
    as a reliable all-clear.
    """
    requesting = [str(item["zone_id"]) for item in previews if item.get("heat_demand") is True]
    satisfied = [str(item["zone_id"]) for item in previews if item.get("heat_demand") is False]
    unknown = [str(item["zone_id"]) for item in previews if item.get("heat_demand") is None]
    return {
        "requesting_zone_ids": requesting,
        "satisfied_zone_ids": satisfied,
        "unknown_zone_ids": unknown,
        "any_heat_demand": bool(requesting),
        "all_zones_known": bool(previews) and not unknown,
        "boiler_control_authorized": False,
        "passive": True,
        "commands": [],
    }
