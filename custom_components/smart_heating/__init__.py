"""Smart Heating integration.

The Beta 11 compatibility mode owns its internal state and schedule without
external helpers or Simple Scheduler, but remains deliberately passive toward
climate, controller, helper, scheduler, and special-mode writes.
"""

from __future__ import annotations

import inspect
import logging
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping
from uuid import uuid4

import voluptuous as vol
from homeassistant.components import frontend, websocket_api
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import CONF_CHIMNEY_TEMPERATURE, CONF_FROST_TEMPERATURE, CONF_OPERATION_MODE, CONF_SUMMER_MODE, MODE_COMPATIBILITY, MODE_FULL, SUMMER_COMPATIBILITY, SUMMER_HVAC_OFF, CONF_CLIMATE_ENTITY, CONF_OUTDOOR_TEMPERATURE, CONF_TADO_FALLBACK, DOMAIN, PLATFORMS, SIGNAL_ENTRY_UPDATED, VERSION
from .engine import calculate_status
from .models import ScheduleValidationError, WeeklySchedule
from .migration import preview_migration
from .control import analyze_control_plane
from .cleanup import build_cleanup_plan
from .management import (
    area_suggestions,
    discover_climate_entities,
    discover_controller_entities,
    discover_helper_entities,
    discover_temperature_entities,
    is_eligible_temperature_entity,
    discover_persons,
    normalize_management,
    normalize_special_modes,
    person_presence,
    remove_item,
    upsert_item,
    validate_management,
    window_contact_summary,
    build_window_role_diagnostics,
    zone_status,
    zone_backend_summary,
    SAFETY_MODES,
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
        self.runtime_management_raw: dict[str, Any] = {}
        super().__init__(hass, config_entry=entry, logger=_LOGGER, name=DOMAIN)

    async def _async_update_data(self) -> dict[str, Any]:
        config = effective_config(self.entry)
        management = config.get("management", {})
        self.runtime_management_raw = deepcopy(management) if isinstance(management, Mapping) else {}
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
    for mode, settings in management.get("safety", {}).get("modes", {}).items():
        helper_entity = settings.get("helper_entity") if isinstance(settings, dict) else ""
        if isinstance(helper_entity, str) and helper_entity and settings.get("enabled", False):
            result[mode] = hass.states.is_state(helper_entity, "on")
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
    from .backend_engine import evaluate_window_contacts
    configured_contacts = []
    configured_ids = set()
    for kind in ("window", "tilt"):
        for item in management.get("sensors", {}).get(kind, []):
            if item.get("entity_id") and not item.get("ignored"):
                configured_ids.add(item["entity_id"])
                state = hass.states.get(item["entity_id"])
                configured_contacts.append({**item, "state": getattr(state, "state", "missing")})
    for entity_id in config.get("window_entities", []):
        if entity_id not in configured_ids:
            state = hass.states.get(entity_id)
            configured_contacts.append({"entity_id": entity_id, "type": "window", "contact_role": "unassigned", "state": getattr(state, "state", "missing")})
    window_evaluation = evaluate_window_contacts(configured_contacts)
    if window_evaluation["state"] == "open":
        result["window_open"] = True
    elif window_evaluation["state"] == "tilted":
        result["window_tilted"] = True
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
    context["special_modes"] = management.get("special_modes", [])
    context["control_plane"] = deepcopy(management.get("control_plane", {}))
    context["heating_sources"] = deepcopy(management.get("heating_sources", {}))
    context["heating_sources"]["primary_climate_entity"] = context["heating_sources"].get("primary_climate_entity") or config.get("climate_entity")
    context["heating_sources"]["fallback_climate_entity"] = context["heating_sources"].get("fallback_climate_entity") or config.get("tado_fallback")
    context["actor_states"] = {}
    context["actor_service_evidence"] = {
        "climate.set_hvac_mode": True,
        "climate.set_temperature": True,
    }
    context["physical_heat_demand_status"] = "not_proven"
    for entity_id in (context["heating_sources"].get("primary_climate_entity"), context["heating_sources"].get("fallback_climate_entity")):
        if not entity_id:
            continue
        state = hass.states.get(entity_id)
        if not state:
            context["actor_states"][entity_id] = {"state": "missing", "available": False}
            continue
        context["actor_states"][entity_id] = {
            "state": str(state.state),
            "hvac_mode": str(state.state),
            "temperature": state.attributes.get("temperature"),
            "hvac_action": state.attributes.get("hvac_action"),
            "available": str(state.state) not in {"unknown", "unavailable"},
            "hvac_modes": list(state.attributes.get("hvac_modes", [])),
        }
    context["presence"] = person_presence(hass, management["persons"])
    context["schedule_source_verified"] = bool(config.get("schedule_source_verified", False))
    context["thermostats"] = []
    context["window_strategy"] = "none"
    context["window_groups"] = []
    context["window_delays"] = {"tilted": 0, "open": 0, "closed": 0}
    if management.get("zones"):
        first_zone = management["zones"][0]
        context["zone_id"] = first_zone.get("id")
        context["thermostats"] = [
            {"entity_id": entity_id, "state": str(getattr(hass.states.get(entity_id), "state", "missing")), "available": bool(hass.states.get(entity_id)) and str(hass.states.get(entity_id).state) not in {"unknown", "unavailable"}}
            for entity_id in first_zone.get("thermostat_entities", [])
        ]
        context["window_strategy"] = first_zone.get("window_strategy", "none")
        context["window_groups"] = first_zone.get("window_groups", [])
        context["window_delays"] = first_zone.get("window_delays", context["window_delays"])
    safety_modes = management.get("safety", {}).get("modes", {})
    if isinstance(safety_modes, dict):
        chimney = safety_modes.get("chimney_sweep", {})
        frost = safety_modes.get("frost_protection", {})
        if chimney.get("temperature") not in (None, ""):
            context["chimney_temperature"] = float(chimney["temperature"])
        if frost.get("temperature") not in (None, ""):
            context["frost_temperature"] = float(frost["temperature"])
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
        websocket_api.async_register_command(hass, _ws_admin_room_save)
        websocket_api.async_register_command(hass, _ws_admin_zone_delete)
        websocket_api.async_register_command(hass, _ws_admin_sensor_set)
        websocket_api.async_register_command(hass, _ws_admin_sensor_delete)
        websocket_api.async_register_command(hass, _ws_admin_controller_set)
        websocket_api.async_register_command(hass, _ws_admin_outdoor_set)
        websocket_api.async_register_command(hass, _ws_admin_area_relevance_set)
        websocket_api.async_register_command(hass, _ws_admin_safety_set)
        websocket_api.async_register_command(hass, _ws_admin_system_set)
        websocket_api.async_register_command(hass, _ws_admin_special_mode_set)
        websocket_api.async_register_command(hass, _ws_admin_special_mode_delete)
        websocket_api.async_register_command(hass, _ws_admin_special_mode_duplicate)
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
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, "version": VERSION, "schedule": load_schedule(config).as_dict(), "status": status, "options": {"name": entry.title, "timezone": config.get("timezone"), "operation_mode": config.get("operation_mode", "compatibility"), "discovery": config.get("discovery", {}), "special_modes": config.get("special_modes", {}), "control_plane": analyze_control_plane(hass, config), "management": management, "areas": area_suggestions(hass, management), "persons_discovered": discover_persons(hass)}})


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
    config = effective_config(entry)
    window_contacts = window_contact_summary(hass, management)
    coordinator = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    runtime_management = getattr(coordinator, "runtime_management_raw", {}) if coordinator else {}
    options_management = entry.options if isinstance(entry.options, Mapping) else {}
    # Include every existing Smart-Heating contact. Older room data can retain
    # a contact without area_id/zone_ids; those fields are not prerequisites
    # for a role or for a read-only diagnostic row.
    configured_ids = {
        str(item.get("entity_id"))
        for kind in ("window", "tilt")
        for item in management.get("sensors", {}).get(kind, [])
        if isinstance(item, Mapping) and item.get("entity_id")
    }
    assigned_contacts = [
        item for item in window_contacts["contacts"]
        if item.get("entity_id") in configured_ids and not item.get("ignored")
    ]
    connection.send_result(msg["id"], {"entry_id": entry.entry_id, "version": VERSION, "settings": {key: config.get(key) for key in (CONF_OPERATION_MODE, CONF_SUMMER_MODE, CONF_CHIMNEY_TEMPERATURE, CONF_FROST_TEMPERATURE)}, "schedule": load_schedule(config).as_dict(), "management": management, "areas": area_suggestions(hass, management), "temperature_entities": discover_temperature_entities(hass), "climate_entities": discover_climate_entities(hass), "controller_entities": discover_controller_entities(hass, management.get("controller", {}).get("entity_id")), "helper_entities": discover_helper_entities(hass), "window_contacts": window_contacts, "window_role_diagnostics": build_window_role_diagnostics(config_entry_options=options_management, runtime_management=runtime_management, readback_management=management, assigned_contacts=assigned_contacts), "persons_discovered": discover_persons(hass), "presence": person_presence(hass, management["persons"]), "zones_status": zone_status(hass, management["zones"]), "backend_evaluations": zone_backend_summary(hass, management["zones"], management), "preview": coordinator.data if coordinator else {}, "validation": validate_management(management)})


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


