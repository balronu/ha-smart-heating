import sys
import types
import unittest
from pathlib import Path

package = types.ModuleType("custom_components.smart_heating")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", package)

from custom_components.smart_heating.management import build_window_role_diagnostics  # noqa: E402


class WindowRoleDiagnosticsTests(unittest.TestCase):
    def test_keeps_missing_values_distinct_and_reports_source_mismatch(self):
        contacts = [
            {"entity_id": "binary_sensor.bath_tilt", "name": "Bad gekippt", "assigned_area_id": "bath"},
            {"entity_id": "binary_sensor.bath_open", "name": "Bad offen", "assigned_area_id": "bath"},
        ]
        result = build_window_role_diagnostics(
            config_entry_options={"management": {"sensors": {"window": [{"entity_id": contacts[0]["entity_id"], "contact_role": "tilt"}]}}},
            runtime_management={"sensors": {"window": [{"entity_id": contacts[0]["entity_id"], "contact_role": "unassigned"}]}},
            readback_management={"sensors": {"window": [{"entity_id": contacts[0]["entity_id"], "contact_role": "tilt"}, {"entity_id": contacts[1]["entity_id"], "contact_role": "open"}]}},
            assigned_contacts=contacts,
        )
        self.assertEqual(result[0]["config_entry_role"], "tilt")
        self.assertEqual(result[0]["runtime_role"], "unassigned")
        self.assertEqual(result[0]["readback_role"], "tilt")
        self.assertFalse(result[0]["matches"])
        self.assertEqual(result[1]["config_entry_role"], None)
        self.assertEqual(result[1]["runtime_role"], None)
        self.assertEqual(result[1]["readback_role"], "open")
        self.assertEqual(result[1]["status"], "Abweichung")

    def test_reports_agreement_for_multiple_contacts_without_writing(self):
        contacts = [
            {"entity_id": "binary_sensor.one", "name": "Kontakt 1", "assigned_area_id": "room"},
            {"entity_id": "binary_sensor.two", "name": "Kontakt 2", "assigned_area_id": "room"},
        ]
        management = {"sensors": {"window": [{"entity_id": "binary_sensor.one", "contact_role": "tilt"}, {"entity_id": "binary_sensor.two", "contact_role": "open"}]}}
        result = build_window_role_diagnostics(
            config_entry_options={"management": management},
            runtime_management=management,
            readback_management=management,
            assigned_contacts=contacts,
        )
        self.assertEqual([item["status"] for item in result], ["Übereinstimmung", "Übereinstimmung"])
        self.assertTrue(all(item["matches"] for item in result))
        self.assertEqual(management["sensors"]["window"][0]["contact_role"], "tilt")

    def test_diagnostic_input_does_not_require_area_or_zone_metadata(self):
        contact = {"entity_id": "binary_sensor.legacy_contact", "name": "Altkontakt"}
        management = {"sensors": {"window": [{"entity_id": contact["entity_id"]}]}}
        result = build_window_role_diagnostics(
            config_entry_options={"management": management},
            runtime_management=management,
            readback_management=management,
            assigned_contacts=[contact],
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["entity_id"], contact["entity_id"])
        self.assertIsNone(result[0]["config_entry_role"])
        self.assertEqual(result[0]["status"], "Nicht vorhanden")


if __name__ == "__main__":
    unittest.main()
