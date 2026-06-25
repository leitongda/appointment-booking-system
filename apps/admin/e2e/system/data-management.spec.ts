/**
 * 数据管理 & 系统配置 E2E 测试
 *
 * 覆盖：数据导入导出、数据备份、邮件模板、邮件接收人、黑名单、引导管理
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

test.describe('数据管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('数据导入导出页应正确加载', async ({ page }) => {
    await page.goto('/system/data/import-export');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/import-export/);
  });

  test('数据导入导出 - 文件上传区域可见', async ({ page }) => {
    await page.goto('/system/data/import-export');
    await page.waitForLoadState('networkidle');
    const upload = page.locator('.ant-upload, input[type="file"]');
    await expect(upload.first()).toBeVisible({ timeout: 5_000 });
  });

  test('数据备份页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/data/backup');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});

test.describe('邮件管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('邮件模板列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/config/email-templates');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('邮件模板 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/config/email-templates');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/email-template.*create|create.*email-template/);
  });

  test('邮件接收人列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/config/email-recipients');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});

test.describe('黑名单管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('黑名单管理页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/blacklist');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});

test.describe('引导管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('引导列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/guide-tours');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('引导 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/system/guide-tours');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/guide-tours.*create/);
  });
});
