import unittest
from pathlib import Path


class FrontendContractTests(unittest.TestCase):
    def test_card_registers_custom_element_and_picker_entry(self):
        source = Path("custom_components/smart_heating/frontend/smart-heating-card.js").read_text()
        self.assertIn('customElements.define("smart-heating-card"', source)
        self.assertIn('card.type === "smart-heating-card"', source)
        self.assertIn('type: "smart-heating-card"', source)
        self.assertIn('smart_heating/plan/get', source)
        self.assertIn('smart_heating/plan/set', source)

