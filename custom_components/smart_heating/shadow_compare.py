"""Pure, non-executing comparison of legacy, Smart Heating, and observed state."""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Mapping


def _get(value: Any, key: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(key, default)
    return getattr(value, key, default)


def compare_shadow_decision(
    *,
    timestamp: datetime,
    zone_id: str | None,
    observed_thermostat: Mapping[str, Any] | None,
    legacy_decision: Mapping[str, Any] | None,
    smart_decision: Mapping[str, Any] | None,
    planned_actor_action: Mapping[str, Any] | None,
    active_special_mode: Mapping[str, Any] | None,
    priority: int | None,
    schedule_decision: Mapping[str, Any] | None,
    window_state: str | None,
    presence: Mapping[str, Any] | None,
    data_quality: str,
    max_legacy_age: timedelta = timedelta(minutes=15),
) -> dict[str, Any]:
    """Return an auditable comparison without treating equal setpoints as proof.

    ``legacy_decision`` must carry ``proven: True`` and a timestamp before it
    can establish parity. Fixtures may provide a synthetic trace, but the
    result retains ``source`` and ``simulated`` so it cannot be mistaken for a
    live HA trace.
    """
    legacy = legacy_decision if isinstance(legacy_decision, Mapping) else None
    smart = smart_decision if isinstance(smart_decision, Mapping) else {}
    observed = observed_thermostat if isinstance(observed_thermostat, Mapping) else {}
    legacy_target = _get(legacy, "target_temperature") if legacy else None
    smart_target = _get(smart, "target_temperature")
    legacy_timestamp_raw = _get(legacy, "timestamp") if legacy else None
    legacy_timestamp = None
    if isinstance(legacy_timestamp_raw, datetime):
        legacy_timestamp = legacy_timestamp_raw
    elif isinstance(legacy_timestamp_raw, str):
        try:
            legacy_timestamp = datetime.fromisoformat(legacy_timestamp_raw)
        except ValueError:
            legacy_timestamp = None
    source = _get(legacy, "source", "missing") if legacy else "missing"
    proven = bool(_get(legacy, "proven", False)) if legacy else False
    simulated = bool(_get(legacy, "simulated", False)) if legacy else False
    legacy_age_seconds = None
    if legacy_timestamp is not None:
        legacy_age_seconds = (timestamp - legacy_timestamp).total_seconds()
    if not proven or legacy_target is None:
        result = "comparison_not_possible"
        reason = "Keine nachgewiesene Legacy-Entscheidung oder kein Legacy-Sollwert verfügbar."
    elif legacy_timestamp is None:
        result = "comparison_not_possible"
        reason = "Der Legacy-Nachweis besitzt keinen validen Zeitstempel."
    else:
        age = timestamp - legacy_timestamp
        if age < timedelta(0) or age > max_legacy_age:
            result = "stale_data"
            reason = "Der letzte Legacy-Nachweis ist älter als das zulässige Vergleichsfenster."
        elif smart_target is None:
            result = "comparison_not_possible"
            reason = "Smart Heating konnte keinen Sollwert berechnen."
        elif float(legacy_target) == float(smart_target):
            result = "match_proven"
            reason = "Legacy- und Smart-Heating-Sollwert stimmen innerhalb des nachgewiesenen Zeitfensters überein."
        else:
            result = "divergence_proven"
            reason = "Legacy- und Smart-Heating-Sollwert weichen bei einem nachgewiesenen Legacy-Trace ab."
    mode = active_special_mode if isinstance(active_special_mode, Mapping) else None
    return {
        "timestamp": timestamp.isoformat(),
        "zone_id": zone_id,
        "observed_thermostat": dict(observed),
        "observed_target_temperature": observed.get("temperature"),
        "legacy_decision": dict(legacy) if legacy else None,
        "legacy_target_temperature": legacy_target,
        "smart_target_temperature": smart_target,
        "planned_actor_action": dict(planned_actor_action) if isinstance(planned_actor_action, Mapping) else None,
        "active_special_mode": dict(mode) if mode else None,
        "priority": priority,
        "schedule_decision": dict(schedule_decision) if isinstance(schedule_decision, Mapping) else None,
        "window_state": window_state,
        "presence": dict(presence) if isinstance(presence, Mapping) else {},
        "data_quality": data_quality,
        "comparison": result,
        "reason": reason,
        "legacy_source": source,
        "legacy_proven": proven,
        "legacy_age_seconds": legacy_age_seconds,
        "simulated": simulated,
        "passive": True,
        "smart_takeover_allowed": False,
    }
