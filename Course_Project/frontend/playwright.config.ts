import { defineConfig } from "@playwright/test";

// The browser tests start their own backend and web server on spare ports with a fresh in-memory
// state, so they never depend on, or disturb, a dev server that is running. They drive the real
// API and the real pages. Synthetic data only, and a throwaway password that exists only here.
const API = "http://127.0.0.1:8100";
const WEB = "http://127.0.0.1:3100";
export const E2E_PASSWORD = "e2e-only-not-a-secret-12345";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: process.env.CI ? 1 : 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : [["list"]],
  use: {
    baseURL: WEB,
    // locally the Chrome that is already installed, so nothing is downloaded. CI installs Chromium
    channel: process.env.CI ? undefined : "chrome",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8100",
      cwd: "../backend",
      url: `${API}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATA_MODE: "synthetic",
        LLM_PROVIDER: "fake",
        EDSS_DEMO_LOGIN: "true",
        EDSS_SEED_PASSWORD: E2E_PASSWORD,
        SOURCE_LATENCY_MS: "0",
        COOKIE_SECURE: "false",
      },
    },
    {
      command: "pnpm exec next dev --hostname 127.0.0.1 --port 3100",
      url: `${WEB}/login`,
      reuseExistingServer: false,
      timeout: 120_000,
      env: { EDSS_API_ORIGIN: API, EDSS_DIST_DIR: ".next-e2e" },
    },
  ],
});
