"""Config and options flows for Smart Heating."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_COMFORT_SETPOINT,
    CONF_CHIMNEY_TEMPERATURE,
    CONF_CLIMATE_ENTITY,
    CONF_FROST_TEMPERATURE,
    CONF_OPERATION_MODE,
    CONF_TADO_FALLBACK,
    CONF_HEATING_BOOLEAN,
    CONF_HEATING_PERMISSION,
    CONF_NIGHT_SETPOINT,
    CONF_NAME,
    CONF_PRESENCE_ENTITIES,
    CONF_SCHEDULE,
    CONF_SPECIAL_MODES,
    CONF_SUMMER_MODE,
    CONF_TIMEZONE,
    CONF_WINDOW_ENTITIES,
    DEFAULT_NAME,
    DEFAULT_SCHEDULE,
    DEFAULT_TIMEZONE,
    DOMAIN,
    MODE_COMPATIBILITY,
    MODE_FULL,
    SUMMER_COMPATIBILITY,
    SUMMER_HVAC_OFF,
)
from .models import ScheduleValidationError, WeeklySchedule
from .discovery import apply_discovery_defaults, discover_entities


def _entity_selector(domains: list[str], multiple: bool = False) -> selector.EntitySelector:
    return selector.EntitySelector(selector.EntitySelectorConfig(domain=domains, multiple=multiple))


class SmartHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one passive Smart Heating configuration entry."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        discovery = discover_entities(self.hass)
        if user_input is not None:
            user_input = apply_discovery_defaults(user_input, discovery)
            await self.async_set_unique_id(f"{user_input[CONF_NAME].strip().lower()}-{user_input[CONF_TIMEZONE]}")
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME].strip(), data={**user_input, CONF_SCHEDULE: DEFAULT_SCHEDULE, CONF_SUMMER_MODE: SUMMER_COMPATIBILITY, CONF_OPERATION_MODE: MODE_COMPATIBILITY, CONF_CHIMNEY_TEMPERATURE: 25.0, CONF_FROST_TEMPERATURE: 5.0, "discovery": discovery, "simulation": True})
        defaults = apply_discovery_defaults({CONF_NAME: DEFAULT_NAME, CONF_TIMEZONE: DEFAULT_TIMEZONE}, discovery)
        schema_values: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
            vol.Required(CONF_TIMEZONE, default=defaults[CONF_TIMEZONE]): str,
        }
        for key, domains in (
            (CONF_CLIMATE_ENTITY, ["climate"]),
            (CONF_TADO_FALLBACK, ["climate"]),
            (CONF_HEATING_BOOLEAN, ["input_boolean"]),
            (CONF_HEATING_PERMISSION, ["input_boolean"]),
            (CONF_COMFORT_SETPOINT, ["input_number", "number"]),
            (CONF_NIGHT_SETPOINT, ["input_number", "number"]),
        ):
            selector_value = _entity_selector(domains)
            if defaults.get(key):
                schema_values[vol.Optional(key, default=defaults[key])] = selector_value
            else:
                schema_values[vol.Optional(key)] = selector_value
        for key, domains in (
            (CONF_WINDOW_ENTITIES, ["binary_sensor", "sensor"]),
            (CONF_PRESENCE_ENTITIES, ["person", "device_tracker", "input_boolean"]),
        ):
            schema_values[vol.Optional(key, default=defaults.get(key, []))] = _entity_selector(domains, multiple=True)
        schema = vol.Schema(
            schema_values
        )
        return self.async_show_form(step_id="user", data_schema=schema, description_placeholders={"mode": "passive", "ambiguous": ", ".join(discovery.get("ambiguous", [])) or "none"})

    def _discover_defaults(self) -> dict[str, Any]:
        """Return a read-only discovery report for diagnostics and tests."""
        return discover_entities(self.hass)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return SmartHeatingOptionsFlow(config_entry)


class SmartHeatingOptionsFlow(config_entries.OptionsFlow):
    """Edit schedule and explicit entity associations."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        return await self.async_step_schedule(user_input)

    async def async_step_schedule(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        if user_input is not None:
            try:
                schedule = WeeklySchedule.from_mapping(user_input[CONF_SCHEDULE])
            except ScheduleValidationError as err:
                return self.async_show_form(step_id="schedule", data_schema=self._schema(), errors={"base": "invalid_schedule"}, description_placeholders={"error": str(err)})
            options = dict(self._entry.options)
            options.update(user_input)
            options[CONF_SCHEDULE] = schedule.as_dict()
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="schedule", data_schema=self._schema())

    def _schema(self) -> vol.Schema:
        return vol.Schema({
            vol.Required(CONF_SCHEDULE, default=self._entry.options.get(CONF_SCHEDULE, self._entry.data.get(CONF_SCHEDULE, DEFAULT_SCHEDULE))): dict,
            vol.Optional(CONF_SUMMER_MODE, default=self._entry.options.get(CONF_SUMMER_MODE, self._entry.data.get(CONF_SUMMER_MODE, SUMMER_COMPATIBILITY))): vol.In([SUMMER_COMPATIBILITY, SUMMER_HVAC_OFF]),
            vol.Optional(CONF_OPERATION_MODE, default=self._entry.options.get(CONF_OPERATION_MODE, self._entry.data.get(CONF_OPERATION_MODE, MODE_COMPATIBILITY))): vol.In([MODE_COMPATIBILITY, MODE_FULL]),
            vol.Optional(CONF_CHIMNEY_TEMPERATURE, default=self._entry.options.get(CONF_CHIMNEY_TEMPERATURE, self._entry.data.get(CONF_CHIMNEY_TEMPERATURE, 25.0))): vol.All(vol.Coerce(float), vol.Range(min=5, max=35)),
            vol.Optional(CONF_FROST_TEMPERATURE, default=self._entry.options.get(CONF_FROST_TEMPERATURE, self._entry.data.get(CONF_FROST_TEMPERATURE, 5.0))): vol.All(vol.Coerce(float), vol.Range(min=3, max=12)),
        })
