import sys
import types
import unittest
from pathlib import Path

_package = types.ModuleType("custom_components.smart_heating")
_package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", _package)

from custom_components.smart_heating.discovery import discover_entities
from custom_components.smart_heating.migration import MigrationState, MigrationTransaction, preview_migration


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


class FakeTransport:
    def __init__(self, readback_ok=True):
        self.current = {"schedule": {"old": True}}
        self.readback_ok = readback_ok
        self.restored = None

    def snapshot(self):
        return dict(self.current)

    def activate(self, schedule):
        self.current = {"schedule": schedule}

    def readback(self):
        return self.current if self.readback_ok else {"schedule": {"wrong": True}}

    def restore(self, snapshot):
        self.restored = snapshot
        self.current = dict(snapshot)


class DiscoveryMigrationTests(unittest.TestCase):
    def test_unique_roles_are_selected_and_ties_stay_ambiguous(self):
        hass = FakeHass([
            FakeState("climate.esszimmer", "Esszimmer Heizung"),
            FakeState("input_boolean.heizung", "Heizung"),
            FakeState("input_boolean.heizung_freigabe", "Heizungsfreigabe"),
            FakeState("input_number.heiztemperatur", "Heiztemperatur"),
            FakeState("input_number.absenktemperatur", "Absenktemperatur"),
            FakeState("sensor.outdoor", "Outdoor Temperature"),
            FakeState("binary_sensor.fenster", "Fenster Esszimmer", attributes={"device_class": "window"}),
            FakeState("binary_sensor.batterie", "Fenster Batterie", state="on", attributes={"device_class": "battery"}),
            FakeState("sensor.fenster_temperatur", "Fenster Temperatur", state="20", attributes={"device_class": "temperature"}),
            FakeState("device_tracker.michael", "Michael Tracker", state="home"),
            FakeState("person.michael", "Michael"),
            FakeState("input_boolean.party", "Party"),
        ])
        result = discover_entities(hass)
        self.assertEqual(result["selected"]["climate_entity"], "climate.esszimmer")
        self.assertEqual(result["selected"]["heating_permission"], "input_boolean.heizung_freigabe")
        self.assertEqual(result["selected"]["outdoor_temperature"], "sensor.outdoor")
        self.assertEqual(result["roles"]["window_entities"]["selected"], ["binary_sensor.fenster"])
        self.assertEqual(result["roles"]["presence_entities"]["selected"], ["person.michael"])
        self.assertEqual(result["selected"]["special_modes"]["party"], "input_boolean.party")

    def test_preview_never_imports_fixture_and_reports_conflicts(self):
        hass = FakeHass([FakeState("input_boolean.heizung", "Heizung")])
        result = preview_migration(hass, FakeEntry())
        self.assertFalse(result["automatic_import"])
        self.assertEqual(result["source"], "none")
        self.assertIsNone(result["proposed_schedule"])
        self.assertTrue(any(item["code"] == "scheduler_export_unavailable" for item in result["conflicts"]))
        self.assertEqual(result["rollback"]["prepared"], False)
        self.assertFalse(result["installation"]["full_mode_ready"])
        self.assertIn("manual_action", result["installation"])

    def test_manual_schedule_is_only_a_validated_proposal(self):
        hass = FakeHass([])
        result = preview_migration(hass, FakeEntry(), {"monday": [{"start": "05:30", "end": "06:00"}]})
        self.assertEqual(result["source"], "manual_ui_proposal")
        self.assertEqual(result["proposed_schedule"]["monday"][0]["start"], "05:30:00")
        self.assertEqual(result["rollback"]["prepared"], False)

    def test_transaction_requires_explicit_confirmation_and_rolls_back_on_readback_failure(self):
        plan = {"proposed_schedule": {"monday": [{"start": "05:30:00", "end": "06:00:00"}]}, "activation_allowed": True}
        transport = FakeTransport(readback_ok=False)
        transaction = MigrationTransaction(plan, transport)
        with self.assertRaises(PermissionError):
            transaction.execute_isolated("wrong")
        with self.assertRaises(RuntimeError):
            transaction.execute_isolated(transaction.transaction_id)
        self.assertEqual(transaction.state, MigrationState.ROLLED_BACK)
        self.assertEqual(transport.current, {"schedule": {"old": True}})

    def test_successful_transaction_is_idempotent(self):
        schedule = {"monday": [{"start": "05:30:00", "end": "06:00:00"}]}
        transport = FakeTransport(readback_ok=True)
        transaction = MigrationTransaction({"proposed_schedule": schedule, "activation_allowed": True}, transport)
        result = transaction.execute_isolated(transaction.transaction_id)
        self.assertEqual(transaction.execute_isolated(transaction.transaction_id), result)
        self.assertEqual(transaction.state, MigrationState.VERIFIED)
        self.assertTrue(transaction.idempotency_key)

    def test_installation_plan_keeps_compatibility_separate_from_full_mode(self):
        hass = FakeHass([
            FakeState("climate.esszimmer", "Esszimmer Heizung"),
            FakeState("input_boolean.heizung_freigabe", "Heizungsfreigabe"),
            FakeState("input_number.heiztemperatur", "Heiztemperatur"),
            FakeState("input_number.absenktemperatur", "Absenktemperatur"),
        ])
        result = preview_migration(hass, FakeEntry(), {"monday": [{"start": "05:30", "end": "06:00"}]})
        self.assertTrue(result["installation"]["compatibility_ready"])
        self.assertFalse(result["installation"]["full_mode_ready"])
