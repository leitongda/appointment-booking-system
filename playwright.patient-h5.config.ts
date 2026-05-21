import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './apps/patient-h5/e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  reporter: [
    ['html', { outputFolder: 'e2e-report-patient-h5' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.E2E_PATIENT_H5_URL || 'http://127.0.0.1:9102',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    // Mobile viewport for H5
    viewport: { width: 375, height: 812 },
    userAgent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15',
  },
  projects: [
    {
      name: 'patient-h5',
      use: {
        ...devices['iPhone 13'],
      },
    },
  ],
  webServer: {
    command: 'pnpm dev:patient-h5',
    url: 'http://127.0.0.1:9102',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
