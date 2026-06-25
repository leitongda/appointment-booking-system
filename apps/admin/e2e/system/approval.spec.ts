/**
 * 审批中心 E2E 测试
 *
 * 覆盖：审批实例（待办/已办/我发起）、审批详情、流程定义、流程设计器
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

test.describe('审批中心', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  // ==================== 审批实例 ====================

  test('审批实例列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/approval/instances');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('审批实例 - Tab 切换（待办/已办/我发起）', async ({ page }) => {
    await page.goto('/approval/instances');
    await page.waitForLoadState('networkidle');
    const tabs = page.locator('.ant-tabs-tab');
    const tabCount = await tabs.count();
    // 应有多个 Tab
    if (tabCount > 1) {
      await tabs.nth(1).click();
      await page.waitForTimeout(1000);
      await tabs.nth(0).click();
    }
  });

  test('审批实例 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/approval/instances');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('审批详情页应正确加载', async ({ page }) => {
    await page.goto('/approval/instances');
    await page.waitForLoadState('networkidle');
    const detailLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: /查看|详情/ });
    if (await detailLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailLink.click();
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/\/approval\/instances\/[^/]+$/);
    }
  });

  test('审批操作 - 点击审批按钮弹出 Modal', async ({ page }) => {
    await page.goto('/approval/instances');
    await page.waitForLoadState('networkidle');
    const approveBtn = page.locator('button, a').filter({ hasText: /审批|同意|通过/ }).first();
    if (await approveBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await approveBtn.click();
      const modal = page.locator('.ant-modal:visible');
      await expect(modal.first()).toBeVisible({ timeout: 5_000 });
      // 取消
      const cancelBtn = modal.locator('button').filter({ hasText: /取消/ }).first();
      if (await cancelBtn.isVisible()) await cancelBtn.click();
    }
  });

  // ==================== 流程定义 ====================

  test('流程定义列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/approval/definitions');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('流程定义 - 新建按钮可见', async ({ page }) => {
    const listPage = new ListPageBase(page, '/approval/definitions');
    await listPage.goto();
    const createBtn = page.locator('button').filter({ hasText: /新建|添加|创建/ });
    await expect(createBtn.first()).toBeVisible({ timeout: 5_000 });
  });

  test('流程设计器页应正确加载', async ({ page }) => {
    // 先获取一个流程定义 ID
    await page.goto('/approval/definitions');
    await page.waitForLoadState('networkidle');
    const editLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: /编辑|设计/ });
    if (await editLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await editLink.click();
      await page.waitForLoadState('networkidle');
      // 流程设计器应有画布
      const canvas = page.locator('.react-flow, .xy-flow, [class*="flow"], [class*="canvas"]');
      await expect(canvas.first()).toBeVisible({ timeout: 10_000 });
    }
  });
});
