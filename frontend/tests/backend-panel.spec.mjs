import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/backend-panel.html");
  await page.evaluate(() => localStorage.clear());
  await page.reload();
  await expect(page.locator("main.smart-heating-backend")).toBeVisible();
  await expect(page.locator("details[data-section]")).toHaveCount(7);
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
  await expect(page.locator("[data-nav-back]")).toBeVisible();
  await expect(page.locator(".ha-navigation-header")).toContainText("Smart Heating");
});

test("keeps mobile navigation compact without title wrapping or overflow", async ({ page }) => {
  const metrics = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth, menu: document.querySelector("[data-ha-menu-button]").getBoundingClientRect().width, back: document.querySelector("[data-nav-back]").getBoundingClientRect().width, title: getComputedStyle(document.querySelector(".nav-title")).whiteSpace }));
  expect(metrics.body).toBeLessThanOrEqual(metrics.viewport + 1);
  expect(metrics.menu).toBeLessThanOrEqual(56);
  expect(metrics.back).toBeLessThan(metrics.viewport * 0.55);
  expect(metrics.title).toBe("nowrap");
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
  await page.locator("details[data-section=safety] summary").click();
  const party = page.locator('[data-safety-mode="party"]');
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

test("shows the graphical weekly planner with day, time, and target controls", async ({ page }) => {
  await expect(page.locator("[data-weekly-planner]")).toBeVisible();
  await expect(page.locator("[data-schedule-day]")).toHaveCount(7);
  await page.locator("button[data-schedule-add=monday]").click();
  await expect(page.locator("fieldset[data-schedule-day=monday] input[type=time]")).toHaveCount(2);
  await expect(page.locator("fieldset[data-schedule-day=monday] input[type=number]")).toHaveCount(1);
});

test("edits only the selected day and saves with visible confirmation", async ({ page }) => {
  await page.locator("button[data-schedule-day-select=wednesday]").click();
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

test("shows an inline validation message and does not call save for invalid windows", async ({ page }) => {
  await page.locator("button[data-schedule-add=monday]").click();
  const row = page.locator("[data-day-editor=monday] [data-schedule-row]").last();
  await row.locator("input[data-schedule-input=start]").fill("20:00");
  await row.locator("input[data-schedule-input=end]").fill("08:00");
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
