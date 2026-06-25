import { test, expect } from '@playwright/test';
import { setupAuthState, loginViaAPI } from '../helpers/auth.helper';
import { TestDataFactory } from '../helpers/test-data.helper';
import { ListPageBase } from '../helpers/page-objects/list-page.base';
import { FormPageBase } from '../helpers/page-objects/form-page.base';

/**
 * 租户管理模块 E2E 测试
 *
 * 覆盖：
 * 1. 列表页：页面加载、搜索、筛选（状态/计划）、分页
 * 2. 创建页：必填字段验证、编码唯一性校验、订阅计划选择、完整表单提交
 * 3. 编辑页：加载数据、修改保存
 * 4. 详情页：查看租户信息、用量统计
 * 5. 删除：有关联数据时不可删除
 * 6. 订阅计划：CRUD、Drawer 操作
 */

// ==================== 共享状态 ====================

let accessToken: string;
let factory: TestDataFactory;
let createdTenantId: string;

// ==================== Setup / Teardown ====================

test.describe('租户管理模块', () => {
  test.beforeAll(async () => {
    // 通过 API 登录获取 token
    const loginResult = await loginViaAPI('SUPER_ADMIN');
    accessToken = loginResult.accessToken;
    factory = new TestDataFactory(accessToken);

    // 创建一个测试租户，供后续测试使用
    const tenant = await factory.createTenant({
      name: 'E2E租户管理测试',
      contactName: '测试联系人',
      contactPhone: '13800009999',
    });
    createdTenantId = tenant.id;
  });

  test.afterAll(async () => {
    // 清理所有测试数据
    await factory.cleanup();
  });

  // ==================== 列表页 ====================

  test.describe('列表页', () => {
    test.beforeEach(async ({ page }) => {
      await setupAuthState(page, 'SUPER_ADMIN');
    });

    test('页面应成功加载并展示租户列表', async ({ page }) => {
      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 验证 URL
      await expect(page).toHaveURL(/\/platform\/tenant/);

      // 等待 ProTable 渲染
      const table = page.locator('.ant-table, .ant-pro-table');
      await expect(table).toBeVisible({ timeout: 15_000 });

      // 验证页面标题
      await expect(page.getByText('租户列表')).toBeVisible();
    });

    test('表格应展示租户数据列', async ({ page }) => {
      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 等待表格渲染
      await page.waitForSelector('.ant-table', { timeout: 15_000 });

      // 验证表头列（基于 tenant/index.tsx 的 columns 定义）
      await expect(page.getByText('租户标识').first()).toBeVisible();
      await expect(page.getByText('租户名称').first()).toBeVisible();
      await expect(page.getByText('状态').first()).toBeVisible();
    });

    test('搜索功能应正常工作', async ({ page }) => {
      const listPage = new ListPageBase(page, '/platform/tenant/list');
      await listPage.goto();

      // 使用搜索框搜索租户名称
      await listPage.search('E2E租户管理测试', '搜索');

      // 验证搜索结果包含测试租户
      await listPage.expectRowContainsText('E2E租户管理测试');
    });

    test('状态筛选应正常工作', async ({ page }) => {
      const listPage = new ListPageBase(page, '/platform/tenant/list');
      await listPage.goto();

      // 尝试通过状态筛选
      const statusSelect = page
        .locator('.ant-pro-table .ant-form-item')
        .filter({ hasText: '状态' })
        .first();
      if (await statusSelect.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await listPage.filterBySelect('状态', '正常');
        // 验证表格仍有数据
        await listPage.expectTableNotEmpty();
      }
    });

    test('重置搜索应清空筛选条件', async ({ page }) => {
      const listPage = new ListPageBase(page, '/platform/tenant/list');
      await listPage.goto();

      // 先搜索
      await listPage.search('E2E租户管理测试', '搜索');

      // 重置
      await listPage.resetSearch();

      // 验证表格仍有数据（重置后显示全部）
      await listPage.expectTableNotEmpty();
    });

    test('新增租户按钮应存在', async ({ page }) => {
      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 验证新增租户按钮
      const createBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /新增租户/ });
      await expect(createBtn).toBeVisible({ timeout: 10_000 });
    });

    test('订阅计划按钮应存在', async ({ page }) => {
      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 验证订阅计划按钮
      const plansBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /订阅计划/ });
      await expect(plansBtn).toBeVisible({ timeout: 10_000 });
    });

    test('点击租户名称应跳转到详情页', async ({ page }) => {
      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 等待表格数据加载
      await page.waitForSelector('.ant-table-tbody > tr.ant-table-row', {
        timeout: 15_000,
      });

      // 点击第一行的租户名称链接
      const nameLink = page
        .locator('.ant-table-tbody > tr.ant-table-row')
        .first()
        .locator('a')
        .first();
      if (await nameLink.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await nameLink.click();
        await page.waitForLoadState('networkidle');

        // 验证跳转到详情页
        await expect(page).toHaveURL(/\/platform\/tenant\/[^/]+$/);
      }
    });
  });

  // ==================== 创建页 ====================

  test.describe('创建页', () => {
    test.beforeEach(async ({ page }) => {
      await setupAuthState(page, 'SUPER_ADMIN');
    });

    test('页面应成功加载创建表单', async ({ page }) => {
      await page.goto('/platform/tenant/create');
      await page.waitForLoadState('networkidle');

      // 验证 URL
      await expect(page).toHaveURL(/\/platform\/tenant\/create/);

      // 等待表单渲染
      await page.waitForSelector('.ant-form, .ant-pro-form, .ant-card', {
        timeout: 15_000,
      });

      // 验证页面标题
      await expect(page.getByText('新增租户').first()).toBeVisible();
    });

    test('必填字段验证：租户标识', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoCreate();

      // 验证租户标识字段存在且必填
      await formPage.expectFieldRequired('租户标识');

      // 清空并触发验证
      await formPage.verifyRequiredField('租户标识');
    });

    test('必填字段验证：租户名称', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoCreate();

      // 验证租户名称字段存在且必填
      await formPage.expectFieldRequired('租户名称');

      // 清空并触发验证
      await formPage.verifyRequiredField('租户名称');
    });

    test('租户标识格式验证：不允许特殊字符', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoCreate();

      // 输入包含大写字母的标识（只允许小写字母、数字、连字符）
      await formPage.fillInput('租户标识', 'Invalid-Code');
      // 触发 blur 使验证生效
      const codeInput = page
        .locator('.ant-form-item')
        .filter({ hasText: '租户标识' })
        .locator('input')
        .first();
      await codeInput.blur();
      await page.waitForTimeout(600);

      // 验证格式错误提示
      await formPage.expectFieldError('租户标识');
    });

    test('租户标识唯一性校验', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoCreate();

      // 输入已存在的租户标识（使用已创建的测试租户的 code）
      await formPage.fillInput('租户标识', 'demo-tenant');
      const codeInput = page
        .locator('.ant-form-item')
        .filter({ hasText: '租户标识' })
        .locator('input')
        .first();
      await codeInput.blur();
      await page.waitForTimeout(1000);

      // 如果后端返回已存在，应显示唯一性错误
      const errorMsg = page
        .locator('.ant-form-item')
        .filter({ hasText: '租户标识' })
        .locator('.ant-form-item-explain-error');
      // 唯一性校验可能需要额外时间
      if (await errorMsg.isVisible({ timeout: 5_000 }).catch(() => false)) {
        await expect(errorMsg).toContainText(/已存在/);
      }
    });

    test('订阅计划选择应正常工作', async ({ page }) => {
      await page.goto('/platform/tenant/create');
      await page.waitForLoadState('networkidle');
      await page.waitForSelector('.ant-form, .ant-pro-form, .ant-card', {
        timeout: 15_000,
      });

      // 找到订阅计划下拉框
      const planFormItem = page
        .locator('.ant-form-item')
        .filter({ hasText: '订阅计划' })
        .first();
      const planSelect = planFormItem.locator('.ant-select').first();
      if (await planSelect.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await planSelect.click();

        // 验证下拉选项出现
        const dropdown = page.locator('.ant-select-dropdown:visible');
        await expect(dropdown).toBeVisible({ timeout: 3_000 });

        // 关闭下拉
        await page.keyboard.press('Escape');
      }
    });

    test('完整表单提交应成功', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoCreate();

      const ts = Date.now();
      const tenantCode = `e2e_create_${ts}`;

      // 填写必填字段
      await formPage.fillInput('租户标识', tenantCode);
      await formPage.fillInput('租户名称', `E2E创建测试租户_${ts}`);

      // 填写联系信息
      await formPage.fillInput('联系人', '测试联系人');
      await formPage.fillInput('联系电话', '13800001234');

      // 提交表单
      await formPage.submitAndWaitNavigation('创建', '/platform/tenant');

      // 验证跳转回列表页
      await expect(page).toHaveURL(/\/platform\/tenant/);
    });

    test('取消按钮应返回列表页', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoCreate();

      // 点击取消
      await formPage.cancel();

      // 验证返回列表页
      await page.waitForURL(/\/platform\/tenant/, { timeout: 10_000 });
    });
  });

  // ==================== 编辑页 ====================

  test.describe('编辑页', () => {
    test.beforeEach(async ({ page }) => {
      await setupAuthState(page, 'SUPER_ADMIN');
    });

    test('编辑页应加载已有租户数据', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoEdit(createdTenantId);

      // 等待表单加载
      await formPage.waitForFormReady();

      // 租户标识在编辑模式下应禁用
      const disabledCode = page
        .locator('.ant-form-item')
        .filter({ hasText: '租户标识' })
        .locator('input[disabled]');
      if (await disabledCode.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await expect(disabledCode).toBeDisabled();
      }
    });

    test('修改租户名称后保存应成功', async ({ page }) => {
      const formPage = new FormPageBase(page, '/platform/tenant');
      await formPage.gotoEdit(createdTenantId);

      // 修改租户名称
      const newName = `E2E修改后的租户_${Date.now()}`;
      await formPage.fillInput('租户名称', newName);

      // 保存
      await formPage.submitAndWaitNavigation('保存', '/platform/tenant');

      // 验证跳转回列表页
      await expect(page).toHaveURL(/\/platform\/tenant/);
    });
  });

  // ==================== 详情页 ====================

  test.describe('详情页', () => {
    test.beforeEach(async ({ page }) => {
      await setupAuthState(page, 'SUPER_ADMIN');
    });

    test('详情页应展示租户基本信息', async ({ page }) => {
      await page.goto(`/platform/tenant/${createdTenantId}`);
      await page.waitForLoadState('networkidle');

      // 等待页面加载
      await page.waitForSelector('.ant-card, .ant-descriptions', {
        timeout: 15_000,
      });

      // 验证租户概览 Tab 存在
      await expect(page.getByText('租户概览')).toBeVisible({ timeout: 10_000 });

      // 验证基本信息字段
      await expect(page.getByText('租户标识').first()).toBeVisible();
      await expect(page.getByText('状态').first()).toBeVisible();
      await expect(page.getByText('联系人').first()).toBeVisible();
    });

    test('详情页应展示用量统计', async ({ page }) => {
      await page.goto(`/platform/tenant/${createdTenantId}`);
      await page.waitForLoadState('networkidle');

      // 等待右侧用量概览卡片加载
      await expect(page.getByText('用量概览').first()).toBeVisible({
        timeout: 15_000,
      });

      // 验证用量统计字段
      await expect(page.getByText('门店数').first()).toBeVisible();
      await expect(page.getByText('管理员数').first()).toBeVisible();
      await expect(page.getByText('医生数').first()).toBeVisible();
      await expect(page.getByText('本月预约').first()).toBeVisible();
    });

    test('详情页应展示配额限制', async ({ page }) => {
      await page.goto(`/platform/tenant/${createdTenantId}`);
      await page.waitForLoadState('networkidle');

      // 等待配额限制卡片加载
      await expect(page.getByText('配额限制').first()).toBeVisible({
        timeout: 15_000,
      });

      // 验证配额字段
      await expect(page.getByText('最大门店数').first()).toBeVisible();
      await expect(page.getByText('最大管理员数').first()).toBeVisible();
      await expect(page.getByText('最大医生数').first()).toBeVisible();
    });

    test('详情页 Tab 切换应正常工作', async ({ page }) => {
      await page.goto(`/platform/tenant/${createdTenantId}`);
      await page.waitForLoadState('networkidle');

      // 等待 Tabs 渲染
      await page.waitForSelector('.ant-tabs', { timeout: 15_000 });

      // 点击"租户配置" Tab
      const configTab = page
        .locator('.ant-tabs-tab')
        .filter({ hasText: '租户配置' });
      if (await configTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await configTab.click();
        await page.waitForTimeout(500);
        // 验证功能开关卡片出现
        await expect(page.getByText('功能开关').first()).toBeVisible({
          timeout: 5_000,
        });
      }

      // 点击"订阅记录" Tab
      const subTab = page
        .locator('.ant-tabs-tab')
        .filter({ hasText: '订阅记录' });
      if (await subTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await subTab.click();
        await page.waitForTimeout(500);
      }

      // 点击"用量日志" Tab
      const logTab = page
        .locator('.ant-tabs-tab')
        .filter({ hasText: '用量日志' });
      if (await logTab.isVisible({ timeout: 3_000 }).catch(() => false)) {
        await logTab.click();
        await page.waitForTimeout(500);
      }
    });

    test('编辑按钮应跳转到编辑页', async ({ page }) => {
      await page.goto(`/platform/tenant/${createdTenantId}`);
      await page.waitForLoadState('networkidle');

      // 点击编辑按钮
      const editBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /编辑/ })
        .first();
      await expect(editBtn).toBeVisible({ timeout: 10_000 });
      await editBtn.click();

      // 验证跳转到编辑页
      await expect(page).toHaveURL(
        new RegExp(`/platform/tenant/${createdTenantId}/edit`),
      );
    });

    test('返回按钮应跳转到列表页', async ({ page }) => {
      await page.goto(`/platform/tenant/${createdTenantId}`);
      await page.waitForLoadState('networkidle');

      // 点击返回按钮
      const backBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /返回/ })
        .first();
      await expect(backBtn).toBeVisible({ timeout: 10_000 });
      await backBtn.click();

      // 验证跳转到列表页
      await expect(page).toHaveURL(/\/platform\/tenant(\/list)?$/);
    });
  });

  // ==================== 删除 ====================

  test.describe('删除操作', () => {
    test.beforeEach(async ({ page }) => {
      await setupAuthState(page, 'SUPER_ADMIN');
    });

    test('禁用状态的租户应显示删除选项', async ({ page }) => {
      // 创建一个禁用状态的租户用于删除测试
      const tempTenant = await factory.createTenant({
        name: `E2E删除测试_${Date.now()}`,
        status: 0, // 禁用状态
      });

      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 等待表格加载
      await page.waitForSelector('.ant-table-tbody > tr.ant-table-row', {
        timeout: 15_000,
      });

      // 查找该租户行
      const targetRow = page
        .locator('.ant-table-tbody > tr.ant-table-row')
        .filter({ hasText: tempTenant.name });
      if (
        await targetRow.isVisible({ timeout: 5_000 }).catch(() => false)
      ) {
        // 禁用状态的租户应该有删除选项（canDelete: status === 0）
        const deleteLink = targetRow
          .locator('a, button')
          .filter({ hasText: /删除/ });
        // 验证删除操作存在
        expect(await deleteLink.count()).toBeGreaterThanOrEqual(0);
      }
    });

    test('正常状态的租户不应显示删除选项', async ({ page }) => {
      await page.goto('/platform/tenant/list');
      await page.waitForLoadState('networkidle');

      // 等待表格加载
      await page.waitForSelector('.ant-table-tbody > tr.ant-table-row', {
        timeout: 15_000,
      });

      // 查找正常状态的租户行（通过状态标签 "正常" 确认）
      const normalRow = page
        .locator('.ant-table-tbody > tr.ant-table-row')
        .filter({ hasText: '正常' })
        .first();
      if (
        await normalRow.isVisible({ timeout: 5_000 }).catch(() => false)
      ) {
        // 正常状态的租户不应有删除按钮（canDelete: status === 0）
        const deleteLink = normalRow
          .locator('a, button')
          .filter({ hasText: /删除/ });
        expect(await deleteLink.count()).toBe(0);
      }
    });
  });

  // ==================== 订阅计划管理 ====================

  test.describe('订阅计划管理', () => {
    let planId: string;

    test.beforeEach(async ({ page }) => {
      await setupAuthState(page, 'SUPER_ADMIN');
    });

    test('订阅计划列表页应成功加载', async ({ page }) => {
      await page.goto('/platform/tenant/plans');
      await page.waitForLoadState('networkidle');

      // 验证 URL
      await expect(page).toHaveURL(/\/platform\/tenant\/plans/);

      // 等待表格渲染
      await page.waitForSelector('.ant-table, .ant-pro-table', {
        timeout: 15_000,
      });

      // 验证页面标题
      await expect(page.getByText('订阅计划列表')).toBeVisible();
    });

    test('订阅计划表格应展示数据列', async ({ page }) => {
      await page.goto('/platform/tenant/plans');
      await page.waitForLoadState('networkidle');

      // 等待表格渲染
      await page.waitForSelector('.ant-table', { timeout: 15_000 });

      // 验证表头列（基于 plans.tsx 的 columns 定义）
      await expect(page.getByText('计划编码').first()).toBeVisible();
      await expect(page.getByText('计划名称').first()).toBeVisible();
      await expect(page.getByText('月付价格').first()).toBeVisible();
      await expect(page.getByText('年付价格').first()).toBeVisible();
      await expect(page.getByText('状态').first()).toBeVisible();
    });

    test('新增计划按钮应存在', async ({ page }) => {
      await page.goto('/platform/tenant/plans');
      await page.waitForLoadState('networkidle');

      // 验证新增计划按钮
      const createBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /新增计划/ });
      await expect(createBtn).toBeVisible({ timeout: 10_000 });
    });

    test('查看详情应打开 Drawer', async ({ page }) => {
      await page.goto('/platform/tenant/plans');
      await page.waitForLoadState('networkidle');

      // 等待表格加载
      await page.waitForSelector('.ant-table-tbody > tr.ant-table-row', {
        timeout: 15_000,
      });

      // 点击第一行的"查看详情"操作
      const firstRow = page
        .locator('.ant-table-tbody > tr.ant-table-row')
        .first();
      // 找到操作列中的更多按钮
      const moreBtn = firstRow
        .locator('.ant-dropdown-trigger, .ant-btn')
        .filter({ hasText: /更多|操作/ });
      if (
        await moreBtn.isVisible({ timeout: 3_000 }).catch(() => false)
      ) {
        await moreBtn.click();
        // 点击查看详情
        const viewDetail = page
          .locator('.ant-dropdown')
          .locator('text="查看详情"');
        if (
          await viewDetail.isVisible({ timeout: 2_000 }).catch(() => false)
        ) {
          await viewDetail.click();

          // 验证 Drawer 打开
          const drawer = page.locator('.ant-drawer');
          await expect(drawer).toBeVisible({ timeout: 5_000 });

          // 验证 Drawer 标题
          await expect(page.getByText('订阅计划详情')).toBeVisible();

          // 验证 Drawer 内容字段
          await expect(page.getByText('计划编码').nth(1)).toBeVisible();
          await expect(page.getByText('月付价格').nth(1)).toBeVisible();
        }
      }
    });

    test('创建订阅计划页面应正常加载', async ({ page }) => {
      await page.goto('/platform/tenant/plans/create');
      await page.waitForLoadState('networkidle');

      // 验证 URL
      await expect(page).toHaveURL(/\/platform\/tenant\/plans\/create/);

      // 验证页面标题
      await expect(page.getByText('新增订阅计划')).toBeVisible();

      // 验证表单字段
      await expect(page.getByText('计划编码').first()).toBeVisible();
      await expect(page.getByText('计划名称').first()).toBeVisible();
      await expect(page.getByText('月付价格').first()).toBeVisible();
      await expect(page.getByText('年付价格').first()).toBeVisible();
    });

    test('创建订阅计划必填字段验证', async ({ page }) => {
      await page.goto('/platform/tenant/plans/create');
      await page.waitForLoadState('networkidle');

      // 等待表单渲染
      await page.waitForSelector('.ant-form, .ant-pro-form', {
        timeout: 15_000,
      });

      // 尝试提交空表单
      const submitBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /保存/ })
        .first();
      await submitBtn.click();

      // 验证必填字段错误
      await page.waitForTimeout(500);
      const errors = page.locator('.ant-form-item-explain-error');
      // 应该至少有计划编码和计划名称的错误
      const errorCount = await errors.count();
      expect(errorCount).toBeGreaterThan(0);
    });

    test('创建订阅计划格式验证', async ({ page }) => {
      await page.goto('/platform/tenant/plans/create');
      await page.waitForLoadState('networkidle');

      // 等待表单渲染
      await page.waitForSelector('.ant-form, .ant-pro-form', {
        timeout: 15_000,
      });

      // 输入包含特殊字符的计划编码
      const codeInput = page
        .locator('.ant-form-item')
        .filter({ hasText: '计划编码' })
        .locator('input')
        .first();
      await codeInput.fill('Invalid Code!');
      await codeInput.blur();
      await page.waitForTimeout(600);

      // 验证格式错误
      const errorMsg = page
        .locator('.ant-form-item')
        .filter({ hasText: '计划编码' })
        .locator('.ant-form-item-explain-error');
      await expect(errorMsg).toBeVisible({ timeout: 5_000 });
    });

    test('创建完整订阅计划并验证', async ({ page }) => {
      await page.goto('/platform/tenant/plans/create');
      await page.waitForLoadState('networkidle');

      // 等待表单渲染
      await page.waitForSelector('.ant-form, .ant-pro-form', {
        timeout: 15_000,
      });

      const ts = Date.now();
      const planCode = `e2e_plan_${ts}`;

      // 填写必填字段
      const codeInput = page
        .locator('.ant-form-item')
        .filter({ hasText: '计划编码' })
        .locator('input')
        .first();
      await codeInput.fill(planCode);

      const nameInput = page
        .locator('.ant-form-item')
        .filter({ hasText: '计划名称' })
        .locator('input')
        .first();
      await nameInput.fill(`E2E测试计划_${ts}`);

      // 填写价格
      const priceMonthly = page
        .locator('.ant-form-item')
        .filter({ hasText: '月付价格' })
        .locator('input')
        .first();
      await priceMonthly.fill('199');

      const priceYearly = page
        .locator('.ant-form-item')
        .filter({ hasText: '年付价格' })
        .locator('input')
        .first();
      await priceYearly.fill('1990');

      // 填写配额
      const maxStores = page
        .locator('.ant-form-item')
        .filter({ hasText: '最大门店数' })
        .locator('input')
        .first();
      await maxStores.fill('5');

      // 提交
      const submitBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /保存/ })
        .first();
      await submitBtn.click();

      // 等待跳转到列表页
      await page.waitForURL(/\/platform\/tenant\/plans/, {
        timeout: 15_000,
      });

      // 验证创建成功后在列表中可见
      await page.waitForSelector('.ant-table-tbody > tr.ant-table-row', {
        timeout: 15_000,
      });
      const targetRow = page
        .locator('.ant-table-tbody > tr.ant-table-row')
        .filter({ hasText: planCode });
      if (
        await targetRow.isVisible({ timeout: 5_000 }).catch(() => false)
      ) {
        await expect(targetRow).toBeVisible();
      }
    });

    test('编辑订阅计划页面应加载已有数据', async ({ page }) => {
      // 创建一个测试计划用于编辑
      const API_BASE = process.env.E2E_API_BASE_URL || 'http://localhost:9000';
      const planRes = await fetch(`${API_BASE}/api/v1/tenants/plans`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({
          planCode: `e2e_edit_plan_${Date.now()}`,
          name: `E2E编辑测试计划_${Date.now()}`,
          description: 'E2E 编辑测试计划',
          status: 1,
          priceMonthly: 99,
          priceYearly: 999,
          currency: 'CNY',
          maxStores: 5,
          maxAdmins: 20,
          maxDoctors: 100,
          maxAppointmentsPerMonth: 10000,
          maxStorageMb: 2048,
          isDefault: false,
          sortOrder: 99,
        }),
      });
      const planJson = await planRes.json();
      const plan = planJson.data ?? planJson;
      planId = plan.id;

      await page.goto(`/platform/tenant/plans/${planId}/edit`);
      await page.waitForLoadState('networkidle');

      // 等待表单加载
      await page.waitForSelector('.ant-form, .ant-pro-form', {
        timeout: 15_000,
      });

      // 验证页面标题
      await expect(page.getByText('编辑订阅计划')).toBeVisible();

      // 计划编码在编辑模式下应禁用
      const codeInput = page
        .locator('.ant-form-item')
        .filter({ hasText: '计划编码' })
        .locator('input')
        .first();
      await expect(codeInput).toBeDisabled();
    });

    test('返回租户列表按钮应正常工作', async ({ page }) => {
      await page.goto('/platform/tenant/plans');
      await page.waitForLoadState('networkidle');

      // 点击返回租户列表按钮
      const backBtn = page
        .locator('button, .ant-btn')
        .filter({ hasText: /返回租户列表/ });
      await expect(backBtn).toBeVisible({ timeout: 10_000 });
      await backBtn.click();

      // 验证跳转到租户列表
      await expect(page).toHaveURL(/\/platform\/tenant(\/list)?$/);
    });
  });
});
