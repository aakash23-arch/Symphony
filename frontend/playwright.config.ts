import { defineConfig, devices } from '@playwright/test';

/**
 * Browser verification for the dashboard.
 *
 * The dev server is started here, but the BACKEND is not: it loads real model
 * weights and takes ~20 s, so it is started once alongside the suite rather
 * than per run. Tests that need live analysis skip themselves if it is absent,
 * so the honesty checks (empty, awaiting, null rendering) still run everywhere.
 */
export default defineConfig({
  testDir: './e2e',
  outputDir: './e2e/artifacts/test-results',
  timeout: 120_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  workers: 1,
  reporter: [
    ['html', { outputFolder: './e2e/artifacts/report', open: 'never' }],
    ['list'],
  ],
  use: {
    baseURL: 'http://127.0.0.1:5173',
    trace: 'retain-on-failure',
    video: 'retain-on-failure',
    screenshot: 'only-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'npx vite --port 5173 --strictPort',
    url: 'http://127.0.0.1:5173',
    reuseExistingServer: true,
    timeout: 60_000,
  },
});
