import sys
import types
import unittest
from pathlib import Path

_package = types.ModuleType("custom_components.smart_heating")
_package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", _package)

from custom_components.smart_heating.discovery import discover_entities
from custom_components.smart_heating.migration import preview_migration


class FakeState:
    def __init__(self, entity_id, name, state="off", attributes=None):
        self.entity_id = entity_id
        self.name = name
        self.state = state
        self.attributes = attributes or {}


class FakeStates:
    def __init__(self, items):
        self.items = items

    def async_all(self, domain):
        return [item for item in self.items if item.entity_id.split(".", 1)[0] == domain]


class FakeHass:
    def __init__(self, items):
        self.states = FakeStates(items)


class FakeEntry:
    entry_id = "entry-1"


class DiscoveryMigrationTests(unittest.TestCase):
    def test_unique_roles_are_selected_and_ties_stay_ambiguous(self):
        hass = FakeHass([
            FakeState("climate.esszimmer", "Esszimmer Heizung"),
            FakeState("input_boolean.heizung", "Heizung"),
            FakeState("input_boolean.heizung_freigabe", "Heizungsfreigabe"),
            FakeState("input_number.heiztemperatur", "Heiztemperatur"),
            FakeState("input_number.absenktemperatur", "Absenktemperatur"),
            FakeState("binary_sensor.fenster", "Fenster Esszimmer", attributes={"device_class": "window"}),
            FakeState("person.michael", "Michael"),
            FakeState("input_boolean.party", "Party"),
        ])
        result = discover_entities(hass)
        self.assertEqual(result["selected"]["climate_entity"], "climate.esszimmer")
        self.assertEqual(result["selected"]["heating_permission"], "input_boolean.heizung_freigabe")
        self.assertEqual(result["roles"]["window_entities"]["selected"], ["binary_sensor.fenster"])
        self.assertEqual(result["selected"]["special_modes"]["party"], "input_boolean.party")

    def test_preview_never_imports_fixture_and_reports_conflicts(self):
        hass = FakeHass([FakeState("input_boolean.heizung", "Heizung")])
        result = preview_migration(hass, FakeEntry())
        self.assertFalse(result["automatic_import"])
        self.assertEqual(result["source"], "none")
        self.assertIsNone(result["proposed_schedule"])
        self.assertTrue(any(item["code"] == "scheduler_export_unavailable" for item in result["conflicts"]))
        self.assertEqual(result["rollback"]["prepared"], False)

    def test_manual_schedule_is_only_a_validated_proposal(self):
        hass = FakeHass([])
        result = preview_migration(hass, FakeEntry(), {"monday": [{"start": "05:30", "end": "06:00"}]})
        self.assertEqual(result["source"], "manual_ui_proposal")
        self.assertEqual(result["proposed_schedule"]["monday"][0]["start"], "05:30:00")
        self.assertEqual(result["rollback"]["prepared"], False)
