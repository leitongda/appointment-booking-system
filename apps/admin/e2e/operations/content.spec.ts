/**
 * 运营中心内容管理 E2E 测试
 *
 * 覆盖：公告管理、轮播图管理、用户反馈、积分管理
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

// ==================== 公告管理 ====================

test.describe('公告管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('公告列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/content/notice');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('公告 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/content/notice');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('公告 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/content/notice');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/notice.*create/);
  });

  test('公告创建页 - 必填字段验证', async ({ page }) => {
    const formPage = new FormPageBase(page, '/content-center/content/notice');
    await formPage.gotoCreate();
    await formPage.submit();
    await formPage.expectFieldError('标题');
  });

  test('公告 - 编辑页加载数据', async ({ page }) => {
    await page.goto('/content-center/content/notice');
    await page.waitForLoadState('networkidle');
    const editLink = page.locator('.ant-table-tbody > tr').first().locator('a').filter({ hasText: '编辑' });
    if (await editLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await editLink.click();
      await page.waitForLoadState('networkidle');
      const titleInput = page.locator('input').first();
      expect((await titleInput.inputValue()).length).toBeGreaterThan(0);
    }
  });
});

// ==================== 轮播图管理 ====================

test.describe('轮播图管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('轮播图列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/content/banner');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('轮播图 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/content/banner');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/banner.*create/);
  });

  test('轮播图创建页 - 表单加载', async ({ page }) => {
    const formPage = new FormPageBase(page, '/content-center/content/banner');
    await formPage.gotoCreate();
    await formPage.waitForFormReady();
  });
});

// ==================== 用户反馈 ====================

test.describe('用户反馈', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('反馈列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/feedback');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('反馈 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/feedback');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('反馈 - 回复操作弹出 Modal', async ({ page }) => {
    await page.goto('/content-center/feedback');
    await page.waitForLoadState('networkidle');
    const replyBtn = page.locator('.ant-table-tbody > tr').first().locator('button, a').filter({ hasText: /回复/ });
    if (await replyBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await replyBtn.click();
      const modal = page.locator('.ant-modal:visible');
      await expect(modal.first()).toBeVisible({ timeout: 5_000 });
      const cancelBtn = modal.locator('button').filter({ hasText: /取消/ }).first();
      if (await cancelBtn.isVisible()) await cancelBtn.click();
    }
  });
});

// ==================== 积分管理 ====================

test.describe('积分管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('积分管理页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/content-center/points');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});
