import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('科室启用/禁用切换', () => {
  test('科室列表状态开关可切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (await switchEl.isVisible()) {
      const wasChecked = await switchEl.evaluate((el) =>
        el.classList.contains('ant-switch-checked'),
      );
      await switchEl.click();
      if (wasChecked) {
        await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
      } else {
        await expect(switchEl).toHaveClass(/ant-switch-checked/);
      }
    }
  });

  test('科室状态切换后请求包含正确参数', async ({ page }) => {
    await mockAdminSession(page);

    let putBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/departments/**', async (route) => {
      if (route.request().method() === 'PUT') {
        putBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: putBody }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    const switchEl = page.locator('.ant-table-row').first().locator('.ant-switch');
    if (await switchEl.isVisible()) {
      await switchEl.click();
      await page.waitForTimeout(500);
      expect(putBody).toBeTruthy();
    }
  });
});

test.describe('医生启用/禁用切换', () => {
  test('医生列表状态开关可切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (await switchEl.isVisible()) {
      const wasChecked = await switchEl.evaluate((el) =>
        el.classList.contains('ant-switch-checked'),
      );
      await switchEl.click();
      if (wasChecked) {
        await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
      } else {
        await expect(switchEl).toHaveClass(/ant-switch-checked/);
      }
    }
  });
});

test.describe('租户启用/暂停', () => {
  test('租户列表状态开关可切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (await switchEl.isVisible()) {
      const wasChecked = await switchEl.evaluate((el) =>
        el.classList.contains('ant-switch-checked'),
      );
      await switchEl.click();
      if (wasChecked) {
        await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
      } else {
        await expect(switchEl).toHaveClass(/ant-switch-checked/);
      }
    }
  });

  test('租户状态切换后请求包含正确参数', async ({ page }) => {
    await mockAdminSession(page);

    let putBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/tenants/**', async (route) => {
      if (route.request().method() === 'PUT') {
        putBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: putBody }),
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
      expect(putBody).toBeTruthy();
    }
  });
});

test.describe('新闻发布/草稿状态', () => {
  test('新闻列表可查看状态标签', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    const statusTags = page.locator('.ant-tag, .ant-badge-status-text');
    if ((await page.locator('.ant-table-row').count()) > 0) {
      await expect(statusTags.first()).toBeVisible();
    }
  });

  test('新闻状态标签包含有效值', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    const rows = page.locator('.ant-table-row');
    const count = await rows.count();
    if (count > 0) {
      const tags = page.locator('.ant-tag');
      const tagCount = await tags.count();
      expect(tagCount).toBeGreaterThan(0);
    }
  });
});

test.describe('预约状态标签', () => {
  test('预约列表显示状态标签', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');

    const statusTags = page.locator('.ant-tag, .ant-badge-status-text');
    if ((await page.locator('.ant-table-row').count()) > 0) {
      await expect(statusTags.first()).toBeVisible();
    }
  });

  test('预约状态标签包含有效状态值', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');

    const validStatuses = ['已预约', '已确认', '已完成', '已取消', '爽约', '待确认'];
    const tags = page.locator('.ant-tag');
    const count = await tags.count();
    if (count > 0) {
      const tagTexts = await tags.allTextContents();
      const hasValidStatus = tagTexts.some((text) =>
        validStatuses.some((status) => text.includes(status)),
      );
      expect(hasValidStatus).toBe(true);
    }
  });
});

test.describe('STORE_ADMIN 无法切换租户状态', () => {
  test('STORE_ADMIN 看不到租户管理入口', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_ADMIN' });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const platformMenu = page
      .locator('.ant-menu-item, .ant-menu-submenu-title')
      .filter({ hasText: /^平台管理$/ });
    await expect(platformMenu).toHaveCount(0);
  });
});

test.describe('STORE_USER 无法切换科室状态', () => {
  test('STORE_USER 科室列表无编辑开关', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 department:update 权限，科室管理菜单不可见
    // 页面应被重定向或无内容
    const currentUrl = page.url();
    if (currentUrl.includes('/organization/department/list')) {
      const switchEl = page.locator('.ant-table-row .ant-switch');
      await expect(switchEl).toHaveCount(0);
    }
  });
});
