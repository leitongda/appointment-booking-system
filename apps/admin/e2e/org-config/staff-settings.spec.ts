/**
 * 员工管理 & 系统配置 E2E 测试
 *
 * 覆盖：员工管理、预约规则配置、班次类型、规则组、预约须知
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

// ==================== 员工管理 ====================

test.describe('员工管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('员工列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/staff');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('员工 - 搜索', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/staff');
    await listPage.goto();
    await listPage.search('测试');
  });

  test('员工 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/staff');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/staff.*create/);
  });

  test('员工创建页 - 必填字段验证', async ({ page }) => {
    const formPage = new FormPageBase(page, '/organization/staff');
    await formPage.gotoCreate();
    await formPage.submit();
    // 应有验证错误
    const errors = page.locator('.ant-form-item-explain-error');
    await expect(errors.first()).toBeVisible({ timeout: 5_000 });
  });

  test('员工 - 启用/禁用弹窗', async ({ page }) => {
    await page.goto('/organization/staff');
    await page.waitForLoadState('networkidle');
    const toggleBtn = page.locator('.ant-table-tbody > tr').first().locator('.ant-switch, button').filter({ hasText: /启用|禁用/ });
    if (await toggleBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await toggleBtn.click();
      // 可能弹出确认框
      const confirm = page.locator('.ant-modal-confirm:visible, .ant-popover:visible');
      if (await confirm.first().isVisible({ timeout: 2_000 }).catch(() => false)) {
        const cancelBtn = confirm.locator('button').filter({ hasText: /取消/ }).first();
        if (await cancelBtn.isVisible()) await cancelBtn.click();
      }
    }
  });
});

// ==================== 班次类型 ====================

test.describe('班次类型', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('班次类型列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/medical-config/shift-types');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('班次类型 - 点击新建跳转', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/medical-config/shift-types');
    await listPage.goto();
    await listPage.clickCreate();
    await expect(page).toHaveURL(/shift-type.*create/);
  });
});

// ==================== 规则组管理 ====================

test.describe('规则组管理', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('规则组列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/medical-config/rule-sets');
    await listPage.goto();
    await listPage.waitForTableReady();
  });

  test('规则组 - 预览弹窗', async ({ page }) => {
    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');
    const previewBtn = page.locator('.ant-table-tbody > tr').first().locator('button, a').filter({ hasText: /预览/ });
    if (await previewBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await previewBtn.click();
      const modal = page.locator('.ant-modal:visible');
      await expect(modal.first()).toBeVisible({ timeout: 5_000 });
      const closeBtn = modal.locator('.ant-modal-close').first();
      if (await closeBtn.isVisible()) await closeBtn.click();
    }
  });

  test('规则组 - 审计日志 Drawer', async ({ page }) => {
    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');
    const auditBtn = page.locator('.ant-table-tbody > tr').first().locator('button, a').filter({ hasText: /审计|日志|历史/ });
    if (await auditBtn.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await auditBtn.click();
      const drawer = page.locator('.ant-drawer:visible');
      await expect(drawer.first()).toBeVisible({ timeout: 5_000 });
    }
  });
});

// ==================== 预约须知 ====================

test.describe('预约须知', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('预约须知列表页应正确加载', async ({ page }) => {
    const listPage = new ListPageBase(page, '/organization/medical-config/booking-notice');
    await listPage.goto();
    await listPage.waitForTableReady();
  });
});

// ==================== 预约规则配置 ====================

test.describe('预约规则配置', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('预约规则配置页应正确加载', async ({ page }) => {
    await page.goto('/organization/medical-config/booking-rules');
    await page.waitForLoadState('networkidle');
    const form = page.locator('.ant-form, .ant-pro-form, .ant-card');
    await expect(form.first()).toBeVisible({ timeout: 5_000 });
  });

  test('预约字段配置页应正确加载', async ({ page }) => {
    await page.goto('/organization/medical-config/booking-fields');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/booking-fields/);
  });

  test('就诊卡配置页应正确加载', async ({ page }) => {
    await page.goto('/organization/medical-config/patient-card');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/patient-card/);
  });
});
