import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./tests/e2e",
  // Serial, generous timeouts: against a dev server, Turbopack JIT-compiles
  // each route (and its dependency graph — next-auth, snowflake-sdk, etc.)
  // on first hit, which can take several seconds and made default timeouts
  // flaky for the first client-side navigation in a run.
  fullyParallel: false,
  workers: 1,
  expect: {
    timeout: 15_000,
  },
  use: {
    baseURL: "http://localhost:3000",
  },
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
