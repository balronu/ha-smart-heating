"""Config and options flows for Smart Heating."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_CLIMATE_ENTITY,
    CONF_HEATING_BOOLEAN,
    CONF_HEATING_PERMISSION,
    CONF_NAME,
    CONF_PRESENCE_ENTITIES,
    CONF_SCHEDULE,
    CONF_SPECIAL_MODES,
    CONF_TIMEZONE,
    CONF_WINDOW_ENTITIES,
    DEFAULT_NAME,
    DEFAULT_SCHEDULE,
    DEFAULT_TIMEZONE,
    DOMAIN,
)
from .models import ScheduleValidationError, WeeklySchedule


def _entity_selector(domains: list[str], multiple: bool = False) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domains, multiple=multiple))


class SmartHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one passive Smart Heating configuration entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is not None:
            await self.async_set_unique_id(f"{user_input[CONF_NAME].strip().lower()}-{user_input[CONF_TIMEZONE]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME].strip(), data={**user_input, CONF_SCHEDULE: DEFAULT_SCHEDULE, "special_modes": self._discover_defaults().get("special_modes", {}), "simulation": True})
        defaults = self._discover_defaults()
        schema = vol.Schema(
            {
                vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
                vol.Required(CONF_TIMEZONE, default=defaults[CONF_TIMEZONE]): str,
                vol.Optional(CONF_CLIMATE_ENTITY, default=defaults.get(CONF_CLIMATE_ENTITY, "")): str,
                vol.Optional(CONF_HEATING_BOOLEAN, default=defaults.get(CONF_HEATING_BOOLEAN, "")): str,
                vol.Optional(CONF_HEATING_PERMISSION, default=defaults.get(CONF_HEATING_PERMISSION, "")): str,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, description_placeholders={"mode": "passive"})

    def _discover_defaults(self) -> dict[str, Any]:
        """Suggest entities by friendly name; never hard-code a personal ID."""
        result = {CONF_NAME: DEFAULT_NAME, CONF_TIMEZONE: DEFAULT_TIMEZONE}
        states = getattr(self.hass, "states", None)
        if states is None:
            return result
        for state in states.async_all("climate"):
            label = state.name.lower()
            if any(word in label for word in ("heizung", "thermostat", "heating")):
                result[CONF_CLIMATE_ENTITY] = state.entity_id
                break
        for state in states.async_all("input_boolean"):
            label = state.name.lower()
            if any(word in label for word in ("heizung", "heating")) and "freigabe" not in label:
                result[CONF_HEATING_BOOLEAN] = state.entity_id
                break
        special_names = {
            "party": ("party",),
            "visit": ("besuch", "visit"),
            "return_home": ("heimweg", "return home"),
            "chimney_sweep": ("schornsteinfeger", "chimney"),
            "summer": ("sommermodus", "summer mode"),
        }
        result[CONF_SPECIAL_MODES] = {
            key: state.entity_id
            for state in states.async_all("input_boolean")
            for key, labels in special_names.items()
            if any(label in state.name.lower() for label in labels)
        }
        return result

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return SmartHeatingOptionsFlow(config_entry)


class SmartHeatingOptionsFlow(config_entries.OptionsFlow):
    """Edit schedule and explicit entity associations."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self.config_entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        return await self.async_step_schedule(user_input)

    async def async_step_schedule(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is not None:
            try:
                schedule = WeeklySchedule.from_mapping(user_input[CONF_SCHEDULE])
            except ScheduleValidationError as err:
                return self.async_show_form(step_id="schedule", data_schema=self._schema(), errors={"base": "invalid_schedule"}, description_placeholders={"error": str(err)})
            options = dict(self.config_entry.options)
            options.update(user_input)
            options[CONF_SCHEDULE] = schedule.as_dict()
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="schedule", data_schema=self._schema())

    def _schema(self) -> vol.Schema:
        return vol.Schema({vol.Required(CONF_SCHEDULE, default=self.config_entry.options.get(CONF_SCHEDULE, self.config_entry.data.get(CONF_SCHEDULE, DEFAULT_SCHEDULE))): dict})
