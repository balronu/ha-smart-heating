"""Bounded read-only Home Assistant data adapters for shadow diagnostics."""

from __future__ import annotations

import asyncio
import inspect
from datetime import datetime
from typing import Any, Awaitable, Callable, Mapping


KNOWN_READ_ONLY_ENTITIES = (
    "automation.heizung_automatik_ersetzt_node_red",
    "input_boolean.heizung",
    "input_boolean.heizung_freigabe",
    "input_boolean.heizung_sommermodus",
    "input_boolean.schornsteinfeger",
)


def _safe_state(hass: Any, entity_id: str, timestamp: str) -> dict[str, Any]:
    state = hass.states.get(entity_id) if getattr(hass, "states", None) else None
    if state is None:
        return {"entity_id": entity_id, "state": "missing", "available": False, "source": "hass.states", "timestamp": timestamp}
    attributes = getattr(state, "attributes", {}) or {}
    return {
        "entity_id": entity_id,
        "state": str(getattr(state, "state", "missing")),
        "available": str(getattr(state, "state", "missing")) not in {"unknown", "unavailable", "missing"},
        "temperature": attributes.get("temperature"),
        "current_temperature": attributes.get("current_temperature"),
        "hvac_action": attributes.get("hvac_action"),
        "hvac_modes": list(attributes.get("hvac_modes", [])),
        "source": "hass.states",
        "timestamp": timestamp,
    }


def normalize_legacy_trace(trace: Mapping[str, Any] | None, *, timestamp: str) -> dict[str, Any]:
    """Normalize an already available trace; never infer a decision from state."""
    if not isinstance(trace, Mapping):
        return {"status": "missing", "proven": False, "source": "ha.automation_trace", "timestamp": timestamp, "reason": "Kein Legacy-Trace verfügbar."}
    decision = trace.get("decision") if isinstance(trace.get("decision"), Mapping) else {}
    trace_timestamp = trace.get("timestamp")
    if not trace.get("proven") or decision.get("target_temperature") is None or not trace_timestamp:
        return {"status": "incomplete", "proven": False, "source": "ha.automation_trace", "timestamp": trace_timestamp or timestamp, "reason": "Trace enthält keine nachgewiesene Entscheidung mit Sollwert und Zeitstempel."}
    return {
        "status": "proven",
        "proven": True,
        "source": str(trace.get("source") or "ha.automation_trace"),
        "timestamp": str(trace_timestamp),
        "decision": dict(decision),
        "trace_id": str(trace.get("trace_id")) if trace.get("trace_id") else None,
        "simulated": bool(trace.get("simulated", False)),
    }


async def read_only_with_timeout(reader: Callable[[], Any], timeout_seconds: float = 1.0) -> dict[str, Any]:
    """Run an injected read-only reader with a bounded timeout for diagnostics."""
    try:
        value = reader()
        if inspect.isawaitable(value):
            value = await asyncio.wait_for(value, timeout=timeout_seconds)
        return {"status": "ok", "value": value, "timeout_seconds": timeout_seconds}
    except asyncio.TimeoutError:
        return {"status": "timeout", "value": None, "timeout_seconds": timeout_seconds}
    except Exception as err:  # diagnostics must expose failure without secrets
        return {"status": "error", "value": None, "timeout_seconds": timeout_seconds, "error": type(err).__name__}


class ReadOnlyShadowDataAdapter:
    """Read known HA state only; it has no service or config-write interface."""

    def __init__(self, hass: Any, *, clock: Callable[[], datetime] | None = None) -> None:
        self.hass = hass
        self.clock = clock or datetime.now

    def snapshot(
        self,
        *,
        primary_climate: str | None,
        fallback_climate: str | None,
        configured_entities: tuple[str, ...] = (),
        schedule_source_verified: bool = False,
    ) -> dict[str, Any]:
        timestamp = self.clock().astimezone().isoformat()
        entity_ids = tuple(dict.fromkeys((*KNOWN_READ_ONLY_ENTITIES, *(item for item in configured_entities if item))))
        states = {entity_id: _safe_state(self.hass, entity_id, timestamp) for entity_id in entity_ids}
        climates = {
            entity_id: _safe_state(self.hass, entity_id, timestamp)
            for entity_id in (primary_climate, fallback_climate)
            if entity_id
        }
        scheduler = {
            "status": "partial" if not schedule_source_verified else "configured",
            "source": "hass.states",
            "timestamp": timestamp,
            "inputs": {entity_id: states[entity_id] for entity_id in KNOWN_READ_ONLY_ENTITIES if entity_id.startswith("input_boolean.")},
            "missing": [] if schedule_source_verified else ["simple_scheduler_readonly_export"],
        }
        return {
            "timestamp": timestamp,
            "sources": {"states": "hass.states", "legacy_traces": "ha.automation_trace", "scheduler": "hass.states"},
            "automation": states["automation.heizung_automatik_ersetzt_node_red"],
            "climates": climates,
            "scheduler": scheduler,
            "legacy_trace": normalize_legacy_trace(None, timestamp=timestamp),
            "read_only": True,
            "service_calls": 0,
        }
