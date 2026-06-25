/**
 * 排班管理模块 E2E 测试
 *
 * 覆盖：排班规则、排班列表、排班日历、自定义排班、休息日
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

let factory: TestDataFactory;

test.describe('排班管理', () => {
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const loginResult = await setupAuthState(page);
    factory = new TestDataFactory(loginResult.accessToken);
    await context.close();
  });

  test.afterAll(async () => {
    await factory?.cleanup();
  });

  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('排班规则列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/rule');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('排班列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/list');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('排班日历页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/calendar');
    await page.waitForLoadState('networkidle');
    // 日历组件应可见
    const calendar = page.locator('.ant-picker-calendar, .fc, [class*="calendar"]');
    await expect(calendar.first()).toBeVisible({ timeout: 10_000 });
  });

  test('排班日历 - 周/月视图切换', async ({ page }) => {
    await page.goto('/medical-services/schedule/calendar');
    await page.waitForLoadState('networkidle');
    // 尝试切换视图
    const weekBtn = page.locator('button, .ant-radio-button').filter({ hasText: /周/ });
    const monthBtn = page.locator('button, .ant-radio-button').filter({ hasText: /月/ });
    if (await weekBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await weekBtn.click();
      await page.waitForTimeout(1000);
    }
    if (await monthBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await monthBtn.click();
      await page.waitForTimeout(1000);
    }
  });

  test('排班甘特图页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/gantt');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/gantt/);
  });

  test('自定义排班列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/custom');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('休息日列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/rest-day');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('停诊管理页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/suspension');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('停诊审核页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/leave-request');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('额外号源页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/extra-quota');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('诊室管理页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/medical-services/schedule/room');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('排班统计页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/statistics');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/statistics/);
  });
});
