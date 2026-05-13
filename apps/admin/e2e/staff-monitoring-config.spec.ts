import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

// ---------------------------------------------------------------------------
// 1. 员工管理
// ---------------------------------------------------------------------------

test.describe('员工管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('员工列表页面加载', async ({ page }) => {
    await page.goto('/organization/staff');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/organization\/staff/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('新增员工', async ({ page }) => {
    const name = `测试员工${Date.now().toString().slice(-4)}`;
    const phone = `138${Date.now().toString().slice(-8)}`;

    await page.goto('/organization/staff');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增/ }).click();
    await expect(page).toHaveURL(/\/organization\/staff\/create/);

    await page.getByLabel(/用户名|账号/).fill(`user${Date.now().toString().slice(-6)}`);
    await page.getByLabel(/姓名/).fill(name);
    await page.getByLabel(/手机号/).fill(phone);
    await page.getByLabel(/角色/).click();
    await page.getByTitle(/管理员|角色/).first().click();

    await page.getByRole('button', { name: /创\s*建|保\s*存/ }).click();
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/organization\/staff/);
  });

  test('编辑员工', async ({ page }) => {
    await page.goto('/organization/staff');
    await page.waitForLoadState('networkidle');

    const editLink = page.getByRole('row').first().getByText('编辑');
    await editLink.click();
    await expect(page).toHaveURL(/\/staff\/.*\/edit/);
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-pro-form, .ant-form, form')).toBeVisible();
  });

  test('员工密码重置', async ({ page }) => {
    await page.goto('/organization/staff');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').nth(1);
    const moreBtn = row.locator('.ant-dropdown-trigger, [data-testid="more-actions"]').first();
    if (await moreBtn.isVisible()) {
      await moreBtn.click();
      const resetBtn = page.getByText('重置密码');
      if (await resetBtn.isVisible()) {
        await resetBtn.click();
        await expect(page.getByText(/确定重置密码/)).toBeVisible();
        await page.getByRole('button', { name: /确\s*定/ }).click();
        await page.waitForLoadState('networkidle');
      }
    }
  });
});

// ---------------------------------------------------------------------------
// 2. 用户反馈
// ---------------------------------------------------------------------------

test.describe('用户反馈', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('反馈列表页面加载', async ({ page }) => {
    await page.goto('/content-center/feedback');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/content-center\/feedback/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('反馈详情查看', async ({ page }) => {
    await page.goto('/content-center/feedback');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').nth(1);
    if (await row.isVisible()) {
      const viewBtn = row.getByText(/查看|详情/);
      if (await viewBtn.isVisible()) {
        await viewBtn.click();
        await expect(page.locator('.ant-drawer')).toBeVisible();
      }
    }
  });

  test('反馈回复', async ({ page }) => {
    await page.goto('/content-center/feedback');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').nth(1);
    if (await row.isVisible()) {
      const replyBtn = row.getByText('回复');
      if (await replyBtn.isVisible()) {
        await replyBtn.click();
        await expect(page.locator('.ant-modal')).toBeVisible();
        await page.getByLabel(/回复内容/).fill('已收到您的反馈，我们会尽快处理。');
        await page.getByRole('button', { name: /确\s*定|提\s*交/ }).click();
        await page.waitForLoadState('networkidle');
      }
    }
  });
});

// ---------------------------------------------------------------------------
// 3. 黑名单管理
// ---------------------------------------------------------------------------

test.describe('黑名单管理', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('黑名单列表加载', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/blacklist/);
    await expect(page.locator('.ant-table, .ant-pro-table')).toBeVisible();
  });

  test('新增黑名单', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    const addBtn = page.getByRole('button', { name: /添加黑名单|新增/ });
    await addBtn.click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    await page.getByLabel(/关键词|手机号|身份证/).fill('13900001111');
    await page.getByRole('button', { name: /确\s*定|添\s*加/ }).click();
    await page.waitForLoadState('networkidle');
  });

  test('删除黑名单', async ({ page }) => {
    await page.goto('/system/blacklist');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').nth(1);
    if (await row.isVisible()) {
      const releaseBtn = row.getByText(/解禁|删除/);
      if (await releaseBtn.isVisible()) {
        await releaseBtn.click();
        await page.getByRole('button', { name: /确\s*定/ }).click();
        await page.waitForLoadState('networkidle');
      }
    }
  });
});

