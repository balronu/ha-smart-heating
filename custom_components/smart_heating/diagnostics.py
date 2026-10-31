"""Secret-free diagnostics."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION
from .discovery import discover_entities
from .management import discover_persons, normalize_management, person_presence, validate_management
from .storage import effective_config


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    config = effective_config(entry)
    management = normalize_management(config.get("management"))
    return {
        "integration_version": VERSION,
        "entry_id": entry.entry_id,
        "title": entry.title,
        "options": {
            "timezone": config.get("timezone"),
            "schedule": config.get("schedule", {}),
            "simulation": config.get("simulation", True),
            "configured_entities": sorted(key for key in config if key.endswith("_entity") or key.endswith("_entities")),
            "discovery_roles": sorted(discover_entities(hass).get("roles", {})),
            "ambiguous_roles": discover_entities(hass).get("ambiguous", []),
            "management_schema_version": management["schema_version"],
            "management_validation": validate_management(management),
            "persons": discover_persons(hass),
            "presence": person_presence(hass, management["persons"]),
            "zone_count": len(management["zones"]),
            "sensor_counts": {kind: len(items) for kind, items in management["sensors"].items()},
        },
        "loaded": entry.entry_id in hass.data.get(DOMAIN, {}),
        "production_control": "disabled_in_beta_8",
        "migration_activation": "locked_until_single_writer_is_proven",
    }
