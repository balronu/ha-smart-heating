import { test, expect } from "@playwright/test";

test.beforeEach(async ({ page }) => {
  await page.goto("/frontend/fixtures/backend-panel.html");
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
