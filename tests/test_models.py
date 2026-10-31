import unittest
from datetime import datetime
import sys
import types
from pathlib import Path

_package = types.ModuleType("custom_components.smart_heating")
_package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", _package)

from custom_components.smart_heating.engine import calculate_status
from custom_components.smart_heating.models import ScheduleValidationError, WeeklySchedule


class ScheduleTests(unittest.TestCase):
    def test_all_weekdays_and_multiple_windows(self):
        schedule = WeeklySchedule.from_mapping({day: [{"start": "06:00", "end": "08:00"}, {"start": "17:00", "end": "22:00"}] for day in ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")})
        self.assertEqual(len(schedule.windows["sunday"]), 2)
        self.assertTrue(schedule.active_at(datetime.fromisoformat("2026-11-02T07:00:00+01:00"), "Europe/Berlin"))

    def test_overlap_rejected(self):
        with self.assertRaises(ScheduleValidationError):
            WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "08:00"}, {"start": "07:00", "end": "09:00"}]})

    def test_invalid_and_midnight_window_rejected(self):
        with self.assertRaises(ScheduleValidationError):
            WeeklySchedule.from_mapping({"monday": [{"start": "22:00", "end": "05:00"}]})

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
