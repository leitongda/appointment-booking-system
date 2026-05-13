import { test } from '@playwright/test';
import { adminModuleGroupMap } from './helpers/admin-modules';
import { expectAdminRouteReady, mockAdminSession } from './helpers/admin-mocks';

const group = adminModuleGroupMap.dashboard;

test.describe('Admin 端 - 仪表盘模块', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  for (const route of group.routes) {
    test(`应可访问 ${route.label}`, async ({ page }) => {
      await expectAdminRouteReady(page, route.path, route.label);
    });
  }
});
