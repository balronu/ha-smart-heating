"""Phase 38 passive room/window/mode engine contracts."""

from datetime import datetime, timezone
import unittest

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import sys

_SPEC = spec_from_file_location("smart_heating_backend_engine", Path(__file__).parents[1] / "custom_components" / "smart_heating" / "backend_engine.py")
_ENGINE = module_from_spec(_SPEC)
assert _SPEC and _SPEC.loader
sys.modules["smart_heating_backend_engine"] = _ENGINE
_SPEC.loader.exec_module(_ENGINE)

from smart_heating_backend_engine import (
    aggregate_window_states,
    calculate_room_demand,
    evaluate_window_groups,
    evaluate_window_strategy,
    normalize_window_state,
    resolve_special_modes,
)


class BackendEngineTests(unittest.TestCase):
    def test_binary_contact_never_invents_tilt(self):
        self.assertEqual(normalize_window_state("on", "binary"), "open")
        self.assertEqual(normalize_window_state("on", "tilt"), "tilted")
        self.assertEqual(aggregate_window_states(["open", "closed"]), "open")

    def test_window_groups_keep_conflicts_and_unknowns(self):
        result = evaluate_window_groups([
            {"id": "window-1", "name": "Esszimmer", "sensors": [
                {"entity_id": "binary_sensor.open", "state": "on", "semantics": "open"},
                {"entity_id": "binary_sensor.tilt", "state": "on", "semantics": "tilt"},
            ]},
            {"id": "window-2", "sensors": [{"entity_id": "binary_sensor.missing", "state": "unknown", "semantics": "binary"}]},
        ])
        self.assertEqual(result["windows"][0]["state"], "open")
        self.assertFalse(result["windows"][0]["conflict"])
        self.assertEqual(result["windows"][1]["state"], "unknown")

    def test_window_strategy_is_delayed_and_passive(self):
        before = evaluate_window_strategy(state="open", strategy="frost", open_delay=60, elapsed_seconds=30)
        after = evaluate_window_strategy(state="open", strategy="frost", open_delay=60, elapsed_seconds=60)
        self.assertFalse(before["effective"])
        self.assertEqual(after["action"], "frost")
        self.assertTrue(after["passive"])

    def test_special_mode_priority_expiry_and_deterministic_tie(self):
        now = datetime(2026, 11, 1, tzinfo=timezone.utc)
        result = resolve_special_modes([
            {"id": "party", "mode_type": "party", "available": True, "active": True},
            {"id": "chimney", "mode_type": "chimney_sweep", "available": True, "active": True},
            {"id": "expired", "mode_type": "custom", "available": True, "active": True, "expires_at": "2026-10-31T23:00:00+00:00"},
        ], now=now)
        self.assertEqual(result["winner"]["id"], "chimney")
        self.assertEqual(result["expired"], ["expired"])
        self.assertEqual(result["suppressed"][0]["id"], "party")

    def test_room_demand_unknown_never_becomes_heat_demand(self):
        result = calculate_room_demand(
            room_temperature=None,
            target_temperature=21,
            windows={"state": "unknown"},
            window_reaction={"action": "none"},
            thermostats=[{"entity_id": "climate.a", "state": "heat", "available": True}],
        )
        self.assertIsNone(result["heat_demand"])
        self.assertEqual(result["commands"], [])
        self.assertTrue(result["passive"])

    def test_multiple_thermostats_allow_partial_outage(self):
        result = calculate_room_demand(
            room_temperature=19,
            target_temperature=21,
            windows={"state": "closed"},
            window_reaction={"action": "none"},
            thermostats=[
                {"entity_id": "climate.a", "state": "heat", "available": True},
                {"entity_id": "climate.b", "state": "unavailable", "available": False},
                {"entity_id": "climate.c", "state": "heat", "available": True},
            ],
        )
        self.assertTrue(result["heat_demand"])
        self.assertEqual(result["available_thermostats"], 2)
        self.assertEqual(result["thermostat_count"], 3)
        self.assertEqual(result["commands"], [])
