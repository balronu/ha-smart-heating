"""Read-only inventory tests for existing heating helpers."""
import unittest
from types import SimpleNamespace
from custom_components.smart_heating.migration import inspect_legacy_helpers


class FakeStates:
    def __init__(self, values):
        self.values = values
    def async_all(self, domain):
        return [SimpleNamespace(entity_id=k, state=v) for k, v in self.values.items() if k.startswith(domain + ".")]


class LegacyHelperInventoryTests(unittest.TestCase):
    def test_missing_and_unavailable_are_not_claimed_available(self):
        hass = SimpleNamespace(states=FakeStates({
            "input_boolean.heizung": "on",
            "input_boolean.party": "unavailable",
            "input_number.heiztemperatur": "21",
        }))
        result = inspect_legacy_helpers(hass)
        self.assertEqual(result["input_boolean.heizung"], {"state": "on", "available": True, "valid": True})
        self.assertEqual(result["input_boolean.party"], {"state": "unavailable", "available": False, "valid": False})
        self.assertEqual(result["input_boolean.besuch"], {"state": None, "available": False, "valid": False})
        self.assertEqual(result["input_number.heiztemperatur"], {"state": "21", "available": True, "valid": True})
        self.assertEqual(len(result), 9)

    def test_inventory_does_not_write_states_or_call_services(self):
        class ReadOnlyStates(FakeStates):
            def async_set(self, *args, **kwargs):
                raise AssertionError("write attempted")
        hass = SimpleNamespace(states=ReadOnlyStates({}), services=None)
        self.assertEqual(len(inspect_legacy_helpers(hass)), 9)
