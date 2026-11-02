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


def build_installation_plan(discovery: Mapping[str, Any], control_plane: Mapping[str, Any]) -> dict[str, Any]:
    """Return an explicit, UI-safe first-install decision."""
    ambiguous = list(discovery.get("ambiguous", []))
    selected = discovery.get("selected", {})
    missing = list(discovery.get("missing", []))
    required = ("climate_entity", "heating_permission", "comfort_setpoint", "night_setpoint")
    missing_required = [role for role in required if not selected.get(role)]
    errors = sorted(set(ambiguous + missing_required))
    return {
        "default_mode": "compatibility",
        "compatibility_ready": not errors,
        "compatibility_effect": "observe schedule and leave the existing thermostat writer untouched",
        "full_mode_ready": False,
        "full_mode_blockers": [
            "legacy automation writer cannot be disabled or proven through this read-only plan",
            "Simple Scheduler has no supported public export in this installation",
        ],
        "selected_roles": selected,
        "missing_optional_roles": missing,
        "ambiguous_roles": ambiguous,
        "manual_action": "review the proposal and confirm unresolved roles in the UI; no YAML is required",
        "control_plane": control_plane,
    }


def inspect_legacy_automation(hass: Any) -> dict[str, Any]:
    """Read the public state of the known legacy automation; never infer its rules."""
    entity_id = "automation.heizung_automatik_ersetzt_node_red"
    state = hass.states.get(entity_id) if hasattr(hass.states, "get") else None
    if state is None:
        return {"entity_id": entity_id, "present": False, "enabled": None, "rules_verified": False}
    raw = str(state.state)
    return {
        "entity_id": entity_id,
        "present": True,
        "enabled": True if raw == "on" else False if raw == "off" else None,
        "rules_verified": False,
        "rules_source": "not_available_from_public_state",
    }


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
    installation = build_installation_plan(discovery, control_plane)
    legacy_helpers = inspect_legacy_helpers(hass)
    legacy_automation = inspect_legacy_automation(hass)
    conflicts.append(_conflict("legacy_rules_unverified", "error", "The public automation state does not expose triggers, conditions, actions, or priority order; rule parity requires an independently reviewed configuration export."))
    if legacy_automation["present"] and legacy_automation["enabled"] is True:
        conflicts.append(_conflict("legacy_automation_active", "error", "The existing heating automation is active; no second writer may be enabled."))
    elif legacy_automation["present"] and legacy_automation["enabled"] is None:
        conflicts.append(_conflict("legacy_automation_state_unknown", "error", "The existing automation state is unavailable; writer ownership cannot be verified."))
    elif not legacy_automation["present"]:
        conflicts.append(_conflict("legacy_automation_not_found", "warning", "The known legacy automation was not found in public states; its absence does not prove there are no other writers."))
    invalid_helpers = [entity_id for entity_id, item in legacy_helpers.items() if item["available"] and not item["valid"]]
    missing_helpers = [entity_id for entity_id, item in legacy_helpers.items() if not item["available"]]
    if invalid_helpers:
        conflicts.append(_conflict("invalid_legacy_helpers", "warning", "Some legacy helper values are present but invalid; review the listed entities before migration."))
    if missing_helpers:
        conflicts.append(_conflict("missing_legacy_helpers", "warning", "Legacy helper values are missing or unavailable; they cannot be imported or assumed to be off."))
    return {
        "entry_id": entry.entry_id,
        "mode": "preview_only",
        "automatic_import": False,
        "source": source,
        "fixture_schedule": REFERENCE_SCHEDULE,
        "proposed_schedule": schedule,
        "discovery": discovery,
        "control_plane": control_plane,
        "installation": installation,
        "legacy_helpers": legacy_helpers,
        "legacy_automation": legacy_automation,
        "rule_parity": {"verified": False, "required": ["triggers", "conditions", "actions", "priority_order", "window_handling", "presence_handling", "special_modes", "setpoints", "reset_automation"], "source": "configuration_review_required"},
        "invalid_legacy_helpers": invalid_helpers,
        "missing_legacy_helpers": missing_helpers,
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


def inspect_legacy_helpers(hass: Any) -> dict[str, Any]:
    """Read and validate allowlisted heating helper states without writes.

    Unknown/missing or malformed values are never treated as valid migration
    inputs. The raw state remains visible for user review.
    """
    from math import isfinite

    ids = ("input_boolean.heizung", "input_boolean.heizung_freigabe", "input_boolean.heizung_sommermodus", "input_boolean.party", "input_boolean.besuch", "input_boolean.heimweg", "input_boolean.schornsteinfeger", "input_number.heiztemperatur", "input_number.absenktemperatur")
    states = {item.entity_id: item for domain in ("input_boolean", "input_number") for item in hass.states.async_all(domain)}
    result = {}
    for entity_id in ids:
        item = states.get(entity_id)
        raw = str(item.state) if item is not None else None
        available = raw is not None and raw.lower() not in ("unknown", "unavailable", "")
        if entity_id.startswith("input_boolean."):
            valid = available and raw in ("on", "off")
        else:
            try:
                valid = available and isfinite(float(raw))
            except (TypeError, ValueError, OverflowError):
                valid = False
        result[entity_id] = {"state": raw, "available": available, "valid": bool(valid)}
    return result
