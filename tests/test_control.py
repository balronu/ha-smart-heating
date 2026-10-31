import asyncio
import sys
import types
import unittest
from pathlib import Path

_package = types.ModuleType("custom_components.smart_heating")
_package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", _package)

from custom_components.smart_heating.control import analyze_control_plane, async_apply_decision
from custom_components.smart_heating.models import HeatingDecision


class State:
    def __init__(self, entity_id, state, attributes=None, name=""):
        self.entity_id = entity_id
        self.state = state
        self.attributes = attributes or {}
        self.name = name


class States:
    def __init__(self, items):
        self.items = {item.entity_id: item for item in items}

    def get(self, entity_id):
        return self.items.get(entity_id)

    def async_all(self, domain):
        return [item for item in self.items.values() if item.entity_id.startswith(domain + ".")]

    def async_set(self, entity_id, state, attributes=None):
        self.items[entity_id] = State(entity_id, state, attributes or self.items[entity_id].attributes)


class Services:
    def __init__(self, hass):
        self.hass = hass
        self.calls = []
        self.fail_readback = False
        self.fail_on_temperature = False
        self.emit_hvac_action = True

    async def async_call(self, domain, service, data, blocking=True):
        self.calls.append((domain, service, data))
        entity_id = data["entity_id"]
        state = self.hass.states.get(entity_id)
        attrs = dict(state.attributes)
        if service == "set_hvac_mode":
            if self.emit_hvac_action:
                attrs["hvac_action"] = "heating" if data["hvac_mode"] == "heat" else "idle"
            self.hass.states.async_set(entity_id, data["hvac_mode"], attrs)
        elif service == "set_temperature":
            if self.fail_on_temperature:
                self.fail_on_temperature = False
                raise RuntimeError("simulated climate service failure")
            attrs["temperature"] = data["temperature"]
            if not self.fail_readback:
                self.hass.states.async_set(entity_id, state.state, attrs)


class Hass:
    def __init__(self, states):
        self.states = States(states)
        self.services = Services(self)


class ControlTests(unittest.TestCase):
    def setUp(self):
        self.decision = HeatingDecision("comfort", "Schedule active", 22.0, "heat", "test")

    def test_compatibility_mode_never_calls_climate(self):
        hass = Hass([State("climate.esszimmer", "heat", {"temperature": 18})])
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "compatibility", "climate_entity": "climate.esszimmer"}, self.decision))
        self.assertEqual(result.status, "compatibility_noop")
        self.assertEqual(hass.services.calls, [])

    def test_full_mode_requires_single_writer_proof(self):
        hass = Hass([State("climate.esszimmer", "heat")])
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "full", "climate_entity": "climate.esszimmer"}, self.decision, isolated_test=True))
        self.assertEqual(result.status, "locked")
        self.assertEqual(hass.services.calls, [])

    def test_full_mode_calls_simulated_climate_and_reads_back(self):
        hass = Hass([State("climate.esszimmer", "off", {"temperature": 17})])
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "full", "climate_entity": "climate.esszimmer"}, self.decision, activation_confirmed=True, legacy_writer_disabled=True, isolated_test=True))
        self.assertEqual(result.status, "applied")
        self.assertEqual([call[1] for call in hass.services.calls], ["set_hvac_mode", "set_temperature"])
        self.assertEqual(hass.states.get("climate.esszimmer").state, "heat")
        self.assertEqual(hass.states.get("climate.esszimmer").attributes["temperature"], 22.0)

    def test_unavailable_primary_uses_tado_fallback(self):
        hass = Hass([State("climate.esszimmer", "unavailable"), State("climate.tado", "heat")])
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "full", "climate_entity": "climate.esszimmer", "tado_fallback": "climate.tado"}, self.decision, activation_confirmed=True, legacy_writer_disabled=True, isolated_test=True))
        self.assertEqual(result.entity_id, "climate.tado")

    def test_failed_takeover_rolls_back_simulated_climate(self):
        hass = Hass([State("climate.esszimmer", "off", {"temperature": 17})])
        hass.services.fail_on_temperature = True
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "full", "climate_entity": "climate.esszimmer"}, self.decision, activation_confirmed=True, legacy_writer_disabled=True, isolated_test=True))
        self.assertEqual(result.status, "rolled_back")
        self.assertTrue(result.rolled_back)
        self.assertEqual(hass.states.get("climate.esszimmer").state, "off")

    def test_control_plane_does_not_claim_hidden_automation_actions(self):
        hass = Hass([State("automation.heizung_automatik", "on", name="Heizung Automatik")])
        report = analyze_control_plane(hass, {"heating_boolean": "input_boolean.heizung", "climate_entity": "climate.esszimmer"})
        self.assertEqual(report["thermostat_writer"]["legacy_automation_candidates"], ["automation.heizung_automatik"])
        self.assertFalse(report["single_writer_proven"])

    def test_heat_demand_is_not_claimed_without_hvac_action(self):
        hass = Hass([State("climate.esszimmer", "off", {"temperature": 17})])
        hass.services.emit_hvac_action = False
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "full", "climate_entity": "climate.esszimmer"}, self.decision, activation_confirmed=True, legacy_writer_disabled=True, isolated_test=True))
        self.assertEqual(result.status, "applied_unverified_demand")
        self.assertFalse(result.heat_demand_verified)
        self.assertEqual(result.heat_demand_status, "not_exposed_by_device")

    def test_target_temperature_readback_failure_rolls_back(self):
        hass = Hass([State("climate.esszimmer", "off", {"temperature": 17})])
        hass.services.fail_readback = True
        result = asyncio.run(async_apply_decision(hass, {"operation_mode": "full", "climate_entity": "climate.esszimmer"}, self.decision, activation_confirmed=True, legacy_writer_disabled=True, isolated_test=True))
        self.assertEqual(result.status, "rolled_back")
        self.assertTrue(result.rolled_back)
