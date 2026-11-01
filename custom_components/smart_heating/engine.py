"""Server-side calculations for the passive Smart Heating coordinator."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .models import WeeklySchedule, evaluate_decision
from .backend_engine import calculate_room_demand, evaluate_window_groups, evaluate_window_strategy, resolve_special_modes


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
    mode_result = resolve_special_modes(context.get("special_modes", ()), now=now, zone_id=context.get("zone_id"))
    window_result = evaluate_window_groups(context.get("window_groups", ()))
    window_reaction = evaluate_window_strategy(
        state=window_result["state"],
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
        windows=window_result,
        window_reaction=window_reaction,
        thermostats=context.get("thermostats", ()),
        mode_result=mode_result,
        now=now,
    )
    return {
        "schedule_active": active,
        "next_switch": next_switch.isoformat() if next_switch else None,
        "next_state": next_state,
        "mode": decision.mode,
        "actual_mode": decision.mode,
        "mode_source": decision.source,
        "reason": decision.reason,
        "target_temperature": decision.target_temperature,
        "target_hvac_mode": decision.target_hvac_mode,
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
    }
