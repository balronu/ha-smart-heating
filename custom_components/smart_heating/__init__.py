"""Smart Heating integration.

The Beta 11 compatibility mode owns its internal state and schedule without
external helpers or Simple Scheduler, but remains deliberately passive toward
climate, controller, helper, scheduler, and special-mode writes.
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
from .cleanup import build_cleanup_plan
from .management import (
    area_suggestions,
    discover_persons,
    normalize_management,
    person_presence,
    remove_item,
    upsert_item,
    validate_management,
    zone_status,
)
from .storage import effective_config, load_schedule, normalized_options

_LOGGER = logging.getLogger(__name__)
_WS_REGISTERED = f"{DOMAIN}_ws_registered"
_STATIC_REGISTERED = f"{DOMAIN}_static_registered"
_PANEL_REGISTERED = f"{DOMAIN}_panel_registered"

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
    management = normalize_management(config.get("management"))
    internal = management["internal"]
    if internal.get("enabled") is False:
        result["internal_enabled"] = False
    if internal.get("operating_mode") == "manual_heat":
        result["manual_heat"] = True
    elif internal.get("operating_mode") == "manual_setback":
        result["manual_setback"] = True
    for mode in ("party", "visit", "return_home", "summer", "chimney_sweep"):
        if internal.get(mode):
            result[mode] = True
    presence = person_presence(hass, management["persons"])
    if presence["home"]:
        result["someone_home"] = True
    if presence["away"]:
        result["away"] = True
    if presence["unknown"]:
        result["presence_unknown"] = True
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
    management = normalize_management(config.get("management"))
    settings = next(iter(management["internal"]["zones"].values()), {})
    context["comfort_temperature"] = settings.get("comfort_temperature", 20.0)
    context["night_temperature"] = settings.get("night_temperature", 17.0)
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
        websocket_api.async_register_command(hass, _ws_admin_get)
        websocket_api.async_register_command(hass, _ws_admin_person_set)
        websocket_api.async_register_command(hass, _ws_admin_person_delete)
        websocket_api.async_register_command(hass, _ws_admin_zone_set)
        websocket_api.async_register_command(hass, _ws_admin_zone_delete)
        websocket_api.async_register_command(hass, _ws_admin_sensor_set)
        websocket_api.async_register_command(hass, _ws_admin_sensor_delete)
        websocket_api.async_register_command(hass, _ws_admin_controller_set)
        websocket_api.async_register_command(hass, _ws_admin_outdoor_set)
        websocket_api.async_register_command(hass, _ws_admin_safety_set)
        websocket_api.async_register_command(hass, _ws_admin_validate)
        websocket_api.async_register_command(hass, _ws_cleanup_preview)
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
        coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
        if coordinator:
            await coordinator.async_shutdown()
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unloaded


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate legacy entries without changing their identity or ownership."""
    if config_entry.version < 2:
        hass.config_entries.async_update_entry(
            config_entry,
            version=2,
            data={
                **config_entry.data,
                "simulation": config_entry.data.get("simulation", True),
                "operation_mode": config_entry.data.get("operation_mode", "compatibility"),
            },
        )
    return True


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
        if not hass.data.get(_PANEL_REGISTERED):
            frontend.async_register_built_in_panel(
                hass,
                component_name="custom",
                sidebar_title="Smart Heating",
                sidebar_icon="mdi:radiator",
                frontend_url_path=DOMAIN,
                config={
                    "_panel_custom": {
                        "name": "smart-heating-backend-panel",
                        "embed_iframe": False,
                        "trust_external": False,
                        "module_url": f"/smart_heating/backend-panel.js?v={VERSION}",
                    }
                },
                require_admin=True,
                update=True,
            )
            hass.data[_PANEL_REGISTERED] = True
        hass.data[_STATIC_REGISTERED] = True
    except (AttributeError, ImportError):
        _LOGGER.debug("Frontend registration is unavailable in this fixture", exc_info=True)


