/**
 * 科室管理模块 E2E 测试
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

const BASE = '/organization/department/list';
let factory: TestDataFactory;
let storeId: string;

test.describe('科室管理', () => {
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const loginResult = await setupAuthState(page);
    factory = new TestDataFactory(loginResult.accessToken);
    const store = await factory.createStore({ name: 'E2E科室测试门店' });
    storeId = store.id;
    await factory.createDepartment(storeId, { name: 'E2E内科' });
    await factory.createDepartment(storeId, { name: 'E2E外科' });
    await context.close();
  });

  test.afterAll(async () => { await factory?.cleanup(); });
  test.beforeEach(async ({ page }) => { await setupAuthState(page); });

  test('列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('搜索科室', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.search('E2E');
    await listPage.expectRowContainsText('E2E');
  });

  test('点击新建应跳转到创建页', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/\/department\/create/);
  });

  test('创建页 - 必填字段验证', async ({ page }) => {
    const formPage = new FormPageBase(page, '/organization/department');
    await formPage.gotoCreate();
    await formPage.submit();
    await formPage.expectFieldError('名称');
  });

  test('创建页 - 完整填写并提交', async ({ page }) => {
    const formPage = new FormPageBase(page, '/organization/department');
    await formPage.gotoCreate();
    await formPage.fillInput('名称', 'E2E新建科室');
    await formPage.submitAndWaitNavigation('/department');
  });

  test('编辑页应加载已有数据', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    await page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: '编辑' }).click();
    await page.waitForLoadState('networkidle');
    const nameInput = page.locator('input').first();
    expect((await nameInput.inputValue()).length).toBeGreaterThan(0);
  });

  test('删除操作应弹出确认框', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.clickFirstRowAction('删除');
    const confirm = page.locator('.ant-modal-confirm, .ant-popconfirm');
    await expect(confirm.first()).toBeVisible({ timeout: 5_000 });
    const cancelBtn = confirm.locator('button').filter({ hasText: /取消/ }).first();
    if (await cancelBtn.isVisible()) await cancelBtn.click();
  });
});
