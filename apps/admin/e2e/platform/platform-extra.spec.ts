/**
 * 平台管理扩展 E2E 测试
 *
 * 覆盖：平台公告、小程序平台（企业/实例/模板/构建/发布）
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

// ==================== 平台公告 ====================

test.describe('平台公告', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page, 'SUPER_ADMIN');
  });

  test('平台公告列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/announcement/list');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('平台公告 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/announcement/list');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/announcement.*create/);
  });
});

// ==================== 小程序平台 ====================

test.describe('小程序平台', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page, 'SUPER_ADMIN');
  });

  test('企业列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/miniapp-platform/company');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('支付配置列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/miniapp-platform/payment-profile');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('小程序实例列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/miniapp-platform/instance');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('模板管理列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/miniapp-platform/template');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('构建管理列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/miniapp-platform/build');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('发布管理列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/platform/miniapp-platform/release');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});

// ==================== 运营看板 ====================

test.describe('运营看板', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page, 'SUPER_ADMIN');
  });

  test('运营看板页应正确加载', async ({ page }) => {
    await page.goto('/platform/operations-dashboard');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/operations-dashboard/);
  });
});
