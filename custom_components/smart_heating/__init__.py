"""Smart Heating integration.

Beta 1 is deliberately passive: it calculates and displays a schedule and
decision context. It never writes a climate, helper, scheduler, or special-mode
entity. A future migration bridge must be separately enabled and reviewed.
"""

from __future__ import annotations

import inspect
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_CLIMATE_ENTITY, CONF_OUTDOOR_TEMPERATURE, CONF_TADO_FALLBACK, DOMAIN, PLATFORMS, SIGNAL_ENTRY_UPDATED, VERSION
from .engine import calculate_status
from .models import ScheduleValidationError, WeeklySchedule
from .migration import preview_migration
from .control import analyze_control_plane
from .storage import effective_config, load_schedule, normalized_options

_LOGGER = logging.getLogger(__name__)
_WS_REGISTERED = f"{DOMAIN}_ws_registered"
_STATIC_REGISTERED = f"{DOMAIN}_static_registered"

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


class SmartHeatingCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Compute passive status from config-entry data and current HA states."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.entry = entry
        super().__init__(hass, config_entry=entry, logger=_LOGGER, name=DOMAIN)

    async def _async_update_data(self) -> dict[str, Any]:
        config = effective_config(self.entry)
        return calculate_status(
            load_schedule(config),
            now=datetime.now().astimezone(),
            timezone=config.get("timezone", "Europe/Berlin"),
            overrides=_read_overrides(self.hass, self.entry),
            context=_read_context(self.hass, self.entry),
        )


def _read_overrides(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, bool]:
    """Read explicitly configured state context; never issue a service call."""
    config = effective_config(entry)
    result: dict[str, bool] = {}
    for key, entity_id in config.get("special_modes", {}).items():
        if isinstance(entity_id, str) and entity_id:
            result[key] = hass.states.is_state(entity_id, "on")
    window_unknown = False
    for entity_id in config.get("window_entities", []):
        state = hass.states.get(entity_id)
        if state and str(state.state).lower() in {"on", "open", "opened", "offen", "true"}:
            result["window_open"] = True
        elif state and str(state.state).lower() in {"tilt", "tilted", "gekippt", "gekipp", "gekippte"}:
            result["window_tilted"] = True
        elif not state or str(state.state).lower() in {"unknown", "unbekannt", "unavailable", "nicht verfügbar", "none", ""}:
            window_unknown = True
    if window_unknown and not result.get("window_open") and not result.get("window_tilted"):
        result["window_unknown"] = True
    for entity_id in config.get("presence_entities", []):
        state = hass.states.get(entity_id)
        if state and str(state.state).lower() in {"home", "on", "present", "zuhause"}:
            result["someone_home"] = True
    if config.get("presence_entities"):
        result["away"] = not result.get("someone_home", False)
    permission = config.get("heating_permission")
    if isinstance(permission, str) and permission:
        result["heating_permission"] = hass.states.is_state(permission, "on")
    return result


def _read_context(hass: HomeAssistant, entry: ConfigEntry) -> dict[str, Any]:
    """Read numeric targets and capabilities without calling a service."""
    config = effective_config(entry)
    context: dict[str, Any] = {
        "summer_mode": config.get("summer_mode", "compatibility"),
        "operation_mode": config.get("operation_mode", "compatibility"),
        "frost_temperature": float(config.get("frost_temperature", 5.0)),
        "chimney_temperature": float(config.get("chimney_temperature", 25.0)),
    }
    for key, config_key in (("comfort_temperature", "comfort_setpoint"), ("night_temperature", "night_setpoint")):
        entity_id = config.get(config_key)
        state = hass.states.get(entity_id) if isinstance(entity_id, str) else None
        if state:
            try:
                context[key] = float(state.state)
            except (TypeError, ValueError):
                pass
    climate = hass.states.get(config.get("climate_entity")) if config.get("climate_entity") else None
    if climate:
        context["hvac_supports_off"] = "off" in climate.attributes.get("hvac_modes", []) or climate.state == "off"
    return context


