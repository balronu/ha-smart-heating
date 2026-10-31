"""Server-side calculations for the passive Smart Heating coordinator."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .models import WeeklySchedule, evaluate_decision


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
        "heat_demand_verified": False,
        "heat_demand_status": "not_measured",
        "special_modes": {key: bool(value) for key, value in (overrides or {}).items() if key in {"party", "visit", "return_home", "chimney_sweep", "summer"}},
        "simulated": True,
    }
