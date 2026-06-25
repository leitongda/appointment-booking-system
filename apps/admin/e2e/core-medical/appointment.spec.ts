/**
 * 预约管理模块 E2E 测试
 *
 * 覆盖：列表（搜索/筛选/分页）、详情、取消预约、签到队列、候补队列
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

const BASE = '/medical-services/appointment/list';
let factory: TestDataFactory;

test.describe('预约管理', () => {
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

  test('列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.waitForTableReady();
    await expect(page).toHaveURL(/appointment/);
  });

  test('搜索预约 - 按患者名', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.search('张', '患者');
  });

  test('搜索无结果应显示空状态', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.search('不存在的患者XYZ');
    await listPage.expectTableEmpty();
  });

  test('重置搜索应恢复列表', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.search('不存在的患者');
    await listPage.resetSearch();
    await listPage.waitForTableReady();
  });

  test('点击详情应跳转到详情页', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    const detailLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: /查看|详情/ });
    if (await detailLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailLink.click();
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/\/appointment\/[^/]+$/);
    }
  });

  test('取消预约 - 弹窗流程', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    const cancelBtn = page.locator('.ant-table-tbody > tr').first().locator('button, a').filter({ hasText: /取消/ });
    if (await cancelBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await cancelBtn.click();
      // 验证弹窗出现
      const modal = page.locator('.ant-modal');
      await expect(modal.first()).toBeVisible({ timeout: 5_000 });
      // 取消操作
      const closeBtn = modal.locator('button').filter({ hasText: /取消|关闭/ }).first();
      if (await closeBtn.isVisible()) await closeBtn.click();
    }
  });

  test('签到队列页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/queue/);
  });

  test('候补队列页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/appointment/waitlist');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/waitlist/);
  });

  test('预约统计页应正确加载', async ({ page }) => {
    await page.goto('/medical-services/appointment/statistics');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/statistics/);
  });
});
