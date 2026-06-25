/**
 * 运营中心扩展 E2E 测试
 *
 * 覆盖：工单支持、兼职管理、积分管理、数据统计
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

// ==================== 工单支持 ====================

test.describe('工单支持', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('工单列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/support');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('工单 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/support');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('工单 - 回复弹窗', async ({ page }) => {
    await page.goto('/content-center/support');
    await page.waitForLoadState('networkidle');
    const replyBtn = page.locator('.ant-table-tbody > tr').first().locator('button, a').filter({ hasText: /回复/ });
    if (await replyBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await replyBtn.click();
      const modal = page.locator('.ant-modal:visible');
      await expect(modal.first()).toBeVisible({ timeout: 5_000 });
      const cancelBtn = modal.locator('button').filter({ hasText: /取消/ }).first();
      if (await cancelBtn.isVisible()) await cancelBtn.click();
    }
  });
});

// ==================== 兼职管理 ====================

test.describe('兼职管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('兼职人员列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/freelance/freelancers');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('兼职任务列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/freelance/tasks');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('兼职结算列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/freelance/settlements');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('兼职统计页应正确加载', async ({ page }) => {
    await page.goto('/content-center/freelance/statistics');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/statistics/);
  });
});

// ==================== 积分管理 ====================

test.describe('积分管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('积分管理页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/points');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});

// ==================== 数据统计 ====================

test.describe('数据统计', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('数据统计页应正确加载', async ({ page }) => {
    await page.goto('/content-center/statistics');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/statistics/);
  });

  test('数据统计应显示图表', async ({ page }) => {
    await page.goto('/content-center/statistics');
    await page.waitForLoadState('networkidle');
    // 应有图表或统计卡片
    const charts = page.locator('.ant-card, canvas, svg, [class*="chart"]');
    await expect(charts.first()).toBeVisible({ timeout: 10_000 });
  });
});
