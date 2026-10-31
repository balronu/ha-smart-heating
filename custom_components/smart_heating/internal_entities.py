"""Persistence helpers for Smart Heating's own entities."""

from __future__ import annotations

from typing import Any

from .management import normalize_management
from .storage import effective_config


async def async_update_internal(hass: Any, entry: Any, **changes: Any) -> dict[str, Any]:
    management = normalize_management(effective_config(entry).get("management"))
    management["internal"].update(changes)
    options = dict(entry.options)
    options["management"] = management
    hass.config_entries.async_update_entry(entry, options=options)
    coordinator = hass.data.get("smart_heating", {}).get(entry.entry_id)
    if coordinator:
        coordinator.async_set_updated_data(await coordinator._async_update_data())
    return management


async def async_update_zone_internal(hass: Any, entry: Any, zone_id: str, **changes: Any) -> dict[str, Any]:
    management = normalize_management(effective_config(entry).get("management"))
    management["internal"]["zones"].setdefault(zone_id, {}).update(changes)
    options = dict(entry.options)
    options["management"] = management
    hass.config_entries.async_update_entry(entry, options=options)
    coordinator = hass.data.get("smart_heating", {}).get(entry.entry_id)
    if coordinator:
        coordinator.async_set_updated_data(await coordinator._async_update_data())
    return management
