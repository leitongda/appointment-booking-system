import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('Admin 端 - 真实交互登录与门店新增', () => {
  test('应可通过账号密码登录进入仪表盘', async ({ page }) => {
    await mockAdminSession(page, { authenticated: false });

    await page.goto('/login');
    await page.getByRole('tab', { name: '账号登录' }).click();
    await page.getByPlaceholder('请输入用户名').fill('superadmin');
    await page.getByPlaceholder('请输入密码').fill('Password123!');
    await page.getByRole('button', { name: '登 录' }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/dashboard/);
    await expect(page.getByText('仪表盘').first()).toBeVisible();
  });

  test('应可从门店列表进入新增页并提交创建门店', async ({ page }) => {
    await mockAdminSession(page);

    const storeName = `Playwright门店${Date.now()}`;
    const storeCode = `PW${Date.now().toString().slice(-6)}`;

    await page.goto('/organization/store/list');
    await page.getByRole('button', { name: '新增门店' }).click();

    await expect(page).toHaveURL(/\/organization\/store\/create/);
    await expect(page.getByText('新增门店').first()).toBeVisible();

    await page.getByLabel('门店名称').fill(storeName);
    await page.getByLabel('门店编码').fill(storeCode);
    await page.getByLabel('联系人').fill('张测试');
    await page.getByLabel('联系方式').fill('13800138000');
    await page.getByLabel('邮箱').fill('store@example.com');
    await page.getByLabel('地址').fill('上海市浦东新区测试大道 88 号');
    await page.getByLabel('排序').fill('9');
    await page.getByLabel('每用户可建就诊卡数量上限').fill('6');
    await page.getByLabel('门店简介').fill('这是一个由 Playwright 自动创建的测试门店。');

    await page.getByRole('button', { name: /创\s*建/ }).click();

    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/organization\/store\/list/);
    await expect(page.getByText('门店列表').first()).toBeVisible();
    await expect(page.getByText(storeName).first()).toBeVisible();
  });
});
