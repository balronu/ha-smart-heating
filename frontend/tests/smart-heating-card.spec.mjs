import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/harness.html");
  await expect(page.getByTestId("status")).toContainText("compatibility");
  await expect(page.getByTestId("observed")).toContainText("unbekannt");
  await expect(page.getByTestId("version")).toContainText("0.1.0-beta.39");
  await expect(page.locator(".backend-menu")).toHaveCount(0);
  await expect(page.getByText("Räume & Klimazonen", { exact: true })).toHaveCount(0);
});

test("renders all days and edits a window through the operational card", async ({ page }, testInfo) => {
  await expect(page.locator("section[data-day]")).toHaveCount(7);
  const monday = page.locator("section[data-day=monday]");
  await monday.locator("input[data-part=start]").fill("06:00");
  await expect(monday.locator("input[data-part=start]")).toHaveValue("06:00");
  await monday.getByRole("button", { name: "+ Zeit" }).click();
  await expect(monday.locator("input[data-part=start]")).toHaveCount(2);
  await monday.locator("button[data-remove]").nth(1).click();
  await expect(monday.locator("input[data-part=start]")).toHaveCount(1);
  await page.screenshot({ path: `test-results/${testInfo.project.name}-frontend.png`, fullPage: true });
});

test("copies a day and keeps technical administration out of the card", async ({ page }) => {
  const monday = page.locator("section[data-day=monday]");
  await monday.locator("select[data-copy-target]").selectOption("tuesday");
  await monday.getByRole("button", { name: "Tag kopieren" }).click();
  await expect(page.locator("section[data-day=tuesday] input[data-part=start]")).toHaveCount(1);
  await expect(page.locator(".hint").last()).toContainText("Seitenmenü");
});

test("shows a rendered validation error and remains usable", async ({ page }) => {
  await page.locator("section[data-day=monday] input[data-part=start]").fill("22:00");
  await expect(page.getByTestId("error")).toContainText("Ungültiger");
  await expect(page.locator("section[data-day=monday]")).toBeVisible();
});

test("uses the full narrow viewport without horizontal overflow", async ({ page }) => {
  const widths = await page.evaluate(() => ({ body: document.body.scrollWidth, viewport: window.innerWidth }));
  expect(widths.body).toBeLessThanOrEqual(widths.viewport + 1);
});
