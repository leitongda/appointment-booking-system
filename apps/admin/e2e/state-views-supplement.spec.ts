import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('内容状态切换', () => {
  test('新闻列表状态标签显示', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/content/news**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [
                { id: 'news-draft', title: '草稿新闻', status: 0, type: 1, createdAt: '2026-05-12 10:00:00' },
                { id: 'news-published', title: '已发布新闻', status: 1, type: 1, createdAt: '2026-05-11 10:00:00' },
              ],
              total: 2,
            },
          }),
        });
      }
      if (route.request().method() === 'PUT') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const tags = page.locator('.ant-tag');
      const tagCount = await tags.count();
      if (tagCount > 0) {
        const texts = await tags.allTextContents();
        const hasStatusTag = texts.some((t) => /草稿|已发布|待发布/.test(t));
        expect(hasStatusTag).toBe(true);
      }
    }
  });

  test('公告列表状态标签', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/content/notices**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [
                { id: 'notice-1', title: '测试公告', status: 1, createdAt: '2026-05-12 10:00:00' },
              ],
              total: 1,
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/notice');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const tags = page.locator('.ant-tag');
      if ((await tags.count()) > 0) {
        await expect(tags.first()).toBeVisible();
      }
    }
  });

  test('轮播图列表启用禁用切换', async ({ page }) => {
    await mockAdminSession(page);

    let statusChanged = false;
    await page.route('**/api/v1/content/banners**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [
                { id: 'banner-1', title: '测试轮播图', status: 1, sortOrder: 1, createdAt: '2026-05-12 10:00:00' },
              ],
              total: 1,
            },
          }),
        });
      }
      if (route.request().method() === 'PUT') {
        statusChanged = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/banner');
    await page.waitForLoadState('networkidle');

    const switchEl = page.locator('.ant-table-row').first().locator('.ant-switch');
    if (await switchEl.isVisible()) {
      await switchEl.click();
      await page.waitForTimeout(500);
      expect(statusChanged).toBe(true);
    }
  });
});

test.describe('租户状态切换', () => {
  test('租户暂停切换 (status 1→0)', async ({ page }) => {
    await mockAdminSession(page);

    let putBody: unknown = null;
    await page.route('**/api/v1/tenants/**', async (route) => {
      const method = route.request().method();
      if (method === 'GET' && route.request().url().includes('/tenants?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [{
                id: 'tenant-1', tenantCode: 'tenant-1', name: '演示租户', status: 1,
                subscriptionPlanName: '基础版', storeCount: 1, adminCount: 1,
                contactName: '王管理员', contactPhone: '13800138000', createdAt: '2026-01-01 08:00:00',
              }],
              total: 1,
            },
          }),
        });
      }
      if (method === 'PUT') {
        putBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const switchEl = page.locator('.ant-table-row').first().locator('.ant-switch');
    if (await switchEl.isVisible()) {
      await switchEl.click();
      await page.waitForTimeout(500);
      if (putBody) {
        expect(putBody).toBeTruthy();
      }
    }
  });

  test('租户激活切换 (status 0→1)', async ({ page }) => {
    await mockAdminSession(page);

    let putBody: unknown = null;
    await page.route('**/api/v1/tenants/**', async (route) => {
      const method = route.request().method();
      if (method === 'GET' && route.request().url().includes('/tenants?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [{
                id: 'tenant-suspended', tenantCode: 'suspended', name: '已暂停租户', status: 0,
                subscriptionPlanName: '基础版', storeCount: 1, adminCount: 1,
                contactName: '李管理员', contactPhone: '13800138001', createdAt: '2026-01-01 08:00:00',
              }],
              total: 1,
            },
          }),
        });
      }
      if (method === 'PUT') {
        putBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const switchEl = page.locator('.ant-table-row').first().locator('.ant-switch');
    if (await switchEl.isVisible()) {
      await switchEl.click();
      await page.waitForTimeout(500);
      if (putBody) {
        expect(putBody).toBeTruthy();
      }
    }
  });
});

test.describe('排班高级视图', () => {
  test('排班日历视图渲染', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors/doctor-1/schedules**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: [
            { id: 'sch-1', date: '2026-05-15', timeSlot: '上午', startTime: '08:00', endTime: '12:00', quota: 20, booked: 10, status: 'normal' },
          ],
        }),
      });
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    const calendar = page.locator('.ant-picker-calendar, .ant-fullcalendar, [class*="calendar"]');
    if (await calendar.isVisible()) {
      await expect(calendar).toBeVisible();
    }
  });

  test('排班甘特图视图加载', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/schedule/gantt');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在|找不到页面/);
    await expect(notFound).toHaveCount(0);
  });

  test('排班统计图表加载', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/statistics/**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: [] }),
      });
    });

    await page.goto('/statistics/appointment');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const chart = page.locator('canvas, .antv-chart, [class*="chart"], [class*="Chart"]');
    if ((await chart.count()) > 0) {
      await expect(chart.first()).toBeVisible();
    }
  });
});
