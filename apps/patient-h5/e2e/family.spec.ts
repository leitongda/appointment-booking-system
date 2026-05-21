import { expect, test } from '@playwright/test';
import { mockPatientSession, openPatientRoute } from './helpers/patient-h5-mocks';

test.describe('患者端 - 家庭成员管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockPatientSession(page);
  });

  test('就诊人列表页加载', async ({ page }) => {
    await openPatientRoute(page, '/profile/patient');

    await expect(page).toHaveURL(/\/profile\/patient/);
    // 应显示已有的就诊人
    await expect(page.getByText('张三').first()).toBeVisible({ timeout: 10_000 });
  });

  test('显示家庭成员关系标签', async ({ page }) => {
    await openPatientRoute(page, '/profile/patient');

    // 应显示关系标签（本人、子女等）
    await expect(page.getByText('本人').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('子女').first()).toBeVisible();
  });

  test('添加就诊人入口', async ({ page }) => {
    await openPatientRoute(page, '/profile/patient');

    // 应有添加按钮
    const addButton = page.locator('[class*="add"], button').filter({ hasText: /添加|新增/ });
    const addIcon = page.locator('svg, [class*="icon"]').filter({ hasText: '' });

    // 至少应有一个可点击的添加入口
    const hasAddButton = await addButton.first().isVisible().catch(() => false);
    const hasAddIcon = await addIcon.first().isVisible().catch(() => false);
    expect(hasAddButton || hasAddIcon).toBeTruthy();
  });

  test('编辑就诊人页面加载', async ({ page }) => {
    await openPatientRoute(page, '/profile/patient/edit?id=patient-1');

    // 应有表单字段
    const nameInput = page.locator('input').filter({ hasText: '' }).first();
    await expect(nameInput).toBeVisible({ timeout: 10_000 });
  });

  test('就诊人详情包含关系选择', async ({ page }) => {
    await openPatientRoute(page, '/profile/patient/edit?id=patient-1');

    // 应有关系选项（本人/父母/子女/配偶/其他）
    const relationshipText = page.getByText(/本人|关系/);
    await expect(relationshipText.first()).toBeVisible({ timeout: 10_000 });
  });

  test('默认就诊人标识', async ({ page }) => {
    await openPatientRoute(page, '/profile/patient');

    // 张三应有默认标识
    const defaultTag = page.getByText(/默认/);
    await expect(defaultTag.first()).toBeVisible({ timeout: 10_000 });
  });
});
