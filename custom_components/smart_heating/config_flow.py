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
    CONF_OUTDOOR_TEMPERATURE,
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


def _window_selector(multiple: bool = True) -> selector.EntitySelector:
    """Limit the UI to opening-capable binary sensors."""
    return selector.EntitySelector(
        selector.EntitySelectorConfig(
            domain="binary_sensor",
            device_class=["window", "door", "opening"],
            multiple=multiple,
        )
    )


class SmartHeatingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Create one passive Smart Heating configuration entry."""

    VERSION = 1

    def __init__(self) -> None:
        self._pending_input: dict[str, Any] | None = None
        self._pending_discovery: dict[str, Any] | None = None

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        discovery = discover_entities(self.hass)
        if user_input is not None:
            user_input = apply_discovery_defaults(user_input, discovery)
            self._pending_input = user_input
            self._pending_discovery = discovery
            return await self.async_step_confirm()
        return await self._show_user_form(discovery)

    async def async_step_confirm(self, user_input: dict[str, Any] | None = None) -> config_entries.FlowResult:
        """Show all automatic associations before creating the entry."""
        if user_input is None:
            discovery = self._pending_discovery or discover_entities(self.hass)
            selected = discovery.get("selected", {})
            special = selected.get("special_modes", {})
            summary = "; ".join(f"{key}: {value}" for key, value in {**selected, **special}.items() if value) or "keine eindeutige Zuordnung"
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
                description_placeholders={
                    "selected": summary,
                    "ambiguous": ", ".join(discovery.get("ambiguous", [])) or "keine",
                    "missing": ", ".join(discovery.get("missing", [])) or "keine",
                },
            )
        if not user_input.get("confirm", False):
            discovery = self._pending_discovery or discover_entities(self.hass)
            selected = discovery.get("selected", {})
            special = selected.get("special_modes", {})
            summary = "; ".join(f"{key}: {value}" for key, value in {**selected, **special}.items() if value) or "keine eindeutige Zuordnung"
            return self.async_show_form(
                step_id="confirm",
                data_schema=vol.Schema({vol.Required("confirm", default=False): bool}),
                errors={"base": "confirmation_required"},
                description_placeholders={
                    "selected": summary,
                    "ambiguous": ", ".join(discovery.get("ambiguous", [])) or "keine",
                    "missing": ", ".join(discovery.get("missing", [])) or "keine",
                },
            )
        values = self._pending_input or {}
        discovery = self._pending_discovery or discover_entities(self.hass)
        await self.async_set_unique_id(f"{values[CONF_NAME].strip().lower()}-{values[CONF_TIMEZONE]}")
        self._abort_if_unique_id_configured()
        values = dict(values)
        special_modes = dict(values.get(CONF_SPECIAL_MODES, {}) or {})
        for field, mode in (
            ("party_entity", "party"),
            ("visit_entity", "visit"),
            ("return_home_entity", "return_home"),
            ("chimney_sweep_entity", "chimney_sweep"),
            ("summer_entity", "summer"),
        ):
            entity_id = values.pop(field, None)
            if entity_id:
                special_modes[mode] = entity_id
        if special_modes:
            values[CONF_SPECIAL_MODES] = special_modes
        return self.async_create_entry(title=values[CONF_NAME].strip(), data={**values, CONF_SCHEDULE: DEFAULT_SCHEDULE, CONF_SUMMER_MODE: SUMMER_COMPATIBILITY, CONF_OPERATION_MODE: MODE_COMPATIBILITY, CONF_CHIMNEY_TEMPERATURE: 25.0, CONF_FROST_TEMPERATURE: 5.0, "discovery": discovery, "simulation": True})

    async def _show_user_form(self, discovery: dict[str, Any]) -> config_entries.FlowResult:
        """Render only the two required setup values.

        Entity mappings are reviewed on the confirmation page and maintained
        later in the backend/options UI. Legacy helpers must not dominate the
        first-run experience.
        """
        defaults = {CONF_NAME: DEFAULT_NAME, CONF_TIMEZONE: DEFAULT_TIMEZONE}
        schema_values: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
            vol.Required(CONF_TIMEZONE, default=defaults[CONF_TIMEZONE]): str,
        }
        schema = vol.Schema(
            schema_values
        )
        return self.async_show_form(step_id="user", data_schema=schema, description_placeholders={"mode": "passive"})

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
            special_modes = dict(options.get(CONF_SPECIAL_MODES, self._entry.data.get(CONF_SPECIAL_MODES, {})) or {})
            special_mode_field_seen = False
            for field, mode in (
                ("party_entity", "party"),
                ("visit_entity", "visit"),
                ("return_home_entity", "return_home"),
                ("chimney_sweep_entity", "chimney_sweep"),
                ("summer_entity", "summer"),
            ):
                if field in user_input:
                    special_mode_field_seen = True
                    entity_id = user_input.pop(field)
                    options.pop(field, None)
                    if entity_id:
                        special_modes[mode] = entity_id
                    else:
                        special_modes.pop(mode, None)
            if special_mode_field_seen:
                options[CONF_SPECIAL_MODES] = special_modes
            options[CONF_SCHEDULE] = schedule.as_dict()
            return self.async_create_entry(title="", data=options)
        return self.async_show_form(step_id="schedule", data_schema=self._schema())

    def _schema(self) -> vol.Schema:
        schema: dict[Any, Any] = {
            vol.Required(CONF_SCHEDULE, default=self._entry.options.get(CONF_SCHEDULE, self._entry.data.get(CONF_SCHEDULE, DEFAULT_SCHEDULE))): dict,
            vol.Optional(CONF_SUMMER_MODE, default=self._entry.options.get(CONF_SUMMER_MODE, self._entry.data.get(CONF_SUMMER_MODE, SUMMER_COMPATIBILITY))): vol.In([SUMMER_COMPATIBILITY, SUMMER_HVAC_OFF]),
            vol.Optional(CONF_OPERATION_MODE, default=self._entry.options.get(CONF_OPERATION_MODE, self._entry.data.get(CONF_OPERATION_MODE, MODE_COMPATIBILITY))): vol.In([MODE_COMPATIBILITY, MODE_FULL]),
            vol.Optional(CONF_CHIMNEY_TEMPERATURE, default=self._entry.options.get(CONF_CHIMNEY_TEMPERATURE, self._entry.data.get(CONF_CHIMNEY_TEMPERATURE, 25.0))): vol.All(vol.Coerce(float), vol.Range(min=5, max=35)),
            vol.Optional(CONF_FROST_TEMPERATURE, default=self._entry.options.get(CONF_FROST_TEMPERATURE, self._entry.data.get(CONF_FROST_TEMPERATURE, 5.0))): vol.All(vol.Coerce(float), vol.Range(min=3, max=12)),
        }
        current = {**self._entry.data, **self._entry.options}
        discovery = discover_entities(getattr(self, "hass", None)) if getattr(self, "hass", None) else {}
        discovered = discovery.get("selected", {})
        for key, domains in (
            (CONF_CLIMATE_ENTITY, ["climate"]),
            (CONF_TADO_FALLBACK, ["climate"]),
            (CONF_HEATING_BOOLEAN, ["input_boolean"]),
            (CONF_HEATING_PERMISSION, ["input_boolean"]),
            (CONF_COMFORT_SETPOINT, ["input_number", "number"]),
            (CONF_NIGHT_SETPOINT, ["input_number", "number"]),
            (CONF_OUTDOOR_TEMPERATURE, ["sensor"]),
        ):
            default = current.get(key) or discovered.get(key)
            if default:
                schema[vol.Optional(key, default=default)] = _entity_selector(domains)
            else:
                schema[vol.Optional(key)] = _entity_selector(domains)
        default = current.get(CONF_WINDOW_ENTITIES) or discovery.get("roles", {}).get(CONF_WINDOW_ENTITIES, {}).get("selected", [])
        schema[vol.Optional(CONF_WINDOW_ENTITIES, default=default)] = _window_selector()
        default = current.get(CONF_PRESENCE_ENTITIES) or discovery.get("roles", {}).get(CONF_PRESENCE_ENTITIES, {}).get("selected", [])
        schema[vol.Optional(CONF_PRESENCE_ENTITIES, default=default)] = _entity_selector(["person"], multiple=True)
        special_modes = current.get(CONF_SPECIAL_MODES, {}) or discovered.get(CONF_SPECIAL_MODES, {}) or {}
        for field, mode in (
            ("party_entity", "party"),
            ("visit_entity", "visit"),
            ("return_home_entity", "return_home"),
            ("chimney_sweep_entity", "chimney_sweep"),
            ("summer_entity", "summer"),
        ):
            if special_modes.get(mode):
                schema[vol.Optional(field, default=special_modes[mode])] = _entity_selector(["input_boolean"])
            else:
                schema[vol.Optional(field)] = _entity_selector(["input_boolean"])
        return vol.Schema(schema)
