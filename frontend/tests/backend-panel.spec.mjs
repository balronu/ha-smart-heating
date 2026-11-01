import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/backend-panel.html");
  await page.evaluate(() => localStorage.clear());
  await page.waitForTimeout(50);
  await expect(page.locator("main.smart-heating-backend")).toBeVisible();
  await expect(page.locator("details[data-section]")).toHaveCount(8);
  await expect(page.locator("details[open]")).toHaveCount(0);
});

test("renders independent backend sections and nested rooms", async ({ page }) => {
  await page.locator("details[data-section=rooms]").first().locator(":scope > summary").click();
  await page.locator("details[data-section=persons]").first().locator(":scope > summary").click();
  await expect(page.locator("details[data-section=rooms]")).toHaveAttribute("open", "");
  await expect(page.locator("details[data-section=persons]")).toHaveAttribute("open", "");
  await expect(page.locator("details[data-room]")).toHaveCount(1);
});

test("saves a zone and preserves open sections after backend refresh", async ({ page }) => {
  await page.locator("details[data-section=rooms]").first().locator(":scope > summary").click();
  await page.locator("form[data-zone-form] input[name=name]").fill("Wohnbereich");
  await page.getByRole("button", { name: "Zone speichern" }).click();
  await expect(page.locator("details[data-zone]")).toContainText("Wohnbereich");
  await expect(page.locator("details[data-section=rooms]")).toHaveAttribute("open", "");
});

test("uses the full mobile width and keeps technical UI separate", async ({ page }) => {
  const sizes = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }));
  expect(sizes.body).toBeLessThanOrEqual(sizes.viewport + 1);
  await page.screenshot({ path: `test-results/${test.info().project.name}-backend.png`, fullPage: true });
});

test("provides a Home Assistant navigation escape hatch", async ({ page }) => {
  await expect(page.locator("[data-ha-menu-button]")).toBeVisible();
  await expect(page.locator("[data-nav-back]")).toHaveCount(0);
  await expect(page.locator(".ha-navigation-header")).toContainText("Verwaltung");
});

test("keeps mobile navigation compact without title wrapping or overflow", async ({ page }) => {
  const metrics = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth, menu: document.querySelector("[data-ha-menu-button]").getBoundingClientRect().width, context: document.querySelector(".nav-context").textContent }));
  expect(metrics.body).toBeLessThanOrEqual(metrics.viewport + 1);
  expect(metrics.menu).toBeLessThanOrEqual(56);
  expect(metrics.context).toBe("Verwaltung");
});

test("edits a Smart-Heating room internally and leaves the HA area contract intact", async ({ page }) => {
  await page.locator("details[data-section=rooms]").first().locator(":scope > summary").click();
  await page.locator("details[data-room=room-wohnzimmer] summary").click();
  await expect(page.locator("form[data-room-form]")).toBeVisible();
  await page.locator("form[data-room-form] input[name=comfort_temperature]").fill("21.5");
  await page.locator("form[data-room-form] button[type=submit]").click();
  await expect(page.locator("form[data-room-form] [data-room-feedback]")).toContainText("Raumkonfiguration gespeichert");
  await expect(page.locator("details[data-room=room-wohnzimmer]")).toContainText("Smart-Heating-Raum aktiv");
});

test("persists passive special-mode configuration with a helper status source", async ({ page }) => {
  await page.locator("details[data-section=safety] > summary").click();
  const party = page.locator('[data-safety-mode="party"]');
  await party.locator(":scope > summary").click();
  await party.locator("input[name=enabled]").check();
  await party.locator("select[name=helper_entity]").selectOption("input_boolean.party");
  await party.locator("input[name=temperature]").fill("22");
  await page.locator("form[data-safety-form] button[type=submit]").click();
  await expect(page.locator("[data-safety-feedback]")).toContainText("Sondermodi gespeichert");
  await expect(page.locator("form[data-safety-form]")).toContainText("keine aktive Heizungssteuerung");
});

test("does not present an HA-area suggestion as a saved window assignment", async ({ page }) => {
  await page.locator("details[data-section=windows]").first().locator(":scope > summary").click();
  const row = page.locator('tr[data-window-row]').filter({ hasText: "Fenster Batterie" });
  await expect(row).toContainText("Noch nicht zugeordnet");
  await expect(row.locator("select[data-window-area]")).toHaveValue("");
});

test("keeps temperature and controller choices explicit and passive", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.temperature_entities = [{ entity_id: "sensor.outdoor", name: "Außen", state: "unknown" }];
    panel._data.controller_entities = [{ entity_id: "input_boolean.heizung", name: "Heizung", state: "off", passive: true, description: "Beobachtbares Steuersignal; keine Schaltung" }];
    panel._render();
  });
  await page.locator("details[data-section=outdoor] summary").click();
  await expect(page.locator("form[data-outdoor-form] select option[value='sensor.outdoor']")).toHaveCount(1);
  await page.locator("details[data-section=controller] summary").click();
  await expect(page.locator("form[data-controller-form] select option[value='input_boolean.heizung']")).toHaveCount(1);
  await expect(page.locator("details[data-section=controller]")).toContainText("keine Befehle");
});

