"""Read-only status and simulation entities."""

from __future__ import annotations

from datetime import datetime

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartHeatingCoordinator
from .const import DOMAIN


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartHeatingNextSwitchSensor(coordinator, entry), SmartHeatingModeSensor(coordinator, entry)])


class _Base(CoordinatorEntity[SmartHeatingCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry, suffix: str) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{suffix}"


class SmartHeatingNextSwitchSensor(_Base):
    _attr_translation_key = "next_switch"
    _attr_device_class = "timestamp"

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "next_switch")

    @property
    def native_value(self) -> datetime | None:
        value = (self.coordinator.data or {}).get("next_switch")
        return datetime.fromisoformat(value) if value else None


class SmartHeatingModeSensor(_Base):
    _attr_translation_key = "mode"

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "mode")

    @property
    def native_value(self) -> str | None:
        return (self.coordinator.data or {}).get("mode")

    @property
    def extra_state_attributes(self):
        data = self.coordinator.data or {}
        return {"reason": data.get("reason"), "simulated": data.get("simulated", True)}

