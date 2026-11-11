import unittest
from unittest.mock import patch

from custom_components.smart_heating.management import area_suggestions, normalize_management, validate_management


class Beta61RoomModelTests(unittest.TestCase):
    def test_beta60_zone_is_projected_to_one_canonical_room_idempotently(self):
        legacy = {
            "schema_version": 6,
            "zones": [{
                "id": "living",
                "name": "Wohnzimmer",
                "area_ids": ["living-area"],
                "thermostat_entities": ["climate.living"],
                "temperature_entities": ["sensor.living_temperature"],
                "comfort_temperature": 21,
                "night_temperature": 18,
            }],
        }
        first = normalize_management(legacy)
        second = normalize_management(first)
        self.assertEqual(first, second)
        self.assertEqual([room["id"] for room in first["rooms"]], ["living"])
        self.assertEqual(first["rooms"][0]["thermostat_entities"], ["climate.living"])
        self.assertEqual(first["zones"][0]["room_ids"], ["living"])
        self.assertEqual(validate_management(first), [])

    def test_rooms_do_not_require_a_zone_or_ha_area(self):
        data = normalize_management({
            "rooms": [{"id": "guest", "name": "Gästezimmer", "area_ids": [], "thermostat_entities": []}],
            "zones": [],
        })
        self.assertEqual(data["rooms"][0]["area_ids"], [])
        self.assertEqual(data["zones"], [])
        self.assertEqual(validate_management(data), [])

    def test_hidden_area_filter_survives_normalization(self):
        data = normalize_management({"area_filters": {"garage": "hidden"}, "relevant_area_ids": ["garage"]})
        self.assertEqual(data["area_filters"]["garage"], "hidden")
        self.assertNotIn("garage", data["relevant_area_ids"])

    def test_optional_groups_reference_rooms_without_equipment_duplication(self):
        data = normalize_management({
            "rooms": [{"id": "living", "name": "Wohnzimmer", "area_ids": [], "thermostat_entities": ["climate.living"]}],
            "zones": [{"id": "downstairs", "name": "Untergeschoss", "room_ids": ["living"], "thermostat_entities": ["climate.should-not-be-here"]}],
        })
        self.assertEqual(data["zones"][0]["room_ids"], ["living"])
        self.assertEqual(data["rooms"][0]["thermostat_entities"], ["climate.living"])
        self.assertEqual(validate_management(data), [])

    def test_area_status_exposes_saved_room_sources_not_only_ha_area_sources(self):
        class Hass:
            states = {}
        saved = {"rooms": [{"id": "bath", "name": "Badezimmer", "area_ids": ["bathroom"], "thermostat_entities": ["climate.heizthermostat_badezimmer"], "temperature_entities": ["sensor.bathroom"]}], "zones": [], "area_filters": {}}
        areas = [{"area_id": "bathroom", "name": "Badezimmer", "entity_ids": []}]
        with patch("custom_components.smart_heating.management.discover_areas", return_value=areas):
            result = area_suggestions(Hass(), saved)
        self.assertEqual(result[0]["status_source"], "smart_heating_room")
        self.assertEqual(result[0]["assigned_thermostat_entities"], ["climate.heizthermostat_badezimmer"])
        self.assertEqual(result[0]["configured_room"]["id"], "bath")


if __name__ == "__main__":
    unittest.main()
