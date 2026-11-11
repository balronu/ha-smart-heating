import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator(".sh-app")).toBeVisible();
  await page.evaluate(() => { const original = window.hass.callWS; window.hass.callWS = async message => { if (message.type === "smart_heating/admin/internal/set") { window.__calls.push(structuredClone(message)); return { internal: { enabled: message.item.enabled ?? true, operating_mode: message.item.operating_mode || "automatic", comfort_temperature: message.item.comfort_temperature || 22, zones: { [message.item.zone_id || "bathroom"]: { comfort_temperature: message.item.comfort_temperature || 24 } } } }; } return original(message); }; });
});

test("renders the three beta.60 dashboard sections and six touch tiles", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator("h2")).toHaveText(["Heizungssteuerung", "Hauptheizung", "Räume"]);
  await expect(card.locator(".sh-mode-tile")).toHaveCount(6);
  await expect(card.locator(".sh-room-card")).toHaveCount(3);
  await expect(card.locator(".sh-room-card").first()).toContainText("Badezimmer");
});

test("keeps bathroom target, radiator and infrared values separate without IDs", async ({ page }) => {
  const room = page.locator(".sh-room-card").filter({ hasText: "Badezimmer" });
  await expect(room).toContainText("Isttemperatur");
  await expect(room).toContainText("21.5 °C");
  await expect(room).toContainText("Raumziel");
  await expect(room).toContainText("24 °C");
  await expect(room).toContainText("Heizkörperthermostat");
  await expect(room).toContainText("Infrarotheizung");
  await expect(room).not.toContainText("climate.bathroom");
  await expect(room).not.toContainText("climate.bathroom_ir");
});

test("uses internal websocket persistence for mode, central and room controls only", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await card.getByRole("button", { name: "Heizbetrieb Aktiv" }).click();
  await expect.poll(() => page.evaluate(() => window.__calls.at(-1))).toMatchObject({ item: { enabled: true } });
  await card.getByRole("button", { name: "Hauptheizung Solltemperatur erhöhen" }).click();
  await expect.poll(() => page.evaluate(() => window.__calls.at(-1))).toMatchObject({ item: { comfort_temperature: 22.5 } });
  await card.locator(".sh-room-card").first().getByRole("button", { name: "Badezimmer Raumziel erhöhen" }).click();
  await expect.poll(() => page.evaluate(() => window.__calls.at(-1))).toMatchObject({ item: { zone_id: "bathroom", comfort_temperature: 23 } });
  expect(await page.evaluate(() => window.__calls.some(call => call.type === "call_service"))).toBe(false);
});

test("navigates from a room card to its matching room route", async ({ page }) => {
  await page.evaluate(() => document.addEventListener("location-changed", event => { window.__route = event.detail.path; }, { once: true }));
  await page.locator(".sh-room-card").first().getByRole("link", { name: /Raumeinstellungen öffnen/ }).click();
  await expect.poll(() => page.evaluate(() => window.__route)).toBe("/smart_heating?room_id=bathroom");
});

test("captures the rendered card and has no horizontal overflow", async ({ page }, testInfo) => {
  // Kiosk navigation is tested in the kiosk project; screenshot baselines are
  // intentionally limited to the reference viewport matrix.
  test.skip(testInfo.project.name === "kiosk", "kiosk has no reference screenshot baseline");
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator(".sh-room-grid")).toBeVisible();
  await expect(card).toHaveScreenshot(`beta60-${testInfo.project.name}.png`, {
    animations: "disabled",
    caret: "hide",
    maxDiffPixels: 2500,
    maxDiffPixelRatio: 0.02,
  });
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});
