import unittest
from pathlib import Path

class FinalArchitectureTests(unittest.TestCase):
    def test_internal_operating_mode_has_explicit_off_state(self):
        source = Path("custom_components/smart_heating/management.py").read_text()
        self.assertIn('OPERATING_MODES = ("automatic", "manual_heat", "manual_setback", "off")', source)

    def test_dashboard_has_only_passive_internal_mutations(self):
        source = Path("custom_components/smart_heating/frontend/final-dashboard.js").read_text()
        self.assertIn('smart_heating/admin/internal/set', source)
        self.assertIn('item: values', source)
        self.assertNotIn('callService("input_boolean"', source)
        self.assertNotIn('callService("input_number"', source)
        self.assertIn("Heizungssteuerung", source)
        self.assertIn("Hauptheizung", source)
        self.assertIn("Räume", source)

    def test_legacy_helper_migration_is_one_time_and_read_only(self):
        source = Path("custom_components/smart_heating/__init__.py").read_text()
        self.assertIn('migration.get("status") == "completed"', source)
        self.assertIn('runtime": "internal_config_entry"', source)
        self.assertIn("_async_migrate_legacy_helpers(hass, entry)", source)
        self.assertNotIn('hass.services.async_call("input_', source)


if __name__ == "__main__":
    unittest.main()
