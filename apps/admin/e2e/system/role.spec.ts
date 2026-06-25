/**
 * 角色权限模块 E2E 测试
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

const BASE = '/system/role';
let factory: TestDataFactory;

test.describe('角色权限', () => {
  test.beforeAll(async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();
    const loginResult = await setupAuthState(page);
    factory = new TestDataFactory(loginResult.accessToken);
    await factory.createRole({ name: 'E2E测试角色', code: `E2E_ROLE_${Date.now()}` });
    await context.close();
  });

  test.afterAll(async () => { await factory?.cleanup(); });
  test.beforeEach(async ({ page }) => { await setupAuthState(page); });

  test('列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('点击新建应跳转到创建页', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/\/role\/create/);
  });

  test('创建页 - 必填字段验证', async ({ page }) => {
    const formPage = new FormPageBase(page, '/system/role');
    await formPage.gotoCreate();
    await formPage.submit();
    await formPage.expectFieldError('角色名称');
  });

  test('创建页 - 完整填写并提交', async ({ page }) => {
    const formPage = new FormPageBase(page, '/system/role');
    await formPage.gotoCreate();
    await formPage.fillInput('角色名称', 'E2E新建角色');
    await formPage.fillInput('角色编码', `E2E_NEW_${Date.now()}`);
    await formPage.fillInput('描述', 'E2E 测试角色描述');
    await formPage.submitAndWaitNavigation('/role');
  });

  test('编辑页应加载已有数据', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    const editLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: '编辑' });
    if (await editLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await editLink.click();
      await page.waitForLoadState('networkidle');
      const nameInput = page.locator('input').first();
      expect((await nameInput.inputValue()).length).toBeGreaterThan(0);
    }
  });

  test('权限分配页应正确加载', async ({ page }) => {
    await page.goto(BASE);
    await page.waitForLoadState('networkidle');
    const permLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: /权限/ });
    if (await permLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await permLink.click();
      await page.waitForLoadState('networkidle');
      // 应显示树形权限结构
      const tree = page.locator('.ant-tree, .ant-tree-select');
      await expect(tree.first()).toBeVisible({ timeout: 5_000 });
    }
  });

  test('删除角色应弹出确认框', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.clickFirstRowAction('删除');
    const confirm = page.locator('.ant-modal-confirm, .ant-popconfirm');
    await expect(confirm.first()).toBeVisible({ timeout: 5_000 });
    const cancelBtn = confirm.locator('button').filter({ hasText: /取消/ }).first();
    if (await cancelBtn.isVisible()) await cancelBtn.click();
  });
});
