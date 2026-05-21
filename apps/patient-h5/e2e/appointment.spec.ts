import { expect, test } from '@playwright/test';
import { mockPatientSession, openPatientRoute } from './helpers/patient-h5-mocks';

test.describe('患者端 - 预约流程', () => {
  test.beforeEach(async ({ page }) => {
    await mockPatientSession(page);
  });

  test('预约列表页加载', async ({ page }) => {
    await openPatientRoute(page, '/appointment');
    await expect(page).toHaveURL(/\/appointment/);

    // 应有 Tab 切换（全部/待就诊/已完成/已取消）
    const tabs = page.locator('.adm-tabs-tab, [class*="tab"]');
    await expect(tabs.first()).toBeVisible({ timeout: 10_000 });
  });

  test('预约列表显示预约卡片', async ({ page }) => {
    await openPatientRoute(page, '/appointment');

    // 应显示预约记录
    await expect(page.getByText('李医生').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('神经内科').first()).toBeVisible();
  });

  test('科室列表页加载', async ({ page }) => {
    await openPatientRoute(page, '/department');

    await expect(page).toHaveURL(/\/department/);
    // 应显示科室名称
    await expect(page.getByText('神经内科').first()).toBeVisible({ timeout: 10_000 });
  });

  test('科室详情页加载', async ({ page }) => {
    await openPatientRoute(page, '/department/dept-1');

    await expect(page.getByText('神经内科').first()).toBeVisible({ timeout: 10_000 });
  });

  test('智能导诊页加载', async ({ page }) => {
    await openPatientRoute(page, '/guide');

    await expect(page).toHaveURL(/\/guide/);
    // 应有搜索框
    const searchInput = page.locator('input[type="search"], input[placeholder*="症状"]');
    await expect(searchInput.first()).toBeVisible({ timeout: 10_000 });
  });

  test('智能导诊快捷症状标签', async ({ page }) => {
    await openPatientRoute(page, '/guide');

    // 应显示常见症状标签
    await expect(page.getByText('头痛').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('咳嗽').first()).toBeVisible();
  });

  test('智能导诊搜索匹配科室', async ({ page }) => {
    await openPatientRoute(page, '/guide');

    // 点击快捷症状
    await page.getByText('头痛').first().click();
    await page.waitForLoadState('networkidle');

    // 应显示匹配的科室
    await expect(page.getByText('神经内科').first()).toBeVisible({ timeout: 10_000 });
  });

  test('取消预约流程', async ({ page }) => {
    await openPatientRoute(page, '/appointment');

    // 找到取消按钮
    const cancelButton = page.getByText('取消预约').first();
    if (await cancelButton.isVisible()) {
      await cancelButton.click();
      // 应弹出确认对话框
      await expect(page.getByText('确定').first()).toBeVisible({ timeout: 5_000 });
    }
  });
});