test("shows a saved outdoor source even when it is temporarily unavailable", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.management.outdoor_temperature = { entity_id: "sensor.gw1100a_v2_2_3_outdoor_temperature" };
    panel._data.temperature_entities = [{ entity_id: "sensor.gw1100a_v2_2_3_outdoor_temperature", name: "Außentemperatur", temperature_role: "outdoor", state: "unavailable", available: false }];
    panel._render();
  });
  await page.locator("details[data-section=outdoor] summary").click();
  await expect(page.locator("form[data-outdoor-form] select")).toHaveValue("sensor.gw1100a_v2_2_3_outdoor_temperature");
  await expect(page.locator("[data-outdoor-entity]")).toContainText("Gespeicherte Entity");
});

test("offers only boolean status helpers and separates availability from activity", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.helper_entities = [
      { entity_id: "input_boolean.party", name: "Party", state: "on", domain: "input_boolean", available: true, active: true, suggested_for: ["party"] },
      { entity_id: "input_number.temperature", name: "Temperatur", state: "20", domain: "input_number" },
      { entity_id: "input_boolean.besuch", name: "Besuch", state: "unavailable", domain: "input_boolean", available: false, active: false, suggested_for: ["visit"] },
    ];
    panel._render();
  });
  await page.locator("details[data-section=safety] > summary").click();
  const party = page.locator('[data-safety-mode="party"]');
  await party.locator(":scope > summary").click();
  await expect(party.locator("select option[value='input_boolean.party']")).toHaveCount(1);
  await expect(party.locator("select option[value='input_number.temperature']")).toHaveCount(0);
  await expect(party).toContainText("Verfügbarkeit");
  await expect(party).toContainText("Aktivität");
  await expect(party).toContainText("Status");
});

test("keeps special-mode defaults compact and reveals extra Boolean helpers through search", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.helper_entities = [
      { entity_id: "input_boolean.party", name: "Party", state: "off", domain: "input_boolean", available: true, active: false, preferred_for: ["party"] },
      { entity_id: "input_boolean.fremdmodus", name: "Fremdmodus", state: "off", domain: "input_boolean", available: true, active: false, preferred_for: [] },
    ];
    panel._render();
  });
  await page.locator("details[data-section=safety] > summary").click();
  const party = page.locator('[data-safety-mode="party"]');
  await party.locator(":scope > summary").click();
  await expect(party.locator("select option[value='input_boolean.party']")).toHaveCount(1);
  await expect(party.locator("select option[value='input_boolean.fremdmodus']")).toHaveCount(0);
  await party.locator("input[data-mode-source-search]").fill("Fremd");
  await expect(party.locator("select option[value='input_boolean.fremdmodus']")).toHaveCount(1);
  await expect(party).toContainText("Empfehlung");
});

test("manages an internal custom special mode without exposing helper creation", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.management.special_modes = [{ id: "quiet-hours", name: "Ruhezeit", description: "Passiv anzeigen", mode_type: "custom", behavior: "passive_only", available: false, active: false, binding_type: "internal", helper_entity: "", origin: "user" }];
    panel._render();
  });
  await page.locator("details[data-section=safety] > summary").click();
  const mode = page.locator('[data-special-mode="quiet-hours"]');
  await mode.locator(":scope > summary").click();
  await expect(mode).toContainText("Steuerbar: nein");
  await expect(mode.locator("option:disabled")).toContainText("nicht verfügbar");
  await expect(page.locator("[data-special-mode-add]")).toBeVisible();
  await expect(mode.locator("[data-special-mode-duplicate]")).toBeVisible();
  await expect(mode.locator("[data-special-mode-delete]")).toBeVisible();
});

test("edits schema-6 special-mode effects and keeps the chimney-sweep guard", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.management.zones = [{ id: "zone-1", name: "Wohnzimmer", area_ids: ["wohnzimmer"] }];
    panel._data.management.special_modes = [{ id: "quiet-hours", name: "Ruhezeit", description: "Passiv", mode_type: "custom", behavior: "passive_only", available: true, active: false, binding_type: "internal", helper_entity: "", origin: "user", zone_ids: ["zone-1"], priority: 450, effect: { action: "comfort", override_schedule: false, respect_windows: true, respect_presence: true }, deactivation: { action: "return_to_normal" } }];
    panel.__phase77Calls = [];
    panel._hass.callWS = async (message) => { panel.__phase77Calls.push(message); return message.type.endsWith("admin/get") ? structuredClone(panel._data) : {}; };
    panel._render();
  });
  await page.locator("details[data-section=safety] > summary").click();
  const mode = page.locator('[data-special-mode="quiet-hours"]');
  await mode.locator(":scope > summary").click();
  await expect(mode).toContainText("Verhalten bei Aktivierung");
  await mode.locator("[name=effect_action]").selectOption("fixed_temperature");
  await mode.locator("[name=target_temperature]").fill("21.5");
  await mode.locator("[name=override_schedule]").check();
  await mode.locator("[name=zone_ids]").selectOption("zone-1");
  await mode.locator("[name=effect_scope][value=selected]").check();
  await mode.getByRole("button", { name: "Speichern" }).click();
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel").__phase77Calls.find((item) => item.type.endsWith("admin/special_mode/set"))?.item?.effect?.target_temperature)).toBe(21.5);
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel").__phase77Calls.find((item) => item.type.endsWith("admin/special_mode/set"))?.item?.effect?.override_schedule)).toBe(true);
});

