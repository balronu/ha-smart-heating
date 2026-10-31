import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    def test_card_registers_custom_element_and_picker_entry(self):
        source = Path("custom_components/smart_heating/frontend/smart-heating-card.js").read_text()
        self.assertIn('customElements.define("smart-heating-card"', source)
        self.assertRegex(source, r'(?:card|c)\.type\s*===\s*["\']smart-heating-card["\']')
        self.assertIn('type: "smart-heating-card"', source)
        self.assertIn('smart_heating/plan/get', source)
        self.assertIn('smart_heating/plan/set', source)
        self.assertIn('static getConfigElement()', source)
        self.assertIn('static getStubConfig()', source)
        self.assertIn('smart-heating-card-editor', source)
        self.assertIn('actual_mode', source)
        self.assertIn('SMART_HEATING_CARD_VERSION = "0.1.0-beta.13"', source)
        self.assertIn("this._data?.version || SMART_HEATING_CARD_VERSION", source)
        self.assertNotIn("Beta 9", source)
        self.assertIn("target_temperature", source)
        self.assertIn("control_state", source)
        self.assertIn("operation_mode", source)
        self.assertIn("heat_demand_status", source)
        self.assertIn("window_status", source)
        self.assertIn("unbekannt", source)
        self.assertNotIn("backend-menu", source)
        self.assertNotIn("smart_heating/admin/zone/set", source)
        self.assertNotIn("smart_heating/admin/person/set", source)
