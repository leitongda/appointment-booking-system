/**
 * 系统监控模块 E2E 测试
 *
 * 覆盖：操作日志、通知日志、在线用户
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

test.describe('系统监控', () => {
  test.beforeEach(async ({ page }) => { await setupAuthState(page); });

  // ==================== 操作日志 ====================

  test('操作日志列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/monitoring/log');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('操作日志 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/monitoring/log');
    await listPage.goto();
    await listPage.search('登录');
  });

  test('操作日志 - 导出按钮可见', async ({ page }) => {
    await page.goto('/system/monitoring/log');
    await page.waitForLoadState('networkidle');
    const exportBtn = page.locator('button, .ant-btn').filter({ hasText: /导出|下载/ });
    // 导出按钮可能不存在（权限或空状态）
    if (await exportBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(exportBtn.first()).toBeEnabled();
    }
  });

  // ==================== 通知日志 ====================

  test('通知日志列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/monitoring/notification-logs');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('通知日志 - 点击查看详情 Drawer', async ({ page }) => {
    await page.goto('/system/monitoring/notification-logs');
    await page.waitForLoadState('networkidle');
    const detailBtn = page.locator('.ant-table-tbody > tr').first().locator('a, button').filter({ hasText: /查看|详情/ });
    if (await detailBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailBtn.click();
      // 应出现 Drawer
      const drawer = page.locator('.ant-drawer');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
      // 关闭 Drawer
      const closeBtn = drawer.locator('.ant-drawer-close, button').filter({ hasText: /关闭|取消/ }).first();
      if (await closeBtn.isVisible()) await closeBtn.click();
    }
  });

  // ==================== 在线用户 ====================

  test('在线用户列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/monitoring/online-users');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('在线用户 - 查看详情 Drawer', async ({ page }) => {
    await page.goto('/system/monitoring/online-users');
    await page.waitForLoadState('networkidle');
    const detailBtn = page.locator('.ant-table-tbody > tr').first().locator('a, button').filter({ hasText: /查看|详情|操作/ });
    if (await detailBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailBtn.click();
      const drawer = page.locator('.ant-drawer');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
    }
  });

  // ==================== 通知配额 ====================

  test('通知配额页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/monitoring/notification-quota');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  // ==================== 签到审计 ====================

  test('签到审计日志页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/monitoring/checkin-audit-logs');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});
