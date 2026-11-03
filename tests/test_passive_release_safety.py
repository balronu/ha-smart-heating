"""Release guard: Smart Heating must never actuate external heating services."""
import ast
from pathlib import Path
import unittest


COMPONENT = Path(__file__).parents[1] / "custom_components" / "smart_heating"
FORBIDDEN = {
    "services.async_call",
    "services.call",
    "async_set_temperature",
    "async_set_hvac_mode",
    "async_set_preset_mode",
    "async_turn_on",
    "async_turn_off",
    "async_call_service",
}
# The switch entity is intentionally writable, but only to Smart Heating's
# internal config-entry options. It must not be treated as climate actuation.
INTERNAL_SWITCH = COMPONENT / "switch.py"


def attribute_path(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = attribute_path(node.value)
        return f"{prefix}.{node.attr}" if prefix else node.attr
    return ""


class PassiveReleaseSafetyTests(unittest.TestCase):
    def test_no_external_heating_actuation_in_python_sources(self):
        for path in sorted(COMPONENT.glob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = attribute_path(node.func)
                if path == INTERNAL_SWITCH and name in {
                    "async_turn_on", "async_turn_off"
                }:
                    continue
                with self.subTest(file=path.name, call=name, line=node.lineno):
                    self.assertFalse(
                        any(name == banned or name.endswith("." + banned)
                            for banned in FORBIDDEN),
                        f"External service/actuator call forbidden: {path.name}:{node.lineno} {name}",
                    )

    def test_internal_switch_writes_only_internal_state(self):
        source = INTERNAL_SWITCH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(INTERNAL_SWITCH))
        methods = {
            node.name: node
            for cls in tree.body if isinstance(cls, ast.ClassDef)
            for node in cls.body if isinstance(node, ast.AsyncFunctionDef)
        }
        for method_name in ("async_turn_on", "async_turn_off"):
            with self.subTest(method=method_name):
                self.assertIn(method_name, methods)
                calls = {
                    attribute_path(node.func)
                    for node in ast.walk(methods[method_name])
                    if isinstance(node, ast.Call)
                }
                self.assertIn("async_update_internal", calls)
                self.assertFalse(any("services." in call for call in calls))


if __name__ == "__main__":
    unittest.main()
