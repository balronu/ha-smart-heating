"""Explicit control boundary for compatibility and full modes.

The integration never calls this module during normal setup.  A caller must
provide both an isolated test flag and proof that the legacy writer is stopped.
That makes the service-call path testable without making production activation
possible by accident.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .const import CONF_CLIMATE_ENTITY, CONF_OPERATION_MODE, CONF_TADO_FALLBACK, MODE_COMPATIBILITY, MODE_FULL
from .models import HeatingDecision


@dataclass(frozen=True, slots=True)
class ControlResult:
    status: str
    entity_id: str | None
    calls: tuple[str, ...]
    reason: str
    rolled_back: bool = False
    heat_demand_verified: bool = False
    heat_demand_status: str = "not_measured"


def analyze_control_plane(hass: Any, config: Mapping[str, Any]) -> dict[str, Any]:
    """Report what public HA state can prove about the two writer layers."""
    automation_candidates = []
    for state in hass.states.async_all("automation"):
        label = f"{getattr(state, 'name', '')} {state.entity_id}".lower()
        if any(token in label for token in ("heizung", "heating", "thermostat", "tado")):
            automation_candidates.append(state.entity_id)
    return {
        "schedule_writer": {"entity": config.get("heating_boolean"), "source": "entity_state_only", "supported_action_export": False},
        "thermostat_writer": {"climate_entity": config.get(CONF_CLIMATE_ENTITY), "legacy_automation_candidates": sorted(automation_candidates), "supported_action_export": False},
        "tado_fallback": config.get(CONF_TADO_FALLBACK),
        "single_writer_proven": False,
        "activation_allowed": False,
        "limitation": "Home Assistant public state does not expose automation action graphs or Simple Scheduler storage.",
    }


def select_climate_entity(hass: Any, config: Mapping[str, Any]) -> str | None:
    """Select the primary climate and use Tado only when it is unavailable."""
    for key in (CONF_CLIMATE_ENTITY, CONF_TADO_FALLBACK):
        entity_id = config.get(key)
        state = hass.states.get(entity_id) if isinstance(entity_id, str) else None
        if state and state.state not in {"unknown", "unavailable"}:
            return entity_id
    return None


async def async_apply_decision(
    hass: Any,
    config: Mapping[str, Any],
    decision: HeatingDecision,
    *,
    activation_confirmed: bool = False,
    legacy_writer_disabled: bool = False,
    isolated_test: bool = False,
) -> ControlResult:
    """Apply a decision only to a deliberately injected isolated HA runtime."""
    operation_mode = config.get(CONF_OPERATION_MODE, MODE_COMPATIBILITY)
    if operation_mode == MODE_COMPATIBILITY:
        return ControlResult("compatibility_noop", None, (), "Compatibility mode leaves the existing thermostat automation in control.", heat_demand_status="delegated_to_legacy_automation")
    if operation_mode != MODE_FULL:
        return ControlResult("refused", None, (), "Unknown operation mode.")
    if not (activation_confirmed and legacy_writer_disabled and isolated_test):
        return ControlResult("locked", None, (), "Full mode requires explicit confirmation, legacy-writer proof, and an isolated test runtime.")
    entity_id = select_climate_entity(hass, config)
    if not entity_id:
        return ControlResult("unavailable", None, (), "No available primary or Tado fallback climate entity.")

    state = hass.states.get(entity_id)
    old_hvac = state.state if state else None
    old_temp = state.attributes.get("temperature") if state else None
    calls: list[str] = []
    try:
        if decision.target_hvac_mode:
            await hass.services.async_call("climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": decision.target_hvac_mode}, blocking=True)
            calls.append("climate.set_hvac_mode")
        if decision.target_temperature is not None and decision.target_hvac_mode != "off":
            await hass.services.async_call("climate", "set_temperature", {"entity_id": entity_id, "temperature": decision.target_temperature}, blocking=True)
            calls.append("climate.set_temperature")
        observed = hass.states.get(entity_id)
        if not observed or (decision.target_hvac_mode and observed.state != decision.target_hvac_mode):
            raise RuntimeError("Climate read-back did not match the requested HVAC mode")
        hvac_action = str(observed.attributes.get("hvac_action", "")).lower()
        demand_verified = decision.target_hvac_mode != "heat" or hvac_action in {"heating", "heat"}
        demand_status = "verified" if demand_verified else "not_exposed_by_device"
        status = "applied" if demand_verified else "applied_unverified_demand"
        return ControlResult(status, entity_id, tuple(calls), decision.reason, heat_demand_verified=demand_verified, heat_demand_status=demand_status)
    except Exception:
        # Roll back only the simulated/explicitly armed target. No helper or
        # scheduler entity is touched by this path.
        if old_hvac:
            await hass.services.async_call("climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": old_hvac}, blocking=True)
        if old_temp is not None:
            await hass.services.async_call("climate", "set_temperature", {"entity_id": entity_id, "temperature": old_temp}, blocking=True)
        return ControlResult("rolled_back", entity_id, tuple(calls), "Read-back failed; previous simulated climate state restored.", True, heat_demand_status="rollback")