// ---------------------------------------------------------------------------
// 4. 邮件接收人
// ---------------------------------------------------------------------------

test.describe('邮件接收人', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('邮件接收人列表加载', async ({ page }) => {
    await page.goto('/system/config/email-recipients');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/config\/email-recipients/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('新增接收人', async ({ page }) => {
    await page.goto('/system/config/email-recipients');
    await page.waitForLoadState('networkidle');

    await page.getByRole('button', { name: /新增|创建/ }).click();
    await expect(page.locator('.ant-modal')).toBeVisible();

    await page.getByLabel(/邮箱/).fill('test@example.com');
    await page.getByLabel(/姓名|接收人/).fill('测试接收人');
    await page.getByRole('button', { name: /确\s*定|创\s*建|保\s*存/ }).click();
    await page.waitForLoadState('networkidle');
  });

  test('删除接收人', async ({ page }) => {
    await page.goto('/system/config/email-recipients');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').nth(1);
    if (await row.isVisible()) {
      const deleteBtn = row.getByText(/删除/);
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        await page.getByRole('button', { name: /确\s*定/ }).click();
        await page.waitForLoadState('networkidle');
      }
    }
  });
});

// ---------------------------------------------------------------------------
// 5. 系统监控
// ---------------------------------------------------------------------------

test.describe('系统监控', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('操作日志页面加载', async ({ page }) => {
    await page.goto('/system/monitoring/log');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/monitoring\/log/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('操作日志筛选', async ({ page }) => {
    await page.goto('/system/monitoring/log');
    await page.waitForLoadState('networkidle');

    const moduleSelect = page.getByLabel(/模块/);
    if (await moduleSelect.isVisible()) {
      await moduleSelect.click();
      await page.getByTitle(/医生管理|预约管理/).first().click();
      await page.getByRole('button', { name: /查\s*询|搜\s*索/ }).click();
      await page.waitForLoadState('networkidle');
    }
  });

  test('通知日志页面加载', async ({ page }) => {
    await page.goto('/system/monitoring/notification-logs');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/monitoring\/notification-logs/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('签到审计页面加载', async ({ page }) => {
    await page.goto('/system/monitoring/checkin-audit-logs');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/monitoring\/checkin-audit-logs/);
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  test('在线用户页面加载', async ({ page }) => {
    await page.goto('/system/monitoring/online-users');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/monitoring\/online-users/);
    await expect(page.locator('.ant-table, .ant-card')).toBeVisible();
  });

  test('在线用户踢出', async ({ page }) => {
    await page.goto('/system/monitoring/online-users');
    await page.waitForLoadState('networkidle');

    const kickBtn = page.getByRole('button', { name: /强制下线|踢出/ });
    if (await kickBtn.isVisible()) {
      await kickBtn.click();
      await page.getByRole('button', { name: /确\s*定/ }).click();
      await page.waitForLoadState('networkidle');
    }
  });
});

// ---------------------------------------------------------------------------
// 6. 图片配置
// ---------------------------------------------------------------------------

test.describe('图片配置', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
  });

  test('图片配置页面加载', async ({ page }) => {
    await page.goto('/system/config/image-config');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/\/system\/config\/image-config/);
    await expect(page.locator('.ant-pro-form, .ant-form, form, .ant-tabs')).toBeVisible();
  });

  test('图片配置修改', async ({ page }) => {
    await page.goto('/system/config/image-config');
    await page.waitForLoadState('networkidle');

    const qualityInput = page.getByLabel(/压缩质量/);
    if (await qualityInput.isVisible()) {
      await qualityInput.clear();
      await qualityInput.fill('90');
      await page.getByRole('button', { name: /保\s*存/ }).click();
      await page.waitForLoadState('networkidle');
    }
  });
});
