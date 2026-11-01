import unittest
from datetime import datetime
import sys
import types
from pathlib import Path

_package = types.ModuleType("custom_components.smart_heating")
_package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", _package)

from custom_components.smart_heating.engine import calculate_status
from custom_components.smart_heating.models import ScheduleValidationError, WeeklySchedule, evaluate_decision, reset_actions, summer_hysteresis_state


class ScheduleTests(unittest.TestCase):
    def test_all_weekdays_and_multiple_windows(self):
        schedule = WeeklySchedule.from_mapping({day: [{"start": "06:00", "end": "08:00"}, {"start": "17:00", "end": "22:00"}] for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")})
        self.assertEqual(len(schedule.windows["sunday"]), 2)
        self.assertTrue(schedule.active_at(datetime.fromisoformat("2026-11-02T07:00:00+01:00"), "Europe/Berlin"))

    def test_optional_target_temperature_is_preserved(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "08:00", "target_temperature": 20.5}]})
        self.assertEqual(schedule.as_dict()["monday"][0]["target_temperature"], 20.5)

    def test_overlap_rejected(self):
        with self.assertRaises(ScheduleValidationError):
            WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "08:00"}, {"start": "07:00", "end": "09:00"}]})

    def test_equal_start_and_end_is_rejected(self):
        with self.assertRaises(ScheduleValidationError):
            WeeklySchedule.from_mapping({"monday": [{"start": "22:00", "end": "22:00"}]})

    def test_overnight_window_crosses_midnight_and_week_boundary(self):
        schedule = WeeklySchedule.from_mapping({"sunday": [{"start": "22:00", "end": "02:00", "target_temperature": 21.5}]})
        self.assertTrue(schedule.active_at(datetime.fromisoformat("2026-11-01T23:30:00+01:00"), "Europe/Berlin"))
        self.assertTrue(schedule.active_at(datetime.fromisoformat("2026-11-02T01:30:00+01:00"), "Europe/Berlin"))
        self.assertFalse(schedule.active_at(datetime.fromisoformat("2026-11-02T02:00:00+01:00"), "Europe/Berlin"))
        self.assertEqual(schedule.active_window_at(datetime.fromisoformat("2026-11-02T01:30:00+01:00"), "Europe/Berlin").target_temperature, 21.5)
        next_switch, next_state = schedule.next_switch(datetime.fromisoformat("2026-11-02T01:30:00+01:00"), "Europe/Berlin")
        self.assertEqual((next_switch.date().isoformat(), next_switch.hour, next_switch.minute, next_state), ("2026-11-02", 2, 0, False))

    def test_window_target_is_used_by_passive_comfort_decision(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "08:00", "target_temperature": 21.5}]})
        result = calculate_status(
            schedule,
            now=datetime.fromisoformat("2026-11-02T07:00:00+01:00"),
            timezone="Europe/Berlin",
            context={"comfort_temperature": 22, "night_temperature": 17, "heating_sources": {"primary_climate_entity": "climate.test"}, "schedule_source_verified": True},
        )
        self.assertEqual(result["target_temperature"], 21.5)
        self.assertEqual(result["shadow"]["schedule_decision"]["active"], True)
        self.assertEqual(result["shadow"]["schedule_decision"]["next_switch"], "2026-11-02T08:00:00+01:00")

    def test_week_boundary(self):
        schedule = WeeklySchedule.from_mapping({"sunday": [{"start": "23:00", "end": "23:59"}], "monday": [{"start": "06:00", "end": "07:00"}]})
        next_switch, next_state = schedule.next_switch(datetime.fromisoformat("2026-11-01T23:30:00+01:00"), "Europe/Berlin")
        self.assertEqual(next_state, False)
        self.assertEqual(next_switch.hour, 23)

    def test_priority_matches_reference(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(schedule, now=datetime.fromisoformat("2026-11-02T07:00:00+01:00"), timezone="Europe/Berlin", overrides={"window_open": True, "chimney_sweep": True})
        self.assertEqual(result["mode"], "chimney_sweep")

    def test_simulation_does_not_control_entities(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(schedule, now=datetime.fromisoformat("2026-11-02T07:00:00+01:00"), timezone="Europe/Berlin")
        self.assertTrue(result["simulated"])
        self.assertNotIn("service", result)

    def test_unknown_window_is_not_treated_as_closed(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(
            schedule,
            now=datetime.fromisoformat("2026-11-02T07:00:00+01:00"),
            timezone="Europe/Berlin",
            overrides={"window_unknown": True},
            context={"comfort_temperature": 22, "night_temperature": 17},
        )
        self.assertEqual(result["mode"], "window_unknown")
        self.assertIsNone(result["target_temperature"])
        self.assertIsNone(result["target_hvac_mode"])

    def test_dst_transition_uses_local_calendar(self):
        schedule = WeeklySchedule.from_mapping({"sunday": [{"start": "01:30", "end": "03:30"}]})
        self.assertTrue(schedule.active_at(datetime.fromisoformat("2026-03-29T01:45:00+01:00"), "Europe/Berlin"))
        next_switch, next_state = schedule.next_switch(datetime.fromisoformat("2026-03-29T01:45:00+01:00"), "Europe/Berlin")
        self.assertEqual(next_state, False)
        self.assertEqual(next_switch.tzinfo.key, "Europe/Berlin")

    def test_reference_special_mode_semantics(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        cases = [
            ({"heating_permission": False, "chimney_sweep": True}, "chimney_sweep"),
            ({"heating_permission": False}, "disabled"),
            ({"window_open": True, "window_tilted": True}, "window_open"),
            ({"window_tilted": True}, "window_tilted"),
            ({"away": True, "visit": False, "return_home": False}, "away"),
            ({"summer": True, "return_home": False, "party": False}, "summer"),
        ]
        for overrides, expected in cases:
            with self.subTest(expected=expected):
                instant = datetime.fromisoformat("2026-11-02T07:00:00+01:00") if expected == "summer" else datetime.fromisoformat("2026-11-02T22:00:00+01:00")
                result = calculate_status(schedule, now=instant, timezone="Europe/Berlin", overrides=overrides)
                self.assertEqual(result["mode"], expected)

    def test_full_decision_targets_preserve_reference_priority(self):
        cases = [
            ({"chimney_sweep": True, "heating_permission": False, "window_open": True}, "chimney_sweep", "heat", 25.0),
            ({"heating_permission": False}, "disabled", "off", None),
            ({"window_open": True}, "window_open", "heat", 5.0),
            ({"window_tilted": True}, "window_tilted", "heat", 17.0),
            ({"away": True}, "away", "heat", 17.0),
            ({"party": True}, "party", "heat", 22.0),
        ]
        for flags, mode, hvac, target in cases:
            with self.subTest(mode=mode):
                decision = evaluate_decision(schedule_active=False, overrides=flags, comfort_temperature=22, night_temperature=17)
                self.assertEqual((decision.mode, decision.target_hvac_mode, decision.target_temperature), (mode, hvac, target))

    def test_summer_modes_are_explicit_and_safe(self):
        compatibility = evaluate_decision(schedule_active=True, overrides={"summer": True}, comfort_temperature=22, night_temperature=17)
        hvac_off = evaluate_decision(schedule_active=True, overrides={"summer": True}, comfort_temperature=22, night_temperature=17, summer_mode="hvac_off")
        unsupported = evaluate_decision(schedule_active=True, overrides={"summer": True}, comfort_temperature=22, night_temperature=17, summer_mode="hvac_off", hvac_supports_off=False)
        self.assertEqual(compatibility.target_hvac_mode, "heat")
        self.assertEqual(hvac_off.target_hvac_mode, "off")
        self.assertEqual(unsupported.target_hvac_mode, "heat")

    def test_reset_automation_semantics(self):
        self.assertEqual(reset_actions(arrived=True), ("return_home", "visit"))
        self.assertEqual(reset_actions(schedule_on=True), ("party", "visit"))
        self.assertEqual(reset_actions(arrived=True, permission_on=True), ("return_home", "visit", "party"))

    def test_summer_hysteresis_reference_thresholds(self):
        self.assertTrue(summer_hysteresis_state(outdoor_temperature=18.5, currently_active=False))
        self.assertTrue(summer_hysteresis_state(outdoor_temperature=17.1, currently_active=True))
        self.assertFalse(summer_hysteresis_state(outdoor_temperature=17.0, currently_active=True))
        self.assertTrue(summer_hysteresis_state(outdoor_temperature=None, currently_active=True))

    def test_chimney_sweep_is_absolute_at_extreme_conditions(self):
        decision = evaluate_decision(
            schedule_active=False,
            overrides={
                "chimney_sweep": True,
                "heating_permission": False,
                "summer": True,
                "window_open": True,
                "away": True,
                "party": True,
                "visit": True,
                "return_home": True,
            },
            comfort_temperature=22,
            night_temperature=17,
            chimney_temperature=28,
        )
        self.assertEqual(decision.mode, "chimney_sweep")
        self.assertEqual(decision.target_hvac_mode, "heat")
        self.assertEqual(decision.target_temperature, 28)

    def test_chimney_sweep_ignores_extreme_outdoor_temperature_in_status(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            overrides={"chimney_sweep": True, "heating_permission": False, "summer": True},
            context={"outdoor_temperature": 40.0, "summer_mode": "hvac_off", "chimney_temperature": 28.0},
        )
        self.assertEqual(result["mode"], "chimney_sweep")
        self.assertEqual(result["target_hvac_mode"], "heat")

    def test_shadow_status_reports_mode_effect_and_missing_migration_prerequisites(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(
            schedule,
            now=datetime.fromisoformat("2026-11-02T22:00:00+01:00"),
            timezone="Europe/Berlin",
            context={
                "zone_id": "living",
                "comfort_temperature": 22,
                "night_temperature": 17,
                "thermostats": [{"entity_id": "climate.living", "state": "heat", "available": True}],
                "room_temperature": 19,
                "special_modes": [{"id": "party", "mode_type": "party", "available": True, "active": True}],
                "presence": {"status": "home"},
                "heating_sources": {},
            },
        )
        self.assertEqual(result["mode"], "party")
        self.assertEqual(result["target_temperature"], 22.0)
        self.assertTrue(result["shadow"]["schedule_decision"]["active"] is False)
        self.assertIn("actor_path", result["shadow"]["missing_prerequisites"])
        self.assertIn("scheduler_or_schedule_source", result["shadow"]["missing_prerequisites"])
        self.assertEqual(result["shadow"]["commands"], [])
        self.assertEqual(result["room_demand"]["commands"], [])
