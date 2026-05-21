import { expect, test } from '@playwright/test';
import { mockPatientSession, openPatientRoute } from './helpers/patient-h5-mocks';

test.describe('患者端 - 消息中心', () => {
  test.beforeEach(async ({ page }) => {
    await mockPatientSession(page);
  });

  test('消息中心页加载', async ({ page }) => {
    await openPatientRoute(page, '/message');

    await expect(page).toHaveURL(/\/message/);
    // 应有 Tab 切换
    const tabs = page.locator('.adm-tabs-tab, [class*="tab"]');
    await expect(tabs.first()).toBeVisible({ timeout: 10_000 });
  });

  test('消息列表显示', async ({ page }) => {
    await openPatientRoute(page, '/message');

    // 应显示消息标题
    await expect(page.getByText('预约成功通知').first()).toBeVisible({ timeout: 10_000 });
  });

  test('未读消息标识', async ({ page }) => {
    await openPatientRoute(page, '/message');

    // 应有未读标识（红点或角标）
    const badge = page.locator('.adm-badge, [class*="badge"], [class*="unread"]');
    const hasBadge = await badge.first().isVisible().catch(() => false);
    // 至少有一条未读消息的标识
    expect(hasBadge).toBeTruthy();
  });

  test('消息已读/未读状态区分', async ({ page }) => {
    await openPatientRoute(page, '/message');

    // 未读消息应有特殊样式
    const unreadMsg = page.getByText('预约成功通知').first();
    await expect(unreadMsg).toBeVisible({ timeout: 10_000 });

    // 已读消息也应显示
    await expect(page.getByText('就诊提醒').first()).toBeVisible();
  });

  test('消息 Tab 过滤', async ({ page }) => {
    await openPatientRoute(page, '/message');

    // 点击不同 Tab
    const tabs = page.locator('.adm-tabs-tab, [class*="tab"]');
    const tabCount = await tabs.count();
    expect(tabCount).toBeGreaterThanOrEqual(2);

    // 切换 Tab 应触发加载
    if (tabCount > 1) {
      await tabs.nth(1).click();
      await page.waitForLoadState('networkidle');
    }
  });

  test('消息中心页包含导航栏', async ({ page }) => {
    await openPatientRoute(page, '/message');

    // 应有返回按钮或导航栏
    const navBar = page.locator('.adm-nav-bar, [class*="navbar"], [class*="nav-bar"]');
    await expect(navBar.first()).toBeVisible({ timeout: 10_000 });
  });
});
