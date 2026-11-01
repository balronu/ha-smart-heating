import unittest
from datetime import datetime, timedelta

from custom_components.smart_heating.shadow_compare import compare_shadow_decision


class ShadowComparisonTests(unittest.TestCase):
    NOW = datetime.fromisoformat("2026-11-02T07:00:00+01:00")

    def compare(self, legacy, smart=22):
        return compare_shadow_decision(
            timestamp=self.NOW,
            zone_id="esszimmer",
            observed_thermostat={"entity_id": "climate.esszimmer", "state": "heat", "temperature": 22},
            legacy_decision=legacy,
            smart_decision={"target_temperature": smart, "target_hvac_mode": "heat"},
            planned_actor_action={"execution_status": "not_executed"},
            active_special_mode={"id": "chimney_sweep"},
            priority=1000,
            schedule_decision={"active": True, "source_verified": False},
            window_state="closed",
            presence={"status": "home"},
            data_quality="incomplete",
        )

    def test_equal_values_require_proven_fresh_legacy_trace(self):
        result = self.compare({"target_temperature": 22, "proven": True, "source": "trace", "timestamp": self.NOW.isoformat()})
        self.assertEqual(result["comparison"], "match_proven")
        self.assertEqual(result["legacy_source"], "trace")

    def test_different_values_are_reported_as_divergence(self):
        result = self.compare({"target_temperature": 17, "proven": True, "source": "trace", "timestamp": self.NOW.isoformat()})
        self.assertEqual(result["comparison"], "divergence_proven")

    def test_old_trace_is_stale_not_a_match(self):
        old = (self.NOW - timedelta(minutes=16)).isoformat()
        result = self.compare({"target_temperature": 22, "proven": True, "source": "trace", "timestamp": old})
        self.assertEqual(result["comparison"], "stale_data")
        self.assertEqual(result["legacy_age_seconds"], 16 * 60)

    def test_simulated_trace_remains_marked_simulated(self):
        result = self.compare({"target_temperature": 22, "proven": True, "source": "fixture", "simulated": True, "timestamp": self.NOW.isoformat()})
        self.assertTrue(result["simulated"])
        self.assertFalse(result["smart_takeover_allowed"])
