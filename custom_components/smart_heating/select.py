"""Native Smart Heating operating-mode selector."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import SmartHeatingCoordinator
from .const import DOMAIN
from .internal_entities import async_update_internal
from .management import OPERATING_MODES, normalize_management
from .storage import effective_config


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    async_add_entities([SmartHeatingOperatingModeSelect(hass.data[DOMAIN][entry.entry_id], entry)])


class SmartHeatingOperatingModeSelect(CoordinatorEntity[SmartHeatingCoordinator], SelectEntity):
    _attr_has_entity_name = True
    _attr_name = "Operating mode"
    _attr_options = list(OPERATING_MODES)

    def __init__(self, coordinator: SmartHeatingCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_operating_mode"

    @property
    def current_option(self) -> str:
        return normalize_management(effective_config(self._entry).get("management"))["internal"].get("operating_mode", "automatic")

    async def async_select_option(self, option: str) -> None:
        if option not in self.options:
            return
        await async_update_internal(self.hass, self._entry, operating_mode=option)
        self.async_write_ha_state()
