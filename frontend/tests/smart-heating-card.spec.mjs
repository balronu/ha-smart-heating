import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  await expect(page.getByTestId("status").first()).toContainText("Kompatibilitätsmodus");
  await expect(page.getByTestId("version").first()).toContainText("0.1.0-beta.39");
  await expect(page.getByText("Diese Karte zeigt ausschließlich passive Daten.").first()).toBeVisible();
});

test("renders detailed passive overview and all weekdays", async ({ page }, testInfo) => {
  await expect(page.locator("[data-display-mode=detailed]").first()).toBeVisible();
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=schedule] .day-row")).toHaveCount(7);
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=rooms] .room strong").first()).toHaveText("Badezimmer");
  await page.screenshot({ path: `test-results/${testInfo.project.name}-lovelace-detailed.png`, fullPage: true });
});

test("supports compact and individual configuration modes without writes", async ({ page }) => {
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.setConfig({ entry_id: "fixture-compact", display_mode: "compact" }); card.hass = window.hass; });
  await expect(page.locator("[data-display-mode=compact]")).toBeVisible();
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=schedule]")).toHaveCount(0);
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.setConfig({ entry_id: "fixture-custom", display_mode: "custom", visible_sections: ["rooms", "diagnostics"] }); card.hass = window.hass; });
  await expect(page.locator("[data-display-mode=custom]").first().locator("section[data-section=rooms]")).toBeVisible();
  await expect(page.locator("[data-display-mode=custom]").first().locator("section[data-section=schedule]")).toHaveCount(0);
  const calls = await page.evaluate(() => window.__calls);
  expect(calls.every((call) => call.type === "smart_heating/plan/get")).toBeTruthy();
});

test("editor emits the complete visual configuration", async ({ page }) => {
  const result = await page.evaluate(async () => { await customElements.whenDefined("smart-heating-card-editor"); const editor = document.createElement("smart-heating-card-editor"); document.body.append(editor); editor.setConfig({ entry_id: "fixture" }); return await new Promise((resolve) => { editor.addEventListener("config-changed", (event) => resolve(event.detail.config), { once: true }); editor.querySelector("[data-mode]").value = "compact"; editor.querySelector("[data-mode]").dispatchEvent(new Event("change", { bubbles: true })); }); });
  expect(result.display_mode).toBe("compact"); expect(result.entry_id).toBe("fixture"); expect(result.visible_sections).toContain("rooms");
});

test("updates live data without a polling loop", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await page.evaluate(() => { window.__fixtureState.status.zones[0].window_state = "open"; window.__fixtureState.status.observed.window_status = "open_or_tilted"; document.querySelector("smart-heating-card")._data = structuredClone(window.__fixtureState); document.querySelector("smart-heating-card")._render(); });
  await expect(card.locator("section[data-section=windows]")).toContainText("offen");
  const calls = await page.evaluate(() => window.__calls); expect(calls.every((call) => call.type === "smart_heating/plan/get")).toBeTruthy();
});

test("shows missing data instead of inventing temperatures", async ({ page }) => {
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card._data.status.zones[0].temperatures = [{ entity_id: "sensor.missing", state: "unavailable" }]; card._data.status.zones[0].target_temperature = null; card._render(); });
  await expect(page.locator("smart-heating-card").first().locator("section[data-section=rooms]")).toContainText("nicht vorhanden"); await expect(page.locator("smart-heating-card").first().locator("section[data-section=rooms]")).toContainText("Daten teilweise nicht verfügbar");
});

test("keeps multiple card instances independent", async ({ page }) => { await expect(page.locator("smart-heating-card")).toHaveCount(2); const entries = await page.evaluate(() => window.__calls.map((call) => call.entry_id)); expect(entries).toContain("fixture-0"); expect(entries).toContain("fixture-1"); });

test("uses the full narrow viewport without horizontal overflow", async ({ page }) => { const widths = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: window.innerWidth })); expect(widths.body).toBeLessThanOrEqual(widths.viewport + 1); });
