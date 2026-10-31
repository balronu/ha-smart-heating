"""Safe, read-only migration analysis for Beta 2."""

from __future__ import annotations

from typing import Any, Mapping

from .discovery import discover_entities
from .models import WeeklySchedule

REFERENCE_SCHEDULE = {
    "monday": [{"start": "05:30", "end": "21:00"}],
    "tuesday": [{"start": "05:30", "end": "21:00"}],
    "wednesday": [{"start": "05:30", "end": "21:00"}],
    "thursday": [{"start": "05:30", "end": "21:00"}],
    "friday": [{"start": "05:30", "end": "22:00"}],
    "saturday": [{"start": "07:00", "end": "22:00"}],
    "sunday": [{"start": "07:00", "end": "21:00"}],
}


def _conflict(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def preview_migration(hass: Any, entry: Any, manual_schedule: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a proposal; this function never writes an entry or calls a service."""
    discovery = discover_entities(hass)
    schedule = None
    source = "none"
    conflicts: list[dict[str, str]] = []
    if manual_schedule is not None:
        try:
            schedule = WeeklySchedule.from_mapping(manual_schedule).as_dict()
            source = "manual_ui_proposal"
        except ValueError as err:
            conflicts.append(_conflict("invalid_manual_schedule", "error", str(err)))
    else:
        conflicts.append(_conflict("scheduler_export_unavailable", "warning", "Simple Scheduler data is not exposed through a supported read-only API."))
        conflicts.append(_conflict("fixture_requires_confirmation", "warning", "The known four transition groups are a test fixture only and are never imported automatically."))

    selected = discovery.get("selected", {})
    if discovery.get("ambiguous"):
        conflicts.append(_conflict("ambiguous_entities", "error", "Some entity roles have multiple equally plausible candidates."))
    if discovery.get("missing"):
        conflicts.append(_conflict("missing_entities", "warning", "Some optional heating roles were not discovered."))
    if selected.get("heating_boolean"):
        conflicts.append(_conflict("existing_writer", "warning", "The existing heating helper may have writers outside this integration; duplicate-writer analysis needs an explicit supported export."))
    return {
        "entry_id": entry.entry_id,
        "mode": "preview_only",
        "automatic_import": False,
        "source": source,
        "fixture_schedule": REFERENCE_SCHEDULE,
        "proposed_schedule": schedule,
        "discovery": discovery,
        "conflicts": conflicts,
        "rollback": {"prepared": False, "activation_required": True, "description": "No production mutation is available in Beta 2. A future activation must snapshot the ConfigEntry and preserve the old writer."},
        "message": "Review all conflicts and confirm the proposal in an isolated instance before any future activation.",
    }
