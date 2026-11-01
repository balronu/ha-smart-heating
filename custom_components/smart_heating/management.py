"""Persistent, passive management model for Smart Heating zones and devices."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
from uuid import NAMESPACE_URL, uuid4, uuid5

from .models import ScheduleValidationError, WeeklySchedule

SCHEMA_VERSION = 5
COLLECTION_KEYS = ("persons", "zones", "sensors")
SENSOR_TYPES = ("window", "tilt", "temperature", "thermostat")
SAFETY_MODES = ("party", "visit", "return_home", "summer", "chimney_sweep", "frost_protection")
OPERATING_MODES = ("automatic", "manual_heat", "manual_setback")
WINDOW_DEVICE_CLASSES = {"window", "door", "opening"}
WINDOW_OPEN_STATES = {"on", "open", "opened", "offen", "true"}
WINDOW_TILT_STATES = {"tilt", "tilted", "gekippt", "gekipp", "gekippte"}
WINDOW_CLOSED_STATES = {"off", "closed", "close", "geschlossen", "false"}
TEMPERATURE_UNITS = {"°c", "°f", "c", "f"}
# Name hints are retained only as explanatory metadata.  They must never make
# an HA area heating-relevant by themselves: a house room and a camper area
# are both neutral until an explicit Smart-Heating choice or a real local
# heating device provides evidence.
INDOOR_AREA_HINTS = ("wohn", "zimmer", "küche", "kueche", "bad", "schlaf", "büro", "buero", "flur", "diele", "ess", "living", "bed", "bath", "office", "hall")
OUTDOOR_TEMPERATURE_HINTS = (
    "outdoor", "outside", "weather", "wetter", "außen", "aussen", "outside", "forecast",
)
TECHNICAL_TEMPERATURE_HINTS = (
    "battery", "batterie", "cpu", "gpu", "disk", "filament", "drucker", "pve", "nas", "nvme",
    "smart", "ssd", "hdd", "taupunkt", "dewpoint", "feuchte", "humidity", "spannung", "voltage",
    "leistung", "power", "verbrauch", "uptime", "scheduler", "zeitplan", "diagnostic", "diagnose",
)
CONTACT_TEMPERATURE_HINTS = ("fenster", "tür", "tuer", "door", "kontakt", "contact", "öffnung", "offnung")
SAFETY_MODE_HINTS = {
    "party": ("party", "feier"),
    "visit": ("besuch", "guest", "gast"),
    "return_home": ("heimweg", "heimkehr", "rückkehr", "rueckkehr", "return", "homecoming"),
    "summer": ("sommer", "summer"),
    "chimney_sweep": ("schornstein", "feger", "chimney"),
    "frost_protection": ("frost", "frostschutz"),
}
SAFETY_MODE_PREFERRED_HELPERS = {
    "party": "input_boolean.party",
    "visit": "input_boolean.besuch",
    "return_home": "input_boolean.heimweg",
    "summer": "input_boolean.heizung_sommermodus",
    "chimney_sweep": "input_boolean.schornsteinfeger",
}
SPECIAL_MODE_BINDINGS = ("internal", "entity", "helper_create")
SPECIAL_MODE_ACTIVATION_TYPES = ("internal", "entity", "binary_sensor", "switch", "presence", "time", "combined")
WINDOW_HANDLING = ("normal", "ignore_tilted", "ignore_open", "ignore_all")
WINDOW_STRATEGIES = ("none", "setback", "frost", "pause_demand", "custom_temperature")
WINDOW_CONTACT_ROLES = ("unassigned", "tilt", "open")
WINDOW_CONTACT_ROLE_LABELS = {"unassigned": "Nicht zugeordnet", "tilt": "Gekippt-Sensor", "open": "Offen-Sensor"}
SPECIAL_MODE_TYPES = (*SAFETY_MODES, "custom")
SUPPORTED_CUSTOM_BEHAVIORS = ("passive_only",)
SPECIAL_MODE_DEFINITIONS = {
    "party": ("Party", "Komfortbetrieb zeitweise passiv anzeigen."),
    "visit": ("Besuch", "Besuch passiv berücksichtigen."),
    "return_home": ("Heimweg", "Bevorstehende Rückkehr passiv anzeigen."),
    "summer": ("Sommermodus", "Sommerstatus passiv anzeigen."),
    "chimney_sweep": ("Schornsteinfeger", "Höchste fachliche Priorität in der Vorschau; keine Heizbefehle."),
    "frost_protection": ("Frostschutz", "Frostschutzstatus passiv anzeigen."),
}


def discover_persons(hass: Any) -> list[dict[str, Any]]:
    """Return all native HA person entities; never discover trackers as persons."""
    states = getattr(getattr(hass, "states", None), "async_all", lambda _domain: [])("person")
    return [
        {
            "entity_id": state.entity_id,
            "name": getattr(state, "name", state.entity_id),
            "state": str(state.state),
            "available": str(state.state) not in {"unknown", "unavailable"},
        }
        for state in sorted(states, key=lambda item: item.entity_id)
    ]


def discover_helper_entities(hass: Any) -> list[dict[str, Any]]:
    """Return only boolean helpers suitable for passive special-mode status."""
    states = getattr(getattr(hass, "states", None), "async_all", lambda _domain: [])
    result = []
    for state in states("input_boolean"):
        entity_id = state.entity_id
        name = _entity_name(state, entity_id)
        haystack = f"{name} {entity_id}".lower()
        suggestions = [mode for mode, hints in SAFETY_MODE_HINTS.items() if any(hint in haystack for hint in hints)]
        preferred_for = [mode for mode, preferred in SAFETY_MODE_PREFERRED_HELPERS.items() if preferred == entity_id]
        suggestions = list(dict.fromkeys(preferred_for + suggestions))
        current = str(state.state).lower()
        result.append({
            "entity_id": entity_id,
            "name": name,
            "state": str(state.state),
            "domain": "input_boolean",
            "passive": True,
            "available": current not in {"unknown", "unavailable"},
            "active": current == "on",
            "status": "aktiv" if current == "on" else "inaktiv" if current == "off" else "nicht verfügbar",
            "suggested_for": suggestions,
            "preferred_for": preferred_for,
            "suitable": True,
        })
    return sorted(result, key=lambda item: (item["name"].lower(), item["entity_id"]))


def person_presence(hass: Any, persons: list[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate selected native person states without treating unknown as away."""
    selected = [item for item in persons if item.get("enabled", True) and item.get("presence_entities")]
    states = []
    for item in selected:
        entity_id = item["presence_entities"][0]
        state = hass.states.get(entity_id)
        states.append({"person_id": item.get("id"), "entity_id": entity_id, "state": str(state.state) if state else "missing"})
    if not states:
        return {"status": "disabled", "home": False, "away": False, "unknown": False, "persons": []}
    unknown = any(item["state"] in {"unknown", "unavailable", "missing"} for item in states)
    home = any(item["state"] == "home" for item in states)
    away = bool(states) and not unknown and not home and all(item["state"] not in {"home", "unknown", "unavailable", "missing"} for item in states)
    return {"status": "home" if home else "unknown" if unknown else "away" if away else "unknown", "home": home, "away": away, "unknown": unknown, "persons": states}


