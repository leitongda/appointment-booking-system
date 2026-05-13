import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('预约列表 - 多条件筛选', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');
  });

  test('按患者姓名搜索', async ({ page }) => {
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/appointments') && req.method() === 'GET',
    );
    await page.getByPlaceholder(/请输入患者姓名|患者姓名/).first().fill('张三');
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    const request = await requestPromise;
    expect(request.url()).toContain('patientName');
  });

  test('按状态筛选', async ({ page }) => {
    await page.getByLabel(/状态/).click();
    await page.getByTitle('已预约').click();
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    await page.waitForLoadState('networkidle');
  });

  test('按日期范围筛选', async ({ page }) => {
    const dateInputs = page.locator('.ant-picker-range, .ant-picker input');
    if ((await dateInputs.count()) > 0) {
      await dateInputs.first().click();
      await page.locator('.ant-picker-cell').first().click();
      await page.locator('.ant-picker-cell').last().click();
      await page.getByRole('button', { name: /查询|搜索/ }).click();
      await page.waitForLoadState('networkidle');
    }
  });

  test('重置所有筛选条件', async ({ page }) => {
    await page.getByPlaceholder(/请输入患者姓名|患者姓名/).first().fill('测试');
    await page.getByRole('button', { name: /重置/ }).click();
    await page.waitForLoadState('networkidle');
    const input = page.getByPlaceholder(/请输入患者姓名|患者姓名/).first();
    await expect(input).toHaveValue('');
  });
});

test.describe('医生列表 - 搜索', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');
  });

  test('按姓名搜索', async ({ page }) => {
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/doctors') && req.method() === 'GET',
    );
    await page.getByPlaceholder(/请输入医生姓名|医生姓名|搜索/).first().fill('王医生');
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    const request = await requestPromise;
    expect(request.url()).toContain('name');
  });

  test('搜索无结果显示空状态', async ({ page }) => {
    await page.route('**/api/v1/doctors?**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });
    await page.getByPlaceholder(/请输入医生姓名|医生姓名|搜索/).first().fill('不存在的医生');
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-empty, .ant-table-placeholder')).toBeVisible();
  });

  test('重置后恢复完整列表', async ({ page }) => {
    await page.getByPlaceholder(/请输入医生姓名|医生姓名|搜索/).first().fill('测试');
    await page.getByRole('button', { name: /重置/ }).click();
    await page.waitForLoadState('networkidle');
    const input = page.getByPlaceholder(/请输入医生姓名|医生姓名|搜索/).first();
    await expect(input).toHaveValue('');
  });
});

test.describe('患者列表 - 搜索', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/patient/list');
    await page.waitForLoadState('networkidle');
  });

  test('按姓名搜索', async ({ page }) => {
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/patients') && req.method() === 'GET',
    );
    await page.getByPlaceholder(/请输入患者姓名|患者姓名|搜索/).first().fill('李四');
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    const request = await requestPromise;
    expect(request.url()).toContain('name');
  });

  test('重置搜索', async ({ page }) => {
    await page.getByPlaceholder(/请输入患者姓名|患者姓名|搜索/).first().fill('测试');
    await page.getByRole('button', { name: /重置/ }).click();
    await page.waitForLoadState('networkidle');
    const input = page.getByPlaceholder(/请输入患者姓名|患者姓名|搜索/).first();
    await expect(input).toHaveValue('');
  });
});

test.describe('科室列表 - 门店筛选', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');
  });

  test('按门店筛选', async ({ page }) => {
    await page.getByLabel(/门店/).click();
    await page.getByTitle('示例门店').click();
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/departments') && req.method() === 'GET',
    );
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    const request = await requestPromise;
    expect(request.url()).toContain('store_id');
  });

  test('按科室名称搜索', async ({ page }) => {
    await page.getByPlaceholder(/请输入科室名称|科室名称|搜索/).first().fill('中医科');
    const requestPromise = page.waitForRequest(
      (req) => req.url().includes('/api/v1/departments') && req.method() === 'GET',
    );
    await page.getByRole('button', { name: /查询|搜索/ }).click();
    const request = await requestPromise;
    expect(request.url()).toContain('name');
  });

  test('重置后恢复列表', async ({ page }) => {
    await page.getByPlaceholder(/请输入科室名称|科室名称|搜索/).first().fill('测试');
    await page.getByRole('button', { name: /重置/ }).click();
    await page.waitForLoadState('networkidle');
    const input = page.getByPlaceholder(/请输入科室名称|科室名称|搜索/).first();
    await expect(input).toHaveValue('');
  });
});

test.describe('列表分页', () => {
  test('预约列表分页组件存在', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-pagination')).toBeVisible();
  });

  test('医生列表分页组件存在', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-pagination')).toBeVisible();
  });

  test('科室列表分页组件存在', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-pagination')).toBeVisible();
  });

  test('患者列表分页组件存在', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/patient/list');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-pagination')).toBeVisible();
  });

  test('点击下一页不崩溃', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');
    const nextBtn = page.locator('.ant-pagination-next:not(.ant-pagination-disabled)');
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
      await page.waitForLoadState('networkidle');
      await expect(page.locator('.ant-table')).toBeVisible();
    }
  });

  test('pageSize 下拉可交互', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/list');
    await page.waitForLoadState('networkidle');
    const sizeChanger = page.locator('.ant-pagination-options-size-changer');
    if (await sizeChanger.isVisible()) {
      await sizeChanger.click();
      const dropdown = page.locator('.ant-select-dropdown:not(.ant-select-dropdown-hidden)');
      await expect(dropdown).toBeVisible();
    }
  });
});