test("keeps the built-in chimney-sweep priority and passive protection visible", async ({ page }) => {
  await page.locator("details[data-section=safety] > summary").click();
  const chimney = page.locator('[data-safety-mode="chimney_sweep"]');
  await chimney.locator(":scope > summary").click();
  await expect(chimney).toContainText("unveränderliche Priorität 1000");
  await expect(chimney.locator("[name=priority]")).toHaveValue("1000");
  await expect(chimney.locator("[name=priority]")).toBeDisabled();
  await expect(chimney.locator("[name=respect_windows]")).toBeDisabled();
  await expect(chimney.locator("[name=respect_presence]")).toBeDisabled();
  await expect(chimney).toContainText("passiv");
});

test("keeps a new special mode local until create and lets cancel avoid backend writes", async ({ page }) => {
  await page.locator("details[data-section=safety] > summary").click();
  const calls = await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel.__phase71Calls = [];
    const original = panel._hass.callWS;
    panel._hass.callWS = async (message) => { panel.__phase71Calls.push(message); return message.type.endsWith("admin/get") ? structuredClone(panel._data) : original(message); };
    return panel.__phase71Calls;
  });
  await page.getByRole("button", { name: "Sondermodus hinzufügen" }).click();
  await expect(page.locator("[data-special-mode-draft]")).toBeVisible();
  expect(calls).toHaveLength(0);
  await page.getByRole("button", { name: "Abbrechen" }).click();
  await expect(page.locator("[data-special-mode-draft]")).toHaveCount(0);
  expect(await page.evaluate(() => document.querySelector("smart-heating-backend-panel").__phase71Calls)).toHaveLength(0);
  await page.getByRole("button", { name: "Sondermodus hinzufügen" }).click();
  await page.locator("[data-special-mode-draft] input[name=name]").fill("Testentwurf");
  await page.getByRole("button", { name: "Anlegen" }).click();
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel").__phase71Calls.map((item) => item.type))).toContain("smart_heating/admin/special_mode/set");
});

test("keeps built-in modes collapsed and separates an unavailable custom source from activity", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.management.special_modes = [{ id: "remote", name: "Remote", description: "Passiv", mode_type: "custom", behavior: "passive_only", available: true, active: true, binding_type: "entity", helper_entity: "input_boolean.missing", origin: "user" }];
    panel._data.helper_entities = [];
    panel._render();
  });
  await page.locator("details[data-section=safety] > summary").click();
  await expect(page.locator("[data-safety-mode]")).toHaveCount(6);
  await expect(page.locator("[data-safety-mode]").first()).toHaveJSProperty("open", false);
  await expect(page.locator("[data-safety-mode]").first().locator(".mode-description")).toHaveCount(1);
  const mode = page.locator('[data-special-mode="remote"]');
  await expect(mode).toContainText("Status unbekannt");
  await expect(mode).toContainText("input_boolean.missing");
  await expect(mode).toContainText("nicht verfügbar");
});

test("centralizes global settings and keeps active control locked", async ({ page }) => {
  await page.locator("details[data-section=system] summary").click();
  await expect(page.locator("form[data-system-form]")).toContainText("Kompatibilitätsmodus");
  await expect(page.locator("form[data-system-form] option[value=full]")).toHaveAttribute("disabled", "");
  await expect(page.locator("form[data-system-form]")).toContainText("gesperrt");
});

test("separates relevant rooms, other HA areas, and technical temperature sources", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.areas = [
      { area_id: "wohnzimmer", name: "Wohnzimmer", relevant: true, suggestions: { thermostat_entities: ["climate.wohnzimmer"], temperature_entities: ["sensor.wohnzimmer"] }, additional_temperature_entities: [{ entity_id: "sensor.pve_disk_temperature" }] },
      { area_id: "tankstelle", name: "Tankstellen", relevant: false, suggestions: { thermostat_entities: [], temperature_entities: [] }, additional_temperature_entities: [] },
    ];
    panel._data.temperature_entities = [
      { entity_id: "sensor.wohnzimmer", name: "Wohnzimmer", temperature_role: "room" },
      { entity_id: "sensor.pve_disk_temperature", name: "PVE Disk", temperature_role: "technical" },
    ];
    panel._render();
  });
  await page.locator("details[data-section=rooms]").first().locator(":scope > summary").click();
  await expect(page.locator("details[data-room]")).toHaveCount(2);
  await expect(page.locator("details[data-room=room-tankstelle]")).toContainText("nicht zugeordnet");
  await expect(page.locator("details[data-room=room-wohnzimmer]")).toContainText("sensor.pve_disk_temperature");
  await page.locator("[data-area-search]").fill("tank");
  await expect(page.locator("details[data-room=room-wohnzimmer]")).toBeHidden();
  await expect(page.locator("details[data-room=room-tankstelle]")).toBeVisible();
});

