import sys
import types
import unittest
from unittest.mock import patch
from pathlib import Path

package = types.ModuleType("custom_components.smart_heating")
package.__path__ = [str(Path(__file__).parents[1] / "custom_components" / "smart_heating")]
sys.modules.setdefault("custom_components.smart_heating", package)

from custom_components.smart_heating.management import (  # noqa: E402
    default_management,
    normalize_management,
    discover_controller_entities,
    discover_temperature_entities,
    discover_helper_entities,
    area_suggestions,
    is_eligible_window_entity,
    person_presence,
    upsert_item,
    validate_management,
    window_contact_summary,
)
from custom_components.smart_heating.models import evaluate_decision  # noqa: E402
from custom_components.smart_heating.storage import load_schedule  # noqa: E402


class State:
    def __init__(self, state, attributes=None, entity_id=None):
        self.state = state
        self.attributes = attributes or {}
        self.entity_id = entity_id or "sensor.test"


class States:
    def __init__(self, values):
        self.values = values

    def get(self, entity_id):
        return self.values.get(entity_id)

    def async_all(self, domain):
        return [state for entity_id, state in self.values.items() if entity_id.startswith(f"{domain}.")]


class Hass:
    def __init__(self, values):
        self.states = States(values)


class ManagementTests(unittest.TestCase):
    def test_native_persons_aggregate_home_and_unknown(self):
        data = default_management()
        upsert_item(data, "persons", {"id": "a", "name": "A", "presence_entities": ["person.a"]})
        upsert_item(data, "persons", {"id": "b", "name": "B", "presence_entities": ["person.b"]})
        self.assertEqual(person_presence(Hass({"person.a": State("home"), "person.b": State("unknown")}), data["persons"])["status"], "home")
        self.assertTrue(person_presence(Hass({"person.a": State("not_home"), "person.b": State("unknown")}), data["persons"])["unknown"])

    def test_no_persons_disables_presence(self):
        result = person_presence(Hass({}), [])
        self.assertEqual(result["status"], "disabled")
        self.assertFalse(result["away"])

    def test_trackers_are_not_accepted_as_person_assignments(self):
        data = default_management()
        person = upsert_item(data, "persons", {"name": "A", "presence_entities": ["device_tracker.a"]})
        self.assertEqual(person["presence_entities"], [])

    def test_active_thermostat_cannot_have_two_zone_owners(self):
        data = default_management()
        upsert_item(data, "zones", {"id": "one", "name": "One", "thermostat_entities": ["climate.one"]})
        with self.assertRaises(ValueError):
            upsert_item(data, "zones", {"id": "two", "name": "Two", "thermostat_entities": ["climate.one"]})

    def test_sensors_can_be_shared_but_unknown_zone_is_rejected(self):
        data = default_management()
        upsert_item(data, "zones", {"id": "one", "name": "One"})
        upsert_item(data, "sensors", {"type": "window", "entity_id": "binary_sensor.window", "zone_ids": ["one"]})
        self.assertFalse(validate_management(data))
        self.assertTrue(validate_management({**data, "zones": []}))

    def test_internal_modes_and_zone_schedule_work_without_helpers(self):
        data = default_management()
        upsert_item(data, "zones", {"id": "zone", "name": "Zone", "schedule": {"monday": [{"start": "05:00", "end": "06:00"}]}})
        data["internal"]["operating_mode"] = "manual_heat"
        self.assertEqual(evaluate_decision(schedule_active=False, overrides={"manual_heat": True}, comfort_temperature=21).mode, "manual_heat")
        self.assertTrue(load_schedule({"schedule": {}, "management": data}).windows["monday"])

    def test_only_binary_opening_sensors_are_eligible(self):
        self.assertTrue(is_eligible_window_entity("binary_sensor.fenster_wohnzimmer", "window"))
        self.assertTrue(is_eligible_window_entity("binary_sensor.tuer", "door"))
        self.assertFalse(is_eligible_window_entity("sensor.fenster_wohnzimmer_battery", "window"))
        self.assertFalse(is_eligible_window_entity("binary_sensor.fenster_temperatur", "temperature"))

    def test_temperature_discovery_requires_device_class_and_c_or_f_unit(self):
        hass = Hass({
            "sensor.outside": State("unknown", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Außen"}, "sensor.outside"),
            "sensor.battery": State("85", {"device_class": "battery", "unit_of_measurement": "%"}, "sensor.battery"),
            "sensor.humidity": State("50", {"device_class": "humidity", "unit_of_measurement": "%"}, "sensor.humidity"),
            "sensor.voltage": State("12", {"device_class": "voltage", "unit_of_measurement": "V"}, "sensor.voltage"),
        })
        result = discover_temperature_entities(hass)
        self.assertEqual([item["entity_id"] for item in result], ["sensor.outside"])
        self.assertEqual(result[0]["state"], "unknown")

    def test_temperature_discovery_separates_technical_sources(self):
        hass = Hass({
            "sensor.wohnzimmer_temperature": State("21", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Wohnzimmer"}, "sensor.wohnzimmer_temperature"),
            "sensor.pve_disk_temperature": State("40", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "PVE Disk"}, "sensor.pve_disk_temperature"),
            "sensor.esszimmer_taupunkt": State("12", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Esszimmer Taupunkt"}, "sensor.esszimmer_taupunkt"),
        })
        result = {item["entity_id"]: item for item in discover_temperature_entities(hass)}
        self.assertEqual(result["sensor.wohnzimmer_temperature"]["temperature_role"], "room")
        self.assertEqual(result["sensor.pve_disk_temperature"]["temperature_role"], "technical")
        self.assertEqual(result["sensor.esszimmer_taupunkt"]["temperature_role"], "technical")

    def test_outdoor_temperature_sources_are_prioritized_and_classified(self):
        hass = Hass({
            "sensor.gw1100a_v2_2_3_outdoor_temperature": State("12", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Außentemperatur"}, "sensor.gw1100a_v2_2_3_outdoor_temperature"),
            "sensor.wohnzimmer_temperature": State("21", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Wohnzimmer"}, "sensor.wohnzimmer_temperature"),
        })
        result = discover_temperature_entities(hass)
        self.assertEqual(result[0]["entity_id"], "sensor.gw1100a_v2_2_3_outdoor_temperature")
        self.assertEqual(result[0]["temperature_role"], "outdoor")
        self.assertIn("Außentemperatur", result[0]["classification_reason"])

    def test_outdoor_and_contact_temperature_sources_are_not_primary_room_sources(self):
        hass = Hass({
            "sensor.außen_temperature": State("12", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Außen Temperatur"}, "sensor.außen_temperature"),
            "sensor.fenster_temperature": State("20", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Fenster Temperatur"}, "sensor.fenster_temperature"),
            "sensor.badezimmer_temperature": State("21", {"device_class": "temperature", "unit_of_measurement": "°C", "friendly_name": "Badezimmer Temperatur"}, "sensor.badezimmer_temperature"),
        })
        result = discover_temperature_entities(hass)
        roles = {item["entity_id"]: item["temperature_role"] for item in result}
        self.assertEqual(roles["sensor.badezimmer_temperature"], "room")
        self.assertEqual(roles["sensor.fenster_temperature"], "contact")
        self.assertEqual(roles["sensor.außen_temperature"], "outdoor")
        self.assertEqual([item["entity_id"] for item in result], ["sensor.außen_temperature", "sensor.badezimmer_temperature", "sensor.fenster_temperature"])

    def test_explicit_area_relevance_is_internal_and_persistent(self):
        data = normalize_management({"relevant_area_ids": ["wohnzimmer"], "zones": [], "sensors": {}})
        self.assertEqual(data["relevant_area_ids"], ["wohnzimmer"])
        self.assertEqual(data["zones"], [])

    def test_area_names_are_neutral_and_local_climate_is_the_only_device_hint(self):
        class Area:
            def __init__(self, area_id, name):
                self.id, self.name = area_id, name
        class RegistryItem:
            def __init__(self, entity_id, area_id):
                self.entity_id, self.area_id = entity_id, area_id
        hass = Hass({"climate.wohnzimmer": State("heat", {"friendly_name": "Wohnzimmer Heizung"}, "climate.wohnzimmer")})
        with patch("custom_components.smart_heating.management.discover_areas", return_value=[{"area_id": "wohnmobil", "name": "Wohnmobil", "entity_ids": []}, {"area_id": "wohnzimmer", "name": "Wohnzimmer", "entity_ids": ["climate.wohnzimmer"]}]):
            result = area_suggestions(hass, default_management())
        by_id = {item["area_id"]: item for item in result}
        self.assertFalse(by_id["wohnmobil"]["relevant"])
        self.assertEqual(by_id["wohnmobil"]["relevance_source"], "unassigned")
        self.assertTrue(by_id["wohnzimmer"]["relevant"])
        self.assertEqual(by_id["wohnzimmer"]["relevance_source"], "local_heating_device")

    def test_helper_discovery_is_read_only_and_selectable(self):
        hass = Hass({"input_boolean.party": State("off", {"friendly_name": "Party"}, "input_boolean.party"), "input_number.not_a_mode": State("20", {"friendly_name": "Temperatur"}, "input_number.not_a_mode")})
        helpers = discover_helper_entities(hass)
        self.assertEqual(helpers[0]["entity_id"], "input_boolean.party")
        self.assertTrue(helpers[0]["passive"])
        self.assertEqual(helpers[0]["suggested_for"], ["party"])
        self.assertFalse(any(item["entity_id"] == "input_number.not_a_mode" for item in helpers))

    def test_helper_discovery_separates_availability_and_activity(self):
        hass = Hass({
            "input_boolean.sommermodus": State("on", {"friendly_name": "Sommermodus"}, "input_boolean.sommermodus"),
            "input_boolean.besuch": State("unavailable", {"friendly_name": "Besuch"}, "input_boolean.besuch"),
        })
        helpers = {item["entity_id"]: item for item in discover_helper_entities(hass)}
        self.assertTrue(helpers["input_boolean.sommermodus"]["available"])
        self.assertTrue(helpers["input_boolean.sommermodus"]["active"])
        self.assertFalse(helpers["input_boolean.besuch"]["available"])
        self.assertFalse(helpers["input_boolean.besuch"]["active"])

    def test_exact_special_mode_helpers_are_preferred_without_activation(self):
        hass = Hass({
            "input_boolean.party": State("off", {"friendly_name": "Party"}, "input_boolean.party"),
            "input_boolean.besuch": State("off", {"friendly_name": "Besuch"}, "input_boolean.besuch"),
            "input_boolean.heimweg": State("off", {"friendly_name": "Heimweg"}, "input_boolean.heimweg"),
            "input_boolean.heizung_sommermodus": State("off", {"friendly_name": "Heizung Sommermodus"}, "input_boolean.heizung_sommermodus"),
            "input_boolean.schornsteinfeger": State("off", {"friendly_name": "Schornsteinfeger"}, "input_boolean.schornsteinfeger"),
            "input_boolean.fremdmodus": State("off", {"friendly_name": "Fremdmodus"}, "input_boolean.fremdmodus"),
        })
        helpers = {item["entity_id"]: item for item in discover_helper_entities(hass)}
        self.assertEqual(helpers["input_boolean.party"]["preferred_for"], ["party"])
        self.assertEqual(helpers["input_boolean.besuch"]["preferred_for"], ["visit"])
        self.assertEqual(helpers["input_boolean.heimweg"]["preferred_for"], ["return_home"])
        self.assertEqual(helpers["input_boolean.heizung_sommermodus"]["preferred_for"], ["summer"])
        self.assertEqual(helpers["input_boolean.schornsteinfeger"]["preferred_for"], ["chimney_sweep"])
        self.assertEqual(helpers["input_boolean.fremdmodus"]["preferred_for"], [])
        self.assertTrue(all(item["state"] == "off" for item in helpers.values()))

    def test_controller_discovery_is_observable_and_includes_input_boolean(self):
        hass = Hass({
            "input_boolean.heizung": State("off", {"friendly_name": "Heizung"}, "input_boolean.heizung"),
            "climate.esszimmer": State("heat", {"friendly_name": "Esszimmer"}, "climate.esszimmer"),
        })
        result = discover_controller_entities(hass)
        self.assertEqual({item["entity_id"] for item in result}, {"input_boolean.heizung", "climate.esszimmer"})
        self.assertTrue(all(item["passive"] for item in result))

    def test_many_contacts_keep_room_and_review_metadata_without_deletion(self):
        data = default_management()
        upsert_item(data, "sensors", {"id": "old", "type": "window", "entity_id": "sensor.fenster_battery", "area_id": "wohnzimmer"})
        contacts = [
            {"entity_id": "binary_sensor.fenster_a", "name": "Fenster A", "area_id": "wohnzimmer", "area_name": "Wohnzimmer", "status": "closed", "available": True, "configured": False, "review_flags": [], "review_required": False},
            {"entity_id": "binary_sensor.fenster_b", "name": "Fenster B", "area_id": "wohnzimmer", "area_name": "Wohnzimmer", "status": "open", "available": True, "configured": False, "review_flags": [], "review_required": False},
        ]
        with patch("custom_components.smart_heating.management.discover_window_contacts", return_value=contacts):
            result = window_contact_summary(Hass({}), data)
        self.assertEqual(result["total"], 3)
        preserved = next(item for item in result["contacts"] if item["entity_id"] == "sensor.fenster_battery")
        self.assertIn("configured_but_not_eligible", preserved["review_flags"])
        self.assertEqual(result["groups"][0]["area_name"], "Wohnzimmer")

    def test_ignored_contacts_are_separated_and_restorable(self):
        data = default_management()
        upsert_item(data, "sensors", {"id": "ignored", "type": "window", "entity_id": "binary_sensor.fenster_a", "ignored": True})
        contacts = [{"entity_id": "binary_sensor.fenster_a", "name": "Fenster A", "area_id": "wohnzimmer", "area_name": "Wohnzimmer", "status": "open", "available": True, "configured": True, "review_flags": [], "review_required": False}]
        with patch("custom_components.smart_heating.management.discover_window_contacts", return_value=contacts):
            result = window_contact_summary(Hass({}), data)
        self.assertEqual(result["contacts"], [])
        self.assertEqual(result["ignored"], 1)
        self.assertEqual(result["ignored_contacts"][0]["entity_id"], "binary_sensor.fenster_a")
        upsert_item(data, "sensors", {"id": "ignored", "type": "window", "entity_id": "binary_sensor.fenster_a", "ignored": False})
        with patch("custom_components.smart_heating.management.discover_window_contacts", return_value=contacts):
            restored = window_contact_summary(Hass({}), data)
        self.assertEqual(restored["ignored"], 0)
        self.assertEqual(restored["contacts"][0]["entity_id"], "binary_sensor.fenster_a")

    def test_saved_window_assignment_counts_in_target_room_not_ha_room(self):
        data = default_management()
        upsert_item(data, "sensors", {"id": "bathroom-contact", "type": "window", "entity_id": "binary_sensor.badezimmer_fenster", "area_id": "badezimmer", "area_name": "Badezimmer"})
        contacts = [{"entity_id": "binary_sensor.badezimmer_fenster", "name": "Badezimmer Fenster", "area_id": "esszimmer", "area_name": "Esszimmer", "status": "closed", "available": True, "configured": True, "review_flags": [], "review_required": False}]
        with patch("custom_components.smart_heating.management.discover_areas", return_value=[
            {"area_id": "badezimmer", "name": "Badezimmer", "entity_ids": []},
            {"area_id": "esszimmer", "name": "Esszimmer", "entity_ids": []},
        ]), patch("custom_components.smart_heating.management.discover_window_contacts", return_value=contacts):
            result = area_suggestions(Hass({}), data)
        by_id = {item["area_id"]: item for item in result}
        self.assertEqual(by_id["badezimmer"]["window_contact_count"], 1)
        self.assertEqual(by_id["esszimmer"]["window_contact_count"], 0)
        self.assertEqual(by_id["badezimmer"]["window_contacts"][0]["assigned_area_id"], "badezimmer")
        self.assertEqual(by_id["badezimmer"]["window_contacts"][0]["ha_area_id"], "esszimmer")

    def test_same_contact_cannot_be_assigned_twice(self):
        data = default_management()
        upsert_item(data, "sensors", {"id": "one", "type": "window", "entity_id": "binary_sensor.fenster", "area_id": "wohnzimmer"})
        with self.assertRaisesRegex(ValueError, "duplicate_sensor_entity"):
            upsert_item(data, "sensors", {"id": "two", "type": "tilt", "entity_id": "binary_sensor.fenster", "area_id": "bad"})
