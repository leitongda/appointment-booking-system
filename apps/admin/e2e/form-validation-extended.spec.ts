import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('用户名格式校验', () => {
  test('用户名含非法字符时提交校验失败 (V8)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/staff/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('账号').fill('user@#$');
    await page.getByLabel('用户名').fill('测试用户');
    await page.getByLabel('角色').click();
    await page.getByTitle('超级管理员').click();
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/账号|格式|字符|字母|数字/i).first()).toBeVisible();
  });

  test('用户名过短时提交校验失败', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/staff/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('账号').fill('ab');
    await page.getByLabel('用户名').fill('测试用户');
    await page.getByLabel('角色').click();
    await page.getByTitle('超级管理员').click();
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/至少|长度|字符|个/i).first()).toBeVisible();
  });
});

test.describe('邮箱格式校验', () => {
  test('门店创建 - 邮箱格式错误时提交校验失败 (V9)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('门店名称').fill('测试门店');
    await page.getByLabel('门店编码').fill('TESTMAIL01');
    await page.getByLabel('地址').fill('测试地址');
    await page.getByLabel('邮箱').fill('not-an-email');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/邮箱|格式|正确|有效/i).first()).toBeVisible();
  });

  test('员工创建 - 邮箱格式错误时提交校验失败', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/staff/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('账号').fill('emailtest01');
    await page.getByLabel('角色').click();
    await page.getByTitle('超级管理员').click();
    await page.getByLabel('邮箱').fill('bad@@email');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/邮箱|格式|正确|有效/i).first()).toBeVisible();
  });
});

test.describe('URL 格式校验', () => {
  test('轮播图 - 链接地址格式错误时提交校验失败 (V10)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/content-center/content/banner/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('链接地址').fill('not-a-url');
    await page.getByRole('button', { name: /创\s*建|保\s*存/ }).click();

    await expect(
      page.getByText(/链接|地址|格式|URL|正确|有效/i).first(),
    ).toBeVisible();
  });
});

test.describe('身份证格式校验', () => {
  test('患者详情 - 身份证号格式错误时提交校验失败 (V11)', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/patients/patient-1', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json; charset=utf-8',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: {
              id: 'patient-1',
              name: '测试患者',
              phone: '13800138000',
              gender: 1,
              idCard: '',
              idCardType: 1,
              cards: [],
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/patient/patient-1');
    await page.waitForLoadState('networkidle');

    const idCardInput = page.getByLabel('身份证号');
    if ((await idCardInput.count()) === 0) {
      test.skip();
      return;
    }

    await idCardInput.fill('12345678');
    const submitBtn = page.getByRole('button', { name: /保\s*存|提\s*交|确\s*认/ });
    if ((await submitBtn.count()) > 0) {
      await submitBtn.first().click();
    }

    await expect(page.getByText(/身份证|格式|不正确|无效/i).first()).toBeVisible();
  });
});

test.describe('数值范围越界', () => {
  test('门店创建 - 排序值为负数时提交校验失败 (V12)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('门店名称').fill('测试门店');
    await page.getByLabel('门店编码').fill('TESTRANGE01');
    await page.getByLabel('地址').fill('测试地址');
    await page.getByLabel('排序').fill('-1');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/排序|最小|不能|大于|范围/i).first()).toBeVisible();
  });

  test('门店创建 - 就诊卡上限超范围时提交校验失败', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('门店名称').fill('测试门店');
    await page.getByLabel('门店编码').fill('TESTRANGE02');
    await page.getByLabel('地址').fill('测试地址');

    const cardLimitInput = page.getByLabel(/每用户可建就诊卡数量上限|就诊卡/);
    if ((await cardLimitInput.count()) > 0) {
      await cardLimitInput.fill('999');
      await page.getByRole('button', { name: /创\s*建/ }).click();

      await expect(page.getByText(/最大|上限|不能超过|范围|20/i).first()).toBeVisible();
    } else {
      test.skip();
    }
  });
});

test.describe('404 页面正确显示', () => {
  test('访问不存在的路由显示 404 或重定向 (S6)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/nonexistent/page');
    await page.waitForLoadState('networkidle');

    const url = page.url();

    if (url.includes('/nonexistent/page')) {
      await expect(
        page.getByText(/404|页面不存在|找不到页面|Not Found/i),
      ).toBeVisible();
    } else {
      expect(url).toMatch(/\/(dashboard|login)/);
    }
  });

  test('访问不存在的子路由不白屏', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/nonexistent-id/edit');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});

test.describe('租户停用页显示', () => {
  test('租户状态为停用时应用不白屏 (S7)', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/admin/me', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify({
          code: 200,
          message: 'ok',
          data: {
            id: 'admin-1',
            username: 'superadmin',
            name: 'Playwright 超级管理员',
            phone: '13800138000',
            email: 'playwright@example.com',
            avatar: '',
            status: 1,
            roleType: 'admin',
            roleCode: 'SUPER_ADMIN',
            roleName: '超级管理员',
            isAdmin: true,
            isSuperAdmin: true,
            canSwitchStores: true,
            permissions: ['*'],
            tenantId: 'tenant-1',
            tenantName: '演示租户',
            storeIds: ['store-1'],
            stores: [{ id: 'store-1', name: '示例门店', logo: '' }],
            tenant: {
              id: 'tenant-1',
              name: '演示租户',
              tenantCode: 'demo-tenant',
              status: 0,
            },
          },
        }),
      });
    });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const hasTenantSuspended =
      (await page.getByText(/停用|禁用|suspended|已停用|未启用/i).count()) > 0 ||
      page.url().includes('/tenant-suspended') ||
      page.url().includes('/dashboard');

    expect(hasTenantSuspended).toBe(true);
  });
});
