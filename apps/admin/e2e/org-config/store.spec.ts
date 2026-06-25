/**
 * 门店管理 E2E 测试
 *
 * 覆盖路径: /organization/store
 *
 * 场景:
 * 1. 列表页: 页面加载、搜索、分页、创建跳转
 * 2. 创建页: 必填字段验证（名称、编码）、唯一性校验、完整表单提交、取消
 * 3. 编辑页: 加载数据、修改保存
 * 4. 删除: 确认弹窗、有关联数据时不可删除
 */
import { test, expect } from '@playwright/test';
import { mockAdminSession } from '../helpers/admin-mocks';

test.describe('门店管理 - 列表页', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');
  });

  test('页面加载后应显示门店列表', async ({ page }) => {
    // ProTable 渲染完成
    await expect(page.locator('.ant-table, .ant-pro-table')).toBeVisible();

    // 标题应包含"门店列表"
    await expect(page.getByText('门店列表')).toBeVisible();

    // 预置的"示例门店"应可见
    await expect(page.getByRole('row').filter({ hasText: '示例门店' })).toBeVisible();
  });

  test('搜索门店名称应过滤结果', async ({ page }) => {
    // 找到搜索框
    const searchInput = page
      .locator('input[placeholder*="门店名称"], input[placeholder*="搜索"], input[placeholder*="关键字"]')
      .first();

    if (await searchInput.isVisible({ timeout: 3_000 }).catch(() => false)) {
      await searchInput.fill('示例门店');
      // 按回车或点击查询
      const queryBtn = page
        .locator('.ant-pro-table .ant-btn')
        .filter({ hasText: /查询|搜索/ })
        .first();
      if (await queryBtn.isVisible({ timeout: 2_000 }).catch(() => false)) {
        await queryBtn.click();
      } else {
        await searchInput.press('Enter');
      }
      await page.waitForLoadState('networkidle');

      // 应能找到"示例门店"
      await expect(page.getByRole('row').filter({ hasText: '示例门店' })).toBeVisible();
    }
  });

  test('分页组件应正常显示', async ({ page }) => {
    // 分页器应可见（即使只有一页）
    const pagination = page.locator('.ant-pagination');
    await expect(pagination).toBeVisible();
  });

  test('点击新增门店按钮应跳转到创建页', async ({ page }) => {
    await page.getByRole('button', { name: /新增门店/ }).click();

    await expect(page).toHaveURL(/\/organization\/store\/create/);
  });
});

test.describe('门店管理 - 创建页', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');
  });

  test('必填字段为空时提交应显示验证错误', async ({ page }) => {
    // 直接点击创建按钮
    await page.getByRole('button', { name: /创\s*建/ }).click();

    // 应出现必填验证错误（门店名称、门店编码为必填）
    await expect(page.getByText(/请输入|请选择|required/i).first()).toBeVisible();
  });

  test('门店名称为空时应提示必填', async ({ page }) => {
    // 填写编码但不填名称
    await page.getByLabel('门店编码').fill('TEST001');
    await page.getByLabel('门店编码').blur();

    // 清空名称确保为空
    const nameInput = page.getByLabel('门店名称');
    await nameInput.clear();
    await nameInput.blur();

    // 点击创建
    await page.getByRole('button', { name: /创\s*建/ }).click();

    // 应出现名称必填错误
    await expect(page.getByText(/请输入门店名称/)).toBeVisible();
  });

  test('门店编码为空时应提示必填', async ({ page }) => {
    // 填写名称但清空编码
    await page.getByLabel('门店名称').fill('测试门店');
    const codeInput = page.getByLabel('门店编码');
    await codeInput.clear();
    await codeInput.blur();

    // 点击创建
    await page.getByRole('button', { name: /创\s*建/ }).click();

    // 应出现编码必填错误
    await expect(page.getByText(/请输入门店编码/)).toBeVisible();
  });

  test('门店编码唯一性校验应生效', async ({ page }) => {
    // 拦截 POST 请求返回 409 冲突
    await page.route('**/api/v1/stores', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({ code: 409, message: '门店编码已存在' }),
        });
      }
      return route.fallback();
    });

    await page.getByLabel('门店名称').fill('重复编码门店');
    await page.getByLabel('门店编码').fill('EXISTING');
    await page.getByLabel('联系人').fill('张三');
    await page.getByLabel('联系方式').fill('13800138000');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(page.getByText(/门店编码已存在/)).toBeVisible();
  });

  test('填写完整表单后应能成功创建', async ({ page }) => {
    const storeName = `E2E测试门店_${Date.now()}`;
    const storeCode = `E2E_${Date.now()}`;

    await page.getByLabel('门店名称').fill(storeName);
    await page.getByLabel('门店编码').fill(storeCode);
    await page.getByLabel('联系人').fill('测试联系人');
    await page.getByLabel('联系方式').fill('021-12345678');

    // 点击创建
    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    // 应跳转回列表页
    await expect(page).toHaveURL(/\/organization\/store\/list/);
  });

  test('点击取消应返回列表页', async ({ page }) => {
    await page.getByRole('button', { name: /取\s*消/ }).click();

    // 应返回列表页
    await expect(page).toHaveURL(/\/organization\/store\/list/);
  });
});