@websocket_api.websocket_command({
    vol.Required("type"): "smart_heating/admin/room/save",
    vol.Required("entry_id"): cv.string,
    vol.Required("item"): dict,
    vol.Optional("contacts", default=[]): list,
})
@websocket_api.async_response
async def _ws_admin_room_save(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Persist one room and its contact roles as one verified transaction."""
    entry, management = _admin_entry(hass, msg["entry_id"])
    expected_roles: dict[str, str] = {}
    try:
        upsert_item(management, "zones", msg["item"])
        for raw_contact in msg.get("contacts", []):
            if not isinstance(raw_contact, dict):
                raise ValueError("invalid_window_contact")
            entity_id = str(raw_contact.get("entity_id", ""))
            if not entity_id:
                raise ValueError("missing_window_contact_entity")
            existing = next(
                (
                    stored
                    for kind in ("window", "tilt")
                    for stored in management.get("sensors", {}).get(kind, [])
                    if stored.get("entity_id") == entity_id
                ),
                {},
            )
            contact = dict(existing)
            contact.update(raw_contact)
            contact.setdefault("id", existing.get("id"))
            contact.setdefault("type", existing.get("type", "window"))
            upsert_item(management, "sensors", contact)
            expected_roles[entity_id] = str(contact.get("contact_role", "unassigned"))
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)

        # Read the Config Entry again instead of trusting the in-memory request.
        _, persisted = _admin_entry(hass, msg["entry_id"])
        persisted_roles = {
            str(contact.get("entity_id")): str(contact.get("contact_role", "unassigned"))
            for kind in ("window", "tilt")
            for contact in persisted.get("sensors", {}).get(kind, [])
        }
        mismatches = {
            entity_id: {"expected": role, "actual": persisted_roles.get(entity_id, "missing")}
            for entity_id, role in expected_roles.items()
            if persisted_roles.get(entity_id) != role
        }
        if mismatches:
            connection.send_error(msg["id"], "persistence_verification_failed", str(mismatches))
            return
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {
        "management": persisted,
        "persisted_contact_roles": {entity_id: persisted_roles[entity_id] for entity_id in expected_roles},
        "validation": validate_management(persisted),
    })


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/zone/delete", vol.Required("entry_id"): cv.string, vol.Required("item_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_zone_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    await _admin_mutation(hass, connection, msg, "zones", True)


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/area/relevance", vol.Required("entry_id"): cv.string, vol.Required("area_id"): cv.string, vol.Required("relevant"): cv.boolean})
@websocket_api.async_response
async def _ws_admin_area_relevance_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    """Persist only the panel's explicit area relevance preference."""
    entry, management = _admin_entry(hass, msg["entry_id"])
    area_id = msg["area_id"]
    selected = set(management.get("relevant_area_ids", []))
    if msg["relevant"]:
        selected.add(area_id)
    else:
        selected.discard(area_id)
    management["relevant_area_ids"] = sorted(selected)
    try:
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {"management": management, "areas": area_suggestions(hass, management), "validation": validate_management(management)})


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
    entity_id = msg["item"].get("entity_id")
    eligible = {item["entity_id"] for item in discover_controller_entities(hass)}
    if entity_id and entity_id not in eligible:
        connection.send_error(msg["id"], "invalid_configuration", "controller_not_observable")
        return
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
    entity_id = msg["item"].get("entity_id")
    if entity_id and not is_eligible_temperature_entity(hass, entity_id):
        connection.send_error(msg["id"], "invalid_configuration", "temperature_entity_not_eligible")
        return
    await _admin_mapping_set(hass, connection, msg, "outdoor_temperature")


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/safety/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_safety_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    item = msg["item"]
    helper_ids = {helper["entity_id"] for helper in discover_helper_entities(hass)}
    current_management = _admin_entry(hass, msg["entry_id"])[1]
    saved_helper_ids = {
        str(settings.get("helper_entity"))
        for settings in current_management.get("safety", {}).get("modes", {}).values()
        if isinstance(settings, dict) and settings.get("helper_entity")
    }
    for settings in item.get("modes", {}).values() if isinstance(item, dict) else ():
        helper_entity = settings.get("helper_entity", "") if isinstance(settings, dict) else ""
        # Existing assignments remain readable and saveable when the entity is
        # temporarily unavailable or was removed from HA. New assignments must
        # be input_boolean entities discovered by the passive inventory.
        if helper_entity and helper_entity not in helper_ids and helper_entity not in saved_helper_ids and not helper_entity.startswith("input_boolean."):
            connection.send_error(msg["id"], "invalid_configuration", "helper_entity_not_found")
            return
    entry, management = _admin_entry(hass, msg["entry_id"])
    management["safety"] = {key: value for key, value in item.items() if key != "special_modes"}
    submitted_modes = item.get("special_modes")
    if isinstance(submitted_modes, list):
        submitted_by_id = {str(mode.get("id")): mode for mode in submitted_modes if isinstance(mode, dict) and mode.get("id")}
        existing_modes = [mode for mode in management.get("special_modes", []) if str(mode.get("id")) not in submitted_by_id]
        management["special_modes"] = normalize_special_modes({"special_modes": existing_modes + list(submitted_by_id.values())}, management["safety"].get("modes", {}))
    try:
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {"management": management, "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/system/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_system_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, _ = _admin_entry(hass, msg["entry_id"])
    item = msg["item"]
    operation_mode = item.get(CONF_OPERATION_MODE, MODE_COMPATIBILITY)
    summer_mode = item.get(CONF_SUMMER_MODE, SUMMER_COMPATIBILITY)
    if operation_mode not in {MODE_COMPATIBILITY, MODE_FULL}:
        connection.send_error(msg["id"], "invalid_configuration", "invalid_operation_mode")
        return
    if operation_mode == MODE_FULL:
        connection.send_error(msg["id"], "invalid_configuration", "active_control_unavailable")
        return
    if summer_mode not in {SUMMER_COMPATIBILITY, SUMMER_HVAC_OFF}:
        connection.send_error(msg["id"], "invalid_configuration", "invalid_summer_mode")
        return
    try:
        chimney = float(item.get(CONF_CHIMNEY_TEMPERATURE, 25.0))
        frost = float(item.get(CONF_FROST_TEMPERATURE, 5.0))
    except (TypeError, ValueError):
        connection.send_error(msg["id"], "invalid_configuration", "invalid_safety_temperature")
        return
    if not 5 <= chimney <= 35 or not 3 <= frost <= 12:
        connection.send_error(msg["id"], "invalid_configuration", "safety_temperature_out_of_range")
        return
    options = dict(entry.options)
    options.update({CONF_OPERATION_MODE: operation_mode, CONF_SUMMER_MODE: summer_mode, CONF_CHIMNEY_TEMPERATURE: chimney, CONF_FROST_TEMPERATURE: frost})
    hass.config_entries.async_update_entry(entry, options=options)
    await _async_entry_updated(hass, entry)
    connection.send_result(msg["id"], {"settings": {CONF_OPERATION_MODE: operation_mode, CONF_SUMMER_MODE: summer_mode, CONF_CHIMNEY_TEMPERATURE: chimney, CONF_FROST_TEMPERATURE: frost}})


def _special_mode_legacy(mode: dict[str, Any]) -> dict[str, Any]:
    """Keep the Beta 27 runtime mapping in sync with a built-in object."""
    return {
        "enabled": bool(mode.get("available", False)),
        "helper_entity": str(mode.get("helper_entity") or mode.get("status_source") or ""),
        "temperature": mode.get("temperature"),
        "duration_minutes": mode.get("duration_minutes"),
        "zone_ids": list(mode.get("zone_ids", []) or []),
    }


def _validate_special_mode(hass: HomeAssistant, current: dict[str, Any], item: dict[str, Any]) -> dict[str, Any]:
    modes = normalize_special_modes({"special_modes": [item]}, current.get("safety", {}).get("modes", {}))
    mode_id = str(item.get("id") or "")
    candidate = next((mode for mode in modes if mode["id"] == mode_id), modes[-1])
    if candidate["binding_type"] == "helper_create":
        raise ValueError("helper_creation_unsupported:kein sicherer offizieller HA-Helper-Erstellungspfad nachgewiesen")
    helper_entity = candidate.get("helper_entity", "")
    if helper_entity and not str(helper_entity).startswith("input_boolean."):
        raise ValueError("helper_entity_must_be_input_boolean")
    if candidate["mode_type"] == "custom" and candidate["behavior"] != "passive_only":
        raise ValueError("unsupported_special_mode_behavior")
    return candidate


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/special_mode/set", vol.Required("entry_id"): cv.string, vol.Required("item"): dict})
@websocket_api.async_response
async def _ws_admin_special_mode_set(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    try:
        item = dict(msg["item"])
        if not item.get("id"):
            item["id"] = uuid4().hex
        candidate = _validate_special_mode(hass, management, item)
        modes = [mode for mode in management.get("special_modes", []) if mode["id"] != candidate["id"]]
        modes.append(candidate)
        management["special_modes"] = modes
        if candidate["mode_type"] in SAFETY_MODES:
            management["safety"]["modes"][candidate["mode_type"]] = _special_mode_legacy(candidate)
        _admin_save(hass, entry, management)
        await _async_entry_updated(hass, entry)
    except ValueError as err:
        connection.send_error(msg["id"], "invalid_configuration", str(err))
        return
    connection.send_result(msg["id"], {"management": management, "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/special_mode/delete", vol.Required("entry_id"): cv.string, vol.Required("item_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_special_mode_delete(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    mode = next((item for item in management.get("special_modes", []) if item["id"] == msg["item_id"]), None)
    if not mode:
        connection.send_error(msg["id"], "not_found", "special_mode_not_found")
        return
    if mode.get("origin") == "builtin":
        connection.send_error(msg["id"], "invalid_configuration", "builtin_mode_can_only_be_disabled")
        return
    management["special_modes"] = [item for item in management["special_modes"] if item["id"] != msg["item_id"]]
    _admin_save(hass, entry, management)
    await _async_entry_updated(hass, entry)
    connection.send_result(msg["id"], {"management": management, "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/special_mode/duplicate", vol.Required("entry_id"): cv.string, vol.Required("item_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_special_mode_duplicate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    entry, management = _admin_entry(hass, msg["entry_id"])
    source = next((item for item in management.get("special_modes", []) if item["id"] == msg["item_id"]), None)
    if not source:
        connection.send_error(msg["id"], "not_found", "special_mode_not_found")
        return
    duplicate = dict(source)
    duplicate["id"] = uuid4().hex
    duplicate["name"] = f"{source.get('name', 'Sondermodus')} (Kopie)"
    duplicate["origin"] = "user"
    duplicate["mode_type"] = "custom"
    duplicate["behavior"] = "passive_only"
    duplicate["binding_type"] = "internal"
    duplicate["helper_entity"] = ""
    duplicate["status_source"] = ""
    management["special_modes"].append(duplicate)
    _admin_save(hass, entry, management)
    await _async_entry_updated(hass, entry)
    connection.send_result(msg["id"], {"management": management, "created": duplicate, "validation": validate_management(management)})


@websocket_api.websocket_command({vol.Required("type"): "smart_heating/admin/validate", vol.Required("entry_id"): cv.string})
@websocket_api.async_response
async def _ws_admin_validate(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
    _, management = _admin_entry(hass, msg["entry_id"])
    connection.send_result(msg["id"], {"valid": not validate_management(management), "validation": validate_management(management)})
