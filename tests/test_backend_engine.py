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
    evaluate_window_contacts,
    evaluate_window_groups,
    evaluate_window_strategy,
    normalize_window_state,
    resolve_passive_decision,
    resolve_special_modes,
)


class BackendEngineTests(unittest.TestCase):
    def test_contact_roles_use_open_precedence_and_ignore_invalid_states(self):
        result = evaluate_window_contacts([
            {"entity_id": "binary_sensor.tilt", "contact_role": "tilt", "state": "on"},
            {"entity_id": "binary_sensor.open", "contact_role": "open", "state": "on"},
        ])
        self.assertEqual(result["state"], "open")
        self.assertTrue(all(item["considered_for_automation"] for item in result["contacts"]))

        ignored = evaluate_window_contacts([
            {"entity_id": "binary_sensor.tilt", "contact_role": "tilt", "state": "unknown"},
            {"entity_id": "binary_sensor.open", "contact_role": "open", "state": "unavailable"},
        ])
        self.assertEqual(ignored["state"], "closed")
        self.assertEqual(ignored["valid_count"], 0)
        self.assertTrue(all(item["automation_ignored"] for item in ignored["contacts"]))
        self.assertTrue(all(item["reason"] == "Für Heizungsautomatik ignoriert" for item in ignored["contacts"]))

    def test_contact_roles_support_multiple_same_role_and_recovery(self):
        result = evaluate_window_contacts([
            {"entity_id": "binary_sensor.open1", "contact_role": "open", "state": "off"},
            {"entity_id": "binary_sensor.open2", "contact_role": "open", "state": "on"},
            {"entity_id": "binary_sensor.tilt", "contact_role": "tilt", "state": "unavailable"},
        ])
        self.assertEqual(result["state"], "open")
        recovered = evaluate_window_contacts([
            {"entity_id": "binary_sensor.open1", "contact_role": "open", "state": "off"},
            {"entity_id": "binary_sensor.open2", "contact_role": "open", "state": "off"},
            {"entity_id": "binary_sensor.tilt", "contact_role": "tilt", "state": "on"},
        ])
        self.assertEqual(recovered["state"], "tilted")
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

    def test_built_in_effects_are_passive_and_conditions_are_explicit(self):
        now = datetime(2026, 11, 1, tzinfo=timezone.utc)
        result = resolve_special_modes([
            {"id": "party", "mode_type": "party", "available": True, "active": True},
            {"id": "conditional", "mode_type": "custom", "available": True, "active": True, "priority": 900, "conditions": {"presence": "home"}},
            {"id": "unknown", "mode_type": "custom", "available": True, "active": True, "status_state": "unknown"},
        ], now=now, presence_status="away")
        self.assertEqual(result["winner"]["id"], "party")
        self.assertEqual(result["winner"]["effect"]["action"], "comfort")
        self.assertEqual(result["blocked"], [{"id": "conditional", "reason": "Anwesenheitsbedingung nicht erfüllt"}, {"id": "unknown", "reason": "Statusquelle unbekannt"}])
        self.assertTrue(result["passive"])

    def test_mode_effects_apply_target_references_and_return_to_normal(self):
        base = type("Decision", (), {"mode": "night", "reason": "night", "source": "reference", "target_temperature": 17, "target_hvac_mode": "heat"})()
        party = resolve_special_modes([{"id": "party", "mode_type": "party", "available": True, "active": True}], now=datetime(2026, 11, 1, tzinfo=timezone.utc))
        applied = resolve_passive_decision(base, party, comfort_temperature=22, setback_temperature=17)
        self.assertEqual(applied["mode"], "party")
        self.assertEqual(applied["target_temperature"], 22.0)
        self.assertTrue(applied["schedule_overridden"])
        self.assertTrue(applied["passive"])
        expired = resolve_special_modes([{"id": "party", "mode_type": "party", "available": True, "active": True, "expires_at": "2026-10-31T23:00:00+00:00"}], now=datetime(2026, 11, 1, tzinfo=timezone.utc))
        self.assertTrue(resolve_passive_decision(base, expired)["returned_to_normal"])

    def test_chimney_sweep_overrides_windows_presence_and_schedule_without_commands(self):
        base = type("Decision", (), {"mode": "summer", "reason": "summer", "source": "reference", "target_temperature": 17, "target_hvac_mode": "off"})()
        modes = resolve_special_modes([{"id": "chimney", "mode_type": "chimney_sweep", "available": True, "active": True, "priority": 1}], now=datetime(2026, 11, 1, tzinfo=timezone.utc), presence_status="away", window_state="open")
        applied = resolve_passive_decision(base, modes, chimney_temperature=25)
        self.assertEqual(applied["priority"], 1000)
        self.assertEqual(applied["target_temperature"], 25.0)
        self.assertEqual(applied["target_hvac_mode"], "heat")
        self.assertTrue(applied["window_override"])
        self.assertTrue(applied["presence_override"])
        self.assertIsNone(applied["heat_demand_override"])

    def test_configured_mode_respects_window_and_presence_constraints(self):
        base = type("Decision", (), {"mode": "window_open", "reason": "window", "source": "reference", "target_temperature": 5, "target_hvac_mode": "heat"})()
        modes = resolve_special_modes([{"id": "party", "mode_type": "party", "available": True, "active": True}], now=datetime(2026, 11, 1, tzinfo=timezone.utc))
        applied = resolve_passive_decision(base, modes, comfort_temperature=22, window_state="open", presence_status="away")
        self.assertEqual(applied["mode"], "window_open")
        self.assertTrue(applied["blocked_by_window"])
        self.assertEqual(applied["target_temperature"], 5)

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