test.describe('门店管理 - 编辑页', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('编辑页应加载门店数据', async ({ page }) => {
    // 使用预置的 store-1 数据
    await page.goto('/organization/store/store-1/edit');
    await page.waitForLoadState('networkidle');

    // 表单应加载完成
    await expect(page.locator('.ant-form, .ant-pro-form, .ant-card').first()).toBeVisible();

    // 门店名称字段应有值
    const nameInput = page.getByLabel('门店名称');
    await expect(nameInput).not.toHaveValue('');
  });

  test('修改后保存应跳转回列表页', async ({ page }) => {
    const updatedName = `更新门店_${Date.now().toString().slice(-6)}`;

    await page.goto('/organization/store/store-1/edit');
    await page.waitForLoadState('networkidle');

    // 修改门店名称
    await page.getByLabel('门店名称').clear();
    await page.getByLabel('门店名称').fill(updatedName);

    // 保存
    await page.getByRole('button', { name: /保\s*存/ }).click();
    await page.waitForLoadState('networkidle');

    // 应跳转回列表页
    await expect(page).toHaveURL(/\/organization\/store\/list/);

    // 列表中应显示更新后的名称
    await expect(page.getByText(updatedName).first()).toBeVisible();
  });
});

test.describe('门店管理 - 删除操作', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/list');
    await page.waitForLoadState('networkidle');
  });

  test('点击删除应弹出确认弹窗', async ({ page }) => {
    const storeRow = page.getByRole('row').filter({ hasText: '示例门店' });

    // 点击删除链接
    await storeRow.getByRole('link', { name: /删\s*除/ }).click();

    // Popconfirm 弹窗应出现
    await expect(page.getByText(/确定删除该门店/)).toBeVisible();

    // 点击确定删除
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    // 列表中应不再有该门店
    await expect(page.getByRole('row').filter({ hasText: '示例门店' })).toHaveCount(0);
  });

  test('有关联数据的门店删除时应显示错误提示', async ({ page }) => {
    // 拦截 DELETE 请求返回 400
    await page.route('**/api/v1/stores/store-1', async (route) => {
      if (route.request().method() === 'DELETE') {
        return route.fulfill({
          status: 400,
          contentType: 'application/json',
          body: JSON.stringify({ code: 400, message: '该门店下存在关联数据，无法删除' }),
        });
      }
      return route.fallback();
    });

    const storeRow = page.getByRole('row').filter({ hasText: '示例门店' });
    await storeRow.getByRole('link', { name: /删\s*除/ }).click();

    // 确认删除
    await page.getByRole('button', { name: /确\s*定/ }).click();

    // 应显示错误提示
    await expect(page.getByText(/关联数据|无法删除/).first()).toBeVisible();

    // 门店仍在列表中
    await expect(page.getByRole('row').filter({ hasText: '示例门店' })).toBeVisible();
  });
});
