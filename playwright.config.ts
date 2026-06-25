import { defineConfig, devices } from '@playwright/test';

/**
 * E2E 测试配置
 *
 * 测试环境变量：
 * - E2E_ADMIN_URL: Admin 端地址（默认 http://localhost:9105）
 * - E2E_API_BASE_URL: 后端 API 地址（默认 http://localhost:9000）
 * - E2E_REAL_API: 设为 'true' 使用真实后端 API（默认使用 Mock）
 *
 * 使用方式：
 *   pnpm test:e2e                              # 运行所有测试（Mock 模式）
 *   pnpm test:e2e --project admin-core-medical  # 仅运行核心医疗模块
 *   E2E_REAL_API=true pnpm test:e2e             # 真实后端模式
 *   npx playwright test --ui                    # UI 模式调试
 */
const useRealApi = process.env.E2E_REAL_API === 'true';
const adminUrl = process.env.E2E_ADMIN_URL || 'http://127.0.0.1:8005';

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
    baseURL: adminUrl,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
  },
  projects: [
    // ===== 原有 Mock 测试 =====
    {
      name: 'admin',
      use: { ...devices['Desktop Chrome'] },
      testMatch: useRealApi ? [] : undefined, // 真实 API 模式下跳过根目录的旧测试
    },
    // ===== 真实后端模块化测试 =====
    {
      name: 'admin-core-medical',
      use: { ...devices['Desktop Chrome'] },
      testDir: './apps/admin/e2e/core-medical',
    },
    {
      name: 'admin-org-config',
      use: { ...devices['Desktop Chrome'] },
      testDir: './apps/admin/e2e/org-config',
    },
    {
      name: 'admin-platform',
      use: { ...devices['Desktop Chrome'] },
      testDir: './apps/admin/e2e/platform',
    },
    {
      name: 'admin-operations',
      use: { ...devices['Desktop Chrome'] },
      testDir: './apps/admin/e2e/operations',
    },
    {
      name: 'admin-system',
      use: { ...devices['Desktop Chrome'] },
      testDir: './apps/admin/e2e/system',
    },
  ],
  webServer: useRealApi
    ? undefined // 真实 API 模式下不启动 dev server（需要独立启动）
    : {
        command: 'pnpm dev:admin',
        url: 'http://127.0.0.1:8005',
        reuseExistingServer: !process.env.CI,
        timeout: 120_000,
      },
});
