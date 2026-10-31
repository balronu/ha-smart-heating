"""Native per-zone temperature controls backed by the Config Entry."""

from __future__ import annotations

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartHeatingCoordinator
from .const import DOMAIN
from .internal_entities import async_update_zone_internal
from .management import normalize_management
from .storage import effective_config


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    management = normalize_management(effective_config(entry).get("management"))
    entities = []
    for zone in management["zones"]:
        for setting, name in (("comfort_temperature", "Comfort temperature"), ("night_temperature", "Setback temperature")):
            entities.append(SmartHeatingZoneNumber(coordinator, entry, zone["id"], setting, name))
    async_add_entities(entities)


class SmartHeatingZoneNumber(CoordinatorEntity[SmartHeatingCoordinator], NumberEntity):
    _attr_has_entity_name = True
    _attr_native_min_value = 5.0
    _attr_native_max_value = 35.0
    _attr_native_step = 0.5

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry, zone_id: str, setting: str, name: str) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._zone_id = zone_id
        self._setting = setting
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{zone_id}_{setting}"

    @property
    def native_value(self) -> float:
        settings = normalize_management(effective_config(self._entry).get("management"))["internal"]["zones"].get(self._zone_id, {})
        return float(settings.get(self._setting, 20.0 if self._setting == "comfort_temperature" else 17.0))

    async def async_set_native_value(self, value: float) -> None:
        await async_update_zone_internal(self.hass, self._entry, self._zone_id, **{self._setting: float(value)})
        self.async_write_ha_state()
