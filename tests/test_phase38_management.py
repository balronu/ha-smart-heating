import unittest

from custom_components.smart_heating.management import normalize_management, validate_management


class Phase38ManagementTests(unittest.TestCase):
    def test_legacy_single_thermostat_migrates_idempotently(self):
        legacy = {"zones": [{"id": "dining", "name": "Esszimmer", "thermostat_entity": "climate.esszimmer"}]}
        first = normalize_management(legacy)
        second = normalize_management(first)
        self.assertEqual(first, second)
        self.assertEqual(first["zones"][0]["thermostat_entities"], ["climate.esszimmer"])
        self.assertEqual(first["schema_version"], 4)

    def test_three_thermostats_and_duplicate_conflict_are_visible(self):
        data = normalize_management({"zones": [
            {"id": "dining", "name": "Esszimmer", "thermostat_entities": ["climate.a", "climate.b", "climate.c"]},
            {"id": "living", "name": "Wohnzimmer", "thermostat_entities": ["climate.c"]},
        ]})
        errors = validate_management(data)
        self.assertIn("thermostat_conflict:climate.c:dining:living", errors)
        self.assertEqual(len(data["zones"][0]["thermostat_entities"]), 3)

    def test_window_groups_and_mode_effect_are_normalized(self):
        data = normalize_management({
            "zones": [{"id": "dining", "name": "Esszimmer", "window_strategy": "pause_demand", "window_delays": {"open": 120}, "window_groups": [{"id": "w1", "sensors": [{"entity_id": "binary_sensor.window", "semantics": "open"}]}]}],
            "special_modes": [{"id": "party-custom", "name": "Party Plus", "mode_type": "custom", "activation_type": "internal", "effect": {"action": "fixed_temperature"}, "window_handling": "ignore_tilted", "available": True}],
        })
        self.assertEqual(data["zones"][0]["window_delays"]["open"], 120)
        self.assertEqual(data["zones"][0]["window_groups"][0]["id"], "w1")
        mode = next(item for item in data["special_modes"] if item["id"] == "party-custom")
        self.assertEqual(mode["effect"]["action"], "fixed_temperature")
        self.assertEqual(validate_management(data), [])
