import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

package = types.ModuleType("custom_components.smart_heating")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", package)

from custom_components.smart_heating.management import (  # noqa: E402
    default_management,
    is_eligible_window_entity,
    person_presence,
    upsert_item,
    validate_management,
    window_contact_summary,
)
from custom_components.smart_heating.models import evaluate_decision  # noqa: E402
from custom_components.smart_heating.storage import load_schedule  # noqa: E402


class State:
    def __init__(self, state):
        self.state = state


class States:
    def __init__(self, values):
        self.values = values

    def get(self, entity_id):
        return self.values.get(entity_id)


class Hass:
    def __init__(self, values):
        self.states = States(values)


class ManagementTests(unittest.TestCase):
    def test_native_persons_aggregate_home_and_unknown(self):
        data = default_management()
        upsert_item(data, "persons", {"id": "a", "name": "A", "presence_entities": ["person.a"]})
        upsert_item(data, "persons", {"id": "b", "name": "B", "presence_entities": ["person.b"]})
        self.assertEqual(person_presence(Hass({"person.a": State("home"), "person.b": State("unknown")}), data["persons"])["status"], "home")
        self.assertTrue(person_presence(Hass({"person.a": State("not_home"), "person.b": State("unknown")}), data["persons"])["unknown"])

    def test_no_persons_disables_presence(self):
        result = person_presence(Hass({}), [])
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["away"])

    def test_trackers_are_not_accepted_as_person_assignments(self):
        data = default_management()
        person = upsert_item(data, "persons", {"name": "A", "presence_entities": ["device_tracker.a"]})
        self.assertEqual(person["presence_entities"], [])

    def test_active_thermostat_cannot_have_two_zone_owners(self):
        data = default_management()
        upsert_item(data, "zones", {"id": "one", "name": "One", "thermostat_entities": ["climate.one"]})
        with self.assertRaises(ValueError):
            upsert_item(data, "zones", {"id": "two", "name": "Two", "thermostat_entities": ["climate.one"]})

    def test_sensors_can_be_shared_but_unknown_zone_is_rejected(self):
        data = default_management()
        upsert_item(data, "zones", {"id": "one", "name": "One"})
        upsert_item(data, "sensors", {"type": "window", "entity_id": "binary_sensor.window", "zone_ids": ["one"]})
        self.assertFalse(validate_management(data))
        self.assertTrue(validate_management({**data, "zones": []}))

    def test_internal_modes_and_zone_schedule_work_without_helpers(self):
        data = default_management()
        upsert_item(data, "zones", {"id": "zone", "name": "Zone", "schedule": {"monday": [{"start": "05:00", "end": "06:00"}]}})
        data["internal"]["operating_mode"] = "manual_heat"
        self.assertEqual(evaluate_decision(schedule_active=False, overrides={"manual_heat": True}, comfort_temperature=21).mode, "manual_heat")
        self.assertTrue(load_schedule({"schedule": {}, "management": data}).windows["monday"])

    def test_only_binary_opening_sensors_are_eligible(self):
        self.assertTrue(is_eligible_window_entity("binary_sensor.fenster_wohnzimmer", "window"))
        self.assertTrue(is_eligible_window_entity("binary_sensor.tuer", "door"))
        self.assertFalse(is_eligible_window_entity("sensor.fenster_wohnzimmer_battery", "window"))
        self.assertFalse(is_eligible_window_entity("binary_sensor.fenster_temperatur", "temperature"))

    def test_many_contacts_keep_room_and_review_metadata_without_deletion(self):
        data = default_management()
        upsert_item(data, "sensors", {"id": "old", "type": "window", "entity_id": "sensor.fenster_battery", "area_id": "wohnzimmer"})
        contacts = [
            {"entity_id": "binary_sensor.fenster_a", "name": "Fenster A", "area_id": "wohnzimmer", "area_name": "Wohnzimmer", "status": "closed", "available": True, "configured": False, "review_flags": [], "review_required": False},
            {"entity_id": "binary_sensor.fenster_b", "name": "Fenster B", "area_id": "wohnzimmer", "area_name": "Wohnzimmer", "status": "open", "available": True, "configured": False, "review_flags": [], "review_required": False},
        ]
        with patch("custom_components.smart_heating.management.discover_window_contacts", return_value=contacts):
            result = window_contact_summary(Hass({}), data)
        self.assertEqual(result["total"], 3)
        preserved = next(item for item in result["contacts"] if item["entity_id"] == "sensor.fenster_battery")
        self.assertIn("configured_but_not_eligible", preserved["review_flags"])
        self.assertEqual(result["groups"][0]["area_name"], "Wohnzimmer")
