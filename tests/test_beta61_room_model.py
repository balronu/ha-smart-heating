import unittest

from custom_components.smart_heating.management import normalize_management, validate_management


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


if __name__ == "__main__":
    unittest.main()
