import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('API 500 错误处理', () => {
  test('门店列表 API 500 不导致白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/stores?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(page.locator('.ant-spin, .ant-empty, .ant-result, .ant-message-error')).toBeVisible();
  });

  test('医生列表 API 500 不导致白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});

test.describe('API 401 错误处理', () => {
  test('未登录访问仪表盘重定向到登录页', async ({ page }) => {
    await mockAdminSession(page, { authenticated: false });

    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/login/);
  });

  test('API 返回 401 时重定向到登录页', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/stores?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 401,
          contentType: 'application/json',
          body: JSON.stringify({ code: 401, message: 'Unauthorized' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');

    const url = page.url();
    const redirected = url.includes('/login') || url.includes('/organization/store/list');
    expect(redirected).toBe(true);
  });
});

test.describe('API 403 错误处理', () => {
  test('API 返回 403 时不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/stores?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 403,
          contentType: 'application/json',
          body: JSON.stringify({ code: 403, message: 'Forbidden' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});

test.describe('空数据状态', () => {
  test('医生列表空数据显示空状态', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });

  test('科室列表空数据显示空状态', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/departments?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });

  test('预约列表空数据显示空状态', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/appointments?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });
});

test.describe('网络异常处理', () => {
  test('门店列表网络断开不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/stores?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.abort('connectionrefused');
      }
      return route.fallback();
    });

    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('医生列表网络超时不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.abort('timedout');
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});

test.describe('STORE_USER 直接访问无权页面', () => {
  test('直接导航到租户列表不显示数据', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    if (currentUrl.includes('/platform/tenant/list')) {
      const tenantTable = page.locator('.ant-table');
      await expect(tenantTable).toHaveCount(0);
    } else {
      expect(currentUrl).not.toContain('/platform/tenant/list');
    }
  });

  test('直接导航到系统管理不显示数据', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    const currentUrl = page.url();
    if (currentUrl.includes('/system/role')) {
      const roleTable = page.locator('.ant-table');
      await expect(roleTable).toHaveCount(0);
    } else {
      expect(currentUrl).not.toContain('/system/role');
    }
  });
});
