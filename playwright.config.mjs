import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: ".",
  workers: 1,
  retries: 0,
  timeout: 30_000,
  expect: { timeout: 8_000 },
  reporter: "line",
  use: {
    browserName: "chromium",
    hasTouch: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
  },
});
