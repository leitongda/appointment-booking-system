import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * Admin 端核心模块 编辑 / 删除 E2E 测试
 *
 * 覆盖模块: 医生、科室、门店、租户、角色
 *
 * 选择器约定:
 * - 列表行内操作按钮: getByRole('row').filter({ hasText }) 内找链接/按钮
 * - Ant Design Popconfirm 确认: getByRole('button', { name: /确\s*定/ })
 * - 表单保存: getByRole('button', { name: /保\s*存/ })
 */

test.describe('Admin 端 - 编辑 / 删除操作', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  // ---------------------------------------------------------------------------
  // 1. 医生
  // ---------------------------------------------------------------------------

  test('应可编辑医生信息', async ({ page }) => {
    const updatedTitle = `更新职称${Date.now().toString().slice(-4)}`;

    // 导航到医生列表
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    // 在预置的"李医生"行点击编辑链接
    const doctorRow = page.getByRole('row').filter({ hasText: '李医生' });
    await doctorRow.getByRole('link', { name: /编\s*辑/ }).click();

    // 验证跳转到编辑页
    await expect(page).toHaveURL(/\/medical-services\/doctor\/doctor-1\/edit/);
    await page.waitForLoadState('networkidle');

    // 修改职称字段
    await page.getByLabel('职称').clear();
    await page.getByLabel('职称').fill(updatedTitle);

    // 保存
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证跳转回列表页，列表显示更新数据
    await expect(page).toHaveURL(/\/medical-services\/doctor\/list/);
    await expect(page.getByText(updatedTitle).first()).toBeVisible();
  });

  test('应可删除医生', async ({ page }) => {
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const doctorRow = page.getByRole('row').filter({ hasText: '李医生' });

    // 点击删除链接（Ant Design Popconfirm 包裹）
    await doctorRow.getByRole('link', { name: /删\s*除/ }).click();

    // 在 Popconfirm 弹窗中点击确定
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证列表中不再有该医生
    await expect(page.getByRole('row').filter({ hasText: '李医生' })).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 2. 科室
  // ---------------------------------------------------------------------------

  test('应可编辑科室信息', async ({ page }) => {
    const updatedName = `更新科室${Date.now().toString().slice(-6)}`;
    const updatedTag = `标签${Date.now().toString().slice(-4)}`;

    // 导航到科室列表
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    // 在预置的"中医科"行点击编辑链接
    const deptRow = page.getByRole('row').filter({ hasText: '中医科' });
    await deptRow.getByRole('link', { name: /编\s*辑/ }).click();

    // 验证跳转到编辑页
    await expect(page).toHaveURL(/\/organization\/department\/dept-1\/edit/);
    await page.waitForLoadState('networkidle');

    // 修改科室名称和标签
    await page.getByLabel('科室名称').clear();
    await page.getByLabel('科室名称').fill(updatedName);
    await page.getByLabel('科室标签').clear();
    await page.getByLabel('科室标签').fill(updatedTag);

    // 保存
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证跳转回列表页，列表显示更新数据
    await expect(page).toHaveURL(/\/organization\/department\/list/);
    await expect(page.getByText(updatedName).first()).toBeVisible();
  });

  test('应可删除科室', async ({ page }) => {
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    const deptRow = page.getByRole('row').filter({ hasText: '中医科' });

    // 点击删除链接
    await deptRow.getByRole('link', { name: /删\s*除/ }).click();

    // 在 Popconfirm 弹窗中点击确定
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证列表中不再有该科室
    await expect(page.getByRole('row').filter({ hasText: '中医科' })).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 3. 门店
  // ---------------------------------------------------------------------------

  test('应可编辑门店信息', async ({ page }) => {
    const updatedName = `更新门店${Date.now().toString().slice(-6)}`;
    const updatedPhone = `021-${Date.now().toString().slice(-8)}`;

    // 导航到门店列表
    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');

    // 在预置的"示例门店"行点击编辑链接
    const storeRow = page.getByRole('row').filter({ hasText: '示例门店' });
    await storeRow.getByRole('link', { name: /编\s*辑/ }).click();

    // 验证跳转到编辑页
    await expect(page).toHaveURL(/\/organization\/store\/store-1\/edit/);
    await page.waitForLoadState('networkidle');

    // 修改门店名称和联系电话
    await page.getByLabel('门店名称').clear();
    await page.getByLabel('门店名称').fill(updatedName);
    await page.getByLabel('联系方式').clear();
    await page.getByLabel('联系方式').fill(updatedPhone);

    // 保存
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证跳转回列表页，列表显示更新数据
    await expect(page).toHaveURL(/\/organization\/store\/list/);
    await expect(page.getByText(updatedName).first()).toBeVisible();
  });

  test('应可删除门店', async ({ page }) => {
    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');

    const storeRow = page.getByRole('row').filter({ hasText: '示例门店' });

    // 点击删除链接
    await storeRow.getByRole('link', { name: /删\s*除/ }).click();

    // 在 Popconfirm 弹窗中点击确定
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证列表中不再有该门店
    await expect(page.getByRole('row').filter({ hasText: '示例门店' })).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 4. 租户
  // ---------------------------------------------------------------------------

  test('应可编辑租户信息', async ({ page }) => {
    const updatedName = `更新租户${Date.now().toString().slice(-6)}`;
    const updatedContact = `联系人${Date.now().toString().slice(-4)}`;

    // 导航到租户列表
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    // 在预置的"演示租户"行点击编辑链接
    const tenantRow = page.getByRole('row').filter({ hasText: '演示租户' });
    await tenantRow.getByRole('link', { name: /编\s*辑/ }).click();

    // 验证跳转到编辑页
    await expect(page).toHaveURL(/\/platform\/tenant\/tenant-1\/edit/);
    await page.waitForLoadState('networkidle');

    // 修改租户名称和联系人
    await page.getByLabel('租户名称').clear();
    await page.getByLabel('租户名称').fill(updatedName);
    await page.getByLabel('联系人').clear();
    await page.getByLabel('联系人').fill(updatedContact);

    // 保存
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证跳转回列表页，列表显示更新数据
    await expect(page).toHaveURL(/\/platform\/tenant/);
    await expect(page.getByText(updatedName).first()).toBeVisible();
  });

  test('应可删除禁用状态的租户', async ({ page }) => {
    // 租户删除条件：status === 0（禁用状态）
    // 策略：先创建租户，再通过 PUT API 将其 status 改为 0，然后删除
    const tenantCode = `del-tenant-${Date.now().toString().slice(-6)}`;
    const tenantName = `待删除租户${Date.now().toString().slice(-6)}`;

    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    // 创建租户
    await page.getByRole('button', { name: '新增租户' }).click();
    await expect(page).toHaveURL(/\/platform\/tenant\/create/);
    await page.getByLabel('租户标识').fill(tenantCode);
    await page.getByLabel('租户名称').fill(tenantName);
    await page.getByLabel('订阅计划').click();
    await page.getByTitle('基础版').click();
    await page.getByLabel('联系人').fill('删除测试');
    await page.getByLabel('联系电话').fill('13900001111');
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 新创建的租户 status 为 1（正常），canDelete 要求 status === 0
    // 通过编辑表单提交来触发 PUT，将 status 改为 0
    // 利用 mock 的 PUT 逻辑（Object.assign 更新内存记录）
    const newTenantRow = page.getByRole('row').filter({ hasText: tenantName });
    await newTenantRow.getByRole('link', { name: /编\s*辑/ }).click();
    await page.waitForLoadState('networkidle');

    // 使用 evaluate 直接发 PUT 请求修改 status（绕过 UI 表单无 status 字段的限制）
    // mock 中 PUT /tenants/{id} 会 Object.assign 更新数据
    await page.evaluate(async (tenantNameStr: string) => {
      // 先从列表 API 获取新建租户的 id
      const listRes = await fetch('/api/v1/tenants');
      const listData = await listRes.json();
      const target = (listData.data || []).find(
        (t: { name: string }) => t.name === tenantNameStr,
      );
      if (target) {
        // PUT 更新 status 为 0（禁用）
        await fetch(`/api/v1/tenants/${target.id}`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status: 0 }),
        });
      }
    }, tenantName);

    // 返回列表页
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    // 现在租户状态为 0（禁用），应可删除
    const disabledTenantRow = page.getByRole('row').filter({ hasText: tenantName });
    await disabledTenantRow.getByRole('link', { name: /删\s*除/ }).click();

    // 确认删除弹窗
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证列表中不再有该租户
    await expect(page.getByRole('row').filter({ hasText: tenantName })).toHaveCount(0);
  });

  test('正常状态的租户不应显示删除按钮', async ({ page }) => {
    // 演示租户 status=1（正常），canDelete 要求 status===0
    await page.goto('/platform/tenant/list');
    await page.waitForLoadState('networkidle');

    const tenantRow = page.getByRole('row').filter({ hasText: '演示租户' });
    // 正常状态的租户不应有删除链接
    await expect(tenantRow.getByRole('link', { name: /删\s*除/ })).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 5. 角色
  // ---------------------------------------------------------------------------

  test('应可编辑角色信息', async ({ page }) => {
    // 先创建一个测试角色用于编辑
    const roleName = `待编辑角色${Date.now().toString().slice(-6)}`;
    const roleCode = `EDIT_ROLE_${Date.now().toString().slice(-6)}`;

    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    // 新增角色
    await page.getByRole('button', { name: '新增角色' }).click();
    await expect(page).toHaveURL(/\/system\/role\/create/);
    await page.getByLabel('角色名称').fill(roleName);
    await page.getByLabel('角色编码').fill(roleCode);
    await page.getByLabel('描述').fill('待编辑的角色');
    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证创建成功并回到列表
    await expect(page).toHaveURL(/\/system\/role/);
    await expect(page.getByText(roleName).first()).toBeVisible();

    // 点击编辑
    const roleRow = page.getByRole('row').filter({ hasText: roleName });
    await roleRow.getByRole('link', { name: /编\s*辑/ }).click();

    // 验证跳转到编辑页
    await expect(page).toHaveURL(/\/system\/role\/role-\d+\/edit/);
    await page.waitForLoadState('networkidle');

    // 修改角色名称和描述
    const updatedName = `已编辑角色${Date.now().toString().slice(-6)}`;
    const updatedDesc = '编辑后的角色描述';
    await page.getByLabel('角色名称').clear();
    await page.getByLabel('角色名称').fill(updatedName);
    await page.getByLabel('描述').clear();
    await page.getByLabel('描述').fill(updatedDesc);

    // 保存
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证跳转回列表页，列表显示更新数据
    await expect(page).toHaveURL(/\/system\/role/);
    await expect(page.getByText(updatedName).first()).toBeVisible();
  });

  test('应可删除自定义角色', async ({ page }) => {
    // 先创建一个角色用于删除（非 SUPER_ADMIN）
    const roleName = `待删除角色${Date.now().toString().slice(-6)}`;
    const roleCode = `DEL_ROLE_${Date.now().toString().slice(-6)}`;

    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    // 新增角色
    await page.getByRole('button', { name: '新增角色' }).click();
    await expect(page).toHaveURL(/\/system\/role\/create/);
    await page.getByLabel('角色名称').fill(roleName);
    await page.getByLabel('角色编码').fill(roleCode);
    await page.getByLabel('描述').fill('待删除的角色');
    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    // 确认创建成功
    await expect(page.getByText(roleName).first()).toBeVisible();

    // 删除该角色
    const roleRow = page.getByRole('row').filter({ hasText: roleName });
    await roleRow.getByRole('link', { name: /删\s*除/ }).click();

    // 在 Popconfirm 弹窗中点击确定
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    // 验证列表中不再有该角色
    await expect(page.getByRole('row').filter({ hasText: roleName })).toHaveCount(0);
  });

  test('SUPER_ADMIN 角色不应显示删除按钮', async ({ page }) => {
    await page.goto('/system/role');
    await page.waitForLoadState('networkidle');

    // 超级管理员行不应有删除按钮
    const superAdminRow = page.getByRole('row').filter({ hasText: '超级管理员' });
    await expect(superAdminRow.getByRole('link', { name: /删\s*除/ })).toHaveCount(0);
  });
});
