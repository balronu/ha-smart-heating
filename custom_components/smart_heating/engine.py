"""Server-side calculations for the passive Smart Heating coordinator."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Mapping

from .models import WeeklySchedule, decision_for_state


def calculate_status(
    schedule: WeeklySchedule,
    *,
    now: datetime,
    timezone: str,
    overrides: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    active = schedule.active_at(now, timezone)
    next_switch, next_state = schedule.next_switch(now, timezone)
    mode, reason = decision_for_state(schedule_active=active, overrides=overrides)
    return {
        "schedule_active": active,
        "next_switch": next_switch.isoformat() if next_switch else None,
        "next_state": next_state,
        "mode": mode,
        "reason": reason,
        "simulated": True,
    }

