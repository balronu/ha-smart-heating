import unittest
import json
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    def test_local_version_sources_match_manifest(self):
        manifest = json.loads(Path("custom_components/smart_heating/manifest.json").read_text())
        version = manifest["version"]
        const_source = Path("custom_components/smart_heating/const.py").read_text()
        backend_source = Path("custom_components/smart_heating/frontend/backend-panel.js").read_text()
        card_source = Path("custom_components/smart_heating/frontend/smart-heating-card.js").read_text()
        self.assertIn(f'VERSION = "{version}"', const_source)
        self.assertIn(f'const VERSION = "{version}"', backend_source)
        self.assertIn(f'SMART_HEATING_CARD_VERSION = "{version}"', card_source)

    def test_card_registers_custom_element_and_picker_entry(self):
        source = Path("custom_components/smart_heating/frontend/smart-heating-card.js").read_text()
        self.assertIn('customElements.define("smart-heating-card"', source)
        self.assertRegex(source, r'(?:card|c)\.type\s*===\s*["\']smart-heating-card["\']')
        self.assertIn('type:"smart-heating-card"', source)
        self.assertIn('smart_heating/plan/get', source)
        self.assertNotIn('smart_heating/plan/set', source)
        self.assertIn('static getConfigElement()', source)
        self.assertIn('static getStubConfig()', source)
        self.assertIn('smart-heating-card-editor', source)
        self.assertIn('actual_mode', source)
        self.assertIn('SMART_HEATING_CARD_VERSION = "0.1.0-beta.39"', source)
        self.assertIn("this._data?.version||SMART_HEATING_CARD_VERSION", source)
        self.assertNotIn("Beta 9", source)
        self.assertIn("target_temperature", source)
        self.assertIn("operation_mode", source)
        self.assertIn("window_status", source)
        self.assertIn("comparison_not_possible", source)
        self.assertIn("SMART bleibt gesperrt", source)
        self.assertIn("unbekannt", source)
        self.assertNotIn("backend-menu", source)
        self.assertNotIn("smart_heating/admin/zone/set", source)
        self.assertNotIn("smart_heating/admin/person/set", source)
