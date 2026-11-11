"""Static guard against accidentally exposing Smart Heating configuration mutations."""
import ast
from pathlib import Path
import unittest


SOURCE = Path(__file__).parents[1] / "custom_components" / "smart_heating" / "__init__.py"
MUTATIONS = {
    "_ws_set_schedule",
    "_ws_admin_person_set", "_ws_admin_person_delete",
    "_ws_admin_zone_set", "_ws_admin_room_save", "_ws_admin_room_delete", "_ws_admin_zone_delete",
    "_ws_admin_area_relevance_set",
    "_ws_admin_sensor_set", "_ws_admin_sensor_delete",
    "_ws_admin_controller_set", "_ws_admin_outdoor_set",
    "_ws_admin_safety_set", "_ws_admin_internal_set",
    "_ws_admin_system_set",
    "_ws_admin_special_mode_set", "_ws_admin_special_mode_delete",
    "_ws_admin_special_mode_duplicate",
}


ADMIN_READS = {"_ws_admin_get"}
READ_ONLY = {
    "_ws_cleanup_preview", "_ws_get_status", "_ws_simulate",
    "_ws_migration_preview", "_ws_admin_validate",
}


class WebSocketPermissionTests(unittest.TestCase):
    def test_websocket_permission_inventory_is_complete(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        handlers = {
            node.name: node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("_ws_")
        }
        self.assertEqual(set(handlers), MUTATIONS | ADMIN_READS | READ_ONLY)
        for name in sorted(MUTATIONS | ADMIN_READS):
            with self.subTest(handler=name):
                decorators = {ast.unparse(d) for d in handlers[name].decorator_list}
                self.assertIn("websocket_api.require_admin", decorators)

    def test_full_administrative_read_requires_admin(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        handler = next(
            node for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "_ws_admin_get"
        )
        self.assertIn(
            "websocket_api.require_admin",
            {ast.unparse(d) for d in handler.decorator_list},
        )

    def test_every_configuration_mutation_requires_admin(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        handlers = {
            node.name: node
            for node in tree.body
            if isinstance(node, ast.AsyncFunctionDef) and node.name.startswith("_ws_")
        }
        self.assertTrue(MUTATIONS <= handlers.keys())
        for name in sorted(MUTATIONS):
            with self.subTest(handler=name):
                decorators = {
                    ast.unparse(decorator)
                    for decorator in handlers[name].decorator_list
                }
                self.assertIn("websocket_api.require_admin", decorators)
                self.assertIn("websocket_api.async_response", decorators)

    def test_schedule_write_cannot_be_accidentally_downgraded(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        schedule = next(node for node in tree.body
                        if isinstance(node, ast.AsyncFunctionDef)
                        and node.name == "_ws_set_schedule")
        self.assertIn("websocket_api.require_admin",
                      [ast.unparse(d) for d in schedule.decorator_list])


if __name__ == "__main__":
    unittest.main()
