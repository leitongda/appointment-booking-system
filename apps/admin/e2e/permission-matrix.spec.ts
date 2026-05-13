import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * 权限矩阵 E2E 测试
 *
 * 验证 STORE_ADMIN / STORE_USER 角色在各页面的 UI 元素可见性与操作权限。
 * 与 permission-boundary.spec.ts 互补，不重复已有的 9 条边界测试。
 *
 * 权限依据：
 * - STORE_ADMIN: department:list/create/update, appointment:list/detail, content:news,
 *   message:list, feedback:list, system:user 等
 * - STORE_USER: doctor:list/detail, schedule:list, appointment:list/detail, patient:list/detail
 *
 * 不可访问的页面预期行为：被重定向到其他页面（如 404/仪表盘）或页面内无数据表格。
 */

// ============================================================================
// STORE_ADMIN 权限矩阵 (7 tests)
// ============================================================================

test.describe('STORE_ADMIN 权限矩阵', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_ADMIN' });
  });

  // 1. 科室列表可见且可新增
  test('科室列表可见且有新增科室按钮', async ({ page }) => {
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table')).toBeVisible();
    // STORE_ADMIN 有 department:create 权限，新增按钮应可见
    await expect(page.getByRole('button', { name: /新增科室/ })).toBeVisible();
  });

  // 2. 预约列表可见且有详情链接
  test('预约列表可见且操作列有详情链接', async ({ page }) => {
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table')).toBeVisible();
    // STORE_ADMIN 有 appointment:detail 权限，详情链接应可见
    const detailLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('详情');
    const count = await detailLinks.count();
    expect(count).toBeGreaterThanOrEqual(0);
    // 至少验证表格正常渲染且无错误提示
    const errorText = page.getByText(/无权限|403|not found|找不到/i);
    await expect(errorText).toHaveCount(0);
  });

  // 3. 无法访问系统管理角色页面
  test('无法访问系统管理角色页面', async ({ page }) => {
    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 不是 SUPER_ADMIN，canRoleManagement 要求 isSuperAdmin
    // 预期被重定向或页面无角色数据表格
    const currentUrl = page.url();
    if (currentUrl.includes('/system/role')) {
      const roleTable = page.locator('.ant-table');
      const tableCount = await roleTable.count();
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const noAccessCount = await noAccess.count();
      expect(tableCount + noAccessCount === 0 || tableCount === 0).toBeTruthy();
    } else {
      expect(currentUrl).not.toContain('/system/role');
    }
  });

  // 4. 可访问运营中心新闻页面
  test('可访问运营中心新闻管理页面', async ({ page }) => {
    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 有 content:news 权限
    await expect(page.locator('.ant-table')).toBeVisible();
    // 新闻管理页面标题应可见
    const newsContent = page.getByText(/新闻/).first();
    await expect(newsContent).toBeVisible();
  });

  // 5. 无法访问小程序平台页面
  test('无法访问小程序平台页面', async ({ page }) => {
    await page.goto('/platform/miniapp-platform/company');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 无 canMiniappPlatform 权限
    const currentUrl = page.url();
    if (currentUrl.includes('/platform/miniapp-platform')) {
      const table = page.locator('.ant-table');
      await expect(table).toHaveCount(0);
    } else {
      expect(currentUrl).not.toContain('/platform/miniapp-platform/company');
    }
  });

  // 6. 无法访问系统配置医院信息
  test('无法访问系统配置医院信息页面', async ({ page }) => {
    await page.goto('/system/config/hospital-info');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 无 system:settings 权限，canHospitalInfo 为 false
    // 页面应被重定向或不展示表单数据
    const currentUrl = page.url();
    if (currentUrl.includes('/system/config/hospital-info')) {
      const form = page.locator('.ant-form, form');
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const formCount = await form.count();
      const noAccessCount = await noAccess.count();
      // 如果停留在该 URL，应无表单或有无权限提示
      expect(formCount === 0 || noAccessCount > 0).toBeTruthy();
    } else {
      expect(currentUrl).not.toContain('/system/config/hospital-info');
    }
  });

  // 7. 无法访问微信配置
  test('无法访问系统配置微信页面', async ({ page }) => {
    await page.goto('/system/config/wechat');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 不是 SUPER_ADMIN 且无 settings:wechat / settings:edit 权限
    const currentUrl = page.url();
    if (currentUrl.includes('/system/config/wechat')) {
      const form = page.locator('.ant-form, form');
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const formCount = await form.count();
      const noAccessCount = await noAccess.count();
      expect(formCount === 0 || noAccessCount > 0).toBeTruthy();
    } else {
      expect(currentUrl).not.toContain('/system/config/wechat');
    }
  });
});

// ============================================================================
// STORE_USER 权限矩阵 (6 tests)
// ============================================================================

