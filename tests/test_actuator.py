import unittest

from custom_components.smart_heating.actuator import build_passive_actor_plan


class PassiveActuatorContractTests(unittest.TestCase):
    def decision(self, mode="comfort", target=22, hvac="heat"):
        return {"mode": mode, "target_temperature": target, "target_hvac_mode": hvac, "reason": "shadow"}

    def test_primary_is_selected_and_temperature_action_is_data_only(self):
        result = build_passive_actor_plan(
            zone_id="esszimmer",
            heating_sources={"primary_climate_entity": "climate.esszimmer", "fallback_climate_entity": "climate.tado"},
            decision=self.decision(target=22),
            actor_states={
                "climate.esszimmer": {"state": "heat", "hvac_mode": "heat", "temperature": 20, "available": True},
                "climate.tado": {"state": "heat", "hvac_mode": "heat", "temperature": 20, "available": True},
            },
            service_evidence={"climate.set_temperature": True, "climate.set_hvac_mode": True},
        )
        self.assertEqual(result["selected_entity"], "climate.esszimmer")
        self.assertEqual([item["service"] for item in result["planned_commands"]], ["climate.set_temperature"])
        self.assertEqual(result["executed_commands"], [])
        self.assertTrue(all(item["execution_status"] == "not_executed" for item in result["planned_commands"]))

    def test_unavailable_primary_uses_only_available_fallback(self):
        result = build_passive_actor_plan(
            zone_id="esszimmer",
            heating_sources={"primary_climate_entity": "climate.esszimmer", "fallback_climate_entity": "climate.tado"},
            decision=self.decision(target=20),
            actor_states={
                "climate.esszimmer": {"state": "unavailable", "available": False},
                "climate.tado": {"state": "heat", "hvac_mode": "heat", "temperature": 18, "available": True},
            },
            service_evidence={"climate.set_temperature": True},
        )
        self.assertEqual(result["selected_entity"], "climate.tado")
        self.assertEqual({item["entity_id"] for item in result["planned_commands"]}, {"climate.tado"})

    def test_unknown_targets_and_capabilities_block_without_guessing(self):
        result = build_passive_actor_plan(
            zone_id="bathroom",
            heating_sources={"primary_climate_entity": "climate.unknown"},
            decision=self.decision(),
            actor_states={"climate.unknown": {"state": "unknown", "available": False}},
            service_evidence={},
        )
        self.assertEqual(result["planned_commands"], [])
        self.assertIn("actor_availability_readback", result["missing_prerequisites"])
        self.assertIn("physical_heat_demand_feedback", result["missing_prerequisites"])

    def test_chimney_sweep_keeps_priority_and_marks_physical_demand_unproven(self):
        result = build_passive_actor_plan(
            zone_id="esszimmer",
            heating_sources={"primary_climate_entity": "climate.esszimmer"},
            decision=self.decision(mode="chimney_sweep", target=25),
            active_special_mode={"id": "chimney_sweep"},
            priority=1000,
            actor_states={"climate.esszimmer": {"state": "heat", "hvac_mode": "heat", "temperature": 20, "available": True}},
            service_evidence={"climate.set_temperature": True},
        )
        self.assertEqual(result["priority"], 1000)
        self.assertEqual(result["physical_heat_demand"]["status"], "not_proven")
        self.assertEqual(result["execution_status"], "not_executed")
