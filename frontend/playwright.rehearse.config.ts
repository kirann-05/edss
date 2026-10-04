import { defineConfig } from "@playwright/test";

// `make rehearse`: the demo exactly as `make demo` serves it (a production build, the ready-made
// state, the simulated source delay), on its own ports so it never touches a demo that is running.
// The test walks docs/DEMO.md step by step and must finish inside the timeout below.
const API = "http://127.0.0.1:8300";
const WEB = "http://127.0.0.1:3300";

export default defineConfig({
  testDir: "./rehearse",
  workers: 1,
  retries: 0,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: [["list"]],
  use: {
    baseURL: WEB,
    channel: process.env.CI ? undefined : "chrome",
    // a 1280 by 720 projector with the browser at 125 percent zoom
    viewport: { width: 1024, height: 576 },
    deviceScaleFactor: 1.25,
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: "uv run uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8300",
      cwd: "../backend",
      url: `${API}/api/health`,
      reuseExistingServer: false,
      timeout: 60_000,
      env: {
        DATA_MODE: "synthetic",
        LLM_PROVIDER: "fake",
        EDSS_DEMO_LOGIN: "true",
        EDSS_DEMO_STATE: "true",
        SOURCE_LATENCY_MS: "700",
        COOKIE_SECURE: "false",
      },
    },
    {
      command: "pnpm exec next build && pnpm exec next start --hostname 127.0.0.1 --port 3300",
      url: `${WEB}/login`,
      reuseExistingServer: false,
      timeout: 240_000,
      env: { EDSS_API_ORIGIN: API, EDSS_DIST_DIR: ".next-rehearse" },
    },
  ],
});
