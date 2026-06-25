/**
 * 病历管理 & 检查报告 E2E 测试
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

test.describe('病历管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('病历列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/medical-record');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('病历 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/medical-record');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('病历 - 点击查看详情 Drawer', async ({ page }) => {
    await page.goto('/medical-services/medical-record');
    await page.waitForLoadState('networkidle');
    const detailBtn = page.locator('.ant-table-tbody > tr').first().locator('a, button').filter({ hasText: /查看|详情/ });
    if (await detailBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailBtn.click();
      const drawer = page.locator('.ant-drawer:visible');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
    }
  });
});

test.describe('检查报告', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('检查报告列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/examination-report');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('检查报告 - 点击查看详情 Drawer', async ({ page }) => {
    await page.goto('/medical-services/examination-report');
    await page.waitForLoadState('networkidle');
    const detailBtn = page.locator('.ant-table-tbody > tr').first().locator('a, button').filter({ hasText: /查看|详情/ });
    if (await detailBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailBtn.click();
      const drawer = page.locator('.ant-drawer:visible');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
