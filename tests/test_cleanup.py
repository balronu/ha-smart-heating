import unittest
import sys
import types
from pathlib import Path

package = types.ModuleType("custom_components.smart_heating")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", package)

from custom_components.smart_heating.cleanup import build_cleanup_plan


class CleanupPlanTests(unittest.TestCase):
    def test_exact_native_ownership_and_duplicate_entry_are_candidates(self):
        plan = build_cleanup_plan(
            [
                {"entry_id": "keep", "domain": "smart_heating"},
                {"entry_id": "duplicate", "domain": "smart_heating"},
            ],
            [
                {"entity_id": "sensor.mode", "platform": "smart_heating", "config_entry_id": "keep"},
                {"entity_id": "sensor.mode_2", "platform": "smart_heating", "config_entry_id": "duplicate"},
                {"entity_id": "input_boolean.heizung", "platform": "input_boolean", "config_entry_id": None},
            ],
            keep_entry_id="keep",
        )
        self.assertEqual(plan["duplicate_entry_ids"], ["duplicate"])
        self.assertEqual([item["entity_id"] for item in plan["native_owned_entities"]], ["sensor.mode", "sensor.mode_2"])
        self.assertEqual([item["entity_id"] for item in plan["retained_entities"]], ["input_boolean.heizung"])
        self.assertTrue(plan["requires_explicit_approval"])

    def test_protected_entity_is_never_a_candidate(self):
        plan = build_cleanup_plan(
            [{"entry_id": "keep", "domain": "smart_heating"}],
            [{"entity_id": "input_boolean.heizung", "platform": "smart_heating", "config_entry_id": "keep"}],
            keep_entry_id="keep",
            protected_entity_ids=["input_boolean.heizung"],
        )
        self.assertEqual(plan["native_owned_entities"], [])
        self.assertEqual(plan["retained_entities"][0]["entity_id"], "input_boolean.heizung")
