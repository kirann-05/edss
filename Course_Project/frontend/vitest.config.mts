import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// West of UTC, where reading a date-only string as UTC would show the day before. Pinned so that
// mistake fails here on any machine, not only on one in the Americas.
process.env.TZ = "America/Los_Angeles";

export default defineConfig({
  plugins: [react()],
  resolve: { tsconfigPaths: true },
  test: {
    environment: "jsdom",
    setupFiles: ["./vitest.setup.ts"],
    include: ["src/**/*.test.{ts,tsx}"],
    css: false,
  },
});
