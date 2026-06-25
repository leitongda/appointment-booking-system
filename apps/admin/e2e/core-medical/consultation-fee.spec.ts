/**
 * 诊费管理 E2E 测试
 *
 * 覆盖：诊费类型、诊费模板
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

const FEE_TYPE_LIST = '/medical-services/consultation-fee/types';
const FEE_TEMPLATE_LIST = '/medical-services/consultation-fee/templates';
let factory: TestDataFactory;

test.describe('诊费管理', () => {
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const loginResult = await setupAuthState(page);
    factory = new TestDataFactory(loginResult.accessToken);
    await factory.createFeeType({ name: 'E2E诊费类型' });
    await context.close();
  });

  test.afterAll(async () => {
    await factory?.cleanup();
  });

  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('诊费类型列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, FEE_TYPE_LIST);
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('诊费类型 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, FEE_TYPE_LIST);
    await listPage.goto();
    await listPage.search('E2E');
    await listPage.expectRowContainsText('E2E');
  });

  test('诊费类型 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, FEE_TYPE_LIST);
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/consultation-fee.*create/);
  });

  test('诊费类型创建页 - 必填字段验证', async ({ page }) => {
    const formPage = new FormPageBase(page, '/medical-services/consultation-fee/types');
    await formPage.gotoCreate();
    await formPage.submit();
    await formPage.expectFieldError('名称');
  });

  test('诊费类型创建页 - 完整填写并提交', async ({ page }) => {
    const formPage = new FormPageBase(page, '/medical-services/consultation-fee/types');
    await formPage.gotoCreate();
    await formPage.fillInput('名称', `E2E新建诊费_${Date.now()}`);
    await formPage.fillInput('编码', `e2e_fee_${Date.now()}`);
    await formPage.submitAndWaitNavigation('/consultation-fee');
  });

  test('诊费类型 - 编辑页加载数据', async ({ page }) => {
    await page.goto(FEE_TYPE_LIST);
    await page.waitForLoadState('networkidle');
    const editLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: '编辑' });
    if (await editLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await editLink.click();
      await page.waitForLoadState('networkidle');
      const nameInput = page.locator('input').first();
      expect((await nameInput.inputValue()).length).toBeGreaterThan(0);
    }
  });

  test('诊费模板列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, FEE_TEMPLATE_LIST);
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});
