import { defineConfig, devices } from "@playwright/test";

// Two ways to run the end-to-end tests:
//   pnpm test:e2e                    on the mocks (starts its own dev server on :3100)
//   E2E_REAL=1 pnpm test:e2e         against a running `pnpm dev` (:3000) and API (:8000) with the demo cache recorded
const real = process.env.E2E_REAL === "1";
const port = real ? 3000 : 3100;

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"]],
  use: { baseURL: `http://localhost:${port}`, viewport: { width: 1366, height: 768 }, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1366, height: 768 } } }],
  webServer: real
    ? undefined
    : {
        command: `pnpm exec next dev --port ${port}`,
        url: `http://localhost:${port}`,
        reuseExistingServer: true,
        timeout: 180_000,
        env: { NEXT_PUBLIC_USE_MOCKS: "1", NEXT_DIST_DIR: ".next-e2e" },
      },
});
