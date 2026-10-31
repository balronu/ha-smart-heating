"""Constants for Smart Heating."""

from __future__ import annotations

DOMAIN = "smart_heating"
VERSION = "0.1.0-beta.1"
PLATFORMS = ["binary_sensor", "sensor"]

CONF_NAME = "name"
CONF_TIMEZONE = "timezone"
CONF_CLIMATE_ENTITY = "climate_entity"
CONF_HEATING_BOOLEAN = "heating_boolean"
CONF_HEATING_PERMISSION = "heating_permission"
CONF_WINDOW_ENTITIES = "window_entities"
CONF_PRESENCE_ENTITIES = "presence_entities"
CONF_SPECIAL_MODES = "special_modes"
CONF_SCHEDULE = "schedule"
CONF_SIMULATION = "simulation"

DEFAULT_NAME = "Smart Heating"
DEFAULT_TIMEZONE = "Europe/Berlin"
DEFAULT_SCHEDULE = {day: [] for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")}

SIGNAL_UPDATE = f"{DOMAIN}_update"
SIGNAL_ENTRY_UPDATED = f"{DOMAIN}_entry_updated"

ATTR_NEXT_SWITCH = "next_switch"
ATTR_SCHEDULE_ACTIVE = "schedule_active"
ATTR_DECISION = "decision"
ATTR_REASON = "reason"

MODE_COMFORT = "comfort"
MODE_NIGHT = "night"
MODE_AWAY = "away"
MODE_WINDOW_OPEN = "window_open"
MODE_WINDOW_TILTED = "window_tilted"
MODE_PARTY = "party"
MODE_VISIT = "visit"
MODE_RETURN_HOME = "return_home"
MODE_CHIMNEY_SWEEP = "chimney_sweep"
MODE_DISABLED = "disabled"
MODE_SUMMER = "summer"

