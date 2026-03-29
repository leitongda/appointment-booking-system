import { test, expect } from '@playwright/test';

test.describe('Admin 端 - 登录页面', () => {
  test('应正确加载登录页面', async ({ page }) => {
    await page.goto('/login');

    // 验证页面标题包含关键词
    const title = page.locator('h1');
    await expect(title).toBeVisible({ timeout: 10_000 });

    // 验证登录 Tab 可见（微信登录、手机号登录、账号登录）
    const tabs = page.locator('.ant-tabs-tab');
    await expect(tabs).toHaveCount(3, { timeout: 5_000 });

    // 验证页面 URL 包含 /login
    await expect(page).toHaveURL(/\/login/);
  });

  test('登录页面应包含登录表单', async ({ page }) => {
    await page.goto('/login');

    // 等待页面加载完成
    await page.waitForSelector('.ant-tabs', { timeout: 10_000 });

    // 验证存在 Tab 内容区域
    const tabPane = page.locator('.ant-tabs-tabpane-active');
    await expect(tabPane).toBeVisible();
  });
});
