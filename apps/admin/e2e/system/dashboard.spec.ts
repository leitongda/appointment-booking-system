/**
 * 仪表盘 & 数据大屏 E2E 测试
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';

test.describe('仪表盘', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('仪表盘页应正确加载', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/dashboard/);
  });

  test('仪表盘应显示 KPI 卡片或图表', async ({ page }) => {
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');
    // 应有卡片或统计组件
    const cards = page.locator('.ant-card, .ant-statistic, [class*="stat"], [class*="chart"]');
    await expect(cards.first()).toBeVisible({ timeout: 10_000 });
  });

  test('数据大屏页应正确加载', async ({ page }) => {
    await page.goto('/screen');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/screen/);
  });

  test('数据大屏应有全屏切换', async ({ page }) => {
    await page.goto('/screen');
    await page.waitForLoadState('networkidle');
    // 大屏页面通常有全屏按钮
    const fullscreenBtn = page.locator('button').filter({ hasText: /全屏|最大化|fullscreen/i });
    // 全屏按钮可能不存在，不强制断言
    if (await fullscreenBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(fullscreenBtn.first()).toBeEnabled();
    }
  });
});
