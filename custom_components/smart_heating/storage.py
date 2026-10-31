"""Config-entry storage normalization; no recorder or HA internal storage access."""

from __future__ import annotations

from typing import Any, Mapping

from .const import DEFAULT_SCHEDULE, MODE_COMPATIBILITY
from .models import WeeklySchedule


def load_schedule(options: Mapping[str, Any]) -> WeeklySchedule:
    schedule = options.get("schedule")
    if not any(schedule.get(day) for day in schedule or {} if day in DEFAULT_SCHEDULE):
        from .management import normalize_management

        management = normalize_management(options.get("management"))
        internal = management.get("internal", {}) if isinstance(management, Mapping) else {}
        zone_settings = internal.get("zones", {}) if isinstance(internal, Mapping) else {}
        for settings in zone_settings.values() if isinstance(zone_settings, Mapping) else ():
            candidate = settings.get("schedule", {}) if isinstance(settings, Mapping) else {}
            if any(candidate.get(day) for day in DEFAULT_SCHEDULE):
                schedule = candidate
                break
    return WeeklySchedule.from_mapping(schedule or DEFAULT_SCHEDULE)


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