test("uses contact cards on small displays", async ({ page }) => {
  await page.locator("details[data-section=windows] summary").click();
  await expect(page.locator(".contact-cards article")).toHaveCount(3);
});

test("keeps bathroom window status readable and separates saved assignment", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.window_contacts.contacts.push({ id: "window-bathroom", name: "Badezimmer Fenster", entity_id: "binary_sensor.badezimmer_fenster", area_name: "Badezimmer", assigned_area_id: "badezimmer", assigned_area_name: "Badezimmer", status: "closed", review_required: false, review_flags: [] });
    panel._data.areas.push({ area_id: "badezimmer", name: "Badezimmer", relevant: false, relevance_source: "unassigned", window_contacts: [panel._data.window_contacts.contacts.at(-1)], window_contact_count: 1 });
    panel._render();
  });
  await page.locator("details[data-section=rooms] > summary").click();
  await expect(page.locator("details[data-room=room-badezimmer] summary")).toContainText("1 Fenster");
  const roomContact = page.locator("details[data-room=room-badezimmer] [data-room-window-contact]");
  await expect(roomContact).toContainText("Badezimmer Fenster");
  await expect(roomContact).toContainText("geschlossen");
  await page.locator("details[data-section=windows] summary").click();
  await expect(page.locator("tr[data-window-row]").filter({ hasText: "Badezimmer Fenster" })).toHaveCount(0);
});

test("shows distinct read-only sources for assigned window role diagnostics", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.window_role_diagnostics = [
      { entity_id: "binary_sensor.bath_tilt", name: "Bad gekippt", config_entry_role: "tilt", runtime_role: "unassigned", readback_role: "tilt", status: "Abweichung" },
      { entity_id: "binary_sensor.bath_open", name: "Bad offen", config_entry_role: null, runtime_role: null, readback_role: "open", status: "Abweichung" },
    ];
    panel._render();
  });
  const section = page.locator("details[data-section=diagnostics]");
  await section.locator(":scope > summary").click();
  await expect(section.locator("[data-window-role-diagnostic]")).toHaveCount(2);
  await expect(section).toContainText("binary_sensor.bath_tilt");
  await expect(section).toContainText("Nicht vorhanden");
  await expect(section).toContainText("Abweichung");
  await expect(section.locator("button,select,input")).toHaveCount(0);
});

test("shows an explicit diagnostic-unavailable state instead of hiding existing contacts", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.window_role_diagnostics = [];
    panel._data.window_contacts.contacts = [
      { entity_id: "binary_sensor.legacy_contact", name: "Altkontakt", ignored: false },
    ];
    panel._render();
  });
  const section = page.locator("details[data-section=diagnostics]");
  await section.locator(":scope > summary").click();
  await expect(section.locator("[data-window-role-diagnostics]")).toContainText("Diagnosedaten nicht verfügbar");
  await expect(section.locator("[data-window-role-diagnostics]")).toContainText("Backend");
  await expect(section.locator("button,select,input")).toHaveCount(0);
});

test("renders every configured contact and all three missing sources from a wrapped admin response", async ({ page }) => {
  await page.evaluate(async () => {
    const panel = document.querySelector("smart-heating-backend-panel");
    const payload = structuredClone(panel._data);
    payload.window_contacts.contacts = [
      { entity_id: "binary_sensor.fensterkontakt_badezimmer_contact", name: "Fenster Badezimmer", ignored: false },
      { entity_id: "binary_sensor.fensterkontakt_badezimmer_1_2_contact", name: "Fensterkontakt Badezimmer 1 2", ignored: false },
    ];
    delete payload.window_role_diagnostics;
    const original = panel._hass.callWS;
    panel._hass.callWS = async (message) => message.type.endsWith("admin/get") ? { result: payload } : original(message);
    panel._loaded = false;
    panel._data = null;
    await panel._load();
  });
  const section = page.locator("details[data-section=diagnostics]");
  await section.locator(":scope > summary").click();
  await expect(section.locator("[data-window-role-diagnostic]")).toHaveCount(2);
  await expect(section).toContainText("binary_sensor.fensterkontakt_badezimmer_contact");
  await expect(section).toContainText("binary_sensor.fensterkontakt_badezimmer_1_2_contact");
  await expect(section.locator("[data-window-role-diagnostic]").first()).toContainText("Nicht vorhanden");
  await expect(section).toContainText("Diagnosedaten nicht verfügbar");
  await expect(section.locator("th")).toHaveCount(5);
});

