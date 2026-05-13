import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * Admin 端 - 小程序平台模块 E2E 测试
 *
 * 覆盖子模块: 公司管理、支付配置、实例管理、模板管理、构建管理、发布管理
 *
 * 选择器约定:
 * - 创建按钮: getByRole('button', { name: /新增|创建/ })
 * - 表单字段: getByLabel()
 * - 表格: .ant-table
 * - 提交按钮: getByRole('button', { name: /保\s*存|创\s*建/ })
 * - 行内操作: getByRole('row').filter({ hasText }) 内找链接
 */

// ---------------------------------------------------------------------------
// 1. 公司管理
// ---------------------------------------------------------------------------

test.describe('小程序平台 - 公司管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('公司列表页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/company');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-table')).toBeVisible();
  });

  test('新增公司 - 填写表单并提交', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/company');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增公司/ }).click();
    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/company\/create/);

    await page.getByLabel('公司名称').fill('测试公司');
    await page.getByLabel('公司编码').fill('TEST_COMPANY');
    await page.getByLabel('联系人').fill('张三');
    await page.getByLabel('联系电话').fill('13800001111');

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/company/);
    expect(page.url()).not.toContain('/create');
  });

  test('编辑公司 - 修改表单并提交', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/company/company-1/edit');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form')).toBeVisible();

    await page.getByLabel('公司名称').clear();
    await page.getByLabel('公司名称').fill('已更新公司');

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/company/);
    expect(page.url()).not.toContain('/edit');
  });

  test('公司详情页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/company/company-1');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// 2. 支付配置
// ---------------------------------------------------------------------------

test.describe('小程序平台 - 支付配置', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('支付配置列表页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/payment-profile');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-table')).toBeVisible();
  });

  test('新增支付配置 - 填写表单并提交', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/payment-profile');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增支付配置/ }).click();
    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/payment-profile\/create/);

    await page.getByLabel('配置名称').fill('测试支付配置');
    await page.getByLabel('配置编码').fill('test_payment');

    await page.getByLabel('支付模式').click();
    await page.getByTitle('直连').click();

    await page.getByLabel('AppID').fill('wx1234567890abcdef');
    await page.getByLabel('商户号').fill('1234567890');

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/payment-profile/);
    expect(page.url()).not.toContain('/create');
  });

  test('编辑支付配置 - 修改表单并提交', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/payment-profile/profile-1/edit');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form')).toBeVisible();

    await page.getByLabel('配置名称').clear();
    await page.getByLabel('配置名称').fill('已更新支付配置');

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/payment-profile/);
    expect(page.url()).not.toContain('/edit');
  });

  test('支付配置详情页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/payment-profile/profile-1');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// 3. 实例管理
// ---------------------------------------------------------------------------

test.describe('小程序平台 - 实例管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('实例列表页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/instance');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-table')).toBeVisible();
  });

  test('新增实例 - 填写表单并提交', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/instance/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('实例名称').fill('测试实例');
    await page.getByLabel('实例编码').fill('test_instance');
    await page.getByLabel('AppID').fill('wxabcdef1234567890');

    // 创建模式使用卡片式模板选择，点击第一个模板卡片
    const templateCard = page.locator('.ant-card').filter({ hasText: '现代综合医疗' });
    if (await templateCard.count() > 0) {
      await templateCard.first().click();
    }

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/instance/);
    expect(page.url()).not.toContain('/create');
  });

  test('编辑实例 - 修改表单并提交', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/instance/instance-1/edit');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('form, .ant-form')).toBeVisible();

    await page.getByLabel('实例名称').clear();
    await page.getByLabel('实例名称').fill('已更新实例');

    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/platform\/miniapp-platform\/instance/);
    expect(page.url()).not.toContain('/edit');
  });

  test('实例详情页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/instance/instance-1');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// 4. 模板管理
// ---------------------------------------------------------------------------

test.describe('小程序平台 - 模板管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('模板管理页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/template');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);
  });
});

// ---------------------------------------------------------------------------
// 5. 构建管理
// ---------------------------------------------------------------------------

test.describe('小程序平台 - 构建管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('构建管理页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/build');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-table')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// 6. 发布管理
// ---------------------------------------------------------------------------

test.describe('小程序平台 - 发布管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('发布管理页面加载', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/release');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-table')).toBeVisible();
  });
});
