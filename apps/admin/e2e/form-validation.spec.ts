import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('新增医生 - 表单校验', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/create');
    await page.waitForLoadState('networkidle');
  });

  test('账号唯一性校验', async ({ page }) => {
    await page.route('**/api/v1/doctors', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ code: 409, message: '账号已存在' }),
        });
      }
      return route.fallback();
    });

    await page.getByLabel('医生姓名').fill('测试医生');
    await page.getByLabel('所属门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('医生账号').fill('existing_doctor');
    await page.getByPlaceholder('不填则默认为 123456').fill('Password123!');
    await page.getByLabel('确认密码').fill('Password123!');
    await page.getByLabel('所属科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('职称').fill('主治医师');
    await page.getByLabel('手机号').fill('13900139000');
    await page.getByLabel('擅长').fill('针灸');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/账号已存在/)).toBeVisible();
  });

  test('必填字段为空时提交失败', async ({ page }) => {
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/请输入|请选择|required/i).first()).toBeVisible();
  });

  test('手机号格式校验', async ({ page }) => {
    await page.getByLabel('医生姓名').fill('测试医生');
    await page.getByLabel('所属门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('医生账号').fill('test_phone');
    await page.getByPlaceholder('不填则默认为 123456').fill('Password123!');
    await page.getByLabel('确认密码').fill('Password123!');
    await page.getByLabel('所属科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('职称').fill('主治医师');
    await page.getByLabel('手机号').fill('abc');
    await page.getByLabel('擅长').fill('针灸');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/手机号|格式|正确/i).first()).toBeVisible();
  });

  test('密码确认不匹配时校验失败', async ({ page }) => {
    await page.getByLabel('医生姓名').fill('测试医生');
    await page.getByLabel('所属门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('医生账号').fill('test_pwd');
    await page.getByPlaceholder('不填则默认为 123456').fill('Password123!');
    await page.getByLabel('确认密码').fill('DifferentPwd!');
    await page.getByLabel('所属科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('职称').fill('主治医师');
    await page.getByLabel('手机号').fill('13900139000');
    await page.getByLabel('擅长').fill('针灸');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/密码|不一致|不匹配|确认/i).first()).toBeVisible();
  });
});

test.describe('新增门店 - 表单校验', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');
  });

  test('门店编码唯一性校验', async ({ page }) => {
    await page.route('**/api/v1/stores', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ code: 409, message: '门店编码已存在' }),
        });
      }
      return route.fallback();
    });

    await page.getByLabel('门店名称').fill('测试门店');
    await page.getByLabel('门店编码').fill('EXISTING');
    await page.getByLabel('联系人').fill('张三');
    await page.getByLabel('联系方式').fill('13800138000');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/门店编码已存在/)).toBeVisible();
  });

  test('必填字段为空时提交失败', async ({ page }) => {
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/请输入|请选择|required/i).first()).toBeVisible();
  });
});

test.describe('新增租户 - 表单校验', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/platform/tenant/create');
    await page.waitForLoadState('networkidle');
  });

  test('租户标识唯一性校验', async ({ page }) => {
    await page.route('**/api/v1/tenants', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ code: 409, message: '租户标识已存在' }),
        });
      }
      return route.fallback();
    });

    await page.getByLabel('租户标识').fill('existing-tenant');
    await page.getByLabel('租户名称').fill('测试租户');
    await page.getByLabel('订阅计划').click();
    await page.getByTitle('基础版').click();
    await page.getByLabel('联系人').fill('联系人');
    await page.getByLabel('联系电话').fill('13800138000');
    await page.getByRole('button', { name: /保\s*存/ }).click();

    await expect(page.getByText(/租户标识已存在/)).toBeVisible();
  });

  test('必填字段为空时提交失败', async ({ page }) => {
    await page.getByRole('button', { name: /保\s*存/ }).click();

    await expect(page.getByText(/请输入|请选择|required/i).first()).toBeVisible();
  });
});

test.describe('新增科室 - 表单校验', () => {
  test('必填字段为空时提交失败', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/create');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/请输入|请选择|required/i).first()).toBeVisible();
  });
});

test.describe('新增角色 - 表单校验', () => {
  test('必填字段为空时提交失败', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/system/role/create');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/请输入|请选择|required/i).first()).toBeVisible();
  });
});
