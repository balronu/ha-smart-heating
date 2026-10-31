"""Native Smart Heating switches for internal state only."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartHeatingCoordinator
from .const import DOMAIN
from .internal_entities import async_update_internal
from .management import normalize_management
from .storage import effective_config


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    coordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([SmartHeatingEnabledSwitch(coordinator, entry)])


class SmartHeatingEnabledSwitch(CoordinatorEntity[SmartHeatingCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Enabled"

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_enabled"

    @property
    def is_on(self) -> bool:
        return bool(normalize_management(effective_config(self._entry).get("management"))["internal"].get("enabled", True))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await async_update_internal(self.hass, self._entry, enabled=True)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        await async_update_internal(self.hass, self._entry, enabled=False)
        self.async_write_ha_state()
