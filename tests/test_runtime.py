"""Pinned Home Assistant lifecycle tests for the custom integration."""

import asyncio
import custom_components
import sys
from pathlib import Path
from shutil import copytree
import tempfile
import unittest

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
                    hass.states.async_set("input_boolean.heizung", "on", {"friendly_name": "Heizung"})
                    hass.states.async_set("input_boolean.heizung_freigabe", "on", {"friendly_name": "Heizungsfreigabe"})
                    hass.states.async_set("input_number.heiztemperatur", "20", {"friendly_name": "Heiztemperatur"})
                    hass.states.async_set("input_number.absenktemperatur", "17", {"friendly_name": "Absenktemperatur"})
                    hass.states.async_set("binary_sensor.fenster", "off", {"friendly_name": "Fenster", "device_class": "window"})
                    hass.states.async_set("person.michael", "home", {"friendly_name": "Michael"})

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

                    self.assertTrue(await hass.config_entries.async_unload(entry.entry_id))
                    await hass.async_block_till_done()
                    self.assertTrue(await hass.config_entries.async_setup(entry.entry_id))
                    await hass.async_block_till_done()
                    self.assertEqual(entry.state.value, "loaded")
                    self.assertEqual(entry.data["schedule"]["monday"][0]["end"], "08:00:00")
                    self.assertTrue(await hass.config_entries.async_remove(entry.entry_id))
                    await hass.async_block_till_done()
                    readd = await hass.config_entries.flow.async_init("smart_heating", context={"source": "user"})
                    readd = await hass.config_entries.flow.async_configure(readd["flow_id"], {"name": "Runtime Re-add", "timezone": "Europe/Berlin"})
                    self.assertEqual(readd["type"], "form")
                    readd = await hass.config_entries.flow.async_configure(readd["flow_id"], {"confirm": True})
                    self.assertEqual(readd["result"].state.value, "loaded")
                    entry = readd["result"]
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
