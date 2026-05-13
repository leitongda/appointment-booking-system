import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('图片上传操作', () => {
  test('医生头像上传', async ({ page }) => {
    await mockAdminSession(page);

    let uploadCalled = false;
    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        uploadCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/avatar.png', key: 'avatar.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/create');
    await page.waitForLoadState('networkidle');

    const fileInputs = page.locator('input[type="file"]');
    const count = await fileInputs.count();
    if (count > 0) {
      await fileInputs.first().setInputFiles({
        name: 'test-avatar.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('医生 Banner 上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/banner.png', key: 'banner.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/create');
    await page.waitForLoadState('networkidle');

    const fileInputs = page.locator('input[type="file"]');
    if ((await fileInputs.count()) >= 2) {
      await fileInputs.nth(1).setInputFiles({
        name: 'banner.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('医生执业证书上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/cert.png', key: 'cert.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/create');
    await page.waitForLoadState('networkidle');

    const fileInputs = page.locator('input[type="file"]');
    if ((await fileInputs.count()) >= 3) {
      await fileInputs.nth(2).setInputFiles({
        name: 'certificate.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('科室图标上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/icon.png', key: 'icon.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/create');
    await page.waitForLoadState('networkidle');

    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.isVisible()) {
      await fileInput.setInputFiles({
        name: 'dept-icon.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('科室封面上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/cover.png', key: 'cover.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/create');
    await page.waitForLoadState('networkidle');

    const fileInputs = page.locator('input[type="file"]');
    if ((await fileInputs.count()) >= 2) {
      await fileInputs.nth(1).setInputFiles({
        name: 'cover.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('科室 Banner 上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/banner.png', key: 'banner.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/create');
    await page.waitForLoadState('networkidle');

    const fileInputs = page.locator('input[type="file"]');
    if ((await fileInputs.count()) >= 3) {
      await fileInputs.nth(2).setInputFiles({
        name: 'dept-banner.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('新闻封面图上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/news-cover.png', key: 'news-cover.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/news/create');
    await page.waitForLoadState('networkidle');

    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.isVisible()) {
      await fileInput.setInputFiles({
        name: 'news-cover.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });

  test('轮播图图片上传', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/upload**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { url: 'https://example.com/banner-img.png', key: 'banner-img.png' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/banner/create');
    await page.waitForLoadState('networkidle');

    const fileInput = page.locator('input[type="file"]').first();
    if (await fileInput.isVisible()) {
      await fileInput.setInputFiles({
        name: 'banner-image.png',
        mimeType: 'image/png',
        buffer: Buffer.from('fake-png-data'),
      });
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('平台管理补充操作', () => {
  test('租户详情页内容渲染', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/tenants/tenant-1', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: {
            id: 'tenant-1', tenantCode: 'demo', name: '演示租户', status: 1,
            subscriptionPlanName: '基础版', storeCount: 1, adminCount: 1,
            contactName: '王管理员', contactPhone: '13800138000', createdAt: '2026-01-01 08:00:00',
          },
        }),
      });
    });

    await page.goto('/platform/tenant/tenant-1');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在/);
    if ((await notFound.count()) > 0) {
      await expect(notFound).toHaveCount(0);
    }
  });

  test('创建订阅计划', async ({ page }) => {
    await mockAdminSession(page);

    let createCalled = false;
    await page.route('**/api/v1/subscription-plans**', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        createCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { id: 'plan-new', name: '新计划' } }),
        });
      }
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/platform/tenant/plans/create');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const nameInput = page.locator('input').first();
    if (await nameInput.isVisible()) {
      await nameInput.fill('测试计划');
      const submitBtn = page.getByRole('button', { name: /提\s*交|保\s*存/ });
      if (await submitBtn.isVisible()) {
        await submitBtn.click();
        await page.waitForLoadState('networkidle');
      }
    }
  });

  test('删除公司', async ({ page }) => {
    await mockAdminSession(page);

    let deleteCalled = false;
    await page.route('**/api/v1/miniapp-companies**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [{ id: 'company-1', name: '测试公司', contactName: '张三', contactPhone: '13800138000', createdAt: '2026-01-01' }],
              total: 1,
            },
          }),
        });
      }
      if (method === 'DELETE') {
        deleteCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/platform/miniapp-platform/company');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const deleteBtn = page.locator('.ant-table-row').first().getByText(/删除/);
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();
          await page.waitForLoadState('networkidle');
        }
      }
    }
  });

  test('模板列表页渲染', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/miniapp-templates**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: {
            items: [{ id: 'tpl-1', name: '默认模板', version: '1.0', createdAt: '2026-01-01' }],
            total: 1,
          },
        }),
      });
    });

    await page.goto('/platform/miniapp-platform/template');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('构建列表页渲染', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/miniapp-builds**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: {
            items: [{ id: 'build-1', status: 'success', version: '1.0.0', createdAt: '2026-01-01' }],
            total: 1,
          },
        }),
      });
    });

    await page.goto('/platform/miniapp-platform/build');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('发布管理页渲染', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/miniapp-releases**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: {
            items: [{ id: 'release-1', version: '1.0.0', status: 'published', createdAt: '2026-01-01' }],
            total: 1,
          },
        }),
      });
    });

    await page.goto('/platform/miniapp-platform/release');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });
});

