import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('Admin 端 - 详情页与补充场景', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  // ---------------------------------------------------------------------------
  // B27. 订阅计划编辑
  // ---------------------------------------------------------------------------

  test('订阅计划编辑', async ({ page }) => {
    await page.goto('/platform/tenant/plans');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table-row')).not.toHaveCount(0);

    const firstRow = page.locator('.ant-table-row').first();
    await firstRow.getByRole('link', { name: /编\s*辑/ }).click();

    await expect(page).toHaveURL(/\/platform\/tenant\/plans\/.+\/edit/);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    const nameInput = page.getByLabel(/计划名称/);
    await expect(nameInput).toBeVisible();
    const originalValue = await nameInput.inputValue();
    expect(originalValue.length).toBeGreaterThan(0);

    const updatedName = `修改后计划${Date.now().toString().slice(-4)}`;
    await nameInput.clear();
    await nameInput.fill(updatedName);

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/tenant\/plans/);
  });

  // ---------------------------------------------------------------------------
  // B28. 诊费类型编辑
  // ---------------------------------------------------------------------------

  test('诊费类型编辑', async ({ page }) => {
    await page.goto('/medical-services/consultation-fee/types');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table-row')).not.toHaveCount(0);

    const firstRow = page.locator('.ant-table-row').first();
    await firstRow.getByRole('link', { name: /编\s*辑/ }).click();

    await expect(page).toHaveURL(/\/medical-services\/consultation-fee\/types\/.+\/edit/);
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    const nameInput = page.getByLabel(/类型名称/);
    await expect(nameInput).toBeVisible();
    const originalValue = await nameInput.inputValue();
    expect(originalValue.length).toBeGreaterThan(0);

    const updatedName = `修改后类型${Date.now().toString().slice(-4)}`;
    await nameInput.clear();
    await nameInput.fill(updatedName);

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/medical-services\/consultation-fee\/types/);
  });

  // ---------------------------------------------------------------------------
  // B38. 患者列表搜索
  // ---------------------------------------------------------------------------

  test('患者列表搜索', async ({ page }) => {
    await page.goto('/medical-services/patient/list');
    await page.waitForLoadState('networkidle');

    const searchInput = page.getByPlaceholder(/请输入|搜索|患者|姓名/).first();
    await searchInput.fill('张三');

    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/patients') && req.method() === 'GET',
    );
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    const request = await requestPromise;
    expect(request.url()).toContain('keyword');

    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /重置/ }).click();
    await page.waitForLoadState('networkidle');
    await expect(searchInput).toHaveValue('');
  });

  // ---------------------------------------------------------------------------
  // B41. 患者详情页
  // ---------------------------------------------------------------------------

  test('患者详情页', async ({ page }) => {
    await page.goto('/medical-services/patient/patient-1');
    await page.waitForLoadState('networkidle');

    await expect(
      page.locator('.ant-descriptions, .ant-card, .ant-spin, .ant-tabs'),
    ).toBeVisible();

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(50);
  });

  // ---------------------------------------------------------------------------
  // B42. 租户详情页
  // ---------------------------------------------------------------------------

  test('租户详情页', async ({ page }) => {
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const tenantRow = page.getByRole('row').filter({ hasText: '演示租户' });
    await expect(tenantRow).toBeVisible();
    await tenantRow.locator('a').filter({ hasText: '演示租户' }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/platform\/tenant\/tenant-1/);

    await expect(
      page.locator('.ant-descriptions, .ant-card, .ant-tabs, .ant-statistic'),
    ).toBeVisible();

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // B43. 就诊卡详情页
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
  // B44. 创建成功后数据回显
  // ---------------------------------------------------------------------------

  test('创建医生后列表回显', async ({ page }) => {
    const doctorName = `回显测试${Date.now().toString().slice(-4)}`;
    const username = `echo${Date.now().toString().slice(-6)}`;

    await page.goto('/medical-services/doctor/list');
    await page.getByRole('button', { name: '新增医生' }).click();

    await expect(page).toHaveURL(/\/medical-services\/doctor\/create/);
    await page.getByLabel('医生姓名').fill(doctorName);
    await page.getByLabel('所属门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('医生账号').fill(username);
    await page.getByPlaceholder('不填则默认为 123456').fill('Password123!');
    await page.getByLabel('确认密码').fill('Password123!');
    await page.getByLabel('所属科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('职称').fill('主治医师');
    await page.getByLabel('手机号').fill('13900139000');
    await page.getByLabel('擅长').fill('测试专长');
    await page.locator('[data-slate-editor] [contenteditable="true"], .w-e-text-container [contenteditable="true"]').first().fill('这是回显测试医生。');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/medical-services\/doctor\/list/);
    await expect(page.getByText(doctorName).first()).toBeVisible();
  });
});
