"""Server-side calculations for the passive Smart Heating coordinator."""

from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any, Mapping

from .models import WeeklySchedule, evaluate_decision
from .backend_engine import calculate_room_demand, evaluate_window_groups, evaluate_window_strategy, resolve_passive_decision, resolve_special_modes


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
    decision = evaluate_decision(
        schedule_active=active,
        overrides=overrides,
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
        },
    }
