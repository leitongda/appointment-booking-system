/**
 * 财务中心 E2E 测试
 *
 * 覆盖：支付查询、退款管理
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

test.describe('财务中心', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('支付查询列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/finance/payment');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('支付查询 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/finance/payment');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('退款管理列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/finance/refund');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('退款管理 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/finance/refund');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('退款管理 - 点击查看详情 Drawer', async ({ page }) => {
    await page.goto('/finance/refund');
    await page.waitForLoadState('networkidle');
    const detailBtn = page.locator('.ant-table-tbody > tr').first().locator('a, button').filter({ hasText: /查看|详情/ });
    if (await detailBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailBtn.click();
      const drawer = page.locator('.ant-drawer:visible');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
