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
from .management import normalize_management, zone_status
from .storage import effective_config


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    management = normalize_management(effective_config(entry).get("management"))
    async_add_entities([SmartHeatingNextSwitchSensor(coordinator, entry), SmartHeatingModeSensor(coordinator, entry), SmartHeatingInternalStateSensor(coordinator, entry), *[SmartHeatingZoneStatusSensor(coordinator, entry, zone["id"], zone.get("name", zone["id"])) for zone in management["zones"]]])


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


class SmartHeatingInternalStateSensor(_Base):
    _attr_name = "Internal state"

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry, "internal_state")
        self._entry = entry

    @property
    def native_value(self) -> str:
        internal = normalize_management(effective_config(self._entry).get("management"))["internal"]
        return str(internal.get("operating_mode", "automatic"))

    @property
    def extra_state_attributes(self):
        internal = normalize_management(effective_config(self._entry).get("management"))["internal"]
        return {key: value for key, value in internal.items() if key != "zones"}


class SmartHeatingZoneStatusSensor(_Base):
    _attr_name = "Zone status"

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry, zone_id: str, name: str) -> None:
        super().__init__(coordinator, entry, f"zone_{zone_id}_status")
        self._entry = entry
        self._zone_id = zone_id

    @property
    def native_value(self) -> str:
        management = normalize_management(effective_config(self._entry).get("management"))
        item = next((item for item in zone_status(self.hass, management["zones"]) if item["zone_id"] == self._zone_id), None)
        return "available" if item and item["available"] else "unavailable" if item else "unknown"

    @property
    def extra_state_attributes(self):
        management = normalize_management(effective_config(self._entry).get("management"))
        return next((item for item in zone_status(self.hass, management["zones"]) if item["zone_id"] == self._zone_id), {"zone_id": self._zone_id})