test("keeps role changes local until room save and persists independent contact roles across reload", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.climate_entities = [
      { entity_id: "climate.badezimmer_one", name: "Badezimmer Heizkörper 1", state: "heat", available: true },
      { entity_id: "climate.badezimmer_two", name: "Badezimmer Heizkörper 2", state: "heat", available: true },
    ];
    panel._data.temperature_entities = [{ entity_id: "sensor.badezimmer_temperatur", name: "Badezimmer Temperatur", temperature_role: "room", state: "20", available: true }];
    const contacts = [
      { id: "window-bathroom-tilt", name: "Badezimmer gekippt", entity_id: "binary_sensor.fensterkontakt_badezimmer_contact", area_name: "Badezimmer", assigned_area_id: "badezimmer", assigned_area_name: "Badezimmer", status: "closed", available: true, contact_role: "unassigned", review_required: false, review_flags: [] },
      { id: "window-bathroom-open", name: "Badezimmer offen", entity_id: "binary_sensor.fensterkontakt_badezimmer_1_2_contact", area_name: "Badezimmer", assigned_area_id: "badezimmer", assigned_area_name: "Badezimmer", status: "closed", available: true, contact_role: "unassigned", review_required: false, review_flags: [] },
    ];
    panel._data.window_contacts.contacts.push(...contacts);
    panel._data.areas.push({ area_id: "badezimmer", name: "Badezimmer", relevant: false, relevance_source: "unassigned", window_contacts: contacts, window_contact_count: contacts.length });
    panel._render();
  });
  await page.locator("details[data-section=rooms] > summary").click();
  await page.locator("details[data-room=room-badezimmer] summary").click();
  const room = page.locator("details[data-room=room-badezimmer]");
  await expect(room.locator("[data-room-window-contact]")).toHaveCount(2);
  await expect(room.locator("[data-room-window-contact]").first()).toContainText("binary_sensor.fensterkontakt_badezimmer_contact");
  await page.evaluate(() => { const panel = document.querySelector("smart-heating-backend-panel"); panel._calls = []; const original = panel._hass.callWS; panel._hass.callWS = async (message) => { panel._calls.push(message); return original(message); }; });
  await room.locator("[data-room-window-contact]").nth(0).locator("select[data-room-window-role]").selectOption("tilt");
  await room.locator("[data-room-window-contact]").nth(1).locator("select[data-room-window-role]").selectOption("open");
  await expect(room.locator("[data-room-window-contact]").nth(0).locator("select")).toHaveValue("tilt");
  await expect(room.locator("[data-room-window-contact]").nth(1).locator("select")).toHaveValue("open");
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel")._calls.filter((item) => item.type.endsWith("admin/sensor/set")).length)).toBe(0);
  await room.locator("select[name=thermostat_entity]").selectOption(["climate.badezimmer_one", "climate.badezimmer_two"]);
  await room.locator("select[name=temperature_entity]").selectOption("sensor.badezimmer_temperatur");
  await page.evaluate(() => { document.querySelector("smart-heating-backend-panel")._roomWindowRoleDrafts = {}; });
  await room.locator("button[type=submit]").click();
  await expect(page.locator("details[data-room=room-badezimmer] [data-room-feedback]")).toContainText("Raumkonfiguration gespeichert");
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel")._data.window_contacts.contacts.filter((item) => item.assigned_area_id === "badezimmer").map((item) => item.contact_role))).toEqual(["tilt", "open"]);
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel")._calls.filter((item) => item.type.endsWith("admin/room/save")).length)).toBe(1);
  await expect.poll(() => page.evaluate(() => document.querySelector("smart-heating-backend-panel")._calls.filter((item) => item.type.endsWith("admin/sensor/set")).length)).toBe(0);
  const roomSave = await page.evaluate(() => document.querySelector("smart-heating-backend-panel")._calls.find((item) => item.type.endsWith("admin/room/save")));
  expect(roomSave.item.thermostat_entities).toEqual(["climate.badezimmer_one", "climate.badezimmer_two"]);
  expect(roomSave.item.temperature_entities).toEqual(["sensor.badezimmer_temperatur"]);
  expect(Object.fromEntries(roomSave.contacts.map((item) => [item.entity_id, item.contact_role]))).toEqual({
    "binary_sensor.fensterkontakt_badezimmer_contact": "tilt",
    "binary_sensor.fensterkontakt_badezimmer_1_2_contact": "open",
  });
  await page.reload();
  await page.locator("details[data-section=rooms] > summary").click();
  await page.locator("details[data-room=room-badezimmer] summary").click();
  await expect(page.locator("details[data-room=room-badezimmer] [data-room-window-contact]").nth(0).locator("select")).toHaveValue("tilt");
  await expect(page.locator("details[data-room=room-badezimmer] [data-room-window-contact]").nth(1).locator("select")).toHaveValue("open");
});

test("ignores and restores a contact without deleting the HA entity", async ({ page }) => {
  await page.locator("details[data-section=windows] summary").click();
  const row = page.locator('tr[data-window-row]').filter({ hasText: "Wohnzimmer Fenster" });
  await row.locator("[data-window-ignore]").click();
  await expect(page.locator('tr[data-window-row]').filter({ hasText: "Wohnzimmer Fenster" })).toHaveCount(0);
  await expect(page.locator(".ignored-sensors summary")).toContainText("Ignorierte Sensoren (1)");
  await page.locator(".ignored-sensors").locator("summary").click();
  await page.locator("[data-window-restore='binary_sensor.wohnzimmer_fenster']").click();
  await expect(page.locator('tr[data-window-row]').filter({ hasText: "Wohnzimmer Fenster" })).toHaveCount(1);
  await expect(page.locator(".ignored-sensors summary")).toContainText("Ignorierte Sensoren (0)");
});