def zone_status(hass: Any, zones: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    """Return read-only availability and observed HVAC state per configured zone."""
    result = []
    for zone in zones:
        thermostats = []
        for entity_id in zone.get("thermostat_entities", []):
            state = hass.states.get(entity_id)
            thermostats.append({"entity_id": entity_id, "state": str(state.state) if state else "missing", "hvac_action": state.attributes.get("hvac_action") if state else None})
        temperatures = []
        for entity_id in zone.get("temperature_entities", []):
            state = hass.states.get(entity_id)
            temperatures.append({"entity_id": entity_id, "state": str(state.state) if state else "missing"})
        result.append({"zone_id": zone.get("id"), "name": zone.get("name"), "enabled": zone.get("enabled", True), "thermostats": thermostats, "temperatures": temperatures, "available": bool(thermostats) and any(item["state"] not in {"missing", "unknown", "unavailable"} for item in thermostats), "thermostat_count": len(thermostats), "unavailable_thermostats": sum(item["state"] in {"missing", "unknown", "unavailable"} for item in thermostats), "lead_thermostat_entity": zone.get("lead_thermostat_entity")})
    return result


def zone_backend_summary(hass: Any, zones: list[Mapping[str, Any]], management: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Expose passive per-room window/thermostat diagnostics for the UI."""
    from .backend_engine import evaluate_window_contacts, evaluate_window_groups, evaluate_window_strategy

    result = []
    for zone in zones:
        assigned_contacts = []
        if management:
            area_ids = set(zone.get("area_ids", []))
            for kind in ("window", "tilt"):
                for configured in management.get("sensors", {}).get(kind, []):
                    if configured.get("ignored") or (configured.get("area_id") not in area_ids and zone.get("id") not in configured.get("zone_ids", [])):
                        continue
                    state = hass.states.get(configured.get("entity_id"))
                    assigned_contacts.append({**configured, "state": getattr(state, "state", "missing"), "name": configured.get("name") or configured.get("entity_id")})
        contact_evaluation = evaluate_window_contacts(assigned_contacts) if assigned_contacts else None
        groups = []
        for group in zone.get("window_groups", []):
            sensors = []
            for sensor in group.get("sensors", []):
                state = hass.states.get(sensor.get("entity_id"))
                sensors.append({"entity_id": sensor.get("entity_id"), "state": getattr(state, "state", "missing"), "semantics": sensor.get("semantics", "binary")})
            groups.append({**group, "sensors": sensors})
        windows = evaluate_window_groups(groups)
        if contact_evaluation:
            windows = {"windows": [], "state": contact_evaluation["state"], "conflicts": [], "contacts": contact_evaluation["contacts"]}
        delays = zone.get("window_delays", {})
        reaction = evaluate_window_strategy(state=windows["state"], strategy=zone.get("window_strategy", "none"), tilted_delay=delays.get("tilted", 0), open_delay=delays.get("open", 0), close_delay=delays.get("closed", 0))
        status = next((item for item in zone_status(hass, [zone]) if item["zone_id"] == zone.get("id")), {})
        result.append({"zone_id": zone.get("id"), "name": zone.get("name"), "thermostats": status.get("thermostats", []), "thermostat_count": len(status.get("thermostats", [])), "window_state": windows["state"], "window_groups": windows["windows"], "window_contacts": windows.get("contacts", []), "window_conflicts": windows["conflicts"], "window_reaction": reaction, "passive": True})
    return result


def internal_zone_settings(management: Mapping[str, Any], zone_id: str) -> dict[str, Any]:
    data = normalize_management(management)
    return deepcopy(data["internal"]["zones"].get(zone_id, {}))


def _id(value: Any) -> str:
    return str(value) if value else uuid4().hex


def default_management() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "persons": [],
        "zones": [],
        "relevant_area_ids": [],
        "sensors": {kind: [] for kind in SENSOR_TYPES},
        "controller": {},
        "outdoor_temperature": {},
        "safety": {"modes": {mode: {"enabled": False, "helper_entity": "", "temperature": None, "duration_minutes": None, "zone_ids": []} for mode in SAFETY_MODES}},
        "special_modes": default_special_modes(),
        "internal": {
            "enabled": True,
            "operating_mode": "automatic",
            "party": False,
            "visit": False,
            "return_home": False,
            "summer": False,
            "chimney_sweep": False,
            "templates": {},
            "zones": {},
        },
    }


def default_special_modes() -> list[dict[str, Any]]:
    """Return stable, passive objects for the built-in special modes."""
    return [
        {
            "id": mode,
            "name": label,
            "description": description,
            "mode_type": mode,
            "behavior": mode,
            "available": False,
            "active": False,
            "temperature": None,
            "duration_minutes": None,
            "zone_ids": [],
            "binding_type": "internal",
            "status_source": "",
            "helper_entity": "",
            "controllable": False,
            "origin": "builtin",
        }
        for mode, (label, description) in SPECIAL_MODE_DEFINITIONS.items()
    ]


def _special_mode_id(item: Mapping[str, Any], index: int = 0) -> str:
    value = str(item.get("id") or "").strip()
    if value:
        return value
    mode_type = str(item.get("mode_type") or item.get("function") or "custom").strip()
    if mode_type in SPECIAL_MODE_DEFINITIONS:
        return mode_type
    name = str(item.get("name") or "custom").strip().lower() or "custom"
    return f"custom-{uuid5(NAMESPACE_URL, f'{name}:{index}').hex[:12]}"


def _normalize_special_mode(item: Mapping[str, Any], fallback: Mapping[str, Any] | None = None, index: int = 0) -> dict[str, Any]:
    source = dict(fallback or {}) | dict(item)
    mode_type = str(source.get("mode_type") or source.get("function") or "custom")
    if mode_type not in SPECIAL_MODE_TYPES:
        mode_type = "custom"
    label, description = SPECIAL_MODE_DEFINITIONS.get(mode_type, (str(source.get("name") or "Benutzerdefinierter Modus"), "Benutzerdefinierter passiver Sondermodus."))
    helper_entity = str(item.get("helper_entity") or item.get("status_source") or source.get("helper_entity") or source.get("status_source") or "")
    binding = str(item.get("binding_type") or ("entity" if helper_entity else source.get("binding_type") or "internal"))
    if binding not in SPECIAL_MODE_BINDINGS:
        binding = "internal"
    if binding == "entity" and not helper_entity:
        binding = "internal"
    return {
        "id": _special_mode_id(source, index),
        "name": str(source.get("name") or label).strip() or label,
        "description": str(source.get("description") or description).strip(),
        "mode_type": mode_type,
        "behavior": str(source.get("behavior") or (mode_type if mode_type != "custom" else "passive_only")),
        "available": bool(item.get("available", item.get("enabled", source.get("available", False)))),
        "active": bool(item.get("active", source.get("active", False))),
        "temperature": source.get("temperature"),
        "duration_minutes": source.get("duration_minutes"),
        "zone_ids": [str(value) for value in source.get("zone_ids", []) if str(value)],
        "binding_type": binding,
        "status_source": helper_entity,
        "helper_entity": helper_entity,
            "controllable": False,
            "origin": str(source.get("origin") or ("builtin" if mode_type in SPECIAL_MODE_DEFINITIONS else "user")),
            "priority": int(source.get("priority", {"chimney_sweep": 1000, "frost_protection": 900}.get(mode_type, 500))),
            "activation_type": str(source.get("activation_type") or ("entity" if helper_entity else "internal")),
            "activation_source": str(source.get("activation_source") or helper_entity),
            "expires_at": source.get("expires_at"),
            "window_handling": str(source.get("window_handling") or "normal"),
            "effect": deepcopy(source.get("effect") if isinstance(source.get("effect"), Mapping) else {"action": "observe"}),
        }


def normalize_special_modes(source: Mapping[str, Any] | None, safety_modes: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Merge legacy safety mappings into stable special-mode objects once."""
    legacy = safety_modes if isinstance(safety_modes, Mapping) else {}
    explicit = source.get("special_modes", []) if isinstance(source, Mapping) else []
    by_id: dict[str, dict[str, Any]] = {}
    for index, item in enumerate(default_special_modes()):
        legacy_item = legacy.get(item["id"], {}) if isinstance(legacy, Mapping) else {}
        by_id[item["id"]] = _normalize_special_mode(legacy_item, item, index)
    if isinstance(explicit, list):
        for index, item in enumerate(explicit, len(by_id)):
            if not isinstance(item, Mapping):
                continue
            normalized = _normalize_special_mode(item, by_id.get(str(item.get("id") or "")), index)
            by_id[normalized["id"]] = normalized
    return list(by_id.values())


def normalize_management(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize persisted management data without touching HA entities."""
    source = value or {}
    result = default_management()
    result["schema_version"] = SCHEMA_VERSION
    result["persons"] = [deepcopy(item) for item in source.get("persons", []) if isinstance(item, Mapping)]
    result["zones"] = [deepcopy(item) for item in source.get("zones", []) if isinstance(item, Mapping)]
    result["relevant_area_ids"] = [str(item) for item in source.get("relevant_area_ids", []) if str(item)]
    source_sensors = source.get("sensors", {})
    if isinstance(source_sensors, Mapping):
        result["sensors"] = {
            kind: [deepcopy(item) for item in source_sensors.get(kind, []) if isinstance(item, Mapping)]
            for kind in SENSOR_TYPES
        }
    result["controller"] = deepcopy(source.get("controller", {})) if isinstance(source.get("controller", {}), Mapping) else {}
    result["outdoor_temperature"] = deepcopy(source.get("outdoor_temperature", {})) if isinstance(source.get("outdoor_temperature", {}), Mapping) else {}
    result["safety"] = deepcopy(source.get("safety", {})) if isinstance(source.get("safety", {}), Mapping) else {}
    raw_modes = result["safety"].get("modes", {})
    result["safety"]["modes"] = {
        mode: {
            "enabled": bool((raw_modes.get(mode, {}) if isinstance(raw_modes, Mapping) else {}).get("enabled", False)),
            "helper_entity": str((raw_modes.get(mode, {}) if isinstance(raw_modes, Mapping) else {}).get("helper_entity", "") or ""),
            "temperature": (raw_modes.get(mode, {}) if isinstance(raw_modes, Mapping) else {}).get("temperature"),
            "duration_minutes": (raw_modes.get(mode, {}) if isinstance(raw_modes, Mapping) else {}).get("duration_minutes"),
            "zone_ids": list((raw_modes.get(mode, {}) if isinstance(raw_modes, Mapping) else {}).get("zone_ids", []) or []),
        }
        for mode in SAFETY_MODES
    }
    result["special_modes"] = normalize_special_modes(source, result["safety"]["modes"])
    result["safety"].setdefault("priority", ["chimney_sweep", "frost_protection", "party", "visit", "return_home", "summer"])
    internal = source.get("internal", {})
    result["internal"].update(deepcopy(internal) if isinstance(internal, Mapping) else {})
    if result["internal"].get("operating_mode") not in OPERATING_MODES:
        result["internal"]["operating_mode"] = "automatic"
    result["internal"]["zones"] = deepcopy(result["internal"].get("zones", {})) if isinstance(result["internal"].get("zones", {}), Mapping) else {}
    for collection in (result["persons"], result["zones"]):
        for item in collection:
            item["id"] = _id(item.get("id"))
            item.setdefault("enabled", True)
    for zone in result["zones"]:
        legacy_thermostat = zone.get("thermostat_entity")
        if not zone.get("thermostat_entities") and legacy_thermostat:
            zone["thermostat_entities"] = [legacy_thermostat]
        zone["thermostat_entities"] = list(dict.fromkeys(str(item) for item in zone.get("thermostat_entities", []) if str(item).startswith("climate.")))
        zone.setdefault("lead_thermostat_entity", zone["thermostat_entities"][0] if zone["thermostat_entities"] else None)
        if zone.get("lead_thermostat_entity") not in zone["thermostat_entities"]:
            zone["lead_thermostat_entity"] = zone["thermostat_entities"][0] if zone["thermostat_entities"] else None
        zone["window_strategy"] = str(zone.get("window_strategy") or "none") if str(zone.get("window_strategy") or "none") in WINDOW_STRATEGIES else "none"
        raw_delays = zone.get("window_delays", {}) if isinstance(zone.get("window_delays"), Mapping) else {}
        zone["window_delays"] = {key: max(0, int(raw_delays.get(key, 0) or 0)) for key in ("tilted", "open", "closed")}
        zone["window_custom_temperature"] = zone.get("window_custom_temperature")
        groups = zone.get("window_groups", [])
        zone["window_groups"] = [deepcopy(group) for group in groups if isinstance(group, Mapping)] if isinstance(groups, list) else []
        if not zone.get("temperature_entities") and zone.get("temperature_entity"):
            zone["temperature_entities"] = [zone["temperature_entity"]]
        zone["temperature_entities"] = list(dict.fromkeys(str(item) for item in zone.get("temperature_entities", []) if str(item).startswith("sensor.")))
        settings = result["internal"]["zones"].setdefault(zone["id"], {})
        settings.setdefault("comfort_temperature", zone.get("comfort_temperature", 20.0))
        settings.setdefault("night_temperature", zone.get("night_temperature", 17.0))
        settings.setdefault("operating_mode", "automatic")
        settings.setdefault("schedule", deepcopy(zone.get("schedule", {})))
    for kind, items in result["sensors"].items():
        for item in items:
            item["id"] = _id(item.get("id"))
            item["type"] = kind
            item.setdefault("enabled", True)
            item.setdefault("zone_ids", [])
            # Older beta data used both names. Preserve the assignment while
            # exposing one canonical field to the UI and runtime.
            if not item.get("area_id") and item.get("assigned_area_id"):
                item["area_id"] = item["assigned_area_id"]
            if not item.get("area_name") and item.get("assigned_area_name"):
                item["area_name"] = item["assigned_area_name"]
            item.setdefault("state_semantics", "open_or_tilted" if kind in {"window", "tilt"} else "")
            item.setdefault("ignored", False)
            item.setdefault("window_group_id", None)
            if kind in {"window", "tilt"}:
                item.setdefault("legacy_state_semantics", item.get("state_semantics") or ("tilt" if kind == "tilt" else "binary"))
                role = str(item.get("contact_role", item.get("window_role", "unassigned")) or "unassigned")
                item["contact_role"] = role if role in WINDOW_CONTACT_ROLES else "unassigned"
            if kind == "window" and item.get("state_semantics") == "open_or_tilted":
                item["state_semantics"] = "binary"
    if result["controller"]:
        result["controller"]["id"] = _id(result["controller"].get("id"))
    return result


def validate_management(value: Mapping[str, Any] | None) -> list[str]:
    data = normalize_management(value)
    errors: list[str] = []
    mode_ids: set[str] = set()
    for mode in data.get("special_modes", []):
        mode_id = str(mode.get("id", ""))
        if not mode_id or mode_id in mode_ids:
            errors.append(f"duplicate_special_mode_id:{mode_id or 'missing'}")
        mode_ids.add(mode_id)
        if mode.get("binding_type") not in SPECIAL_MODE_BINDINGS:
            errors.append(f"invalid_special_mode_binding:{mode_id}")
        if mode.get("activation_type") not in SPECIAL_MODE_ACTIVATION_TYPES:
            errors.append(f"invalid_special_mode_activation:{mode_id}")
        if mode.get("window_handling") not in WINDOW_HANDLING:
            errors.append(f"invalid_window_handling:{mode_id}")
        effect = mode.get("effect", {})
        if not isinstance(effect, Mapping) or effect.get("action", "observe") not in {"observe", "comfort", "setback", "fixed_temperature", "relative_temperature", "pause_demand", "override_windows"}:
            errors.append(f"invalid_special_mode_effect:{mode_id}")
        if mode.get("mode_type") == "custom" and mode.get("behavior") not in SUPPORTED_CUSTOM_BEHAVIORS:
            errors.append(f"unsupported_special_mode_behavior:{mode_id}")
        if mode.get("binding_type") == "helper_create":
            errors.append(f"helper_creation_unsupported:{mode_id}")
    ids: set[str] = set()
    for collection_name in ("persons", "zones"):
        for item in data[collection_name]:
            item_id = item["id"]
            if item_id in ids:
                errors.append(f"duplicate_id:{item_id}")
            ids.add(item_id)
            if not str(item.get("name", "")).strip():
                errors.append(f"missing_name:{collection_name}:{item_id}")
    thermostat_owners: dict[str, str] = {}
    zone_ids = {item["id"] for item in data["zones"]}
    person_ids = {item["id"] for item in data["persons"]}
    for person in data["persons"]:
        if any(zone_id not in zone_ids for zone_id in person.get("zone_ids", [])):
            errors.append(f"unknown_zone_reference:person:{person['id']}")
    for zone in data["zones"]:
        try:
            WeeklySchedule.from_mapping(zone.get("schedule", {})) if zone.get("schedule") else None
        except ScheduleValidationError as err:
            errors.append(f"invalid_schedule:{zone['id']}:{err}")
        for thermostat in zone.get("thermostat_entities", []):
            if thermostat in thermostat_owners and zone.get("enabled", True):
                errors.append(f"thermostat_conflict:{thermostat}:{thermostat_owners[thermostat]}:{zone['id']}")
            thermostat_owners.setdefault(thermostat, zone["id"])
        if zone.get("window_strategy") not in WINDOW_STRATEGIES:
            errors.append(f"invalid_window_strategy:{zone['id']}")
        group_ids: set[str] = set()
        for group in zone.get("window_groups", []):
            group_id = str(group.get("id", ""))
            if not group_id or group_id in group_ids:
                errors.append(f"duplicate_window_group:{zone['id']}:{group_id or 'missing'}")
            group_ids.add(group_id)
            for sensor in group.get("sensors", []):
                if sensor.get("semantics", "binary") not in {"binary", "tilt", "open", "multistate", "opening"}:
                    errors.append(f"invalid_window_sensor_semantics:{zone['id']}:{sensor.get('entity_id', '')}")
        for person_id in zone.get("person_ids", []):
            if person_id not in person_ids:
                errors.append(f"unknown_person_reference:{zone['id']}:{person_id}")
    for kind, items in data["sensors"].items():
        for item in items:
            if not str(item.get("entity_id", "")):
                errors.append(f"missing_entity:{kind}:{item['id']}")
            if any(zone_id not in zone_ids for zone_id in item.get("zone_ids", [])):
                errors.append(f"unknown_zone_reference:{kind}:{item['id']}")
            if kind == "temperature" and item.get("strategy", "primary_fallback") not in {"primary_fallback", "first_available", "mean_valid"}:
                errors.append(f"invalid_temperature_strategy:{item['id']}")
            if kind in {"window", "tilt"} and item.get("contact_role", "unassigned") not in WINDOW_CONTACT_ROLES:
                errors.append(f"invalid_window_contact_role:{item['id']}")
    sensor_owners: dict[str, str] = {}
    for kind, items in data["sensors"].items():
        for item in items:
            entity_id = str(item.get("entity_id", ""))
            if not entity_id:
                continue
            owner = sensor_owners.get(entity_id)
            if owner and owner != item["id"]:
                errors.append(f"duplicate_sensor_entity:{entity_id}:{owner}:{item['id']}")
            sensor_owners.setdefault(entity_id, item["id"])
    outdoor = data.get("outdoor_temperature", {})
    if outdoor and not str(outdoor.get("entity_id", "")).startswith("sensor."):
        errors.append("invalid_outdoor_temperature_entity")
    return sorted(set(errors))


def discover_areas(hass: Any) -> list[dict[str, Any]]:
    """Read Home Assistant's public Area/Entity registries for room suggestions."""
    try:
        from homeassistant.helpers import area_registry, entity_registry

        areas = area_registry.async_get(hass).async_list_areas()
        entities = entity_registry.async_get(hass).entities
    except (AttributeError, ImportError):
        return []
    result = []
    for area in sorted(areas, key=lambda item: item.name.lower()):
        entity_ids = sorted(entity.entity_id for entity in entities.values() if entity.area_id == area.id)
        result.append({"area_id": area.id, "name": area.name, "entity_ids": entity_ids})
    return result


def area_suggestions(hass: Any, management: Mapping[str, Any] | None = None) -> list[dict[str, Any]]:
    """Add read-only, evidence-based suggestions to discovered areas.

    HA area names are deliberately neutral.  Relevance comes from an explicit
    Smart-Heating selection or a climate entity actually assigned to that HA
    area; a name such as ``Wohnzimmer`` or ``Wohnmobil`` is not evidence.
    """
    result = []
    management = management or {}
    explicit_ids = set(management.get("relevant_area_ids", []))
    configured_area_ids = {
        area_id
        for zone in management.get("zones", [])
        for area_id in zone.get("area_ids", [])
        if area_id
    }
    configured_contacts = {
        str(item.get("entity_id")): item
        for kind in ("window", "tilt")
        for item in management.get("sensors", {}).get(kind, [])
        if isinstance(item, Mapping) and item.get("entity_id") and not item.get("ignored")
    }
    discovered_contacts = {item["entity_id"]: item for item in discover_window_contacts(hass, configured_contacts)}
    for area in discover_areas(hass):
        area = dict(area)
        contacts = []
        for entity_id, discovered in discovered_contacts.items():
            configured = configured_contacts.get(entity_id, {})
            assigned_area_id = configured.get("area_id")
            # A matching HA area is only discovery context, never a saved
            # Smart-Heating assignment. Room cards count explicit mappings;
            # unassigned contacts remain in the central review list.
            if assigned_area_id == area["area_id"]:
                contact = dict(discovered)
                # Keep HA registry placement and Smart-Heating assignment
                # separate. The latter is the source of the room count.
                contact["ha_area_id"] = discovered.get("area_id")
                contact["ha_area_name"] = discovered.get("area_name")
                contact["assigned_area_id"] = assigned_area_id
                contact["assigned_area_name"] = configured.get("area_name")
                contacts.append(contact)
        climates = discover_climate_entities(hass, area["entity_ids"])
        temperatures = discover_temperature_entities(hass, area["entity_ids"])
        room_temperatures = [item for item in temperatures if item.get("temperature_role") == "room"]
        explicit = area["area_id"] in explicit_ids
        local_heating_device = bool(climates)
        area["suggested_indoor"] = False
        area["relevant"] = explicit or local_heating_device or area["area_id"] in configured_area_ids
        area["relevance_source"] = (
            "confirmed" if explicit or area["area_id"] in configured_area_ids
            else "local_heating_device" if local_heating_device
            else "unassigned"
        )
        area["relevance_label"] = {
            "confirmed": "bestätigt",
            "local_heating_device": "Gerätehinweis – Bestätigung empfohlen",
            "unassigned": "nicht zugeordnet",
        }[area["relevance_source"]]
        area["suggestions"] = {
            "thermostat_entities": [entity["entity_id"] for entity in climates],
            "temperature_entities": [entity["entity_id"] for entity in room_temperatures],
            "window_entities": [item["entity_id"] for item in contacts],
        }
        area["thermostat_entities"] = climates
        area["temperature_entities"] = room_temperatures
        area["additional_temperature_entities"] = [item for item in temperatures if item.get("temperature_role") != "room"]
        area["window_contacts"] = contacts
        area["window_contact_count"] = len(contacts)
        result.append(area)
    return result


def _entity_state(hass: Any, entity_id: str) -> Any:
    return getattr(getattr(hass, "states", None), "get", lambda _entity_id: None)(entity_id)


def _entity_name(state: Any, entity_id: str) -> str:
    attrs = getattr(state, "attributes", {}) if state else {}
    return str(attrs.get("friendly_name") or getattr(state, "name", None) or entity_id)


def _entity_record(hass: Any, entity_id: str, role: str) -> dict[str, Any]:
    state = _entity_state(hass, entity_id)
    attrs = getattr(state, "attributes", {}) if state else {}
    value = str(getattr(state, "state", "missing")) if state else "missing"
    available = value not in {"unknown", "unavailable", "missing"}
    numeric = None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        pass
    return {
        "entity_id": entity_id,
        "name": _entity_name(state, entity_id),
        "state": value,
        "unit": attrs.get("unit_of_measurement"),
        "device_class": attrs.get("device_class"),
        "available": available,
        "numeric_state": numeric,
        "role": role,
    }


def _entity_area(hass: Any, entity_id: str) -> tuple[str | None, str | None]:
    """Return HA area metadata for grouping; never change the registry."""
    try:
        from homeassistant.helpers import area_registry, entity_registry

        item = entity_registry.async_get(hass).async_get(entity_id)
        area_id = getattr(item, "area_id", None)
        area = area_registry.async_get(hass).async_get_area(area_id) if area_id else None
        return area_id, getattr(area, "name", None) if area else None
    except (AttributeError, ImportError):
        return None, None


def _registry_device_class(hass: Any, entity_id: str) -> str:
    try:
        from homeassistant.helpers import entity_registry
        item = entity_registry.async_get(hass).async_get(entity_id)
        return str(getattr(item, "device_class", "") or "")
    except (AttributeError, ImportError):
        return ""


def is_eligible_temperature_entity(hass: Any, entity_id: str) -> bool:
    """Accept only real temperature sensors; unknown values stay selectable."""
    if not entity_id.startswith("sensor."):
        return False
    state = _entity_state(hass, entity_id)
    attrs = getattr(state, "attributes", {}) if state else {}
    device_class = str(attrs.get("device_class") or _registry_device_class(hass, entity_id)).lower()
    unit = str(attrs.get("unit_of_measurement") or "").strip().lower()
    return device_class == "temperature" and unit in TEMPERATURE_UNITS


def discover_temperature_entities(hass: Any, entity_ids: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Discover temperature sensors and classify room versus technical sources."""
    ids = list(entity_ids or [])
    if entity_ids is None:
        states = getattr(getattr(hass, "states", None), "async_all", lambda _domain: [])("sensor")
        ids = [state.entity_id for state in states]
    result = []
    for entity_id in ids:
        if not is_eligible_temperature_entity(hass, entity_id):
            continue
        item = _entity_record(hass, entity_id, "temperature")
        item["area_id"], item["area_name"] = _entity_area(hass, entity_id)
        haystack = f"{item['name']} {entity_id}".lower()
        matches = [hint for hint in TECHNICAL_TEMPERATURE_HINTS if hint in haystack]
        contact_matches = [hint for hint in CONTACT_TEMPERATURE_HINTS if hint in haystack]
        item["temperature_role"] = "outdoor" if any(hint in haystack for hint in OUTDOOR_TEMPERATURE_HINTS) else "technical" if matches else "contact" if contact_matches else "room"
        item["classification_reason"] = (
            "Geeigneter Außentemperaturfühler" if item["temperature_role"] == "outdoor"
            else "Technische Quelle: " + ", ".join(matches) if matches
            else "Fenster-/Kontaktfühler: manuell prüfen" if contact_matches
            else "Geeigneter Raumtemperaturfühler"
        )
        result.append(item)
    return sorted(result, key=lambda item: ({"outdoor": 0, "room": 1, "contact": 2, "technical": 3}.get(item["temperature_role"], 4), item["name"].lower(), item["entity_id"]))


def discover_climate_entities(hass: Any, entity_ids: list[str] | tuple[str, ...] | None = None) -> list[dict[str, Any]]:
    """Discover climate entities, including Tado climates, read-only."""
    ids = list(entity_ids or [])
    if entity_ids is None:
        states = getattr(getattr(hass, "states", None), "async_all", lambda _domain: [])("climate")
        ids = [state.entity_id for state in states]
    result = []
    for entity_id in ids:
        if not entity_id.startswith("climate."):
            continue
        item = _entity_record(hass, entity_id, "climate")
        item["area_id"], item["area_name"] = _entity_area(hass, entity_id)
        result.append(item)
    return sorted(result, key=lambda item: (item["name"].lower(), item["entity_id"]))


def discover_controller_entities(hass: Any, configured_entity_id: str | None = None) -> list[dict[str, Any]]:
    """Return observable controller signals separately from active control."""
    states = getattr(getattr(hass, "states", None), "async_all", lambda _domain: [])
    ids = [state.entity_id for state in states("input_boolean")] + [state.entity_id for state in states("climate")]
    records = [_entity_record(hass, entity_id, "observed_controller" if entity_id.startswith("input_boolean.") else "climate") for entity_id in ids]
    for item in records:
        item["passive"] = True
        item["configured"] = item["entity_id"] == configured_entity_id
        item["description"] = "Beobachtbares Steuersignal; keine Schaltung" if item["entity_id"].startswith("input_boolean.") else "Thermostatstatus; keine Befehle"
    return sorted(records, key=lambda item: (not item["configured"], item["name"].lower(), item["entity_id"]))


def is_suggested_indoor_area(name: str) -> bool:
    """Transparent suggestion only; HA Areas remain manually selectable."""
    value = str(name).strip().lower()
    return any(token in value for token in INDOOR_AREA_HINTS)


def _window_status(state: Any) -> str:
    value = str(getattr(state, "state", "missing") if state else "missing").lower()
    if value in {"unavailable", "nicht verfügbar"}:
        return "unavailable"
    if value in {"open_unknown", "open unknown", "offen unbekannt"}:
        return "open_unknown"
    if value in WINDOW_OPEN_STATES:
        return "open"
    if value in WINDOW_TILT_STATES:
        return "tilted"
    if value in WINDOW_CLOSED_STATES:
        return "closed"
    return "unknown"


def is_eligible_window_entity(entity_id: str, device_class: str) -> bool:
    """Return whether an entity is safe to offer as an automatic contact."""
    return entity_id.startswith("binary_sensor.") and str(device_class).lower() in WINDOW_DEVICE_CLASSES


def aggregate_window_status(statuses: list[str] | tuple[str, ...]) -> str:
    """Aggregate contacts conservatively; ambiguity never becomes closed."""
    values = {str(value) for value in statuses}
    if "unavailable" in values:
        return "unavailable"
    if "unknown" in values:
        return "unknown"
    if "open_unknown" in values:
        return "open_unknown"
    if "open" in values:
        return "open"
    if "tilted" in values:
        return "tilted"
    return "closed" if values else "unknown"


def discover_window_contacts(hass: Any, configured_entities: list[str] | tuple[str, ...] = ()) -> list[dict[str, Any]]:
    """Discover opening contacts and return a non-destructive inventory.

    Registry entries and live states are only read. Missing/unavailable and
    duplicate-looking contacts are explicit review flags; this function never
    changes an entity, registry entry, or Config Entry.
    """
    try:
        from homeassistant.helpers import area_registry, entity_registry

        areas = {item.id: item.name for item in area_registry.async_get(hass).async_list_areas()}
        registry = entity_registry.async_get(hass).entities
    except (AttributeError, ImportError):
        areas, registry = {}, {}

    candidates: list[dict[str, Any]] = []
    for item in registry.values():
        entity_id = getattr(item, "entity_id", "")
        domain = entity_id.split(".", 1)[0] if "." in entity_id else ""
        # Binary contacts and explicitly opening-class sensors are eligible.
        # Names alone never make a sensor a contact.
        if domain not in {"binary_sensor", "sensor"}:
            continue
        state = hass.states.get(entity_id)
        attrs = getattr(state, "attributes", {}) if state else {}
        device_class = str(attrs.get("device_class") or getattr(item, "device_class", "") or "").lower()
        name = getattr(item, "name", None) or getattr(item, "original_name", None) or getattr(state, "name", None) or entity_id
        label = f"{name} {entity_id}".lower()
        multi_state_opening = domain == "sensor" and device_class == "opening"
        if not is_eligible_window_entity(entity_id, device_class) and not multi_state_opening:
            continue
        area_id = getattr(item, "area_id", None)
        candidates.append({
            "entity_id": entity_id,
            "name": name,
            "area_id": area_id,
            "area_name": areas.get(area_id, "Kein Raum zugeordnet"),
            "device_class": device_class or "unbekannt",
            "state": str(getattr(state, "state", "missing")) if state else "missing",
            "status": _window_status(state),
            "available": bool(state) and str(getattr(state, "state", "")) not in {"unknown", "unavailable"},
            "configured": entity_id in set(configured_entities),
        })

    duplicate_keys: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for item in candidates:
        key = (" ".join(str(item["name"]).lower().split()), item["area_id"])
        duplicate_keys.setdefault(key, []).append(item)
    for item in candidates:
        key = (" ".join(str(item["name"]).lower().split()), item["area_id"])
        item["review_flags"] = []
        if len(duplicate_keys[key]) > 1:
            item["review_flags"].append("duplicate_name")
        if not item["available"]:
            item["review_flags"].append("stale_or_unavailable")
        item["review_required"] = bool(item["review_flags"])
    return sorted(candidates, key=lambda item: (str(item["area_name"]).lower(), str(item["name"]).lower(), item["entity_id"]))


def window_contact_summary(hass: Any, management: Mapping[str, Any]) -> dict[str, Any]:
    """Return room/group counts for the panel without changing assignments."""
    from .backend_engine import evaluate_window_contacts
    configured_items = [
        item
        for kind in ("window", "tilt")
        for item in management.get("sensors", {}).get(kind, [])
        if isinstance(item, Mapping) and item.get("entity_id")
    ]
    configured_ids = [item["entity_id"] for item in configured_items]
    contacts = discover_window_contacts(hass, configured_ids)
    by_entity = {item["entity_id"]: item for item in configured_items}
    discovered_ids = {item["entity_id"] for item in contacts}
    for contact in contacts:
        configured_item = by_entity.get(contact["entity_id"])
        if configured_item:
            contact["id"] = configured_item.get("id")
            contact["zone_ids"] = list(configured_item.get("zone_ids", []))
            contact["configured_type"] = configured_item.get("type")
            contact["state_semantics"] = configured_item.get("state_semantics", "open_or_tilted")
            contact["contact_role"] = configured_item.get("contact_role", "unassigned")
            contact["role_label"] = WINDOW_CONTACT_ROLE_LABELS.get(contact["contact_role"], "Nicht zugeordnet")
            contact["legacy_state_semantics"] = configured_item.get("legacy_state_semantics", configured_item.get("state_semantics", "binary"))
            # This is an internal override only; the HA Area Registry is
            # never modified by Smart Heating.
            if configured_item.get("area_id"):
                contact["assigned_area_id"] = configured_item["area_id"]
                contact["assigned_area_name"] = configured_item.get("area_name", configured_item["area_id"])
            contact["ignored"] = bool(configured_item.get("ignored", False))
    for configured_item in configured_items:
        if configured_item["entity_id"] in discovered_ids:
            continue
        contacts.append({
            "id": configured_item.get("id"),
            "entity_id": configured_item["entity_id"],
            "name": configured_item["entity_id"],
            "area_id": configured_item.get("area_id"),
            "area_name": configured_item.get("area_name", "Manuell zugeordnet" if configured_item.get("area_id") else "Kein Raum zugeordnet"),
            "device_class": "nicht ermittelt",
            "state": "missing",
            "status": "unknown",
            "available": False,
            "configured": True,
            "zone_ids": list(configured_item.get("zone_ids", [])),
            "configured_type": configured_item.get("type"),
            "state_semantics": configured_item.get("state_semantics", "open_or_tilted"),
            "contact_role": configured_item.get("contact_role", "unassigned"),
            "role_label": WINDOW_CONTACT_ROLE_LABELS.get(configured_item.get("contact_role", "unassigned"), "Nicht zugeordnet"),
            "review_flags": ["configured_but_not_eligible"],
            "review_required": True,
            "ignored": bool(configured_item.get("ignored", False)),
        })
    ignored = [item for item in contacts if item.get("ignored")]
    contacts = [item for item in contacts if not item.get("ignored")]
    groups: dict[str, dict[str, Any]] = {}
    for contact in contacts:
        key = contact.get("assigned_area_id") or contact.get("area_id") or "__unassigned__"
        area_name = contact.get("assigned_area_name") or contact.get("area_name")
        group = groups.setdefault(key, {"area_id": key if key != "__unassigned__" else None, "area_name": area_name, "count": 0, "open": 0, "open_unknown": 0, "tilted": 0, "closed": 0, "unknown": 0, "unavailable": 0, "review": 0, "contacts": []})
        group["count"] += 1
        group[contact["status"]] = group.get(contact["status"], 0) + 1
        group["review"] += int(contact["review_required"])
        group["contacts"].append(contact)
        evaluation = evaluate_window_contacts(group["contacts"])
        group["aggregate_status"] = evaluation["state"]
        group["automation_state"] = evaluation["state"]
        diagnostics = {item["entity_id"]: item for item in evaluation["contacts"]}
        contact.update(diagnostics.get(contact["entity_id"], {}))
        group["contact_diagnostics"] = evaluation["contacts"]
    return {
        "total": len(contacts) + len(ignored),
        "configured": sum(item["configured"] for item in contacts) + len(ignored),
        "review": sum(item["review_required"] for item in contacts),
        "ignored": len(ignored),
        "ignored_contacts": ignored,
        "groups": list(groups.values()),
        "contacts": contacts,
    }


def _raw_window_contact_role(management: Mapping[str, Any] | None, entity_id: str) -> str | None:
    """Return a stored role without applying the normalizer's default."""
    if not isinstance(management, Mapping):
        return None
    sensors = management.get("sensors", {})
    if not isinstance(sensors, Mapping):
        return None
    for kind in ("window", "tilt"):
        items = sensors.get(kind, [])
        if not isinstance(items, list):
            continue
        for item in items:
            if isinstance(item, Mapping) and item.get("entity_id") == entity_id:
                value = item.get("contact_role")
                return str(value) if value is not None else None
    return None


def build_window_role_diagnostics(
    *,
    config_entry_options: Mapping[str, Any] | None,
    runtime_management: Mapping[str, Any] | None,
    readback_management: Mapping[str, Any] | None,
    assigned_contacts: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...] = (),
) -> list[dict[str, Any]]:
    """Compare three read-only role sources for assigned contacts.

    The ConfigEntry and runtime mappings are intentionally read as supplied;
    missing ``contact_role`` keys are not converted to ``unassigned`` here.
    ``readback_management`` represents the exact management object exposed by
    the administrative readback, including any normalization it performs.
    """
    options_management = config_entry_options.get("management", {}) if isinstance(config_entry_options, Mapping) else {}
    rows: list[dict[str, Any]] = []
    for contact in assigned_contacts:
        if not isinstance(contact, Mapping):
            continue
        entity_id = str(contact.get("entity_id") or "")
        if not entity_id:
            continue
        config_role = _raw_window_contact_role(options_management, entity_id)
        runtime_role = _raw_window_contact_role(runtime_management, entity_id)
        readback_role = _raw_window_contact_role(readback_management, entity_id)
        values = (config_role, runtime_role, readback_role)
        present = [value for value in values if value is not None]
        matches = len(present) == 3 and len(set(present)) == 1
        rows.append({
            "entity_id": entity_id,
            "name": str(contact.get("name") or entity_id),
            "assigned_area_id": contact.get("assigned_area_id"),
            "config_entry_role": config_role,
            "runtime_role": runtime_role,
            "readback_role": readback_role,
            "matches": matches,
            "status": "Übereinstimmung" if matches else "Abweichung" if present else "Nicht vorhanden",
        })
    return rows


def upsert_item(data: dict[str, Any], collection: str, item: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(item))
    normalized["id"] = _id(normalized.get("id"))
    normalized.setdefault("enabled", True)
    if collection == "persons":
        normalized.setdefault("presence_entities", [])
        normalized.setdefault("zone_ids", [])
        normalized["presence_entities"] = [entity for entity in normalized["presence_entities"] if str(entity).startswith("person.")]
    elif collection == "zones":
        legacy_thermostat = normalized.get("thermostat_entity")
        normalized.setdefault("thermostat_entities", [legacy_thermostat] if legacy_thermostat else [])
        normalized["thermostat_entities"] = list(dict.fromkeys(str(entity) for entity in normalized["thermostat_entities"] if str(entity).startswith("climate.")))
        normalized["lead_thermostat_entity"] = normalized.get("lead_thermostat_entity") or (normalized["thermostat_entities"][0] if normalized["thermostat_entities"] else None)
        if normalized["lead_thermostat_entity"] and normalized["lead_thermostat_entity"] not in normalized["thermostat_entities"]:
            raise ValueError("lead_thermostat_not_in_zone")
        normalized.setdefault("temperature_entities", [])
        normalized.setdefault("window_entities", [])
        normalized.setdefault("tilt_entities", [])
        normalized.setdefault("comfort_temperature", None)
        normalized.setdefault("night_temperature", None)
        normalized.setdefault("schedule", {})
        zone_settings = data.setdefault("internal", {}).setdefault("zones", {}).setdefault(normalized["id"], {})
        for key in ("comfort_temperature", "night_temperature", "frost_temperature"):
            if normalized.get(key) is not None:
                zone_settings[key] = normalized[key]
    elif collection == "sensors":
        kind = str(normalized.get("type", ""))
        if kind not in SENSOR_TYPES:
            raise ValueError("invalid_sensor_type")
        normalized.setdefault("zone_ids", [])
        items = data["sensors"][kind]
        entity_id = str(normalized.get("entity_id", ""))
        if entity_id and any(
            existing.get("entity_id") == entity_id and existing.get("id") != normalized["id"]
            for sensor_items in data["sensors"].values()
            for existing in sensor_items
        ):
            raise ValueError(f"duplicate_sensor_entity:{entity_id}")
        items[:] = [existing for existing in items if existing.get("id") != normalized["id"]]
        items.append(normalized)
        errors = validate_management(data)
        if errors:
            items.pop()
            raise ValueError(";".join(errors))
        return normalized
    else:
        raise ValueError("invalid_collection")
    items = data[collection]
    items[:] = [existing for existing in items if existing.get("id") != normalized["id"]]
    items.append(normalized)
    errors = validate_management(data)
    if errors:
        items.pop()
        raise ValueError(";".join(errors))
    return normalized


def remove_item(data: dict[str, Any], collection: str, item_id: str) -> bool:
    if collection == "sensors":
        removed = False
        for kind in SENSOR_TYPES:
            before = len(data["sensors"][kind])
            data["sensors"][kind] = [item for item in data["sensors"][kind] if item.get("id") != item_id]
            removed = removed or len(data["sensors"][kind]) != before
        return removed
    else:
        collections = [collection]
    removed = False
    for key in collections:
        before = len(data.get(key, []))
        data[key] = [item for item in data.get(key, []) if item.get("id") != item_id]
        removed = removed or len(data[key]) != before
    if collection == "zones":
        removed = data.setdefault("internal", {}).setdefault("zones", {}).pop(item_id, None) is not None or removed
    return removed
