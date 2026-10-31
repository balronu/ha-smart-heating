"""Supported-API migration planning and an isolated transactional adapter."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Mapping, Protocol
from uuid import NAMESPACE_URL, uuid4, uuid5

from .discovery import discover_entities
from .control import analyze_control_plane
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


class MigrationState(StrEnum):
    PREVIEWED = "previewed"
    CONFIRMED = "confirmed"
    SNAPSHOTTED = "snapshotted"
    ACTIVATED = "activated"
    VERIFIED = "verified"
    ROLLED_BACK = "rolled_back"
    REFUSED = "refused"
    FAILED = "failed"


def _conflict(code: str, severity: str, message: str) -> dict[str, str]:
    return {"code": code, "severity": severity, "message": message}


def preview_migration(hass: Any, entry: Any, manual_schedule: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a proposal from public state only; no writes or services."""
    discovery = discover_entities(hass)
    control_plane = analyze_control_plane(hass, getattr(entry, "data", {}) | getattr(entry, "options", {}))
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
        conflicts.append(_conflict("fixture_requires_confirmation", "warning", "The known transition groups are a proposal only and are never imported automatically."))
    selected = discovery.get("selected", {})
    if discovery.get("ambiguous"):
        conflicts.append(_conflict("ambiguous_entities", "error", "Some entity roles have multiple equally plausible candidates."))
    if discovery.get("missing"):
        conflicts.append(_conflict("missing_entities", "warning", "Some optional heating roles were not discovered."))
    if selected.get("heating_boolean"):
        conflicts.append(_conflict("existing_writer", "error", "The existing heating helper may have writers outside this integration; single-writer safety cannot be proven through supported read-only APIs."))
    return {
        "entry_id": entry.entry_id,
        "mode": "preview_only",
        "automatic_import": False,
        "source": source,
        "fixture_schedule": REFERENCE_SCHEDULE,
        "proposed_schedule": schedule,
        "discovery": discovery,
        "control_plane": control_plane,
        "conflicts": conflicts,
        "activation_allowed": False,
        "rollback": {"prepared": False, "activation_required": True, "description": "Production activation is locked until the old writer is explicitly and safely replaced."},
        "message": "Review conflicts and confirm only in an isolated test transport.",
    }


class MigrationTransport(Protocol):
    """Write/read boundary injected only by isolated tests or a future adapter."""

    def snapshot(self) -> Mapping[str, Any]: ...
    def activate(self, schedule: Mapping[str, Any]) -> None: ...
    def readback(self) -> Mapping[str, Any]: ...
    def restore(self, snapshot: Mapping[str, Any]) -> None: ...


@dataclass(slots=True)
class MigrationTransaction:
    plan: Mapping[str, Any]
    transport: MigrationTransport
    transaction_id: str = field(default_factory=lambda: uuid4().hex)
    idempotency_key: str = ""
    state: MigrationState = MigrationState.PREVIEWED
    snapshot_data: Mapping[str, Any] | None = None
    error: str | None = None
    last_result: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.idempotency_key:
            self.idempotency_key = uuid5(NAMESPACE_URL, repr(self.plan.get("proposed_schedule"))).hex

    def confirm(self, confirmation: str) -> None:
        if confirmation != self.transaction_id:
            raise PermissionError("Migration confirmation token does not match")
        if not self.plan.get("proposed_schedule"):
            raise ValueError("No validated schedule proposal exists")
        if self.plan.get("activation_allowed") is False:
            raise PermissionError("Activation is locked by the single-writer safety gate")
        self.state = MigrationState.CONFIRMED

    def execute_isolated(self, confirmation: str) -> Mapping[str, Any]:
        if self.state is MigrationState.VERIFIED and self.last_result is not None:
            return self.last_result
        self.confirm(confirmation)
        try:
            self.snapshot_data = dict(self.transport.snapshot())
            self.state = MigrationState.SNAPSHOTTED
            self.transport.activate(self.plan["proposed_schedule"])
            self.state = MigrationState.ACTIVATED
            observed = dict(self.transport.readback())
            if observed.get("schedule") != self.plan["proposed_schedule"]:
                raise RuntimeError("Migration read-back does not match the proposal")
            self.state = MigrationState.VERIFIED
            self.last_result = observed
            return observed
        except Exception as err:
            self.error = str(err)
            if self.snapshot_data is not None:
                self.transport.restore(self.snapshot_data)
                self.state = MigrationState.ROLLED_BACK
            else:
                self.state = MigrationState.FAILED
            raise

    def rollback(self) -> None:
        if self.snapshot_data is None:
            raise RuntimeError("No migration snapshot exists")
        self.transport.restore(self.snapshot_data)
        self.state = MigrationState.ROLLED_BACK