test("shows the graphical weekly planner with day, time, and target controls", async ({ page }) => {
  await expect(page.locator("[data-weekly-planner]")).toBeVisible();
  await expect(page.locator("[data-schedule-day]")).toHaveCount(7);
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  await expect(page.locator("fieldset[data-schedule-day=monday] input[type=time]")).toHaveCount(2);
  await expect(page.locator("fieldset[data-schedule-day=monday] input[type=number]")).toHaveCount(1);
});

test("edits only the selected day and saves with visible confirmation", async ({ page }) => {
  await page.locator("button[data-schedule-edit=wednesday]").click();
  await expect(page.locator("[data-day-editor=wednesday]")).toBeVisible();
  await expect(page.locator("[data-day-editor=monday]")).toHaveCount(0);
  await page.locator("button[data-schedule-add=wednesday]").click();
  const row = page.locator("[data-day-editor=wednesday] [data-schedule-row]").last();
  await row.locator("input[data-schedule-input=start]").fill("06:00");
  await row.locator("input[data-schedule-input=end]").fill("08:30");
  await row.locator("input[data-schedule-input=target_temperature]").fill("21.5");
  await page.locator("[data-schedule-save]").click();
  await expect(page.locator("[role=status]")).toContainText("erfolgreich gespeichert");
  await page.reload();
  await expect(page.locator("[data-schedule-day=wednesday] [data-day-summary]")).toContainText("06:00–08:30");
});

test("shows unsaved state before saving and stacks time fields on a narrow phone", async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 740 });
  await page.evaluate(() => { const meta = document.createElement("meta"); meta.name = "viewport"; meta.content = "width=device-width, initial-scale=1"; document.head.append(meta); });
  await page.waitForTimeout(50);
  await expect(page.locator("main.smart-heating-backend")).toBeVisible();
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  await expect(page.locator("[data-weekly-planner] [role=status]")).toContainText("noch nicht gespeichert");
  const layout = await page.locator("[data-day-editor=monday] [data-schedule-row]").evaluate((row) => {
    const labels = [...row.querySelectorAll("label")].map((label) => label.getBoundingClientRect());
    return labels.map((box) => ({ top: Math.round(box.top), left: Math.round(box.left), right: Math.round(box.right) }));
  });
  expect(layout[1].top).toBeGreaterThan(layout[0].top);
  expect(layout[0].right).toBeLessThanOrEqual(320);
  expect(layout[1].right).toBeLessThanOrEqual(320);
});

test("supports an overnight window and explicitly cancels local edits", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel.__phase78Calls = [];
    const callWS = panel._hass.callWS;
    panel._hass.callWS = async (message) => { panel.__phase78Calls.push(message); return callWS(message); };
  });
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  const row = page.locator("[data-day-editor=monday] [data-schedule-row]").last();
  await row.locator("input[data-schedule-input=start]").fill("22:00");
  await row.locator("input[data-schedule-input=end]").fill("02:00");
  await page.locator("button[data-schedule-close]").click();
  await expect(page.locator("[data-schedule-day=monday] [data-day-summary]")).toContainText("über Mitternacht");
  const callsBeforeCancel = await page.evaluate(() => document.querySelector("smart-heating-backend-panel").__phase78Calls.filter((item) => item.type.endsWith("plan/set")).length);
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-cancel]").click();
  await expect(page.locator("[data-schedule-day=monday] [data-day-summary]")).not.toContainText("über Mitternacht");
  const callsAfterCancel = await page.evaluate(() => document.querySelector("smart-heating-backend-panel").__phase78Calls.filter((item) => item.type.endsWith("plan/set")).length);
  expect(callsAfterCancel).toBe(callsBeforeCancel);
});

test("shows an inline validation message and does not call save for invalid windows", async ({ page }) => {
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  const row = page.locator("[data-day-editor=monday] [data-schedule-row]").last();
  await row.locator("input[data-schedule-input=start]").fill("20:00");
  await row.locator("input[data-schedule-input=end]").fill("20:00");
  await page.locator("[data-schedule-save]").click();
  await expect(page.locator("[role=status]")).toContainText("Zeitfenster");
  await expect(page.locator("[role=alert]")).toHaveCount(0);
});

test("accepts the array form returned by config_entries/get", async ({ page }) => {
  await page.goto("/frontend/fixtures/backend-panel.html?array");
  await expect(page.locator("main.smart-heating-backend")).toBeVisible();
  await expect(page.locator("[role=alert]")).toHaveCount(0);
});

test("fails closed when more than one active entry exists", async ({ page }) => {
  await page.goto("/frontend/fixtures/backend-panel.html?multiple");
  await expect(page.locator("[role=alert]")).toContainText("Mehrere Smart-Heating-Konfigurationen");
  await expect(page.locator("[role=alert]")).toContainText("duplicate");
});

