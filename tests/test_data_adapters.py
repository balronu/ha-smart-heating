import asyncio
import unittest
from datetime import datetime

from custom_components.smart_heating.data_adapters import ReadOnlyShadowDataAdapter, normalize_legacy_trace, read_only_with_timeout


class State:
    def __init__(self, state, attributes=None):
        self.state = state
        self.attributes = attributes or {}


class States:
    def __init__(self, values):
        self.values = values

    def get(self, entity_id):
        return self.values.get(entity_id)


class Hass:
    def __init__(self, values):
        self.states = States(values)


class DataAdapterTests(unittest.TestCase):
    def test_snapshot_reads_only_known_sources_and_marks_scheduler_gap(self):
        hass = Hass({"climate.esszimmer": State("heat", {"temperature": 22, "hvac_action": "heating"}), "input_boolean.heizung": State("on")})
        result = ReadOnlyShadowDataAdapter(hass, clock=lambda: datetime(2026, 11, 2, 7, 0)).snapshot(
            primary_climate="climate.esszimmer", fallback_climate="climate.tado"
        )
        self.assertTrue(result["read_only"])
        self.assertEqual(result["service_calls"], 0)
        self.assertEqual(result["climates"]["climate.esszimmer"]["temperature"], 22)
        self.assertEqual(result["climates"]["climate.tado"]["state"], "missing")
        self.assertEqual(result["scheduler"]["status"], "partial")
        self.assertIn("simple_scheduler_readonly_export", result["scheduler"]["missing"])

    def test_missing_trace_is_not_a_legacy_decision(self):
        result = normalize_legacy_trace(None, timestamp="2026-11-02T07:00:00+01:00")
        self.assertFalse(result["proven"])
        self.assertEqual(result["status"], "missing")

    def test_incomplete_trace_does_not_invent_target(self):
        result = normalize_legacy_trace({"proven": True, "timestamp": "2026-11-02T07:00:00+01:00"}, timestamp="now")
        self.assertFalse(result["proven"])
        self.assertNotIn("decision", result)

    def test_proven_trace_is_normalized_without_state_inference(self):
        result = normalize_legacy_trace(
            {
                "proven": True,
                "source": "trace.fixture",
                "timestamp": "2026-11-02T07:00:00+01:00",
                "decision": {"target_temperature": 22, "target_hvac_mode": "heat"},
            },
            timestamp="now",
        )
        self.assertTrue(result["proven"])
        self.assertEqual(result["decision"]["target_temperature"], 22)
        self.assertEqual(result["source"], "trace.fixture")

    def test_read_only_timeout_and_error_are_bounded_and_sanitized(self):
        async def slow():
            await asyncio.sleep(0.02)
            return {"secret": "never logged"}

        timeout = asyncio.run(read_only_with_timeout(slow, timeout_seconds=0.001))
        self.assertEqual(timeout["status"], "timeout")
        error = asyncio.run(read_only_with_timeout(lambda: (_ for _ in ()).throw(RuntimeError("secret"))))
        self.assertEqual(error["status"], "error")
        self.assertEqual(error["error"], "RuntimeError")
        self.assertNotIn("secret", error)
