import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('排班模块 E2E 测试', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  // ---------------------------------------------------------------------------
  // 1. 排班规则列表加载
  // ---------------------------------------------------------------------------

  test('排班规则列表页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/rule/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // 2. 新增排班规则
  // ---------------------------------------------------------------------------

  test('新增排班规则', async ({ page }) => {
    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增规则/ }).click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/schedule\/rule\/create/);

    // Step 1: 基本信息
    await expect(page.getByText('基础信息')).toBeVisible();

    await page.getByLabel('规则名称').fill('测试排班规则');
    await page.getByLabel('所属门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('选择科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('选择医生').click();
    await page.getByTitle(/李医生/).click();
    await page.getByLabel('班次类型').click();
    await page.locator('.ant-select-item-option').first().click();

    // Step 2: 时间配置
    await page.getByRole('button', { name: '下一步' }).click();
    await expect(page.getByText('排班设置')).toBeVisible();

    await page.getByLabel('选择星期').locator('input[type="checkbox"]').first().check({ force: true });
    await page.getByLabel('开始时间').click();
    await page.locator('.ant-picker').first().fill('09:00');
    await page.getByLabel('结束时间').click();
    await page.locator('.ant-picker').last().fill('12:00');

    // Step 3: 高级设置 -> 提交
    await page.getByRole('button', { name: '下一步' }).click();
    await page.getByRole('button', { name: '创建' }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/rule$/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 3. 编辑排班规则
  // ---------------------------------------------------------------------------

  test('编辑排班规则', async ({ page }) => {
    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row, .ant-pro-table-row').first();
    if (await row.count() === 0) {
      return;
    }

    await row.locator('a').filter({ hasText: /操作/ }).click();
    await page.getByText('编辑', { exact: true }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/rule\/.*\/edit/);

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    await page.getByLabel('规则名称').clear();
    await page.getByLabel('规则名称').fill('已编辑排班规则');

    await page.getByRole('button', { name: '下一步' }).click();
    await page.getByRole('button', { name: '下一步' }).click();
    await page.getByRole('button', { name: '保存' }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/rule$/);
  });

  // ---------------------------------------------------------------------------
  // 4. 排班列表页面
  // ---------------------------------------------------------------------------

  test('排班列表页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/list');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/list/);
    await expect(page.locator('.ant-pro-table, .ant-table, .ant-pro-card')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // 5. 排班日历页面
  // ---------------------------------------------------------------------------

  test('排班日历页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/calendar');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/calendar/);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(page.getByText(/404|页面不存在/)).toHaveCount(0);
  });

  test('排班日历月/周视图切换', async ({ page }) => {
    await page.goto('/medical-services/schedule/calendar');
    await page.waitForLoadState('networkidle');

    const weekBtn = page.getByRole('button', { name: /周/ });
    const monthBtn = page.getByRole('button', { name: /月/ });

    if (await weekBtn.count() > 0) {
      await weekBtn.click();
      await page.waitForTimeout(300);
    }

    if (await monthBtn.count() > 0) {
      await monthBtn.click();
      await page.waitForTimeout(300);
    }

    await expect(page.getByText(/404|页面不存在/)).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 6. 排班甘特图页面
  // ---------------------------------------------------------------------------

  test('排班甘特图页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/gantt');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/gantt/);

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
    await expect(page.getByText(/404|页面不存在/)).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 7. 自定义排班列表
  // ---------------------------------------------------------------------------

  test('自定义排班列表页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/custom');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/custom/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // 8. 添加自定义排班
  // ---------------------------------------------------------------------------

  test('添加自定义排班', async ({ page }) => {
    await page.goto('/medical-services/schedule/custom');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /添加/ }).click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/schedule\/custom\/create/);

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    await page.getByLabel('选择门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('选择科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('选择医生').click();
    await page.getByTitle(/李医生/).click();

    await page.getByLabel('排班日期').click();
    await page.locator('.ant-picker').first().fill('2026-06-01');
    await page.locator('.ant-picker').last().fill('2026-06-07');

    await page.getByRole('button', { name: /创建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/custom$/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 9. 休息日设置列表
  // ---------------------------------------------------------------------------

  test('休息日设置列表页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/rest-day');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/rest-day/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // 10. 添加休息日
  // ---------------------------------------------------------------------------

  test('添加休息日', async ({ page }) => {
    await page.goto('/medical-services/schedule/rest-day');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /添加/ }).click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/schedule\/rest-day\/create/);

    await expect(page.locator('form, .ant-form, .ant-pro-form')).toBeVisible();

    await page.getByLabel('选择门店').click();
    await page.getByTitle('示例门店').click();

    await page.getByLabel('休息原因').fill('节假日休息');

    await page.getByLabel('休息日期').click();
    await page.locator('.ant-picker').first().fill('2026-06-15');
    await page.locator('.ant-picker').last().fill('2026-06-16');

    await page.getByRole('button', { name: /创建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/rest-day$/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 11. 停诊管理页面
  // ---------------------------------------------------------------------------

  test('停诊管理页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/suspension');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/suspension/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('停诊管理 - 添加停诊弹窗', async ({ page }) => {
    await page.goto('/medical-services/schedule/suspension');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /添加/ }).click();

    await expect(page.locator('.ant-modal, .ant-modal-wrap')).toBeVisible();
    await expect(page.getByText('添加停诊')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // 12. 停诊审核页面
  // ---------------------------------------------------------------------------

  test('停诊审核页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/leave-request');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/leave-request/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  // ---------------------------------------------------------------------------
  // 13. 排班统计页面
  // ---------------------------------------------------------------------------

  test('排班统计页面加载', async ({ page }) => {
    await page.goto('/medical-services/schedule/statistics');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/schedule\/statistics/);
    await expect(page.getByText('查询条件')).toBeVisible();
  });

  test('排班统计 - 查询条件表单', async ({ page }) => {
    await page.goto('/medical-services/schedule/statistics');
    await page.waitForLoadState('networkidle');

    await expect(page.getByText('选择门店')).toBeVisible();
    await expect(page.getByText('选择月份')).toBeVisible();
    await expect(page.getByRole('button', { name: /查询/ })).toBeVisible();
  });
});
