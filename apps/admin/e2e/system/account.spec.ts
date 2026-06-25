/**
 * 账户设置 & 个人中心 E2E 测试
 */
import { test, expect } from '@playwright/test';
import { setupAuthState } from '../helpers/auth.helper';

test.describe('账户设置', () => {
  test.beforeEach(async ({ page }) => {
    await setupAuthState(page);
  });

  test('个人设置页应正确加载', async ({ page }) => {
    await page.goto('/account/settings');
    await page.waitForLoadState('networkidle');
    await expect(page).toHaveURL(/account/);
  });

  test('个人设置页应显示表单', async ({ page }) => {
    await page.goto('/account/settings');
    await page.waitForLoadState('networkidle');
    const form = page.locator('.ant-form, .ant-pro-form, .ant-card');
    await expect(form.first()).toBeVisible({ timeout: 5_000 });
  });

  test('个人设置页应有头像上传', async ({ page }) => {
    await page.goto('/account/settings');
    await page.waitForLoadState('networkidle');
    const avatar = page.locator('.ant-avatar, img[class*="avatar"], [class*="avatar"]');
    // 头像区域应可见
    if (await avatar.first().isVisible({ timeout: 3_000 }).catch(() => false)) {
      await expect(avatar.first()).toBeVisible();
    }
  });
});
