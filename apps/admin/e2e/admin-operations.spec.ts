import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('Admin 端 - 关键操作自动化', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('应可新增租户', async ({ page }) => {
    const tenantCode = `tenant-${Date.now().toString().slice(-6)}`;
    const tenantName = `Playwright租户${Date.now()}`;

    await page.goto('/platform/tenant/list');
    await page.getByRole('button', { name: '新增租户' }).click();

    await expect(page).toHaveURL(/\/platform\/tenant\/create/);
    await page.getByLabel('租户标识').fill(tenantCode);
    await page.getByLabel('租户名称').fill(tenantName);
    await page.getByLabel('订阅计划').click();
    await page.getByTitle('基础版').click();
    await page.getByLabel('联系人').fill('租户联系人');
    await page.getByLabel('联系电话').fill('13800138000');
    await page.getByRole('button', { name: /保\s*存/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/platform\/tenant/);
    await expect(page.getByText(tenantName).first()).toBeVisible();
  });

  test('应可新增科室', async ({ page }) => {
    const departmentName = `Playwright科室${Date.now()}`;

    await page.goto('/organization/department/list');
    await page.getByRole('button', { name: '新增科室' }).click();

    await expect(page).toHaveURL(/\/organization\/department\/create/);
    await page.getByLabel('门店选择').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('科室名称').fill(departmentName);
    await page.getByLabel('科室标签').fill('测试科室');
    await page.getByLabel('排序').fill('5');
    await page.getByLabel('描述').fill('用于自动化测试的科室。');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/organization\/department\/list/);
    await expect(page.getByText(departmentName).first()).toBeVisible();
  });

  test('应可新增医生', async ({ page }) => {
    const doctorName = `王测试${Date.now().toString().slice(-4)}`;
    const username = `doctor${Date.now().toString().slice(-6)}`;

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
    await page.getByLabel('擅长').fill('针灸调理、睡眠管理');
    await page.locator('[data-slate-editor] [contenteditable="true"], .w-e-text-container [contenteditable="true"]').first().fill('这是自动化测试创建的医生介绍。');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/medical-services\/doctor\/list/);
    await expect(page.getByText(doctorName).first()).toBeVisible();
  });

  test('应可发布新闻', async ({ page }) => {
    const newsTitle = `Playwright新闻${Date.now()}`;

    await page.goto('/content-center/content/news');
    await page.getByRole('button', { name: '发布新闻' }).click();

    await expect(page).toHaveURL(/\/content-center\/content\/news\/create/);
    await page.getByLabel('标题').fill(newsTitle);
    await page.getByLabel('类型').click();
    await page.getByTitle('医院动态').last().click();
    await page.getByLabel('摘要').fill('这是自动化测试发布的新闻摘要。');
    await page.locator('.w-e-text-container [contenteditable="true"]').first().fill('这是自动化测试发布的新闻内容。');
    await page.getByRole('button', { name: /发\s*布/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/content-center\/content\/news/);
    await expect(page.getByText(newsTitle).first()).toBeVisible();
  });

  test('应可新增角色', async ({ page }) => {
    const roleName = `测试角色${Date.now()}`;
    const roleCode = `ROLE_${Date.now().toString().slice(-6)}`;

    await page.goto('/system/role');
    await page.getByRole('button', { name: '新增角色' }).click();

    await expect(page).toHaveURL(/\/system\/role\/create/);
    await page.getByLabel('角色名称').fill(roleName);
    await page.getByLabel('角色编码').fill(roleCode);
    await page.getByLabel('描述').fill('自动化测试创建的角色。');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/role/);
    await expect(page.getByText(roleName).first()).toBeVisible();
  });
});
