import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./tests",
  timeout: 15_000,
  fullyParallel: true,
  reporter: [["list"], ["html", { outputFolder: "playwright-report", open: "never" }]],
  use: { baseURL: "http://127.0.0.1:4173", screenshot: "only-on-failure", trace: "retain-on-failure" },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"], colorScheme: "light" } },
    { name: "iphone", use: { viewport: { width: 390, height: 844 }, hasTouch: true, isMobile: true, deviceScaleFactor: 3, colorScheme: "light" } },
    { name: "ipad", use: { ...devices["iPad (gen 9)"], colorScheme: "dark" } },
    { name: "touch-monitor", use: { viewport: { width: 800, height: 600 }, hasTouch: true, colorScheme: "dark" } },
  ],
  webServer: { command: "python3 -m http.server 4173 --directory ..", cwd: ".", url: "http://127.0.0.1:4173/frontend/fixtures/harness.html", reuseExistingServer: false, timeout: 10_000 },
});
