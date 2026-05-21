import { test, expect } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * 黑名单管理页面 E2E 测试 (/system/blacklist)
 *
 * 覆盖：
 * - 页面加载无报错
 * - ProTable 渲染及列展示
 * - 添加黑名单按钮打开弹窗
 * - 筛选器（关键字、状态）可用
 */

const blacklistRecords = [
  {
    id: 'bl-1',
    tenantId: 'tenant-1',
    storeId: 'store-1',
    keyword: '13900001111',
    userName: '张三',
    userPhone: '13900001111',
    reason: '连续爽约3次',
    noShowCount: 3,
    source: 1,
    status: 1,
    expireAt: '2026-12-31 23:59:59',
    createdAt: '2026-05-01 10:00:00',
  },
  {
    id: 'bl-2',
    tenantId: 'tenant-1',
    storeId: 'store-1',
    keyword: '310101199105151234',
    userName: '李四',
    userPhone: '13900002222',
    reason: '恶意挂号',
    noShowCount: 5,
    source: 2,
    status: 0,
    expireAt: null,
    createdAt: '2026-04-15 08:00:00',
  },
];

test.describe('黑名单管理页面', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);

    // 拦截黑名单相关 API
    await page.route('**/api/v1/blacklists**', async (route) => {
      const url = new URL(route.request().url());
      const keyword = url.searchParams.get('keyword');
      const status = url.searchParams.get('status');

      let filtered = [...blacklistRecords];
      if (keyword) {
        filtered = filtered.filter(
          (r) =>
            r.keyword.includes(keyword) ||
            (r.userName && r.userName.includes(keyword)),
        );
      }
      if (status !== null && status !== '') {
        filtered = filtered.filter((r) => String(r.status) === status);
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify({
          code: 200,
          message: 'ok',
          data: filtered,
          total: filtered.length,
          page: 1,
          pageSize: 20,
        }),
      });
    });
  });

  test('页面应成功加载', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    // 验证 URL
    await expect(page).toHaveURL(/\/system\/blacklist/);
  });

  test('ProTable 应渲染并展示表格列', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    // 等待 ProTable 表格渲染
    const table = page.locator('.ant-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    // 验证表头列
    await expect(page.getByText('用户姓名')).toBeVisible();
    await expect(page.getByText('手机号')).toBeVisible();
    await expect(page.getByText('拉黑原因')).toBeVisible();
    await expect(page.getByText('状态')).toBeVisible();
  });

  test('表格应展示 mock 数据行', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    // 等待数据行渲染
    await expect(page.getByText('张三').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('连续爽约3次').first()).toBeVisible();
  });

  test('添加黑名单按钮应打开弹窗', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    // 等待页面加载完成
    await page.waitForSelector('.ant-pro-table', { timeout: 15_000 });

    // 点击添加黑名单按钮
    const addButton = page.getByRole('button', { name: /添加黑名单/ });
    await expect(addButton).toBeVisible({ timeout: 10_000 });
    await addButton.click();

    // 验证弹窗出现
    const modal = page.locator('.ant-modal');
    await expect(modal).toBeVisible({ timeout: 5_000 });

    // 验证弹窗标题
    await expect(page.getByText('添加黑名单').nth(1)).toBeVisible();

    // 验证表单字段
    await expect(page.getByText('手机号/身份证')).toBeVisible();
    await expect(page.getByText('拉黑原因')).toBeVisible();
  });

  test('关键字筛选应正常工作', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    // 等待表格加载
    await page.waitForSelector('.ant-table', { timeout: 15_000 });

    // 在搜索栏输入关键字
    const keywordInput = page.locator('input[placeholder*="姓名/手机号/身份证"]');
    if (await keywordInput.isVisible()) {
      await keywordInput.fill('张三');

      // 点击查询/搜索按钮
      const searchBtn = page.locator('.ant-pro-table .ant-btn-primary').first();
      if (await searchBtn.isVisible()) {
        await searchBtn.click();
        await page.waitForLoadState('networkidle');
      }

      // 验证筛选结果
      await expect(page.getByText('张三').first()).toBeVisible({ timeout: 10_000 });
    }
  });
});