def _entry_from_connection(hass: HomeAssistant, entry_id: str) -> tuple[ConfigEntry, SmartHeatingCoordinator]:
    for entry in hass.config_entries.async_entries(DOMAIN):
        if entry.entry_id == entry_id:
            return entry, hass.data[DOMAIN][entry_id]
    raise vol.Invalid("Unknown Smart Heating config entry")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/cleanup/preview", vol.Required("entry_id"): cv.string})
@websocket_api.async_response
async def _ws_cleanup_preview(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Return an ownership dry-run; never mutate registries or entries."""
    entry, _ = _entry_from_connection(hass, msg["entry_id"])
    from homeassistant.helpers import entity_registry

    entries = [{"entry_id": item.entry_id, "domain": item.domain} for item in hass.config_entries.async_entries(DOMAIN)]
    registry = entity_registry.async_get(hass)
    entities = [
        {
            "entity_id": item.entity_id,
            "platform": item.platform,
            "config_entry_id": item.config_entry_id,
            "unique_id": item.unique_id,
        }
        for item in registry.entities.values()
    ]
    connection.send_result(msg["id"], build_cleanup_plan(entries, entities, keep_entry_id=entry.entry_id))


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
    management = normalize_management(config.get("management"))
    status["presence"] = person_presence(hass, management["persons"])
    status["zones"] = zone_status(hass, management["zones"])
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, "version": VERSION, "schedule": load_schedule(config).as_dict(), "status": status, "options": {"name": entry.title, "timezone": config.get("timezone"), "operation_mode": config.get("operation_mode", "compatibility"), "discovery": config.get("discovery", {}), "special_modes": config.get("special_modes", {}), "control_plane": analyze_control_plane(hass, config), "management": management, "areas": area_suggestions(hass), "persons_discovered": discover_persons(hass)}})


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


def _admin_entry(hass: HomeAssistant, entry_id: str) -> tuple[ConfigEntry, dict[str, Any]]:
    entry, _ = _entry_from_connection(hass, entry_id)
    return entry, normalize_management(effective_config(entry).get("management"))


def _admin_save(hass: HomeAssistant, entry: ConfigEntry, management: dict[str, Any]) -> None:
    errors = validate_management(management)
    if errors:
        raise ValueError(";".join(errors))
    options = dict(entry.options)
    options["management"] = management
    hass.config_entries.async_update_entry(entry, options=options)


async def _admin_mutation(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any], collection: str, delete: bool = False) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    try:
        if delete:
            remove_item(management, collection, msg["item_id"])
        else:
            upsert_item(management, collection, msg["item"])
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {"management": management, "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/get", vol.Required("entry_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_get(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, "version": VERSION, "management": management, "areas": area_suggestions(hass), "persons_discovered": discover_persons(hass), "presence": person_presence(hass, management["persons"]), "zones_status": zone_status(hass, management["zones"]), "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/person/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_person_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "persons")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/person/delete", vol.Required("entry_id"): cv.string, vol.Required("item_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_person_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "persons", True)


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/zone/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_zone_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "zones")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/zone/delete", vol.Required("entry_id"): cv.string, vol.Required("item_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_zone_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "zones", True)


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/sensor/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_sensor_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "sensors")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/sensor/delete", vol.Required("entry_id"): cv.string, vol.Required("item_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_sensor_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "sensors", True)


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/controller/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_controller_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    management["controller"] = dict(msg["item"])
    try:
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {"management": management, "validation": []})


async def _admin_mapping_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any], key: str) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    management[key] = dict(msg["item"])
    try:
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {"management": management, "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/outdoor/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_outdoor_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mapping_set(hass, connection, msg, "outdoor_temperature")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/safety/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_safety_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mapping_set(hass, connection, msg, "safety")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/validate", vol.Required("entry_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_validate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    _, management = _admin_entry(hass, msg["entry_id"])
    connection.send_result(msg["id"], {"valid": not validate_management(management), "validation": validate_management(management)})
