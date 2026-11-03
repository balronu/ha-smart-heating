"""Separate-process Home Assistant config-entry persistence smoke test.

The two workers deliberately share only a temporary HA config directory.
They do not contact a running Home Assistant instance or actuate heating.
"""
import asyncio
from pathlib import Path
from shutil import copytree
import subprocess
import sys
import tempfile
import unittest

# Direct worker execution places tests/ rather than the repository root on sys.path.
REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPOSITORY_ROOT))

try:
    import custom_components
    from homeassistant import loader
    from pytest_homeassistant_custom_component.common import async_test_home_assistant
except ImportError:
    async_test_home_assistant = None


async def worker(stage, config_dir):
    config_path = Path(config_dir)
    if stage == "write":
        copytree(Path("custom_components/smart_heating"), config_path / "custom_components" / "smart_heating")
    custom_components.__path__ = [str(config_path / "custom_components"), *list(custom_components.__path__)]
    for name in list(sys.modules):
        if name == "custom_components.smart_heating" or name.startswith("custom_components.smart_heating."):
            del sys.modules[name]

    async with async_test_home_assistant(config_dir=config_dir) as hass:
        hass.data.pop(loader.DATA_CUSTOM_COMPONENTS, None)
        await loader.async_get_custom_components(hass)
        calls = []

        async def record(call):
            calls.append((call.domain, call.service))

        for service in ("set_temperature", "set_hvac_mode", "turn_on", "turn_off"):
            hass.services.async_register("climate", service, record)
        for service in ("turn_on", "turn_off", "toggle", "reload"):
            hass.services.async_register("automation", service, record)
        for service in ("turn_on", "turn_off", "toggle"):
            hass.services.async_register("homeassistant", service, record)
        hass.states.async_set("automation.heizung_automatik_ersetzt_node_red", "on")
        if stage == "write":
            flow = await hass.config_entries.flow.async_init("smart_heating", context={"source": "user"})
            flow = await hass.config_entries.flow.async_configure(
                flow["flow_id"], {"name": "Restart Smoke", "timezone": "Europe/Berlin"}
            )
            flow = await hass.config_entries.flow.async_configure(flow["flow_id"], {"confirm": True})
            entry = flow["result"]
            hass.config_entries.async_update_entry(
                entry,
                data={**entry.data, "schedule": {"monday": [{"start": "06:00:00", "end": "08:00:00", "target_temperature": 20.5}]}},
            )
            from custom_components.smart_heating.management import default_management
            management = default_management()
            management["internal"]["comfort_temperature"] = 22.5
            management["internal"]["night_temperature"] = 17.5
            management["internal"]["party"] = True
            management["control_plane"]["operating_state"] = "LEGACY"
            management["control_plane"]["confirmed_control_ownership"] = "legacy"
            management["control_plane"]["switch_ready"] = False
            management["zones"] = [{
                "id": "badezimmer", "name": "Badezimmer",
                "comfort_temperature": 24.0, "night_temperature": 18.0,
                "thermostat_entities": ["climate.badezimmer_1"],
            }]
            management["sensors"]["window"] = [{
                "id": "bad-fenster", "type": "window",
                "entity_id": "binary_sensor.bad_fenster",
                "contact_role": "open", "area_id": "badezimmer",
            }]
            hass.config_entries.async_update_entry(entry, options={**entry.options, "management": management})
            await hass.async_block_till_done()
            assert entry.state.value == "loaded", entry.state
            # Flush HA's config-entry storage via the underlying Store API.
            await hass.config_entries._store.async_save({"entries": [entry.as_dict()]})
            assert (config_path / ".storage" / "core.config_entries").exists()
        else:
            # The fixture uses a fresh HA object in this entirely separate OS process.
            # The lightweight fixture skips normal HA startup; load the persisted entries explicitly.
            await hass.config_entries.async_initialize()
            entries = hass.config_entries.async_entries("smart_heating")
            assert len(entries) == 1, f"expected persisted entry, got {entries!r}"
            entry = entries[0]
            assert entry.data["schedule"]["monday"][0]["target_temperature"] == 20.5
            from custom_components.smart_heating.management import normalize_management
            restored = normalize_management(entry.options["management"])
            assert restored["internal"]["comfort_temperature"] == 22.5
            assert restored["internal"]["night_temperature"] == 17.5
            assert restored["internal"]["party"] is True
            assert restored["control_plane"]["operating_state"] == "LEGACY"
            assert restored["control_plane"]["confirmed_control_ownership"] == "legacy"
            assert restored["control_plane"]["switch_ready"] is False
            assert restored["control_plane"]["rollback_ready"] is True
            assert restored["internal"]["enabled"] is True
            assert restored["zones"][0]["comfort_temperature"] == 24.0
            assert restored["zones"][0]["thermostat_entities"] == ["climate.badezimmer_1"]
            assert restored["sensors"]["window"][0]["entity_id"] == "binary_sensor.bad_fenster"
            assert restored["sensors"]["window"][0]["contact_role"] == "open"
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state.value == "loaded", entry.state
        assert not calls, f"passive integration invoked control services: {calls!r}"
        assert hass.states.get("automation.heizung_automatik_ersetzt_node_red").state == "on"


@unittest.skipUnless(async_test_home_assistant is not None, "Home Assistant runtime dependencies are not installed")
class SeparateProcessRestartTests(unittest.TestCase):
    def test_persist_and_restore_across_two_processes(self):
        with tempfile.TemporaryDirectory() as config_dir:
            for stage in ("write", "read"):
                result = subprocess.run(
                    [sys.executable, __file__, "--worker", stage, config_dir],
                    cwd=Path(__file__).resolve().parent.parent,
                    capture_output=True,
                    text=True,
                    timeout=90,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, f"{stage} worker failed:\n{result.stdout}\n{result.stderr}")


if __name__ == "__main__" and len(sys.argv) == 4 and sys.argv[1] == "--worker":
    asyncio.run(worker(sys.argv[2], sys.argv[3]))
