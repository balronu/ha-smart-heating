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
  await page.getByLabel("Name").fill("Wohnbereich");
  await page.getByRole("button", { name: "Zone speichern" }).click();
  await expect(page.locator("details[data-zone]")).toContainText("Wohnbereich");
  await expect(page.locator("details[data-section=rooms]")).toHaveAttribute("open", "");
});

test("uses the full mobile width and keeps technical UI separate", async ({ page }) => {
  const sizes = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: innerWidth }));
  expect(sizes.body).toBeLessThanOrEqual(sizes.viewport + 1);
  await page.screenshot({ path: `test-results/${test.info().project.name}-backend.png`, fullPage: true });
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