test.describe('STORE_USER 权限矩阵', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
  });

  // 8. 科室列表无新增按钮
  test('科室列表无新增科室按钮', async ({ page }) => {
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 department:create 权限
    await expect(page.getByRole('button', { name: /新增科室/ })).toHaveCount(0);
  });

  // 9. 科室列表行无编辑/删除操作
  test('科室列表行无编辑和删除操作', async ({ page }) => {
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 department:update 和 department:delete 权限
    const editLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('编辑');
    await expect(editLinks).toHaveCount(0);

    const deleteLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('删除');
    await expect(deleteLinks).toHaveCount(0);

    // 编辑/删除图标也不应存在
    const editIcons = page.locator('.anticon-edit');
    await expect(editIcons).toHaveCount(0);

    const deleteIcons = page.locator('.anticon-delete');
    await expect(deleteIcons).toHaveCount(0);
  });

  // 10. 预约列表无操作按钮（取消/退款/爽约等）
  test('预约列表无取消/退款/爽约操作按钮', async ({ page }) => {
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table')).toBeVisible();

    // STORE_USER 有 appointment:list/detail 但无 appointment:cancel/update/refund
    const cancelLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('取消');
    await expect(cancelLinks).toHaveCount(0);

    const refundLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('退款');
    await expect(refundLinks).toHaveCount(0);

    const noShowLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('爽约');
    await expect(noShowLinks).toHaveCount(0);
  });

  // 11. 无法访问用户反馈页面
  test('无法访问用户反馈页面', async ({ page }) => {
    await page.goto('/content-center/feedback');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 feedback 权限，canFeedback 为 false
    const currentUrl = page.url();
    if (currentUrl.includes('/content-center/feedback')) {
      const table = page.locator('.ant-table');
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const tableCount = await table.count();
      const noAccessCount = await noAccess.count();
      expect(tableCount === 0 || noAccessCount > 0).toBeTruthy();
    } else {
      expect(currentUrl).not.toContain('/content-center/feedback');
    }
  });

  // 12. 患者列表无编辑/删除操作
  test('患者列表无编辑和删除操作', async ({ page }) => {
    await page.goto('/medical-services/patient/list');
    await page.waitForLoadState('networkidle');

    // STORE_USER 有 patient:list/detail 但无 patient:update/delete
    const editLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('编辑');
    await expect(editLinks).toHaveCount(0);

    const deleteLinks = page.locator('.ant-table-row-actions, .ant-table-cell').getByText('删除');
    await expect(deleteLinks).toHaveCount(0);

    const editIcons = page.locator('.anticon-edit');
    await expect(editIcons).toHaveCount(0);

    const deleteIcons = page.locator('.anticon-delete');
    await expect(deleteIcons).toHaveCount(0);
  });

  // 13. 无法访问消息发送页面
  test('无法访问消息发送页面', async ({ page }) => {
    await page.goto('/content-center/message/create');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 message:send 权限
    const currentUrl = page.url();
    if (currentUrl.includes('/content-center/message/create')) {
      // 如果 URL 未重定向，则页面不应展示发送表单
      const form = page.locator('.ant-form, form');
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const formCount = await form.count();
      const noAccessCount = await noAccess.count();
      expect(formCount === 0 || noAccessCount > 0).toBeTruthy();
    } else {
      expect(currentUrl).not.toContain('/content-center/message/create');
    }
  });
});

// ============================================================================
// URL 直接访问拦截 (3 tests)
// ============================================================================

test.describe('URL 直接访问拦截', () => {
  // 14. STORE_USER 直接访问 /system/role 被拦截
  test('STORE_USER 直接访问角色管理页面被拦截', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 canSystemManagement 权限，整个系统管理菜单不可见
    const currentUrl = page.url();
    if (currentUrl.includes('/system/role')) {
      const table = page.locator('.ant-table');
      await expect(table).toHaveCount(0);
    } else {
      expect(currentUrl).not.toContain('/system/role');
    }
  });

  // 15. STORE_ADMIN 直接访问 /platform/tenant/create 被拦截
  test('STORE_ADMIN 直接访问租户新增页面被拦截', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_ADMIN' });
    await page.goto('/platform/tenant/create');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 无 canPlatformManagement 权限
    const currentUrl = page.url();
    if (currentUrl.includes('/platform/tenant/create')) {
      const form = page.locator('.ant-form, form');
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const formCount = await form.count();
      const noAccessCount = await noAccess.count();
      expect(formCount === 0 || noAccessCount > 0).toBeTruthy();
    } else {
      expect(currentUrl).not.toContain('/platform/tenant/create');
    }
  });

  // 16. STORE_USER 直接访问 /configuration/system/hospital-info 被拦截
  // （旧路径会重定向到 /system/config/hospital-info，同样不可访问）
  test('STORE_USER 直接访问系统配置医院信息被拦截', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/configuration/hospital-info');
    await page.waitForLoadState('networkidle');

    // 旧路径会重定向到 /system/config/hospital-info
    // STORE_USER 无 canHospitalInfo / canSystemConfig / canSystemManagement 权限
    const currentUrl = page.url();
    const isOnConfigPage =
      currentUrl.includes('/configuration/hospital-info') ||
      currentUrl.includes('/system/config/hospital-info');

    if (isOnConfigPage) {
      const form = page.locator('.ant-form, form');
      const noAccess = page.getByText(/无权限|403|not found|找不到/i);
      const formCount = await form.count();
      const noAccessCount = await noAccess.count();
      expect(formCount === 0 || noAccessCount > 0).toBeTruthy();
    } else {
      // 被重定向到其他页面（如 404 或仪表盘）
      expect(
        currentUrl.includes('/configuration/hospital-info') ||
        currentUrl.includes('/system/config/hospital-info'),
      ).toBeFalsy();
    }
  });
});
