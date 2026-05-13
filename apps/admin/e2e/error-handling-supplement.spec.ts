import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

// ==================== 更多模块 API 500 错误处理 ====================

test.describe('更多模块 API 500 错误处理', () => {
  test('租户列表 API 500 不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/tenants**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(
      page.locator('.ant-spin, .ant-empty, .ant-result, .ant-message-error'),
    ).toBeVisible();
  });

  test('角色列表 API 500 不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/admin/roles**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(
      page.locator('.ant-spin, .ant-empty, .ant-result, .ant-message-error'),
    ).toBeVisible();
  });

  test('新闻列表 API 500 不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/content/news**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(
      page.locator('.ant-spin, .ant-empty, .ant-result, .ant-message-error'),
    ).toBeVisible();
  });

  test('排班规则列表 API 500 不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(
      page.locator('.ant-spin, .ant-empty, .ant-result, .ant-message-error'),
    ).toBeVisible();
  });

  test('预约详情 API 500 不白屏', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/appointments/**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: 'Internal Server Error' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/appointment/appt-1');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(
      page.locator('.ant-spin, .ant-empty, .ant-result, .ant-message-error'),
    ).toBeVisible();
  });

  test('反馈列表空数据', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/feedbacks**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/feedback');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });

  test('员工列表空数据', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/admin/admins**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/staff');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });

  test('消息列表空数据', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/messages**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/message/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });
});

// ==================== 提交失败数据保留 ====================

test.describe('提交失败数据保留', () => {
  test('科室编辑提交失败保留数据', async ({ page }) => {
    await mockAdminSession(page);

    let putFailed = false;
    await page.route('**/api/v1/departments/dept-1', async (route) => {
      if (route.request().method() === 'PUT') {
        putFailed = true;
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '更新失败' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/dept-1/edit');
    await page.waitForLoadState('networkidle');

    const updatedName = '修改后科室';
    await page.getByLabel('科室名称').clear();
    await page.getByLabel('科室名称').fill(updatedName);
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证错误提示出现
    await expect(page.getByText(/失败|错误/).first()).toBeVisible();
    // 验证表单数据保留
    await expect(page.getByLabel('科室名称')).toHaveValue(updatedName);
    expect(putFailed).toBe(true);
  });

  test('角色编辑提交失败保留数据', async ({ page }) => {
    await mockAdminSession(page);

    let putFailed = false;
    await page.route('**/api/v1/admin/roles/role-super-admin', async (route) => {
      if (route.request().method() === 'PUT') {
        putFailed = true;
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '更新失败' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/system/role/role-super-admin/edit');
    await page.waitForLoadState('networkidle');

    const updatedName = '修改后角色';
    await page.getByLabel('角色名称').clear();
    await page.getByLabel('角色名称').fill(updatedName);
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证错误提示出现
    await expect(page.getByText(/失败|错误/).first()).toBeVisible();
    // 验证表单数据保留
    await expect(page.getByLabel('角色名称')).toHaveValue(updatedName);
    expect(putFailed).toBe(true);
  });

  test('医生编辑提交失败保留数据', async ({ page }) => {
    await mockAdminSession(page);

    let putFailed = false;
    await page.route('**/api/v1/doctors/doctor-1', async (route) => {
      if (route.request().method() === 'PUT') {
        putFailed = true;
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '更新失败' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1/edit');
    await page.waitForLoadState('networkidle');

    const updatedName = '修改后医生';
    await page.getByLabel('医生姓名').clear();
    await page.getByLabel('医生姓名').fill(updatedName);
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证错误提示出现
    await expect(page.getByText(/失败|错误/).first()).toBeVisible();
    // 验证表单数据保留
    await expect(page.getByLabel('医生姓名')).toHaveValue(updatedName);
    expect(putFailed).toBe(true);
  });

  test('新闻创建提交失败保留数据', async ({ page }) => {
    await mockAdminSession(page);

    let postFailed = false;
    await page.route('**/api/v1/content/news', async (route) => {
      if (route.request().method() === 'POST') {
        postFailed = true;
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '创建失败' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/news/create');
    await page.waitForLoadState('networkidle');

    const newsTitle = '测试新闻标题';
    await page.getByLabel('标题').fill(newsTitle);
    await page.getByRole('button', { name: /发\s*布/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证错误提示出现
    await expect(page.getByText(/失败|错误/).first()).toBeVisible();
    // 验证表单数据保留
    await expect(page.getByLabel('标题')).toHaveValue(newsTitle);
    expect(postFailed).toBe(true);
  });
});
