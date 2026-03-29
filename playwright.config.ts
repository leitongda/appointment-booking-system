import { defineConfig, devices } from '@playwright/test';

/**
 * E2E 测试配置
 *
 * 测试环境变量：
 * - E2E_ADMIN_URL: Admin 端地址（默认 http://localhost:8005）
 * - E2E_API_BASE_URL: 后端 API 地址（默认 http://localhost:8000）
 */
export default defineConfig({
  testDir: './apps/admin/e2e',
  testMatch: '**/*.spec.ts',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  timeout: 30_000,
  reporter: [
    ['html', { outputFolder: 'e2e-report' }],
    ['list'],
  ],
  use: {
    baseURL: process.env.E2E_ADMIN_URL || 'http://127.0.0.1:8005',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: 'admin',
      use: {
        ...devices['Desktop Chrome'],
      },
    },
  ],
  webServer: {
    command: 'pnpm dev:admin',
    url: 'http://127.0.0.1:8005',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
