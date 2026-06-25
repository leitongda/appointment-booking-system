/**
 * 系统分析扩展 E2E 测试
 *
 * 覆盖：热力图、会话回放
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

// ==================== 热力图 ====================

test.describe('热力图', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('热力图页应正确加载', async ({ page }) => {
    await page.goto('/heatmap');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/heatmap/);
  });

  test('热力图应有筛选控件', async ({ page }) => {
    await page.goto('/heatmap');
    await page.waitForLoadState('networkidle');
    // 应有页面选择、事件类型等筛选器
    const filters = page.locator('.ant-select, .ant-picker, .ant-radio-group');
    await expect(filters.first()).toBeVisible({ timeout: 5_000 });
  });

  test('热力图应有画布区域', async ({ page }) => {
    await page.goto('/heatmap');
    await page.waitForLoadState('networkidle');
    // 热力图画布或容器
    const canvas = page.locator('canvas, .heatmap-container, [class*="heatmap"]');
    await expect(canvas.first()).toBeVisible({ timeout: 10_000 });
  });
});

// ==================== 会话回放 ====================

test.describe('会话回放', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('会话回放列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/session-replay/list');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('会话回放 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/session-replay/list');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('会话回放 - 点击进入回放页', async ({ page }) => {
    await page.goto('/session-replay/list');
    await page.waitForLoadState('networkidle');
    const replayLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: /查看|回放|播放/ });
    if (await replayLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await replayLink.click();
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/session-replay\/[^/]+$/);
    }
  });
});