async def async_setup(hass: HomeAssistant, config: dict[str, Any]) -> bool:
    """Register integration-level websocket commands once."""
    if not hass.data.get(_WS_REGISTERED):
        websocket_api.async_register_command(hass, _ws_get_status)
        websocket_api.async_register_command(hass, _ws_set_schedule)
        websocket_api.async_register_command(hass, _ws_simulate)
        websocket_api.async_register_command(hass, _ws_migration_preview)
        hass.data[_WS_REGISTERED] = True
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    coordinator = SmartHeatingCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_entry_updated))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _register_frontend(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def _async_entry_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if coordinator:
        coordinator.async_set_updated_data(await coordinator._async_update_data())
        hass.bus.async_fire(SIGNAL_ENTRY_UPDATED, {"entry_id": entry.entry_id})


async def _register_frontend(hass: HomeAssistant) -> None:
    if hass.data.get(_STATIC_REGISTERED) or not getattr(hass, "http", None):
        return
    try:
        from homeassistant.components.http import StaticPathConfig

        result = hass.http.async_register_static_paths([StaticPathConfig("/smart_heating", str(Path(__file__).parent / "frontend"), cache_headers=False)])
        if inspect.isawaitable(result):
            await result
        frontend.add_extra_js_url(hass, f"/smart_heating/smart-heating-card.js?v={VERSION}")
        hass.data[_STATIC_REGISTERED] = True
    except (AttributeError, ImportError):
        _LOGGER.debug("Frontend registration is unavailable in this fixture", exc_info=True)


def _entry_from_connection(hass: HomeAssistant, entry_id: str) -> tuple[ConfigEntry, SmartHeatingCoordinator]:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == entry_id:
            return entry, hass.data[DOMAIN][entry_id]
    raise vol.Invalid("Unknown Smart Heating config entry")


def _observed_status(hass: HomeAssistant, config: dict[str, Any]) -> dict[str, Any]:
    """Expose current public states for the passive card without writing."""
    def state_of(entity_id: Any) -> dict[str, Any] | None:
        if not isinstance(entity_id, str) or not entity_id:
            return None
        state = hass.states.get(entity_id)
        if not state:
            return {"entity_id": entity_id, "state": "missing"}
        return {"entity_id": entity_id, "state": str(state.state), "hvac_action": state.attributes.get("hvac_action"), "temperature": state.attributes.get("temperature"), "current_temperature": state.attributes.get("current_temperature")}

    windows = [state_of(entity_id) for entity_id in config.get("window_entities", [])]
    windows = [item for item in windows if item is not None]
    unknown_window = any(item["state"].lower() in {"unknown", "unbekannt", "unavailable", "nicht verfügbar", "missing", "none", ""} for item in windows)
    climate = state_of(config.get(CONF_CLIMATE_ENTITY))
    if not climate or climate.get("state") in {"unknown", "unavailable", "missing"}:
        climate = state_of(config.get(CONF_TADO_FALLBACK)) or climate
    outdoor = state_of(config.get(CONF_OUTDOOR_TEMPERATURE))
    window_status = "unknown" if unknown_window else ("open_or_tilted" if windows and any(item["state"].lower() in {"on", "open", "opened", "offen", "true", "tilt", "tilted", "gekippt", "gekipp", "gekippte"} for item in windows) else "closed_or_clear" if windows else "unknown")
    return {"climate": climate, "outdoor_temperature": outdoor, "windows": windows, "window_status": window_status, "heat_demand_status": (climate or {}).get("hvac_action") or "unknown"}


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/plan/get", vol.Required("entry_id"): cv.string})
@websocket_api.async_response
async def _ws_get_status(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, coordinator = _entry_from_connection(hass, msg["entry_id"])
    config = effective_config(entry)
    status = dict(coordinator.data or {})
    status["observed"] = _observed_status(hass, config)
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, "schedule": load_schedule(config).as_dict(), "status": status, "options": {"name": entry.title, "timezone": config.get("timezone"), "operation_mode": config.get("operation_mode", "compatibility"), "discovery": config.get("discovery", {}), "special_modes": config.get("special_modes", {}), "control_plane": analyze_control_plane(hass, config)}})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/plan/set", vol.Required("entry_id"): cv.string, vol.Required("schedule"): dict})
@websocket_api.async_response
async def _ws_set_schedule(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, coordinator = _entry_from_connection(hass, msg["entry_id"])
    try:
        schedule = WeeklySchedule.from_mapping(msg["schedule"])
    except ScheduleValidationError as err:
        connection.send_error(msg["id"], "invalid_schedule", str(err))
        return
    hass.config_entries.async_update_entry(entry, options=normalized_options(effective_config(entry), schedule))
    await _async_entry_updated(hass, entry)
    connection.send_result(msg["id"], {"schedule": schedule.as_dict(), "status": coordinator.data or {}})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/simulate", vol.Required("entry_id"): cv.string, vol.Optional("at"): cv.string, vol.Optional("overrides", default={}): dict})
@websocket_api.async_response
async def _ws_simulate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, _ = _entry_from_connection(hass, msg["entry_id"])
    config = effective_config(entry)
    instant = datetime.fromisoformat(msg["at"]) if msg.get("at") else datetime.now().astimezone()
    result = calculate_status(load_schedule(config), now=instant, timezone=config.get("timezone", "Europe/Berlin"), overrides=msg.get("overrides", {}), context=_read_context(hass, entry))
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/migration/preview", vol.Required("entry_id"): cv.string, vol.Optional("manual_schedule"): dict})
@websocket_api.async_response
async def _ws_migration_preview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, _ = _entry_from_connection(hass, msg["entry_id"])
    connection.send_result(msg["id"], preview_migration(hass, entry, msg.get("manual_schedule")))
