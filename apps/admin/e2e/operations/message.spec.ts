/**
 * 消息管理模块 E2E 测试
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

const BASE = '/content-center/message/list';

test.describe('消息管理', () => {
  test.beforeEach(async ({ page }) => { await setupAuthState(page); });

  test('列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('搜索消息', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.search('测试');
  });

  test('点击新建应跳转到发送页', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/\/message\/create/);
  });

  test('发送消息页应正确加载', async ({ page }) => {
    const formPage = new FormPageBase(page, '/content-center/message');
    await formPage.gotoCreate();
    await formPage.waitForFormReady();
  });

  test('删除消息应弹出确认框', async ({ page }) => {
    const listPage = new ListPageBase(page, BASE);
    await listPage.goto();
    await listPage.clickFirstRowAction('删除');
    const confirm = page.locator('.ant-modal-confirm, .ant-popconfirm');
    await expect(confirm.first()).toBeVisible({ timeout: 5_000 });
    const cancelBtn = confirm.locator('button').filter({ hasText: /取消/ }).first();
    if (await cancelBtn.isVisible()) await cancelBtn.click();
  });

  test('消息模板页应正确加载', async ({ page }) => {
    await page.goto('/content-center/message/templates');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/templates/);
  });

  test('接收人规则页应正确加载', async ({ page }) => {
    await page.goto('/content-center/message/recipient-rules');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/recipient-rules/);
  });
});
