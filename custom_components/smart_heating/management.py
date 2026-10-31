"""Persistent, passive management model for Smart Heating zones and devices."""

from __future__ import annotations

from copy import deepcopy
from typing import Any, Mapping
from uuid import uuid4

from .models import ScheduleValidationError, WeeklySchedule

SCHEMA_VERSION = 2
COLLECTION_KEYS = ("persons", "zones", "sensors")
SENSOR_TYPES = ("window", "tilt", "temperature", "thermostat")


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


def _id(value: Any) -> str:
    return str(value) if value else uuid4().hex


def default_management() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "persons": [],
        "zones": [],
        "sensors": {kind: [] for kind in SENSOR_TYPES},
        "controller": {},
    }


def normalize_management(value: Mapping[str, Any] | None) -> dict[str, Any]:
    """Normalize persisted management data without touching HA entities."""
    source = value or {}
    result = default_management()
    result["schema_version"] = SCHEMA_VERSION
    result["persons"] = [deepcopy(item) for item in source.get("persons", []) if isinstance(item, Mapping)]
    result["zones"] = [deepcopy(item) for item in source.get("zones", []) if isinstance(item, Mapping)]
    source_sensors = source.get("sensors", {})
    if isinstance(source_sensors, Mapping):
        result["sensors"] = {
            kind: [deepcopy(item) for item in source_sensors.get(kind, []) if isinstance(item, Mapping)]
            for kind in SENSOR_TYPES
        }
    result["controller"] = deepcopy(source.get("controller", {})) if isinstance(source.get("controller", {}), Mapping) else {}
    for collection in (result["persons"], result["zones"]):
        for item in collection:
            item["id"] = _id(item.get("id"))
            item.setdefault("enabled", True)
    for kind, items in result["sensors"].items():
        for item in items:
            item["id"] = _id(item.get("id"))
            item["type"] = kind
            item.setdefault("enabled", True)
            item.setdefault("zone_ids", [])
    if result["controller"]:
        result["controller"]["id"] = _id(result["controller"].get("id"))
    return result


def validate_management(value: Mapping[str, Any] | None) -> list[str]:
    data = normalize_management(value)
    errors: list[str] = []
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
        for person_id in zone.get("person_ids", []):
            if person_id not in person_ids:
                errors.append(f"unknown_person_reference:{zone['id']}:{person_id}")
    for kind, items in data["sensors"].items():
        for item in items:
            if not str(item.get("entity_id", "")):
                errors.append(f"missing_entity:{kind}:{item['id']}")
            if any(zone_id not in zone_ids for zone_id in item.get("zone_ids", [])):
                errors.append(f"unknown_zone_reference:{kind}:{item['id']}")
    return sorted(set(errors))


def upsert_item(data: dict[str, Any], collection: str, item: Mapping[str, Any]) -> dict[str, Any]:
    normalized = deepcopy(dict(item))
    normalized["id"] = _id(normalized.get("id"))
    normalized.setdefault("enabled", True)
    if collection == "persons":
        normalized.setdefault("presence_entities", [])
        normalized.setdefault("zone_ids", [])
        normalized["presence_entities"] = [entity for entity in normalized["presence_entities"] if str(entity).startswith("person.")]
    elif collection == "zones":
        normalized.setdefault("thermostat_entities", [])
        normalized.setdefault("temperature_entities", [])
        normalized.setdefault("window_entities", [])
        normalized.setdefault("tilt_entities", [])
        normalized.setdefault("comfort_temperature", None)
        normalized.setdefault("night_temperature", None)
        normalized.setdefault("schedule", {})
    elif collection == "sensors":
        kind = str(normalized.get("type", ""))
        if kind not in SENSOR_TYPES:
            raise ValueError("invalid_sensor_type")
        normalized.setdefault("zone_ids", [])
        items = data["sensors"][kind]
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
    return removed
