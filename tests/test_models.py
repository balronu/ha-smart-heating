import unittest
from datetime import datetime
import sys
import types
from pathlib import Path

_package = types.ModuleType("custom_components.smart_heating")
_package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", _package)

from custom_components.smart_heating.engine import calculate_status, calculate_zone_target_previews, summarize_zone_heat_demand, zone_demand_signature, next_zone_demand_history, reusable_zone_demand
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

    def test_shadow_contains_passive_actor_plan_without_execution(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(
            schedule,
            now=datetime.fromisoformat("2026-11-02T07:00:00+01:00"),
            timezone="Europe/Berlin",
            context={
                "zone_id": "esszimmer",
                "comfort_temperature": 22,
                "night_temperature": 17,
                "heating_sources": {
                    "primary_climate_entity": "climate.esszimmer",
                    "fallback_climate_entity": "climate.tado",
                },
                "actor_states": {
                    "climate.esszimmer": {
                        "state": "heat",
                        "hvac_mode": "heat",
                        "temperature": 20,
                        "available": True,
                    },
                    "climate.tado": {
                        "state": "heat",
                        "hvac_mode": "heat",
                        "temperature": 20,
                        "available": True,
                    },
                },
                "actor_service_evidence": {
                    "climate.set_hvac_mode": True,
                    "climate.set_temperature": True,
                },
                "schedule_source_verified": True,
            },
        )
        plan = result["shadow"]["planned_actor_actions"]
        self.assertEqual(plan["selected_entity"], "climate.esszimmer")
        self.assertEqual([item["service"] for item in plan["planned_commands"]], ["climate.set_temperature"])
        self.assertEqual(plan["executed_commands"], [])
        self.assertTrue(plan["passive"])

    def test_shadow_comparison_does_not_claim_parity_without_proven_legacy_trace(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "20:00"}]})
        result = calculate_status(
            schedule,
            now=datetime.fromisoformat("2026-11-02T07:00:00+01:00"),
            timezone="Europe/Berlin",
            context={
                "zone_id": "esszimmer",
                "comfort_temperature": 22,
                "night_temperature": 17,
                "heating_sources": {"primary_climate_entity": "climate.esszimmer"},
                "actor_states": {"climate.esszimmer": {"state": "heat", "temperature": 22, "available": True}},
                "schedule_source_verified": True,
            },
        )
        comparison = result["shadow"]["comparison"]
        self.assertEqual(comparison["comparison"], "comparison_not_possible")
        self.assertFalse(comparison["legacy_proven"])
        self.assertFalse(comparison["smart_takeover_allowed"])

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

    def test_summer_room_demand_override_matches_uploaded_automation(self):
        for schedule_active in (True, False):
            decision = evaluate_decision(schedule_active=schedule_active, overrides={"summer": True, "need_heat_now": True}, comfort_temperature=22, night_temperature=17)
            self.assertEqual(decision.mode, "comfort" if schedule_active else "night")
        self.assertEqual(evaluate_decision(schedule_active=True, overrides={"summer": True, "need_heat_now": False}, comfort_temperature=22, night_temperature=17).mode, "summer")

    def test_status_derives_summer_override_from_room_temperature(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "05:30", "end": "21:00"}]})
        base = {
            "now": datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            "timezone": "Europe/Berlin",
            "overrides": {"summer": True},
        }
        for room_temp, expected in ((21.59, "comfort"), (21.6, "summer"), (22.0, "summer")):
            with self.subTest(room_temp=room_temp):
                status = calculate_status(
                    schedule, **base,
                    context={"room_temperature": room_temp, "comfort_temperature": 22.0, "night_temperature": 17.0},
                )
                self.assertEqual(status["actual_mode"], expected)
                self.assertFalse(status["control_enabled"])
                self.assertEqual(status["shadow"]["commands"], [])

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

    def test_manual_mode_cannot_bypass_open_window(self):
        decision = evaluate_decision(
            schedule_active=True,
            overrides={"manual_heat": True, "window_open": True},
            comfort_temperature=24,
            night_temperature=18,
            frost_temperature=5,
        )
        self.assertEqual(decision.mode, "window_open")
        self.assertEqual(decision.target_temperature, 5)

    def test_manual_mode_cannot_bypass_unknown_window(self):
        decision = evaluate_decision(
            schedule_active=True,
            overrides={"manual_heat": True, "window_unknown": True},
            comfort_temperature=24,
        )
        self.assertEqual(decision.mode, "window_unknown")
        self.assertIsNone(decision.target_hvac_mode)

    def test_chimney_sweep_remains_highest_priority(self):
        decision = evaluate_decision(
            schedule_active=False,
            overrides={"chimney_sweep": True, "window_open": True, "manual_setback": True},
            chimney_temperature=27,
        )
        self.assertEqual(decision.mode, "chimney_sweep")
        self.assertEqual(decision.target_temperature, 27)

    def test_heating_permission_blocks_manual_heat(self):
        decision = evaluate_decision(
            schedule_active=True,
            overrides={"heating_permission": False, "manual_heat": True},
            comfort_temperature=24,
        )
        self.assertEqual(decision.mode, "disabled")
        self.assertEqual(decision.target_hvac_mode, "off")

    def test_chimney_sweep_overrides_disabled_permission(self):
        decision = evaluate_decision(
            schedule_active=True,
            overrides={"heating_permission": False, "chimney_sweep": True},
            chimney_temperature=26,
        )
        self.assertEqual(decision.mode, "chimney_sweep")

    def test_overnight_window_does_not_start_before_its_day(self):
        schedule = WeeklySchedule.from_mapping({
            "monday": [{"start": "22:00", "end": "02:00", "target_temperature": 23}],
        })
        timezone = "Europe/Berlin"
        monday_early = datetime.fromisoformat("2026-11-02T01:00:00+01:00")
        monday_late = datetime.fromisoformat("2026-11-02T23:00:00+01:00")
        tuesday_early = datetime.fromisoformat("2026-11-03T01:00:00+01:00")
        tuesday_late = datetime.fromisoformat("2026-11-03T03:00:00+01:00")
        self.assertFalse(schedule.active_at(monday_early, timezone))
        self.assertIsNone(schedule.active_window_at(monday_early, timezone))
        for instant in (monday_late, tuesday_early):
            self.assertTrue(schedule.active_at(instant, timezone))
            self.assertEqual(schedule.active_window_at(instant, timezone).target_temperature, 23)
        self.assertFalse(schedule.active_at(tuesday_late, timezone))
        self.assertIsNone(schedule.active_window_at(tuesday_late, timezone))


    def test_isolated_multi_zone_targets_remain_independent_and_passive(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        result = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom", "name": "Bad"}, {"id": "bedroom", "name": "Schlafzimmer"}],
            zone_diagnostics=[{"zone_id": "bathroom", "window_state": "closed"}, {"zone_id": "bedroom", "window_state": "closed"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18,
                      "zones": {"bathroom": {"comfort_temperature": 24}, "bedroom": {"comfort_temperature": 18}}},
            overrides={"heating_permission": True},
        )
        self.assertEqual([zone["target_temperature"] for zone in result], [24, 18])
        self.assertTrue(all(zone["passive"] and zone["commands"] == [] for zone in result))

    def test_multi_zone_preview_is_hidden_in_legacy_mode(self):
        result = calculate_zone_target_previews(
            WeeklySchedule.from_mapping({}),
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}],
            internal={"internal_only": False},
        )
        self.assertEqual(result, [])


    def test_zone_open_window_does_not_disable_other_room(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        previews = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}, {"id": "bedroom"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
            zone_diagnostics=[{"zone_id": "bathroom", "window_state": "open"}, {"zone_id": "bedroom", "window_state": "closed"}],
            overrides={"window_open": True},
        )
        self.assertNotEqual(previews[0]["mode"], "comfort")
        self.assertEqual(previews[1]["mode"], "comfort")
        self.assertEqual(previews[1]["target_temperature"], 21)
        self.assertTrue(all(not item["commands"] for item in previews))


    def test_zone_heat_demand_uses_own_measurement_and_unknown_is_not_false(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        previews = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}, {"id": "bedroom"}, {"id": "unknown"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18,
                      "zones": {"bathroom": {"comfort_temperature": 24}, "bedroom": {"comfort_temperature": 18}}},
            zone_diagnostics=[
                {"zone_id": "bathroom", "window_state": "closed", "room_temperature": 22, "temperature_source": "sensor.bathroom"},
                {"zone_id": "bedroom", "window_state": "closed", "room_temperature": 19, "temperature_source": "sensor.bedroom"},
                {"zone_id": "unknown", "window_state": "closed", "room_temperature": None},
            ],
        )
        self.assertEqual([item["heat_demand"] for item in previews], [True, False, None])
        self.assertEqual(previews[0]["temperature_source"], "sensor.bathroom")
        self.assertTrue(all(item["commands"] == [] for item in previews))


    def test_shared_boiler_demand_is_never_authorized_by_room_preview(self):
        summary = summarize_zone_heat_demand([
            {"zone_id": "bathroom", "heat_demand": True},
            {"zone_id": "bedroom", "heat_demand": False},
            {"zone_id": "living", "heat_demand": None},
        ])
        self.assertEqual(summary["requesting_zone_ids"], ["bathroom"])
        self.assertEqual(summary["satisfied_zone_ids"], ["bedroom"])
        self.assertEqual(summary["unknown_zone_ids"], ["living"])
        self.assertTrue(summary["any_heat_demand"])
        self.assertFalse(summary["all_zones_known"])
        self.assertFalse(summary["boiler_control_authorized"])
        self.assertEqual(summary["commands"], [])

    def test_empty_room_preview_cannot_authorize_boiler(self):
        summary = summarize_zone_heat_demand([])
        self.assertFalse(summary["any_heat_demand"])
        self.assertFalse(summary["all_zones_known"])
        self.assertFalse(summary["boiler_control_authorized"])


    def test_unavailable_room_thermostats_block_positive_demand(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        previews = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "offline"}, {"id": "online"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
            zone_diagnostics=[
                {"zone_id": "offline", "window_state": "closed", "room_temperature": 19, "thermostat_count": 1, "unavailable_thermostats": 1},
                {"zone_id": "online", "window_state": "closed", "room_temperature": 19, "thermostat_count": 1, "unavailable_thermostats": 0},
            ],
        )
        self.assertIsNone(previews[0]["heat_demand"])
        self.assertTrue(previews[0]["thermostats_unavailable"])
        self.assertIs(previews[1]["heat_demand"], True)
        self.assertTrue(all(item["commands"] == [] for item in previews))


    def test_room_target_deadband_is_indeterminate_not_a_boiler_command(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        previews = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "cold"}, {"id": "near"}, {"id": "warm"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
            zone_diagnostics=[
                {"zone_id": "cold", "window_state": "closed", "room_temperature": 20.5},
                {"zone_id": "near", "window_state": "closed", "room_temperature": 20.9},
                {"zone_id": "warm", "window_state": "closed", "room_temperature": 21.5},
            ],
        )
        self.assertEqual([item["heat_demand"] for item in previews], [True, None, False])
        self.assertTrue(all(item["demand_deadband_celsius"] == 0.3 for item in previews))
        self.assertTrue(all(item["commands"] == [] for item in previews))


    def test_shadow_hysteresis_preserves_verified_prior_demand_in_deadband(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        kwargs = dict(
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}, {"id": "bedroom"}, {"id": "new"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
            zone_diagnostics=[
                {"zone_id": "bathroom", "window_state": "closed", "room_temperature": 20.9},
                {"zone_id": "bedroom", "window_state": "closed", "room_temperature": 21.1},
                {"zone_id": "new", "window_state": "closed", "room_temperature": 21.0},
            ],
        )
        previews = calculate_zone_target_previews(
            schedule, previous_demand={"bathroom": True, "bedroom": False}, **kwargs
        )
        self.assertEqual([item["heat_demand"] for item in previews], [True, False, None])
        self.assertTrue(all(item["commands"] == [] for item in previews))

    def test_shadow_hysteresis_never_overrides_unknown_window_safety(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        previews = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
            zone_diagnostics=[{"zone_id": "bathroom", "window_state": "unknown", "room_temperature": 20.9}],
            previous_demand={"bathroom": True},
        )
        self.assertIsNone(previews[0]["heat_demand"])


    def test_shadow_hysteresis_state_is_not_reused_after_missing_measurement(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        base = dict(
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
        )
        first = calculate_zone_target_previews(
            schedule, **base,
            zone_diagnostics=[{"zone_id": "bathroom", "window_state": "closed", "room_temperature": 20.5}],
        )
        self.assertIs(first[0]["heat_demand"], True)
        missing = calculate_zone_target_previews(
            schedule, **base,
            previous_demand={"bathroom": first[0]["heat_demand"]},
            zone_diagnostics=[{"zone_id": "bathroom", "window_state": "closed", "room_temperature": None}],
        )
        self.assertIsNone(missing[0]["heat_demand"])
        recovered = calculate_zone_target_previews(
            schedule, **base,
            previous_demand={},
            zone_diagnostics=[{"zone_id": "bathroom", "window_state": "closed", "room_temperature": 20.9}],
        )
        self.assertIsNone(recovered[0]["heat_demand"])


    def test_hysteresis_history_signature_changes_with_target_mode_or_sensor(self):
        original = {"target_temperature": 21.0, "mode": "comfort", "temperature_source": "sensor.room"}
        same = dict(original)
        new_target = {**original, "target_temperature": 22.0}
        new_mode = {**original, "mode": "night"}
        new_sensor = {**original, "temperature_source": "climate.room"}
        self.assertEqual(zone_demand_signature(original), zone_demand_signature(same))
        for changed in (new_target, new_mode, new_sensor):
            self.assertNotEqual(zone_demand_signature(original), zone_demand_signature(changed))


    def test_window_open_then_closed_inside_deadband_requires_new_confirmation(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        base = dict(
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}],
            internal={"internal_only": True, "comfort_temperature": 21, "night_temperature": 18},
        )
        def preview(window, temperature, prior=None):
            return calculate_zone_target_previews(
                schedule, **base, previous_demand=prior,
                zone_diagnostics=[{"zone_id": "bathroom", "window_state": window,
                                   "room_temperature": temperature}],
            )
        initial = preview("closed", 20.5)
        history, _ = next_zone_demand_history(initial)
        self.assertIs(history["bathroom"], True)
        opened = preview("open", 20.5, history)
        history, _ = next_zone_demand_history(opened)
        self.assertEqual(history, {})
        reopened = preview("closed", 20.9, history)
        self.assertIsNone(reopened[0]["heat_demand"])
        history, _ = next_zone_demand_history(reopened)
        self.assertEqual(history, {})
        confirmed = preview("closed", 20.5, history)
        self.assertIs(confirmed[0]["heat_demand"], True)
        self.assertTrue(all(not item["commands"] for batch in (initial, opened, reopened, confirmed) for item in batch))

    def test_missing_sensor_clears_verified_history_across_updates(self):
        first = [{"zone_id": "bedroom", "heat_demand": False, "target_temperature": 18,
                  "mode": "comfort", "temperature_source": "sensor.bedroom"}]
        history, _ = next_zone_demand_history(first)
        self.assertEqual(history, {"bedroom": False})
        missing = [{**first[0], "heat_demand": None, "temperature_source": None}]
        history, _ = next_zone_demand_history(missing)
        self.assertEqual(history, {})


    def test_hysteresis_history_is_filtered_when_target_or_sensor_changes(self):
        old = {"bathroom": True, "bedroom": False}
        signatures = {
            "bathroom": (24.0, "comfort", "sensor.bathroom"),
            "bedroom": (18.0, "comfort", "sensor.bedroom"),
        }
        previews = [
            {"zone_id": "bathroom", "target_temperature": 25.0,
             "mode": "comfort", "temperature_source": "sensor.bathroom"},
            {"zone_id": "bedroom", "target_temperature": 18.0,
             "mode": "comfort", "temperature_source": "sensor.bedroom"},
        ]
        self.assertEqual(reusable_zone_demand(old, signatures, previews), {"bedroom": False})
        previews[1]["temperature_source"] = "climate.bedroom"
        self.assertEqual(reusable_zone_demand(old, signatures, previews), {})


    def test_multizone_shadow_lifecycle_independent_demand_and_recovery(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        base = dict(
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}, {"id": "bedroom"}],
            internal={
                "internal_only": True, "comfort_temperature": 21,
                "night_temperature": 18,
                "zones": {
                    "bathroom": {"comfort_temperature": 24},
                    "bedroom": {"comfort_temperature": 18},
                },
            },
        )
        history, signatures = {}, {}
        def step(bath_window, bath_temp, bed_temp):
            nonlocal history, signatures
            diagnostics = [
                {"zone_id": "bathroom", "window_state": bath_window,
                 "room_temperature": bath_temp, "temperature_source": "sensor.bath"},
                {"zone_id": "bedroom", "window_state": "closed",
                 "room_temperature": bed_temp, "temperature_source": "sensor.bed"},
            ]
            first = calculate_zone_target_previews(
                schedule, **base, zone_diagnostics=diagnostics, previous_demand=history
            )
            reusable = reusable_zone_demand(history, signatures, first)
            final = calculate_zone_target_previews(
                schedule, **base, zone_diagnostics=diagnostics, previous_demand=reusable
            )
            history, signatures = next_zone_demand_history(final)
            self.assertTrue(all(item["passive"] and not item["commands"] for item in final))
            self.assertFalse(summarize_zone_heat_demand(final)["boiler_control_authorized"])
            return {item["zone_id"]: item for item in final}

        initial = step("closed", 23.5, 18.5)
        self.assertEqual((initial["bathroom"]["heat_demand"], initial["bedroom"]["heat_demand"]), (True, False))
        self.assertEqual((initial["bathroom"]["target_temperature"], initial["bedroom"]["target_temperature"]), (24.0, 18.0))
        near = step("closed", 23.9, 18.1)
        self.assertEqual((near["bathroom"]["heat_demand"], near["bedroom"]["heat_demand"]), (True, False))
        opened = step("open", 23.9, 18.1)
        self.assertIsNone(opened["bathroom"]["heat_demand"])
        self.assertIs(opened["bedroom"]["heat_demand"], False)
        self.assertNotIn("bathroom", history)
        restored = step("closed", 23.9, 18.1)
        self.assertIsNone(restored["bathroom"]["heat_demand"])
        self.assertIs(restored["bedroom"]["heat_demand"], False)
        confirmed = step("closed", 23.5, 18.1)
        self.assertIs(confirmed["bathroom"]["heat_demand"], True)
        self.assertIs(confirmed["bedroom"]["heat_demand"], False)


    def test_multizone_shadow_offline_room_does_not_block_healthy_room(self):
        schedule = WeeklySchedule.from_mapping({"monday": [{"start": "06:00", "end": "22:00"}]})
        previews = calculate_zone_target_previews(
            schedule,
            now=datetime.fromisoformat("2026-11-02T12:00:00+01:00"),
            timezone="Europe/Berlin",
            zones=[{"id": "bathroom"}, {"id": "bedroom"}],
            internal={
                "internal_only": True, "comfort_temperature": 21,
                "night_temperature": 18,
                "zones": {
                    "bathroom": {"comfort_temperature": 24},
                    "bedroom": {"comfort_temperature": 18},
                },
            },
            zone_diagnostics=[
                {"zone_id": "bathroom", "window_state": "closed",
                 "room_temperature": 23.0, "thermostat_count": 1,
                 "unavailable_thermostats": 1, "temperature_source": "sensor.bath"},
                {"zone_id": "bedroom", "window_state": "closed",
                 "room_temperature": 17.0, "thermostat_count": 1,
                 "unavailable_thermostats": 0, "temperature_source": "sensor.bed"},
            ],
            previous_demand={"bathroom": True, "bedroom": False},
        )
        summary = summarize_zone_heat_demand(previews)
        self.assertEqual([item["heat_demand"] for item in previews], [None, True])
        self.assertEqual(summary["unknown_zone_ids"], ["bathroom"])
        self.assertEqual(summary["requesting_zone_ids"], ["bedroom"])
        self.assertFalse(summary["all_zones_known"])
        self.assertFalse(summary["boiler_control_authorized"])
        self.assertTrue(all(not item["commands"] for item in previews))
