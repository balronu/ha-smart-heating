"""Schedule status entity."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartHeatingCoordinator
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SmartHeatingScheduleSensor(hass.data[DOMAIN][entry.entry_id], entry)])


class SmartHeatingScheduleSensor(CoordinatorEntity[SmartHeatingCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "schedule_active"
    _attr_device_class = "running"

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_schedule_active"

    @property
    def is_on(self) -> bool:
        return bool((self.coordinator.data or {}).get("schedule_active"))

