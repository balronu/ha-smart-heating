"""Pinned Home Assistant lifecycle tests for the custom integration."""

import asyncio
import custom_components
import json
import logging
import sys
from pathlib import Path
from shutil import copytree
import tempfile
import unittest
from types import SimpleNamespace

try:
    from homeassistant import loader
    from pytest_homeassistant_custom_component.common import async_test_home_assistant
except ImportError:  # The lightweight offline suite intentionally has no HA dependency.
    loader = None
    async_test_home_assistant = None


@unittest.skipUnless(async_test_home_assistant is not None, "Home Assistant runtime dependencies are not installed")
class RuntimeTests(unittest.TestCase):
    def test_config_options_entities_and_reload(self):
        asyncio.run(self._run_lifecycle())

    async def _run_lifecycle(self):
        with tempfile.TemporaryDirectory() as config_dir:
            copytree(
                Path("custom_components/smart_heating"),
                Path(config_dir) / "custom_components" / "smart_heating",
            )
            old_path = custom_components.__path__
            custom_components.__path__ = [str(Path(config_dir) / "custom_components"), *list(old_path)]
            try:
                # The offline model tests intentionally install a namespace stub;
                # the lifecycle test must load the copied integration module.
                for module_name in list(sys.modules):
                    if module_name == "custom_components.smart_heating" or module_name.startswith("custom_components.smart_heating."):
                        sys.modules.pop(module_name, None)
                async with async_test_home_assistant(config_dir=config_dir) as hass:
                    # The official fixture helper initializes this cache to {}, while
                    # the real loader populates it from the copied checkout.
                    hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
                    await loader.async_get_custom_components(hass)
                    hass.states.async_set("climate.esszimmer", "heat", {"friendly_name": "Esszimmer Heizung"})
                    hass.states.async_set("climate.badezimmer_1", "heat", {"friendly_name": "Badezimmer Heizkörper 1"})
                    hass.states.async_set("climate.badezimmer_2", "heat", {"friendly_name": "Badezimmer Heizkörper 2"})
                    hass.states.async_set("sensor.badezimmer_temperatur", "20", {"friendly_name": "Badezimmer Temperatur", "device_class": "temperature"})
                    hass.states.async_set("input_boolean.heizung", "on", {"friendly_name": "Heizung"})
                    hass.states.async_set("input_boolean.heizung_freigabe", "on", {"friendly_name": "Heizungsfreigabe"})
                    hass.states.async_set("input_number.heiztemperatur", "20", {"friendly_name": "Heiztemperatur"})
                    hass.states.async_set("input_number.absenktemperatur", "17", {"friendly_name": "Absenktemperatur"})
                    hass.states.async_set("binary_sensor.fenster", "off", {"friendly_name": "Fenster", "device_class": "window"})
                    hass.states.async_set("person.michael", "home", {"friendly_name": "Michael"})
                    hass.states.async_set("automation.heizung_automatik_ersetzt_node_red", "on", {"friendly_name": "Bestehende Tado-Heizungsautomation"})

                    passive_climate_calls = []

                    async def record_passive_climate_call(call):
                        passive_climate_calls.append((call.domain, call.service, dict(call.data)))

                    hass.services.async_register("climate", "set_temperature", record_passive_climate_call)
                    hass.services.async_register("climate", "set_hvac_mode", record_passive_climate_call)

                    flow = await hass.config_entries.flow.async_init("smart_heating", context={"source": "user"})
                    self.assertEqual(flow["type"], "form")
                    flow = await hass.config_entries.flow.async_configure(
                        flow["flow_id"],
                        {
                            "name": "Runtime Test",
                            "timezone": "Europe/Berlin",
                        },
                    )
                    self.assertEqual(flow["type"], "form")
                    self.assertEqual(set(flow["data_schema"].schema), {"confirm"})
                    rejected = await hass.config_entries.flow.async_configure(flow["flow_id"], {"confirm": False})
                    self.assertEqual(rejected["type"], "form")
                    self.assertEqual(rejected["errors"]["base"], "confirmation_required")
                    flow = await hass.config_entries.flow.async_configure(rejected["flow_id"], {"confirm": True})
                    entry = flow["result"]
                    hass.config_entries.async_update_entry(entry, data={**entry.data, "schedule": {"monday": [{"start": "06:00:00", "end": "08:00:00", "target_temperature": 20.5}]}})
                    self.assertEqual(entry.domain, "smart_heating")
                    await hass.async_block_till_done()
                    self.assertEqual(entry.state.value, "loaded")

                    from homeassistant.components.websocket_api.connection import ActiveConnection
                    from custom_components.smart_heating.management import normalize_management

                    room_item = {
                        "id": "badezimmer",
                        "name": "Badezimmer",
                        "enabled": True,
                        "area_ids": ["badezimmer"],
                        "thermostat_entities": ["climate.badezimmer_1", "climate.badezimmer_2"],
                        "temperature_entities": ["sensor.badezimmer_temperatur"],
                        "window_entities": [],
                        "tilt_entities": [],
                        "comfort_temperature": 20,
                        "night_temperature": 17,
                        "frost_temperature": 5,
                        "schedule": {},
                    }
                    contacts = [
                        {
                            "id": "bathroom-tilt",
                            "type": "window",
                            "entity_id": "binary_sensor.fensterkontakt_badezimmer_contact",
                            "contact_role": "tilt",
                            "area_id": "badezimmer",
                            "area_name": "Badezimmer",
                        },
                        {
                            "id": "bathroom-open",
                            "type": "window",
                            "entity_id": "binary_sensor.fensterkontakt_badezimmer_1_2_contact",
                            "contact_role": "open",
                            "area_id": "badezimmer",
                            "area_name": "Badezimmer",
                        },
                    ]

                    messages = []
                    connection = ActiveConnection(
                        logging.getLogger("smart_heating.runtime_test"),
                        hass,
                        messages.append,
                        SimpleNamespace(id="runtime-test-user", name="Runtime Test", is_admin=True),
                        None,
                        "127.0.0.1",
                    )

                    async def ws_call(message_id, message):
                        connection.async_handle({"id": message_id, **message})
                        await hass.async_block_till_done()
                        payloads = [
                            json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                            for item in messages
                        ]
                        result = next((item for item in payloads if item.get("id") == message_id), None)
                        self.assertIsNotNone(result, payloads)
                        messages.clear()
                        self.assertEqual(result["type"], "result", result)
                        self.assertTrue(result.get("success"), result)
                        return result["result"]

                    async def save_room(message_id, roles):
                        return await ws_call(
                            message_id,
                            {
                                "type": "smart_heating/admin/room/save",
                                "entry_id": entry.entry_id,
                                "item": room_item,
                                "contacts": [{**contact, "contact_role": role} for contact, role in zip(contacts, roles)],
                            },
                        )

                    # A signed-in non-admin must not be able to mutate the room.
                    # Use an independent non-admin connection so rejected requests
                    # cannot affect the administrator's later lifecycle checks.
                    admin_connection = connection
                    connection = ActiveConnection(
                        logging.getLogger("smart_heating.runtime_test.nonadmin"),
                        hass, messages.append,
                        SimpleNamespace(id="runtime-nonadmin", name="Runtime Non-Admin", is_admin=False),
                        None, "127.0.0.1",
                    )
                    # Full administrative diagnostics must not leak to non-admins.
                    connection.async_handle({
                        "id": 97,
                        "type": "smart_heating/admin/get",
                        "entry_id": entry.entry_id,
                    })
                    await hass.async_block_till_done()
                    read_responses = [
                        json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                        for item in messages
                    ]
                    denied_read = next(
                        (item for item in read_responses if item.get("id") == 97), None
                    )
                    self.assertIsNotNone(denied_read, read_responses)
                    self.assertEqual(denied_read["type"], "result")
                    self.assertFalse(denied_read["success"])
                    self.assertEqual(denied_read["error"]["code"], "unauthorized")
                    messages.clear()
                    options_before_denial = dict(entry.options)
                    connection.async_handle({
                        "id": 100,
                        "type": "smart_heating/admin/room/save",
                        "entry_id": entry.entry_id,
                        "item": room_item,
                        "contacts": contacts,
                    })
                    await hass.async_block_till_done()
                    denied_messages = [
                        json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                        for item in messages
                    ]
                    denied = next((item for item in denied_messages if item.get("id") == 100), None)
                    self.assertIsNotNone(denied, denied_messages)
                    self.assertEqual(denied["type"], "result")
                    self.assertFalse(denied["success"])
                    self.assertEqual(entry.options, options_before_denial)
                    messages.clear()
                    # Internal temperature settings are protected by the same HA role check.
                    internal_before = dict(entry.options)
                    connection.async_handle({
                        "id": 99,
                        "type": "smart_heating/admin/internal/set",
                        "entry_id": entry.entry_id,
                        "item": {"comfort_temperature": 24},
                    })
                    await hass.async_block_till_done()
                    internal_messages = [
                        json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                        for item in messages
                    ]
                    internal_denied = next(
                        (item for item in internal_messages if item.get("id") == 99), None
                    )
                    self.assertIsNotNone(internal_denied, internal_messages)
                    self.assertEqual(internal_denied["type"], "result")
                    self.assertFalse(internal_denied["success"])
                    self.assertEqual(entry.options, internal_before)
                    messages.clear()
                    # A non-admin must not change the weekly schedule either.
                    schedule_before = dict(entry.options)
                    connection.async_handle({
                        "id": 98,
                        "type": "smart_heating/plan/set",
                        "entry_id": entry.entry_id,
                        "schedule": {"monday": [{"start": "07:00", "end": "09:00"}]},
                    })
                    await hass.async_block_till_done()
                    schedule_messages = [
                        json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                        for item in messages
                    ]
                    schedule_denied = next(
                        (item for item in schedule_messages if item.get("id") == 98), None
                    )
                    self.assertIsNotNone(schedule_denied, schedule_messages)
                    self.assertEqual(schedule_denied["type"], "result")
                    self.assertFalse(schedule_denied["success"])
                    self.assertEqual(entry.options, schedule_before)
                    messages.clear()
                    # Additional valid-schema mutations must also reject non-admins.
                    for message_id, message_type in (
                        (200, "smart_heating/admin/person/delete"),
                        (201, "smart_heating/admin/zone/delete"),
                        (202, "smart_heating/admin/sensor/delete"),
                        (203, "smart_heating/admin/special_mode/delete"),
                        (204, "smart_heating/admin/special_mode/duplicate"),
                    ):
                        options_before = dict(entry.options)
                        connection.async_handle({
                            "id": message_id,
                            "type": message_type,
                            "entry_id": entry.entry_id,
                            "item_id": "blocked",
                        })
                        await hass.async_block_till_done()
                        responses = [
                            json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                            for item in messages
                        ]
                        response = next(
                            (item for item in responses if item.get("id") == message_id), None
                        )
                        with self.subTest(message_type=message_type):
                            self.assertIsNotNone(response, responses)
                            self.assertEqual(response["type"], "result")
                            self.assertFalse(response["success"])
                            self.assertEqual(entry.options, options_before)
                        messages.clear()
                    # Valid websocket schemas ensure the authorization layer,
                    # rather than schema validation, rejects these mutations.
                    additional_mutations = [
                        ("smart_heating/admin/person/set", {"item": {"id": "blocked"}}),
                        ("smart_heating/admin/zone/set", {"item": {"id": "blocked"}}),
                        ("smart_heating/admin/area/relevance", {"area_id": "blocked", "relevant": True}),
                        ("smart_heating/admin/sensor/set", {"item": {"id": "blocked"}}),
                        ("smart_heating/admin/controller/set", {"item": {}}),
                        ("smart_heating/admin/outdoor/set", {"item": {}}),
                        ("smart_heating/admin/safety/set", {"item": {}}),
                        ("smart_heating/admin/system/set", {"item": {}}),
                        ("smart_heating/admin/special_mode/set", {"item": {"id": "blocked"}}),
                    ]
                    for offset, (message_type, payload) in enumerate(additional_mutations):
                        message_id = 220 + offset
                        options_before = dict(entry.options)
                        connection.async_handle({
                            "id": message_id, "type": message_type,
                            "entry_id": entry.entry_id, **payload,
                        })
                        await hass.async_block_till_done()
                        responses = [
                            json.loads(item) if isinstance(item, (bytes, bytearray)) else item
                            for item in messages
                        ]
                        response = next(
                            (item for item in responses if item.get("id") == message_id), None
                        )
                        with self.subTest(message_type=message_type):
                            self.assertIsNotNone(response, responses)
                            self.assertEqual(response["type"], "result")
                            self.assertFalse(response["success"])
                            self.assertEqual(response["error"]["code"], "unauthorized")
                            self.assertEqual(entry.options, options_before)
                        messages.clear()
                    connection = admin_connection

                    first_save = await save_room(101, ("tilt", "open"))
                    self.assertEqual(first_save["persisted_contact_roles"], {contact["entity_id"]: role for contact, role in zip(contacts, ("tilt", "open"))})
                    persisted = normalize_management(entry.options["management"])
                    self.assertEqual({item["entity_id"]: item["contact_role"] for item in persisted["sensors"]["window"]}, {contact["entity_id"]: role for contact, role in zip(contacts, ("tilt", "open"))})
                    saved_zone = next(item for item in persisted["zones"] if item["id"] == "badezimmer")
                    self.assertEqual(saved_zone["thermostat_entities"], room_item["thermostat_entities"])
                    self.assertEqual(saved_zone["temperature_entities"], room_item["temperature_entities"])
                    self.assertEqual(
                        {key: saved_zone[key] for key in ("comfort_temperature", "night_temperature", "frost_temperature")},
                        {key: room_item[key] for key in ("comfort_temperature", "night_temperature", "frost_temperature")},
                    )
                    admin_readback = await ws_call(
                        102,
                        {"type": "smart_heating/admin/get", "entry_id": entry.entry_id},
                    )
                    self.assertEqual(
                        {
                            item["entity_id"]: item["contact_role"]
                            for item in admin_readback["window_contacts"]["contacts"]
                            if item["entity_id"] in {contact["entity_id"] for contact in contacts}
                        },
                        first_save["persisted_contact_roles"],
                    )
                    diagnostics = {
                        item["entity_id"]: item
                        for item in admin_readback["window_role_diagnostics"]
                    }
                    self.assertEqual(
                        {entity_id: diagnostics[entity_id]["readback_role"] for entity_id in diagnostics},
                        first_save["persisted_contact_roles"],
                    )
                    self.assertTrue(all(item["matches"] for item in diagnostics.values()))

                    second_save = await save_room(103, ("tilt", "open"))
                    self.assertEqual(second_save["persisted_contact_roles"], first_save["persisted_contact_roles"])

                    # Persist internal-only temperatures through an actual HA
                    # config-entry unload/setup cycle (without any actuation).
                    internal_saved = await ws_call(
                        105,
                        {
                            "type": "smart_heating/admin/internal/set",
                            "entry_id": entry.entry_id,
                            "item": {
                                "internal_only": True,
                                "comfort_temperature": 22.5,
                                "night_temperature": 17.5,
                            },
                        },
                    )
                    self.assertFalse(internal_saved.get("active_control", False))
                    internal_before_reload = normalize_management(
                        entry.options["management"]
                    )["internal"]
                    self.assertTrue(internal_before_reload["internal_only"])
                    self.assertEqual(internal_before_reload["comfort_temperature"], 22.5)
                    self.assertEqual(internal_before_reload["night_temperature"], 17.5)

                    self.assertEqual(
                        hass.states.get("automation.heizung_automatik_ersetzt_node_red").state,
                        "on",
                        "Passive Smart Heating must not disable the existing Tado automation",
                    )
                    self.assertTrue(await hass.config_entries.async_unload(entry.entry_id))
                    await hass.async_block_till_done()
                    self.assertTrue(await hass.config_entries.async_setup(entry.entry_id))
                    await hass.async_block_till_done()
                    self.assertEqual(
                        hass.states.get("automation.heizung_automatik_ersetzt_node_red").state,
                        "on",
                        "Passive reload must leave the existing Tado automation enabled",
                    )
                    persisted_after_reload = normalize_management(entry.options["management"])
                    reloaded_internal = persisted_after_reload["internal"]
                    self.assertTrue(reloaded_internal["internal_only"])
                    self.assertEqual(reloaded_internal["comfort_temperature"], 22.5)
                    self.assertEqual(reloaded_internal["night_temperature"], 17.5)
                    # The pre-existing weekly plan must survive the same reload
                    # alongside internal targets and room/contact assignments.
                    self.assertEqual(
                        entry.data["schedule"]["monday"],
                        [{"start": "06:00:00", "end": "08:00:00", "target_temperature": 20.5}],
                    )
                    self.assertEqual({item["entity_id"]: item["contact_role"] for item in persisted_after_reload["sensors"]["window"]}, first_save["persisted_contact_roles"])
                    reloaded_zone = next(item for item in persisted_after_reload["zones"] if item["id"] == "badezimmer")
                    self.assertEqual(reloaded_zone["thermostat_entities"], room_item["thermostat_entities"])
                    self.assertEqual(reloaded_zone["temperature_entities"], room_item["temperature_entities"])
                    self.assertEqual(
                        {key: reloaded_zone[key] for key in ("comfort_temperature", "night_temperature", "frost_temperature")},
                        {key: room_item[key] for key in ("comfort_temperature", "night_temperature", "frost_temperature")},
                    )
                    reloaded_admin_readback = await ws_call(
                        106,
                        {"type": "smart_heating/admin/get", "entry_id": entry.entry_id},
                    )
                    self.assertEqual(
                        {
                            item["entity_id"]: item["contact_role"]
                            for item in reloaded_admin_readback["window_contacts"]["contacts"]
                            if item["entity_id"] in {contact["entity_id"] for contact in contacts}
                        },
                        first_save["persisted_contact_roles"],
                    )

                    duplicate = await hass.config_entries.flow.async_init(
                        "smart_heating", context={"source": "user"}
                    )
                    self.assertEqual(duplicate["type"], "abort")
                    self.assertEqual(duplicate["reason"], "already_configured")

                    self.assertIsNotNone(hass.states.get("sensor.next_switch"))
                    self.assertIsNotNone(hass.states.get("sensor.calculated_heating_mode"))
                    self.assertIsNotNone(hass.states.get("binary_sensor.schedule_active"))
                    self.assertTrue(hass.states.async_all("switch"))
                    self.assertTrue(hass.states.async_all("select"))
                    self.assertTrue(hass.states.async_all("sensor"))
                    websocket_commands = hass.data["websocket_api"]
                    self.assertTrue({
                        "smart_heating/plan/get",
                        "smart_heating/plan/set",
                        "smart_heating/simulate",
                        "smart_heating/migration/preview",
                        "smart_heating/admin/get",
                        "smart_heating/admin/person/set",
                        "smart_heating/admin/zone/set",
                        "smart_heating/admin/room/save",
                        "smart_heating/admin/sensor/set",
                        "smart_heating/admin/controller/set",
                        "smart_heating/admin/outdoor/set",
                        "smart_heating/admin/safety/set",
                        "smart_heating/admin/validate",
                    }.issubset(websocket_commands))

                    options = await hass.config_entries.options.async_init(entry.entry_id)
                    from homeassistant.helpers import config_validation as cv
                    from probatio import to_field_list

                    serialized_schema = to_field_list(options["data_schema"], custom_serializer=cv.custom_serializer)
                    self.assertEqual({field["name"] for field in serialized_schema}, set())
                    preserved_before = dict(entry.options)
                    acknowledged = await hass.config_entries.options.async_configure(
                        options["flow_id"],
                        {},
                    )
                    self.assertEqual(acknowledged["type"], "create_entry")
                    self.assertEqual(entry.options, preserved_before)

                    self.assertEqual(
                        hass.states.get("automation.heizung_automatik_ersetzt_node_red").state,
                        "on",
                        "Passive Smart Heating must not disable the existing Tado automation",
                    )
                    self.assertTrue(await hass.config_entries.async_unload(entry.entry_id))
                    await hass.async_block_till_done()
                    self.assertTrue(await hass.config_entries.async_setup(entry.entry_id))
                    await hass.async_block_till_done()
                    self.assertEqual(entry.state.value, "loaded")
                    self.assertEqual(entry.data["schedule"]["monday"][0]["end"], "08:00:00")
                    self.assertEqual(
                        hass.states.get("automation.heizung_automatik_ersetzt_node_red").state,
                        "on",
                        "Second passive reload must not disable the existing Tado automation",
                    )
                    self.assertEqual(
                        normalize_management(entry.options["management"])["internal"]["comfort_temperature"],
                        22.5,
                    )
                    self.assertEqual(
                        normalize_management(entry.options["management"])["internal"]["night_temperature"],
                        17.5,
                    )
                    self.assertEqual(
                        {item["entity_id"]: item["contact_role"] for item in normalize_management(entry.options["management"])["sensors"]["window"]},
                        first_save["persisted_contact_roles"],
                        "Repeated passive reload must preserve all window contacts and their roles",
                    )
                    self.assertEqual(
                        passive_climate_calls,
                        [],
                        "Passive setup, options changes and repeated reloads must never command climate devices",
                    )
                    self.assertTrue(await hass.config_entries.async_remove(entry.entry_id))
                    await hass.async_block_till_done()
                    readd = await hass.config_entries.flow.async_init("smart_heating", context={"source": "user"})
                    readd = await hass.config_entries.flow.async_configure(readd["flow_id"], {"name": "Runtime Re-add", "timezone": "Europe/Berlin"})
                    self.assertEqual(readd["type"], "form")
                    readd = await hass.config_entries.flow.async_configure(readd["flow_id"], {"confirm": True})
                    self.assertEqual(readd["result"].state.value, "loaded")
                    entry = readd["result"]
                    self.assertEqual(
                        passive_climate_calls,
                        [],
                        "Passive removal and fresh re-add must not issue climate commands",
                    )
                    self.assertEqual(
                        hass.states.get("automation.heizung_automatik_ersetzt_node_red").state,
                        "on",
                        "Passive removal and fresh re-add must preserve the existing Tado automation",
                    )
                    from custom_components.smart_heating.control import async_apply_decision
                    from custom_components.smart_heating.models import HeatingDecision

                    async def set_hvac_mode(call):
                        state = hass.states.get(call.data["entity_id"])
                        attributes = dict(state.attributes)
                        attributes["hvac_action"] = "heating" if call.data["hvac_mode"] == "heat" else "idle"
                        hass.states.async_set(call.data["entity_id"], call.data["hvac_mode"], attributes)

                    async def set_temperature(call):
                        state = hass.states.get(call.data["entity_id"])
                        attributes = dict(state.attributes)
                        attributes["temperature"] = call.data["temperature"]
                        hass.states.async_set(call.data["entity_id"], state.state, attributes)

                    hass.services.async_register("climate", "set_hvac_mode", set_hvac_mode)
                    hass.services.async_register("climate", "set_temperature", set_temperature)
                    control_result = await async_apply_decision(
                        hass,
                        {"operation_mode": "full", "climate_entity": "climate.esszimmer"},
                        HeatingDecision("comfort", "isolated runtime", 21.5, "heat", "test"),
                        activation_confirmed=True,
                        legacy_writer_disabled=True,
                        isolated_test=True,
                    )
                    self.assertEqual(control_result.status, "applied")
                    self.assertEqual(hass.states.get("climate.esszimmer").state, "heat")
                    self.assertEqual(hass.states.get("climate.esszimmer").attributes["temperature"], 21.5)
                    await hass.async_stop()
            finally:
                custom_components.__path__ = old_path
