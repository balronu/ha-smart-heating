import { expect, test } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  await expect(page.locator("smart-heating-card").first().locator(".sh-app")).toBeVisible();
  await page.evaluate(() => { const card = document.querySelector("smart-heating-card"); card.hass = window.hass; });
  await page.evaluate(() => { const original = window.hass.callWS; window.hass.callWS = async message => { if (message.type === "smart_heating/admin/internal/set") { window.__calls.push(structuredClone(message)); return { internal: { enabled: message.item.enabled ?? true, operating_mode: message.item.operating_mode || "automatic", zones: { [message.item.zone_id || "bathroom"]: { comfort_temperature: message.item.comfort_temperature || 21.5 } } } }; } return original(message); }; });
});

test("renders only controls, central heating and rooms", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator("h2")).toHaveText(["Heizungssteuerung", "Hauptheizung", "Räume"]);
  await expect(card.locator(".sh-room")).toContainText("Badezimmer");
  await expect(card.locator("section")).toHaveCount(3);
});

test("keeps room target and heating sources separate", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await expect(card.locator(".sh-room-facts")).toContainText("Raumziel");
  await expect(card.locator(".sh-room")).toContainText("Heizkörperthermostat");
  await expect(card.locator(".sh-room")).toContainText("Infrarotheizung");
});

test("uses internal websocket persistence for controls and targets", async ({ page }) => {
  const card = page.locator("smart-heating-card").first();
  await card.getByRole("button", { name: "Dauerhaft Komfort" }).click();
  await expect.poll(() => page.evaluate(() => window.__calls.filter(call => call.type.includes("admin/internal/set")).at(-1))).toMatchObject({ item: { enabled: true, operating_mode: "manual_heat" } });
  await card.getByRole("button", { name: "Raumziel erhöhen" }).click();
  await expect.poll(() => page.evaluate(() => window.__calls.filter(call => call.type.includes("admin/internal/set")).at(-1))).toMatchObject({ item: { zone_id: "bathroom" } });
  expect(await page.evaluate(() => window.__calls.filter(call => call.type.includes("admin/internal/set")).at(-1).item.comfort_temperature)).toBeGreaterThan(20);
  expect(await page.evaluate(() => window.__calls.some(call => call.type === "call_service"))).toBe(false);
});

test("offers explicit off state without climate service calls", async ({ page }) => {
  await page.locator("smart-heating-card").first().getByRole("button", { name: "Aus" }).click();
  await expect.poll(() => page.evaluate(() => window.__calls.filter(call => call.type.includes("admin/internal/set")).at(-1))).toMatchObject({ item: { enabled: false, operating_mode: "off" } });
});

test("does not overflow on narrow responsive cards", async ({ page }) => {
  expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
});
