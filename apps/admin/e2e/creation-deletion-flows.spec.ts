import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * Admin 端创建 / 删除流程 E2E 测试
 *
 * 覆盖: 班次类型、规则组、诊费类型、邮件模板、公告、轮播图、消息发送
 *       新闻删除、公告删除、轮播图删除
 *
 * 选择器约定:
 * - 创建按钮: getByRole('button', { name: /新增|创建|发布|发送/ })
 * - 表单字段: getByLabel() / getByPlaceholder()
 * - 富文本编辑器: [contenteditable="true"]
 * - 提交按钮: getByRole('button', { name: /创\s*建|保\s*存|发\s*布|发\s*送/ })
 * - 删除操作: getByText('删除') in row, then confirm popconfirm
 */

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

async function seedViaApi(
  page: import('@playwright/test').Page,
  method: 'POST' | 'PUT',
  path: string,
  body: Record<string, unknown>,
) {
  return page.evaluate(
    async ({ m, p, b }) => {
      const res = await fetch(`/api/v1${p}`, {
        method: m,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(b),
      });
      return res.json();
    },
    { m: method, p: path, b: body },
  );
}

// ---------------------------------------------------------------------------
// 1. 班次类型创建 (B14)
// ---------------------------------------------------------------------------

test.describe('创建流程', () => {
  test('班次类型创建 (B14)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/medical-config/shift-types');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增班次类型/ }).click();
    await expect(page).toHaveURL(/\/shift-types\/create/);

    await page.getByLabel('类型代码').fill('OPD');
    await page.getByLabel('类型名称').fill('上午班');

    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/shift-types/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 2. 规则组创建 (B15)
  // ---------------------------------------------------------------------------

  test('规则组创建 (B15)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增规则组/ }).click();
    await expect(page).toHaveURL(/\/rule-sets\/create/);

    await page.getByLabel('规则组名称').fill('默认规则组');
    await page.getByLabel('优先级').fill('10');

    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/rule-sets/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 3. 诊费类型创建 (B16)
  // ---------------------------------------------------------------------------

  test('诊费类型创建 (B16)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/consultation-fee/types');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增诊费类型/ }).click();
    await expect(page).toHaveURL(/\/consultation-fee\/types\/create/);

    await page.getByLabel('类型名称').fill('专家诊费');
    await page.getByLabel('类型编码').fill('expert');

    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/consultation-fee\/types/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 4. 邮件模板创建 (B17)
  // ---------------------------------------------------------------------------

  test('邮件模板创建 (B17)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/system/config/email-templates');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增模板|新增邮件模板/ }).click();
    await expect(page).toHaveURL(/\/email-templates\/create/);

    await page.getByLabel('模板编码').fill('appointment_reminder');
    await page.getByLabel('模板名称').fill('预约提醒模板');
    await page.getByLabel('模板类型').click();
    await page.getByTitle('自定义').click();
    await page.getByLabel('邮件主题').fill('您的预约提醒');

    const editor = page.locator('[contenteditable="true"]').first();
    await editor.click();
    await editor.fill('您的预约已确认，请按时就诊。');

    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/email-templates/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 5. 公告创建 (B18a)
  // ---------------------------------------------------------------------------

  test('公告创建 (B18a)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/content-center/content/notice');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /发布公告/ }).click();
    await expect(page).toHaveURL(/\/notice\/create/);

    await page.getByLabel('标题').fill('系统升级通知');
    await page.getByLabel('类型').click();
    await page.getByTitle('系统公告').click();

    const editor = page.locator('[contenteditable="true"]').first();
    await editor.click();
    await editor.fill('系统将于今晚进行升级维护。');

    await page.getByRole('button', { name: /发\s*布/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/notice/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 6. 轮播图创建 (B18b)
  // ---------------------------------------------------------------------------

  test('轮播图创建 (B18b)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/content-center/content/banner');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增轮播图/ }).click();
    await expect(page).toHaveURL(/\/banner\/create/);

    await page.getByLabel('链接类型').click();
    await page.getByTitle('无链接').click();
    await page.getByLabel('展示位置').click();
    await page.getByTitle('首页').click();
    await page.getByLabel('链接地址').fill('https://example.com/promo');

    await page.getByRole('button', { name: /创\s*建/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/banner/);
    expect(page.url()).not.toContain('/create');
  });

  // ---------------------------------------------------------------------------
  // 7. 消息发送 (B19)
  // ---------------------------------------------------------------------------

  test('消息发送 (B19)', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/content-center/message/list');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /发送消息/ }).click();
    await expect(page).toHaveURL(/\/message\/create/);

    await page.getByLabel('用户ID').fill('patient-001');
    await page.getByLabel('用户类型').click();
    await page.getByTitle('患者').click();
    await page.getByLabel('消息类型').click();
    await page.getByTitle('系统').click();
    await page.getByLabel('标题').fill('预约成功通知');
    await page.getByLabel('内容').fill('您已成功预约明天的门诊。');

    await page.getByRole('button', { name: /发\s*送/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/message/);
  });
});

// ---------------------------------------------------------------------------
// Deletion tests
// ---------------------------------------------------------------------------

test.describe('删除流程', () => {
  // ---------------------------------------------------------------------------
  // 8. 新闻删除 (B34a)
  // ---------------------------------------------------------------------------

  test('新闻删除 (B34a)', async ({ page }) => {
    await mockAdminSession(page);

    const title = `待删除新闻${Date.now()}`;
    await seedViaApi(page, 'POST', '/content/news', {
      title,
      content: '<p>待删除内容</p>',
      type: 1,
    });

    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: title });
    await expect(row).toBeVisible();

    await row.getByText('删除').click();
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('row').filter({ hasText: title })).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 9. 公告删除 (B34b)
  // ---------------------------------------------------------------------------

  test('公告删除 (B34b)', async ({ page }) => {
    await mockAdminSession(page);

    const title = `待删除公告${Date.now()}`;
    await seedViaApi(page, 'POST', '/content/notices', {
      title,
      content: '<p>待删除公告内容</p>',
      type: 1,
    });

    await page.goto('/content-center/content/notice');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: title });
    await expect(row).toBeVisible();

    await row.getByText('删除').click();
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(page.getByRole('row').filter({ hasText: title })).toHaveCount(0);
  });

  // ---------------------------------------------------------------------------
  // 10. 轮播图删除 (B34c)
  // ---------------------------------------------------------------------------

  test('轮播图删除 (B34c)', async ({ page }) => {
    await mockAdminSession(page);

    const linkUrl = `https://example.com/banner-${Date.now()}`;
    await seedViaApi(page, 'POST', '/content/banners', {
      title: '待删除轮播图',
      imageUrl: '/uploads/test.jpg',
      linkType: 0,
      position: 'home',
      linkUrl,
      sortOrder: 99,
    });

    await page.goto('/content-center/content/banner');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: '待删除轮播图' });
    await expect(row).toBeVisible();

    await row.getByText('删除').click();
    await page.getByRole('button', { name: /确\s*定/ }).click();
    await page.waitForLoadState('networkidle');

    await expect(
      page.getByRole('row').filter({ hasText: '待删除轮播图' }),
    ).toHaveCount(0);
  });
});
