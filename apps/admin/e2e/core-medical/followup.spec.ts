/**
 * 随访管理模块 E2E 测试
 *
 * 覆盖：随访计划、随访任务、随访记录、随访统计
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

test.describe('随访管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('随访计划列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/follow-up/plans');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('随访计划 - 点击新建应弹出 Modal 或跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/follow-up/plans');
    await listPage.goto();
    await listPage.clickCreate();
    // 可能是 Modal 或跳转到创建页
    const modal = page.locator('.ant-modal:visible');
    const urlChanged = await Promise.race([
      modal.waitFor({ timeout: 5_000 }).then(() => 'modal'),
      page.waitForURL(/create|form/, { timeout: 5_000 }).then(() => 'nav'),
    ]).catch(() => 'none');
    expect(['modal', 'nav']).toContain(urlChanged);
  });

  test('随访任务列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/follow-up/tasks');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('随访任务 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/follow-up/tasks');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('随访记录列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/follow-up/records');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('随访记录 - 点击查看详情 Drawer', async ({ page }) => {
    await page.goto('/medical-services/follow-up/records');
    await page.waitForLoadState('networkidle');
    const detailBtn = page.locator('.ant-table-tbody > tr').first().locator('a, button').filter({ hasText: /查看|详情/ });
    if (await detailBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailBtn.click();
      const drawer = page.locator('.ant-drawer:visible');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test('随访统计页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/follow-up/statistics');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/statistics/);
  });
});
