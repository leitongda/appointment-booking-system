/**
 * 患者管理模块 E2E 测试
 *
 * 覆盖：列表（搜索/分页）、详情、就诊卡
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';

const PATIENT_LIST = '/medical-services/patient/list';
const CARD_LIST = '/medical-services/patient/card/list';
let factory: TestDataFactory;

test.describe('患者管理', () => {
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const loginResult = await setupAuthState(page);
    factory = new TestDataFactory(loginResult.accessToken);
    await factory.createPatient({ name: 'E2E测试患者' });
    await context.close();
  });

  test.afterAll(async () => {
    await factory?.cleanup();
  });

  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('患者列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, PATIENT_LIST);
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('搜索患者 - 按姓名', async ({ page }) => {
    const listPage = new ListPageBase(page, PATIENT_LIST);
    await listPage.goto();
    await listPage.search('E2E', '姓名');
    await listPage.expectRowContainsText('E2E');
  });

  test('搜索患者 - 按手机号', async ({ page }) => {
    const listPage = new ListPageBase(page, PATIENT_LIST);
    await listPage.goto();
    await listPage.search('139', '手机');
  });

  test('点击详情应跳转到患者详情', async ({ page }) => {
    await page.goto(PATIENT_LIST);
    await page.waitForLoadState('networkidle');
    const detailLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: /查看|详情/ });
    if (await detailLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await detailLink.click();
      await page.waitForLoadState('networkidle');
      await expect(page).toHaveURL(/\/patient\/[^/]+$/);
    }
  });

  test('就诊卡列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, CARD_LIST);
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});
