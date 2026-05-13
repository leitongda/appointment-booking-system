import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * 权限边界 E2E 测试
 *
 * 验证不同角色在 UI 层的权限隔离：
 * - SUPER_ADMIN（超管）：全部权限
 * - STORE_ADMIN（门店管理员）：医疗服务、组织架构（部分）、运营中心（部分）
 * - STORE_USER（门店普通用户）：仅有医疗服务（查看）、患者查看权限
 */

test.describe('权限边界测试', () => {
  // ---------------------------------------------------------------------------
  // 1. STORE_USER 看不到平台管理菜单
  // ---------------------------------------------------------------------------
  test('STORE_USER 侧边栏不存在平台管理菜单', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    const platformMenu = page
      .locator('.ant-menu-item, .ant-menu-submenu-title')
      .filter({ hasText: /^平台管理$/ });
    await expect(platformMenu).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 2. STORE_USER 看不到系统管理部分菜单 — 角色管理、系统配置
  // ---------------------------------------------------------------------------
  test('STORE_USER 侧边栏不存在角色管理和系统配置菜单', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/dashboard');
    await page.waitForLoadState('networkidle');

    // STORE_USER 无 canSystemManagement 权限，整个系统管理菜单都不可见
    const systemMenu = page
      .locator('.ant-menu-item, .ant-menu-submenu-title')
      .filter({ hasText: /^系统管理$/ });
    await expect(systemMenu).toHaveCount(0);

    // 同时验证组织架构菜单不可见（STORE_USER 无 canOrganizationManagement）
    const orgMenu = page
      .locator('.ant-menu-item, .ant-menu-submenu-title')
      .filter({ hasText: /^组织架构$/ });
    await expect(orgMenu).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 3. STORE_ADMIN 无法访问租户列表 — 导航被拦截
  // ---------------------------------------------------------------------------
  test('STORE_ADMIN 导航到租户列表被拦截', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_ADMIN' });
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    // STORE_ADMIN 无 canPlatformManagement 权限，应被重定向到 404 或其他页面
    // URL 不应停留在 /platform/tenant/list
    const currentUrl = page.url();
    const isOnTenantList = currentUrl.includes('/platform/tenant/list');
    // 如果未被重定向，则页面不应展示租户数据表格
    if (isOnTenantList) {
      const tenantTable = page.locator('.ant-table');
      await expect(tenantTable).toHaveCount(0);
    }
  });

  // ---------------------------------------------------------------------------
  // 4. STORE_USER 无权删除/新增医生
  // ---------------------------------------------------------------------------
  test('STORE_USER 医生列表无删除和新增按钮', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    // 新增医生按钮不应存在（需要 doctor:create 权限，STORE_USER 没有）
    await expect(page.getByRole('button', { name: /新增医生/ })).toHaveCount(0);

    // 操作列中的删除按钮不应存在（需要 doctor:delete 权限）
    const deleteButtons = page.locator('.ant-table-row-actions').getByText('删除');
    await expect(deleteButtons).toHaveCount(0);

    // 删除 Popconfirm 也不应存在
    const deleteIcons = page.locator('.ant-table-row-actions').locator('[aria-label="delete"], .anticon-delete');
    await expect(deleteIcons).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 5. STORE_USER 直接访问租户 URL 被拦截
  // ---------------------------------------------------------------------------
  test('STORE_USER 直接访问租户列表 URL 不显示数据', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    // 页面应被重定向到 404 或仪表盘，或至少不显示租户数据
    const currentUrl = page.url();

    if (currentUrl.includes('/platform/tenant/list')) {
      // 如果 URL 未变，则页面上不应有租户表格数据
      const tenantTable = page.locator('.ant-table');
      await expect(tenantTable).toHaveCount(0);
      // 也可能出现 403 或无权限提示
      const noPermission = page.getByText(/无权限|403|not found|找不到/i);
      // 至少满足：无表格 或 有无权限提示
      const hasTable = await page.locator('.ant-table').count();
      expect(hasTable).toBe(0);
    } else {
      // URL 已被重定向，验证不在租户页面
      expect(currentUrl).not.toContain('/platform/tenant/list');
    }
  });

  // ---------------------------------------------------------------------------
  // 6. 门店用户仅看到自己门店
  // ---------------------------------------------------------------------------
  test('STORE_USER 门店筛选隐藏或仅一个选项', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    // STORE_USER 的 canSwitchStores 为 false，门店选择器应隐藏或只读
    const storeSelect = page.locator('.ant-select').filter({ hasText: /门店|示例门店/ }).first();

    if (await storeSelect.isVisible()) {
      // 如果门店选择器可见，验证只有一个选项且不可切换
      await storeSelect.click();
      const options = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden) .ant-select-item');
      const optionCount = await options.count();
      expect(optionCount).toBeLessThanOrEqual(1);
      // 关闭下拉
      await page.keyboard.press('Escape');
    }
    // 如果门店选择器不可见，则隐式通过
  });

  // ---------------------------------------------------------------------------
  // 7. STORE_USER 不能编辑医生
  // ---------------------------------------------------------------------------
  test('STORE_USER 医生列表操作列无编辑按钮', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_USER' });
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    // 编辑按钮需要 doctor:update 权限，STORE_USER 没有
    const editButtons = page.locator('.ant-table-row-actions').getByText('编辑');
    await expect(editButtons).toHaveCount(0);

    // 编辑图标也不应存在
    const editIcons = page.locator('.ant-table-row-actions').locator('[aria-label="edit"], .anticon-edit');
    await expect(editIcons).toHaveCount(0);

    // 查看详情按钮可能存在（STORE_USER 有 doctor:detail）
    const detailButtons = page.locator('.ant-table-row-actions').getByText('查看');
    // 查看按钮可以存在，这是允许的
  });

  // ---------------------------------------------------------------------------
  // 8. SUPER_ADMIN 角色不可删除
  // ---------------------------------------------------------------------------
  test('角色列表中 SUPER_ADMIN 行无删除按钮', async ({ page }) => {
    await mockAdminSession(page, { role: 'SUPER_ADMIN' });
    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    // 找到 SUPER_ADMIN 所在行
    const superAdminRow = page.locator('.ant-table-row').filter({ hasText: '超级管理员' }).first();
    await expect(superAdminRow).toBeVisible();

    // SUPER_ADMIN 行中不应有删除按钮
    const deleteInRow = superAdminRow.locator('.ant-table-row-actions').getByText('删除');
    await expect(deleteInRow).toHaveCount(0);

    // 也验证删除图标不存在
    const deleteIcon = superAdminRow.locator('.anticon-delete');
    await expect(deleteIcon).toHaveCount(0);

    // 分配权限按钮也不应出现在 SUPER_ADMIN 行
    const permissionBtn = superAdminRow.getByText('分配权限');
    await expect(permissionBtn).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 9. STORE_ADMIN 医生有新增按钮但门店无新增按钮
  // ---------------------------------------------------------------------------
  test('STORE_ADMIN 医生列表有新增按钮但门店列表无新增门店按钮', async ({ page }) => {
    await mockAdminSession(page, { role: 'STORE_ADMIN' });

    // 验证医生列表有新增按钮（STORE_ADMIN 有 doctor:create 权限）
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('button', { name: /新增医生/ })).toBeVisible();

    // STORE_ADMIN 没有 store:create 权限（仅 isSuperAdmin），
    // 但门店列表页面使用 access.hasPermission('store:create') 控制，
    // 由于 STORE_ADMIN 的 permissions 数组中没有 'store:create'，且 isSuperAdmin 为 false
    // 验证门店列表的新增按钮不存在
    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');
    await expect(page.getByRole('button', { name: /新增门店/ })).toHaveCount(0);
  });
});
