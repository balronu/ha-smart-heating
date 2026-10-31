"""Config-entry storage normalization; no recorder or HA internal storage access."""

from __future__ import annotations

from typing import Any, Mapping

from .const import DEFAULT_SCHEDULE, MODE_COMPATIBILITY
from .models import WeeklySchedule


def load_schedule(options: Mapping[str, Any]) -> WeeklySchedule:
    return WeeklySchedule.from_mapping(options.get("schedule", DEFAULT_SCHEDULE))


def effective_config(entry: Any) -> dict[str, Any]:
    """Return persisted data plus option overrides without touching HA internals."""
    result = dict(getattr(entry, "data", {}) or {})
    result.update(getattr(entry, "options", {}) or {})
    return result


def normalized_options(options: Mapping[str, Any], schedule: WeeklySchedule | None = None) -> dict[str, Any]:
    result = dict(options)
    result["schedule"] = (schedule or load_schedule(options)).as_dict()
    result.setdefault("simulation", True)
    result.setdefault("special_modes", {})
    result.setdefault("operation_mode", MODE_COMPATIBILITY)
    return result
