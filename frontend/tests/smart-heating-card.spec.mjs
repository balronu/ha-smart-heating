import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  await expect(page.getByTestId("status")).toContainText("compatibility");
  await expect(page.getByTestId("observed")).toContainText("unbekannt");
  await expect(page.getByTestId("version")).toContainText("0.1.0-beta.11");
  await expect(page.getByTestId("backend-management")).toContainText("Backend-Verwaltung");
  await expect(page.getByText("Räume & Klimazonen", { exact: true })).toBeVisible();
  await expect(page.locator("details[open]")).toHaveCount(0);
});

test("renders all days and edits a window through the visible card", async ({ page }, testInfo) => {
  await expect(page.locator("section[data-day]")).toHaveCount(7);
  const monday = page.locator("section[data-day=monday]");
  await monday.locator("input[data-part=start]").fill("06:00");
  await expect(monday.locator("input[data-part=start]")).toHaveValue("06:00");
  await monday.getByRole("button", { name: "+ Zeit" }).click();
  await expect(page.locator("section[data-day=monday] input[data-part=start]")).toHaveCount(2);
  await page.locator("section[data-day=monday] button[data-remove]").nth(1).click();
  await expect(monday.locator("input[data-part=start]")).toHaveCount(1);
  await page.screenshot({ path: `test-results/${testInfo.project.name}-card.png`, fullPage: true });
});

test("copies a day and exposes special modes without writing them", async ({ page }) => {
  const monday = page.locator("section[data-day=monday]");
  await monday.locator("select[data-copy-target]").selectOption("tuesday");
  await monday.getByRole("button", { name: "Tag kopieren" }).click();
  await expect(page.locator("section[data-day=tuesday] input[data-part=start]")).toHaveCount(1);
  await expect(page.locator(".special[data-special=chimney_sweep]")).toBeDisabled();
  await expect(page.locator(".hint").last()).toContainText("Kompatibilität");
});

test("shows a rendered error and remains usable", async ({ page }) => {
  const start = page.locator("section[data-day=monday] input[data-part=start]");
  await start.fill("22:00");
  await expect(page.getByTestId("error")).toContainText("Ungültiger");
  await expect(page.locator("section[data-day=monday]")).toBeVisible();
});

test("manages a zone and selects a native person through the rendered card", async ({ page }) => {
  await page.getByText("Räume & Klimazonen", { exact: true }).click();
  await page.getByLabel("Name der Zone").fill("Wohnbereich");
  await page.getByLabel("Thermostate").fill("climate.wohnzimmer");
  await page.getByRole("button", { name: "Zone hinzufügen" }).click();
  await expect(page.locator(".management-list").first()).toContainText("Wohnbereich");
  await page.getByText("Personen & Anwesenheit", { exact: true }).click();
  await page.getByRole("button", { name: "berücksichtigen" }).click();
});