test("filters many window contacts without treating battery sensors as eligible", async ({ page }) => {
  await page.locator("details[data-section=windows]").first().locator(":scope > summary").click();
  await expect(page.locator("tr[data-window-row]")).toHaveCount(3);
  await page.locator("[data-window-search]").fill("tür");
  await expect(page.locator("tr[data-window-row]:not([hidden])")).toHaveCount(1);
  await page.locator("[data-window-search]").fill("");
  await page.locator("[data-window-filter]").selectOption("review");
  await expect(page.locator("tr[data-window-row]:not([hidden])")).toHaveCount(1);
  await expect(page.locator("tr[data-window-row]:not([hidden])")).toContainText("manuell prüfen");
});

test("offers suitable bathroom devices outside the HA area and preserves the selected values", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.climate_entities = [{ entity_id: "climate.heizthermostat_badezimmer", name: "Badezimmer Thermostat", state: "heat" }];
    panel._data.temperature_entities = [{ entity_id: "sensor.badezimmer_temperatur", name: "Badezimmer Temperatur", temperature_role: "room", state: "20" }, { entity_id: "sensor.gefrierschrank_temperatur", name: "Gefrierschrank", temperature_role: "technical", state: "-18" }];
    panel._data.areas.push({ area_id: "badezimmer", name: "Badezimmer", relevant: false, relevance_source: "unassigned", thermostat_entities: [], temperature_entities: [] });
    panel._data.management.zones = [{ id: "bathroom-zone", name: "Badezimmer", area_ids: ["badezimmer"], thermostat_entities: ["climate.heizthermostat_badezimmer"], temperature_entities: ["sensor.badezimmer_temperatur"], enabled: true }];
    panel._render();
  });
  await page.getByText("Räume & Klimazonen", { exact: true }).click();
  const room = page.locator("details[data-room=room-badezimmer]");
  await room.locator("summary").click();
  await expect(room.locator("select[name=thermostat_entity] option[value='climate.heizthermostat_badezimmer']")).toHaveCount(1);
  await expect(room.locator("select[name=temperature_entity] option[value='sensor.badezimmer_temperatur']")).toHaveCount(1);
  await expect(room.locator("select[name=temperature_entity] option[value='sensor.gefrierschrank_temperatur']")).toHaveCount(0);
  await expect(room.locator("input[name=comfort_temperature]")).toHaveValue("20");
  await expect(room.locator("input[name=comfort_temperature]")).not.toHaveValue("24");
  await expect(room.locator("[data-room-assignment-hint]")).toContainText("separat aktiviert");
});

test("uses one checked multi-thermostat selector and restores all saved entries", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.climate_entities = [
      { entity_id: "climate.esszimmer_one", name: "Esszimmer Heizkörper 1", state: "heat", available: true },
      { entity_id: "climate.esszimmer_two", name: "Esszimmer Heizkörper 2", state: "unavailable", available: false },
    ];
    panel._data.areas[0].thermostat_entities = panel._data.climate_entities;
    panel._data.management.zones = [{ id: "dining-zone", name: "Esszimmer", area_ids: ["wohnzimmer"], thermostat_entities: ["climate.esszimmer_one", "climate.esszimmer_two"], temperature_entities: [], enabled: true }];
    panel._render();
  });
  await page.getByText("Räume & Klimazonen", { exact: true }).click();
  const room = page.locator("details[data-room=room-wohnzimmer]");
  await room.locator("summary").click();
  await expect(room.locator("select[name=thermostat_entity]")).toHaveCount(1);
  await expect(room.locator("select[name=thermostat_entity]")).toHaveAttribute("multiple", "");
  await expect(room.locator("select[data-lead-thermostat]")).toHaveCount(0);
  await expect(room.locator("select[name=thermostat_entity] option:checked")).toHaveCount(2);
  await expect(room.locator("[data-selected-thermostats]")).toContainText("Esszimmer Heizkörper 1");
  await expect(room.locator("[data-selected-thermostats]")).toContainText("nicht verfügbar");
});

test("labels unavailable contact states as unavailable and explains passive special modes", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.window_contacts.contacts.push({ id: "window-unknown", name: "Keller Sensor", entity_id: "binary_sensor.keller_fenster", area_name: "Keller", status: "unavailable", review_required: true, review_flags: ["stale_or_unavailable"] });
    panel._render();
  });
  await page.locator("details[data-section=windows] summary").click();
  await expect(page.locator("tr[data-window-row]").filter({ hasText: "Keller Sensor" })).toContainText("nicht verfügbar");
  await page.locator("details[data-section=safety] > summary").click();
  const mode = page.locator('[data-safety-mode="party"]');
  await mode.locator(":scope > summary").click();
  await expect(mode).toContainText("Statusquelle");
  await expect(mode).toContainText("Kontrollkästchen aktiviert keinen Modus");
});

test("rejects overlapping windows before the websocket save", async ({ page }) => {
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  const rows = page.locator("[data-day-editor=monday] [data-schedule-row]");
  await rows.nth(0).locator("input[data-schedule-input=start]").fill("06:00");
  await rows.nth(0).locator("input[data-schedule-input=end]").fill("10:00");
  await rows.nth(1).locator("input[data-schedule-input=start]").fill("09:00");
  await rows.nth(1).locator("input[data-schedule-input=end]").fill("12:00");
  await page.locator("[data-schedule-save]").click();
  await expect(page.locator("[role=status]")).toContainText("überlappen");
});

