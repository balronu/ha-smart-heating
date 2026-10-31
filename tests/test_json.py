import json
import unittest
from pathlib import Path


ROOT = Path(__file__).parents[1]


class JsonTests(unittest.TestCase):
    def test_json_files_parse(self):
        for path in [ROOT / "hacs.json", ROOT / "custom_components/smart_heating/manifest.json", ROOT / "custom_components/smart_heating/strings.json", ROOT / "custom_components/smart_heating/translations/de.json", ROOT / "custom_components/smart_heating/translations/en.json"]:
            with self.subTest(path=path):
                json.loads(path.read_text())

