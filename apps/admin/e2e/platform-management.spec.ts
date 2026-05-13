import { test } from '@playwright/test';
import { adminModuleGroupMap } from './helpers/admin-modules';
import { expectAdminRouteReady, mockAdminSession } from './helpers/admin-mocks';

const group = adminModuleGroupMap.platform;

test.describe('Admin 端 - 平台管理模块', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  for (const route of group.routes) {
    test(`应可访问 ${route.label || route.path}`, async ({ page }) => {
      await expectAdminRouteReady(page, route.path, route.label);
    });
  }
});
