// Browser tests for the HTML screen specification (order_design.html).
// Run from the repository root:
//   npx playwright test -c article-01/demo/playwright.config.mjs
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests',
  outputDir: './.test-results',
  reporter: [['list']],
  fullyParallel: true,
  use: { ...devices['Desktop Chrome'], viewport: { width: 1280, height: 900 } },
});
