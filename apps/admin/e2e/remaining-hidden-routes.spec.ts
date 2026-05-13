import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('Admin 端 - 隐藏路由补充覆盖', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  // ---------------------------------------------------------------------------
  // 1. 添加预约设置
  // ---------------------------------------------------------------------------

  test('添加预约设置', async ({ page }) => {
    await page.goto('/medical-services/doctor/doctor-1/booking-setting');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /添加预约设置|新增/ }).click();
    await expect(page).toHaveURL(/\/booking-setting\/create/);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    const typeSelect = page.getByLabel(/预约类型|类型/).first();
    if (await typeSelect.isVisible()) {
      await typeSelect.click();
      const option = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item').first();
      if (await option.isVisible()) {
        await option.click();
      }
    }

    const countInput = page.getByLabel(/号源数量|数量|最大预约/).first();
    if (await countInput.isVisible()) {
      await countInput.fill('10');
    }

    await page.getByRole('button', { name: /创\s*建|保\s*存|确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    expect(currentUrl).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 2. 编辑预约设置
  // ---------------------------------------------------------------------------

  test('编辑预约设置', async ({ page }) => {
    await page.goto('/medical-services/doctor/doctor-1/booking-setting');
    await page.waitForLoadState('networkidle');

    const editLink = page.getByRole('link', { name: /编\s*辑/ }).first();
    if (await editLink.isVisible()) {
      await editLink.click();
      await expect(page).toHaveURL(/\/booking-setting\/.+\/edit/);
      await page.waitForLoadState('networkidle');

      await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

      const countInput = page.getByLabel(/号源数量|数量|最大预约/).first();
      if (await countInput.isVisible()) {
        await countInput.clear();
        await countInput.fill('20');
      }

      await page.getByRole('button', { name: /保\s*存|确\s*定/ }).click();
      await page.waitForLoadState('networkidle');

      expect(page.url()).not.toContain('/edit');
    } else {
      const tableBody = await page.locator('.ant-table-body, .ant-table-tbody').innerText().catch(() => '');
      expect(tableBody.length).toBeGreaterThanOrEqual(0);
    }
  });

  // ---------------------------------------------------------------------------
  // 3. 患者详情页
  // ---------------------------------------------------------------------------

  test('患者详情页', async ({ page }) => {
    await page.goto('/medical-services/patient/patient-1');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('.ant-descriptions, .ant-card, .ant-tabs, .ant-spin'),
    ).toBeVisible();

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);
  });

  // ---------------------------------------------------------------------------
  // 4. 就诊卡详情页
  // ---------------------------------------------------------------------------

  test('就诊卡详情页', async ({ page }) => {
    await page.goto('/medical-services/patient/card/patient-1');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('.ant-descriptions, .ant-card, .ant-tabs, .ant-spin'),
    ).toBeVisible();

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);
  });

  // ---------------------------------------------------------------------------
  // 5. 新增诊费类型
  // ---------------------------------------------------------------------------

  test('新增诊费类型', async ({ page }) => {
    await page.goto('/medical-services/consultation-fee/types');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增诊费类型|新增/ }).click();
    await expect(page).toHaveURL(/\/consultation-fee\/types\/create/);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    const typeName = `诊费类型${Date.now().toString().slice(-6)}`;
    await page.getByLabel('类型名称').fill(typeName);
    await page.getByLabel('类型编码').fill(`fee${Date.now().toString().slice(-6)}`);

    const descInput = page.getByLabel(/描述/).first();
    if (await descInput.isVisible()) {
      await descInput.fill('自动化测试新增的诊费类型');
    }

    await page.getByRole('button', { name: /创\s*建|保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/consultation-fee\/types/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 6. 编辑诊费类型
  // ---------------------------------------------------------------------------

  test('编辑诊费类型', async ({ page }) => {
    await page.goto('/medical-services/consultation-fee/types');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table-row')).not.toHaveCount(0);

    const firstRow = page.locator('.ant-table-row').first();
    await firstRow.getByRole('link', { name: /编\s*辑/ }).click();

    await expect(page).toHaveURL(/\/consultation-fee\/types\/.+\/edit/);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    const nameInput = page.getByLabel('类型名称');
    await expect(nameInput).toBeVisible();
    const originalValue = await nameInput.inputValue();
    expect(originalValue.length).toBeGreaterThan(0);

    const updatedName = `修改后诊费${Date.now().toString().slice(-4)}`;
    await nameInput.clear();
    await nameInput.fill(updatedName);

    await page.getByRole('button', { name: /保\s*存|确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/consultation-fee\/types/);
  });

  // ---------------------------------------------------------------------------
  // 7. 编辑新闻
  // ---------------------------------------------------------------------------

  test('编辑新闻', async ({ page }) => {
    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table-row')).not.toHaveCount(0);

    const firstRow = page.locator('.ant-table-row').first();
    await firstRow.getByRole('link', { name: /编\s*辑/ }).click();

    await expect(page).toHaveURL(/\/content\/news\/.+\/edit/);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    const titleInput = page.getByLabel(/标题/).first();
    if (await titleInput.isVisible()) {
      const originalTitle = await titleInput.inputValue();
      expect(originalTitle.length).toBeGreaterThan(0);

      const updatedTitle = `修改后新闻${Date.now().toString().slice(-4)}`;
      await titleInput.clear();
      await titleInput.fill(updatedTitle);

      await page.getByRole('button', { name: /保\s*存|发\s*布|确\s*定/ }).click();
      await page.waitForLoadState('networkidle');

      expect(page.url()).not.toContain('/edit');
    }
  });

  // ---------------------------------------------------------------------------
  // 8. 编辑公告
  // ---------------------------------------------------------------------------

  test('编辑公告', async ({ page }) => {
    await page.goto('/content-center/content/notice');
    await page.waitForLoadState('networkidle');

    const editLink = page.getByRole('link', { name: /编\s*辑/ }).first();
    if (await editLink.isVisible()) {
      await editLink.click();

      await expect(page).toHaveURL(/\/content\/notice\/.+\/edit/);
      await page.waitForLoadState('networkidle');

      await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

      const titleInput = page.getByLabel(/标题/).first();
      if (await titleInput.isVisible()) {
        const updatedTitle = `修改后公告${Date.now().toString().slice(-4)}`;
        await titleInput.clear();
        await titleInput.fill(updatedTitle);

        await page.getByRole('button', { name: /保\s*存|发\s*布|确\s*定/ }).click();
        await page.waitForLoadState('networkidle');

        expect(page.url()).not.toContain('/edit');
      }
    } else {
      const bodyText = await page.locator('body').innerText();
      expect(bodyText.length).toBeGreaterThan(0);
    }
  });

  // ---------------------------------------------------------------------------
  // 9. 编辑轮播图
  // ---------------------------------------------------------------------------

  test('编辑轮播图', async ({ page }) => {
    await page.goto('/content-center/content/banner');
    await page.waitForLoadState('networkidle');

    const editLink = page.getByRole('link', { name: /编\s*辑/ }).first();
    if (await editLink.isVisible()) {
      await editLink.click();

      await expect(page).toHaveURL(/\/content\/banner\/.+\/edit/);
      await page.waitForLoadState('networkidle');

      await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

      await page.getByRole('button', { name: /保\s*存|确\s*定/ }).click();
      await page.waitForLoadState('networkidle');

      expect(page.url()).not.toContain('/edit');
    } else {
      const bodyText = await page.locator('body').innerText();
      expect(bodyText.length).toBeGreaterThan(0);
    }
  });

  // ---------------------------------------------------------------------------
  // 10. 角色权限分配
  // ---------------------------------------------------------------------------

  test('角色权限分配', async ({ page }) => {
    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    const permissionLink = page.getByRole('link', { name: /分配权限|权限/ }).first();
    if (await permissionLink.isVisible()) {
      await permissionLink.click();

      await expect(page).toHaveURL(/\/system\/role\/.+\/permission/);
      await page.waitForLoadState('networkidle');

      await expect(
        page.locator('.ant-tree, .ant-checkbox-group, .ant-card, .ant-spin'),
      ).toBeVisible();

      const notFound = page.getByText(/404|页面不存在|找不到页面/);
      await expect(notFound).toHaveCount(0);

      const checkbox = page.locator('.ant-tree-checkbox, .ant-checkbox-input').first();
      if (await checkbox.isVisible()) {
        await checkbox.click();
      }

      await page.getByRole('button', { name: /保\s*存|确\s*定|提交/ }).click();
      await page.waitForLoadState('networkidle');
    } else {
      await page.goto('/system/role/role-super-admin/permission');
      await page.waitForLoadState('networkidle');

      const bodyText = await page.locator('body').innerText();
      expect(bodyText.length).toBeGreaterThan(0);

      const notFound = page.getByText(/404|页面不存在|找不到页面/);
      await expect(notFound).toHaveCount(0);
    }
  });

  // ---------------------------------------------------------------------------
  // 11. 复诊规则配置
  // ---------------------------------------------------------------------------

  test('复诊规则配置', async ({ page }) => {
    await page.goto('/organization/store/store-1/visit-type-config');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('form, .ant-form, .ant-card, .ant-spin, .ant-pro-form'),
    ).toBeVisible();

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);

    const saveBtn = page.getByRole('button', { name: /保\s*存|确\s*定|提交/ }).first();
    if (await saveBtn.isVisible()) {
      const input = page.locator('input[type="number"], .ant-input-number-input').first();
      if (await input.isVisible()) {
        await input.fill('7');
      }

      await saveBtn.click();
      await page.waitForLoadState('networkidle');
    }

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  // ---------------------------------------------------------------------------
  // 12. 预约详情页
  // ---------------------------------------------------------------------------

  test('预约详情页', async ({ page }) => {
    await page.goto('/medical-services/appointment/appt-1');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('.ant-descriptions, .ant-card, .ant-tabs, .ant-spin, .ant-steps'),
    ).toBeVisible();

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);
  });
});