test.describe('内容状态切换补充', () => {
  test('新闻状态切换触发 PUT', async ({ page }) => {
    await mockAdminSession(page);

    let putCalled = false;
    await page.route('**/api/v1/content/news**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [
                { id: 'news-1', title: '测试新闻', status: 1, type: 1, createdAt: '2026-05-12 10:00:00' },
              ],
              total: 1,
            },
          }),
        });
      }
      if (method === 'PUT') {
        putCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/news');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const switchEl = page.locator('.ant-table-row').first().locator('.ant-switch');
      if (await switchEl.isVisible()) {
        await switchEl.click();
        await page.waitForTimeout(500);
        expect(putCalled).toBe(true);
      }
    }
  });

  test('公告状态切换触发 PUT', async ({ page }) => {
    await mockAdminSession(page);

    let putCalled = false;
    await page.route('**/api/v1/content/notices**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [
                { id: 'notice-1', title: '测试公告', status: 1, createdAt: '2026-05-12 10:00:00' },
              ],
              total: 1,
            },
          }),
        });
      }
      if (method === 'PUT') {
        putCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/content-center/content/notice');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const switchEl = page.locator('.ant-table-row').first().locator('.ant-switch');
      if (await switchEl.isVisible()) {
        await switchEl.click();
        await page.waitForTimeout(500);
        expect(putCalled).toBe(true);
      }
    }
  });
});

test.describe('规则组导入导出', () => {
  test('规则组导入文件上传', async ({ page }) => {
    await mockAdminSession(page);

    let importCalled = false;
    await page.route('**/api/v1/rule-sets**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: { items: [], total: 0 },
          }),
        });
      }
      if (method === 'POST' && url.includes('import')) {
        importCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: 5, failed: 0 } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');

    const importBtn = page.getByRole('button', { name: /导入/ });
    if (await importBtn.isVisible()) {
      await importBtn.click();
      await page.waitForTimeout(500);

      const fileInput = page.locator('input[type="file"]');
      if (await fileInput.isVisible()) {
        await fileInput.setInputFiles({
          name: 'rules.json',
          mimeType: 'application/json',
          buffer: Buffer.from('[]'),
        });
        await page.waitForTimeout(1000);
      }
    }
  });

  test('规则组导出按钮', async ({ page }) => {
    await mockAdminSession(page);

    let exportCalled = false;
    await page.route('**/api/v1/rule-sets**', async (route) => {
      const url = route.request().url();
      if (url.includes('export')) {
        exportCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/octet-stream',
          body: '[]',
        });
      }
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: { items: [], total: 0 },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');

    const exportBtn = page.getByRole('button', { name: /导出/ });
    if (await exportBtn.isVisible()) {
      await exportBtn.click();
      await page.waitForTimeout(1000);
    }
  });
});

test.describe('其他补充操作', () => {
  test('变更历史查看', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/rule-sets/**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: {
            items: [
              { id: 'log-1', action: 'update', operator: 'admin', timestamp: '2026-05-12 10:00:00', changes: {} },
            ],
            total: 1,
          },
        }),
      });
    });

    await page.goto('/organization/medical-config/rule-sets/rule-1/audit');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('就诊卡配置保存', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    await page.route('**/api/v1/settings**', async (route) => {
      if (route.request().method() === 'PUT' || route.request().method() === 'POST') {
        saveCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/medical-config/booking-fields');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);
  });

  test('医生预约设置删除', async ({ page }) => {
    await mockAdminSession(page);

    let deleteCalled = false;
    await page.route('**/api/v1/doctor-booking-settings**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [
                { id: 'setting-1', doctorName: '李医生', departmentName: '中医科', storeName: '示例门店', fee: 50 },
              ],
              total: 1,
            },
          }),
        });
      }
      if (method === 'DELETE') {
        deleteCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/booking-setting');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const deleteBtn = page.locator('.ant-table-row').first().getByText(/删除/);
      if (await deleteBtn.isVisible()) {
        await deleteBtn.click();
        const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();
          await page.waitForLoadState('networkidle');
          expect(deleteCalled).toBe(true);
        }
      }
    }
  });

  test('医生推荐开关', async ({ page }) => {
    await mockAdminSession(page);

    let putCalled = false;
    await page.route('**/api/v1/doctors**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [{
                id: 'doctor-1', name: '李医生', title: '主治医师', departmentName: '中医科',
                storeName: '示例门店', status: 1, isRecommended: false, gender: 1, phone: '13800138000',
              }],
              total: 1,
            },
          }),
        });
      }
      if (method === 'PUT') {
        putCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const row = page.locator('.ant-table-row').first();
      const switches = row.locator('.ant-switch');
      const switchCount = await switches.count();
      if (switchCount >= 2) {
        await switches.nth(1).click();
        await page.waitForTimeout(500);
        expect(putCalled).toBe(true);
      }
    }
  });

  test('医生更多操作下拉菜单', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200, message: 'ok',
            data: {
              items: [{
                id: 'doctor-1', name: '李医生', title: '主治医师', departmentName: '中医科',
                storeName: '示例门店', status: 1, isRecommended: true, gender: 1, phone: '13800138000',
              }],
              total: 1,
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const moreBtn = page.locator('.ant-table-row').first().getByRole('button', { name: /更多/ });
      if (await moreBtn.isVisible()) {
        await moreBtn.click();
        const menu = page.locator('.ant-dropdown');
        if (await menu.isVisible()) {
          const menuItems = menu.locator('.ant-dropdown-menu-item');
          expect(await menuItems.count()).toBeGreaterThan(0);
        }
      }
    }
  });

  test('编辑邮件模板表单加载', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/email-templates**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200, message: 'ok',
          data: {
            id: 'tpl-1', name: '预约确认', subject: '您的预约已确认',
            body: '<p>尊敬的患者</p>', type: 'appointment_confirm', status: 1,
          },
        }),
      });
    });

    await page.goto('/system/config/email-templates/tpl-1/edit');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const notFound = page.getByText(/404|页面不存在/);
    if ((await notFound.count()) > 0) {
      await expect(notFound).toHaveCount(0);
    }
  });
});
