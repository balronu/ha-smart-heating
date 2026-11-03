"""Guard against stale development-release claims in public documentation."""
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).parents[1]


class BetaMetadataTests(unittest.TestCase):
    def test_manifest_version_is_reported_consistently(self):
        manifest = json.loads(
            (ROOT / "custom_components" / "smart_heating" / "manifest.json")
            .read_text(encoding="utf-8")
        )
        version = manifest["version"]
        self.assertTrue(version.startswith("0.1.0-beta."))
        for path in ("README.md", "README.en.md"):
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn(version, text)
                self.assertIn("passiv" if path == "README.md" else "passive", text.lower())

    def test_unreleased_candidate_not_claimed_as_stable(self):
        for path in ("README.md", "README.en.md"):
            with self.subTest(path=path):
                text = (ROOT / path).read_text(encoding="utf-8")
                self.assertIn("Stable – Coming Soon", text)


if __name__ == "__main__":
    unittest.main()