test("keeps a compact seven-day overview and copies a day without opening all editors", async ({ page }) => {
  await expect(page.locator("[data-schedule-day]")).toHaveCount(7);
  await expect(page.locator("[data-day-editor]")).toHaveCount(0);
  await page.locator("button[data-schedule-edit=monday]").click();
  await page.locator("button[data-schedule-add=monday]").click();
  await page.evaluate(() => window.prompt = () => "friday");
  await page.locator("button[data-schedule-copy]").click();
  await expect(page.locator("fieldset[data-schedule-day=friday] [data-day-summary]")).toContainText("06:00–22:00");
  await expect(page.locator("[data-day-editor]")).toHaveCount(1);
});

test("manages multiple contacts inside a room and persists a room move", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    const contact = panel._data.window_contacts.contacts[0];
    contact.assigned_area_id = "wohnzimmer";
    contact.assigned_area_name = "Wohnzimmer";
    contact.status = "closed";
    state.window_contacts.contacts[0].assigned_area_id = "wohnzimmer";
    state.window_contacts.contacts[0].assigned_area_name = "Wohnzimmer";
    panel._data.areas[0].window_contacts = [contact];
    panel._data.areas[0].window_contact_count = 1;
    panel._render();
  });
  await page.locator("details[data-section=rooms] > summary").click();
  const room = page.locator("details[data-room=room-wohnzimmer]");
  await room.locator("summary").click();
  await expect(room.locator("[data-room-window-contact]")).toHaveCount(1);
  await room.locator("[data-room-window-add-input]").fill("binary_sensor.wohnzimmer_tuer");
  await room.locator("[data-room-window-add]").click();
  await expect(room.locator("[data-room-window-contact]")).toHaveCount(2);
  await room.locator("[data-room-window-remove='binary_sensor.wohnzimmer_fenster']").click();
  await expect(room.locator("[data-room-window-contact]")).toHaveCount(1);
  await expect(room).toContainText("Wohnzimmer Tür");
});

test("shows assigned contacts in their saved room and keeps ignored contacts separate", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    const contact = panel._data.window_contacts.contacts[0];
    contact.assigned_area_id = "wohnzimmer";
    contact.assigned_area_name = "Wohnzimmer";
    panel._data.areas[0].window_contacts = [contact];
    panel._data.areas[0].window_contact_count = 1;
    panel._render();
  });
  await page.locator("details[data-section=rooms] > summary").click();
  await expect(page.locator("details[data-room=room-wohnzimmer] summary")).toContainText("1 Fenster");
  await page.locator("details[data-section=windows] summary").click();
  await expect(page.locator("tr[data-window-row]")).toHaveCount(2);
  await expect(page.locator("tr[data-window-row]").filter({ hasText: "Wohnzimmer Fenster" })).toHaveCount(0);
});

test("searches long cross-area device lists and keeps the saved bathroom choices", async ({ page }) => {
  await page.evaluate(() => {
    const panel = document.querySelector("smart-heating-backend-panel");
    panel._data.climate_entities = [{ entity_id: "climate.heizthermostat_badezimmer_mit_einer_sehr_langen_entity_id", name: "Badezimmer Thermostat", area_id: "badezimmer" }];
    panel._data.temperature_entities = [{ entity_id: "sensor.badezimmer_temperatur_mit_einer_sehr_langen_entity_id", name: "Badezimmer Temperatur", temperature_role: "room", area_id: "badezimmer" }, { entity_id: "sensor.fensterkontakt_temperatur", name: "Fensterkontakt Temperatur", temperature_role: "contact", area_id: "wohnzimmer" }];
    panel._data.areas.push({ area_id: "badezimmer", name: "Badezimmer", relevant: false, relevance_source: "unassigned", thermostat_entities: [], temperature_entities: [] });
    panel._data.management.zones = [{ id: "bathroom-zone", name: "Badezimmer", area_ids: ["badezimmer"], thermostat_entities: ["climate.heizthermostat_badezimmer_mit_einer_sehr_langen_entity_id"], temperature_entities: ["sensor.badezimmer_temperatur_mit_einer_sehr_langen_entity_id"], enabled: true }];
    panel._render();
  });
  await page.getByText("Räume & Klimazonen", { exact: true }).click();
  const room = page.locator("details[data-room=room-badezimmer]");
  await room.locator("summary").click();
  await expect(room.locator("select[name=thermostat_entity] optgroup")).toHaveAttribute("label", "Weitere geeignete Geräte");
  await expect(room.locator("select[name=temperature_entity] option[value='sensor.fensterkontakt_temperatur']")).toHaveCount(1);
  await room.locator("input[data-room-device-search]").fill("fensterkontakt");
  await expect(room.locator("select[name=temperature_entity] option[value='sensor.fensterkontakt_temperatur']")).toHaveJSProperty("hidden", false);
  await expect(room.locator("select[name=temperature_entity] option[value='sensor.badezimmer_temperatur_mit_einer_sehr_langen_entity_id']")).toHaveJSProperty("hidden", true);
});
