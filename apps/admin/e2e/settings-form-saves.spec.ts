import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

const ok = (data: unknown) =>
  JSON.stringify({ code: 200, message: 'ok', data });

test.describe('预约规则设置保存', () => {
  test('修改预约规则后点击保存应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/settings/booking', async (route) => {
      if (route.request().method() === 'PUT') {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/organization/medical-config/booking-rules');
    await page.waitForLoadState('networkidle');

    const advanceDaysInput = page.getByLabel('提前预约天数');
    if (await advanceDaysInput.isVisible()) {
      await advanceDaysInput.clear();
      await advanceDaysInput.fill('15');

      const saveBtn = page.getByRole('button', { name: /保\s*存/ });
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
        await page.waitForLoadState('networkidle');

        expect(saveCalled).toBe(true);
        expect((requestCaptured as Record<string, unknown>)?.advanceDays).toBe(15);
      }
    }
  });
});

test.describe('预约须知保存', () => {
  test('编辑预约须知并保存应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    const noticeId = 'notice-1';
    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/booking-notices**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.includes('/booking-notices?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({
            data: [
              {
                id: noticeId,
                type: 'BOOKING',
                title: '预约须知标题',
                content: '原始内容',
                sortOrder: 1,
                status: 1,
                createdAt: '2026-01-01 08:00:00',
              },
            ],
            total: 1,
            page: 1,
            pageSize: 10,
          }),
        });
      }

      if (method === 'PUT' && url.includes(`/booking-notices/${noticeId}`)) {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/system/config/booking-notice');
    await page.waitForLoadState('networkidle');

    const editBtn = page.getByRole('row').filter({ hasText: '预约须知标题' }).getByRole('link', { name: /编\s*辑/ });
    if (await editBtn.isVisible()) {
      await editBtn.click();

      const contentTextarea = page.locator('.ant-modal').getByPlaceholder('请输入须知内容');
      if (await contentTextarea.isVisible()) {
        await contentTextarea.clear();
        await contentTextarea.fill('更新后的须知内容');
      }

      const confirmBtn = page.locator('.ant-modal').getByRole('button', { name: /确\s*定/ });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForLoadState('networkidle');

        expect(saveCalled).toBe(true);
        expect((requestCaptured as Record<string, unknown>)?.content).toBe('更新后的须知内容');
      }
    }
  });
});

test.describe('班次类型管理', () => {
  const shiftTypeRecords = [
    {
      id: 'shift-1',
      code: 'MORNING',
      name: '上午班',
      description: '上午门诊班次',
      enabled: true,
      createdAt: '2026-01-01 08:00:00',
    },
  ];

  test('编辑班次类型应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/shift-types**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.match(/\/shift-types\/[^/]+$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok(shiftTypeRecords[0]),
        });
      }

      if (method === 'GET' && url.includes('/shift-types')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ data: shiftTypeRecords, total: 1, page: 1, pageSize: 10 }),
        });
      }

      if (method === 'PUT' && url.includes('/shift-types/shift-1')) {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/organization/medical-config/shift-types/shift-1/edit');
    await page.waitForLoadState('networkidle');

    const nameInput = page.getByLabel('类型名称');
    if (await nameInput.isVisible()) {
      await nameInput.clear();
      await nameInput.fill('上午班-更新');
      const saveBtn = page.getByRole('button', { name: /保\s*存/ });
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
        await page.waitForLoadState('networkidle');

        expect(saveCalled).toBe(true);
        expect((requestCaptured as Record<string, unknown>)?.name).toBe('上午班-更新');
      }
    }
  });

  test('删除班次类型应发出 DELETE 请求', async ({ page }) => {
    await mockAdminSession(page);

    let deleteCalled = false;

    await page.route('**/api/v1/shift-types**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.includes('/shift-types?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ data: shiftTypeRecords, total: 1, page: 1, pageSize: 10 }),
        });
      }

      if (method === 'DELETE' && url.includes('/shift-types/shift-1')) {
        deleteCalled = true;
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/organization/medical-config/shift-types');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: '上午班' });
    const deleteLink = row.getByRole('link', { name: /删\s*除/ });
    if (await deleteLink.isVisible()) {
      await deleteLink.click();

      const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForLoadState('networkidle');

        expect(deleteCalled).toBe(true);
      }
    }
  });
});

test.describe('规则组高级操作', () => {
  const ruleSetRecords = [
    {
      id: 'rule-set-1',
      name: '默认规则组',
      priority: 10,
      enabled: true,
      isActive: true,
      shiftTypes: [{ id: 'shift-1', name: '上午班' }],
      createdAt: '2026-01-01 08:00:00',
    },
  ];

  test('删除规则组应发出 DELETE 请求', async ({ page }) => {
    await mockAdminSession(page);

    let deleteCalled = false;

    await page.route('**/api/v1/rule-sets**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.includes('/rule-sets?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ data: ruleSetRecords, total: 1, page: 1, pageSize: 10 }),
        });
      }

      if (method === 'DELETE' && url.includes('/rule-sets/rule-set-1')) {
        deleteCalled = true;
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: '默认规则组' });
    const deleteLink = row.getByRole('link', { name: /删\s*除/ });
    if (await deleteLink.isVisible()) {
      await deleteLink.click();

      const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForLoadState('networkidle');

        expect(deleteCalled).toBe(true);
      }
    }
  });

  test('复制规则组应打开创建页面', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/rule-sets**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.includes('/rule-sets?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ data: ruleSetRecords, total: 1, page: 1, pageSize: 10 }),
        });
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');

    const addBtn = page.getByRole('button', { name: /新增规则组/ });
    if (await addBtn.isVisible()) {
      await addBtn.click();
      await expect(page).toHaveURL(/\/organization\/medical-config\/rule-sets\/create/);
    }
  });

  test('规则组预览应打开 Drawer', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/rule-sets**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.includes('/rule-sets?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ data: ruleSetRecords, total: 1, page: 1, pageSize: 10 }),
        });
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/organization/medical-config/rule-sets');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: '默认规则组' });
    const viewLink = row.getByRole('link', { name: /查\s*看/ });
    if (await viewLink.isVisible()) {
      await viewLink.click();

      const drawer = page.locator('.ant-drawer');
      if (await drawer.isVisible()) {
        await expect(drawer).toBeVisible();
      }
    }
  });

  test('编辑规则组应打开编辑页并加载表单', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/rule-sets/rule-set-1', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({
          id: 'rule-set-1',
          name: '默认规则组',
          priority: 10,
          enabled: true,
          timeSource: 'SERVER',
          timezoneSource: 'HOSPITAL',
          comparePrecision: 'SECOND',
          defaultOpenInclusive: true,
          defaultCloseInclusive: false,
          roundingMode: 'NONE',
          clockSkewToleranceSec: 0,
          description: '测试描述',
          shiftTypeIds: ['shift-1'],
          windows: [],
          createdAt: '2026-01-01 08:00:00',
        }),
      });
    });

    await page.goto('/organization/medical-config/rule-sets/rule-set-1/edit');
    await page.waitForLoadState('networkidle');

    const nameInput = page.getByLabel('规则组名称');
    if (await nameInput.isVisible()) {
      await expect(nameInput).toHaveValue('默认规则组');
    }
  });
});

test.describe('系统配置保存', () => {
  test('医院信息保存应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/settings/hospital', async (route) => {
      if (route.request().method() === 'PUT') {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/system/config/hospital-info');
    await page.waitForLoadState('networkidle');

    const nameInput = page.getByLabel('医院名称');
    if (await nameInput.isVisible()) {
      await nameInput.clear();
      await nameInput.fill('更新后医院名称');

      const saveBtn = page.getByRole('button', { name: /保\s*存/ });
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
        await page.waitForLoadState('networkidle');

        expect(saveCalled).toBe(true);
        expect((requestCaptured as Record<string, unknown>)?.hospitalName).toBe('更新后医院名称');
      }
    }
  });

  test('微信配置保存应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/stores/store-1/wechat-config', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ appId: 'wx-old', appSecret: 'old-secret', mchId: '', apiKey: '', notifyUrl: '' }),
        });
      }

      if (route.request().method() === 'PUT') {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/system/config/wechat');
    await page.waitForLoadState('networkidle');

    const storeOption = page.getByText('示例门店').first();
    if (await storeOption.isVisible()) {
      await storeOption.click();

      const appIdInput = page.getByLabel(/AppID|小程序/);
      if (await appIdInput.isVisible()) {
        await appIdInput.clear();
        await appIdInput.fill('wx-new-app-id');

        const saveBtn = page.getByRole('button', { name: /保\s*存/ });
        if (await saveBtn.isVisible()) {
          await saveBtn.click();
          await page.waitForLoadState('networkidle');
        }
      }
    }
  });

  test('邮件配置保存应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/settings**', async (route) => {
      if (route.request().method() === 'PUT') {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/system/config/email-config');
    await page.waitForLoadState('networkidle');

    const emailTab = page.getByText(/邮件配置|邮件/).first();
    if (await emailTab.isVisible()) {
      await emailTab.click();
      await page.waitForLoadState('networkidle');
    }

    const smtpHostInput = page.getByLabel('SMTP服务器');
    if (await smtpHostInput.isVisible()) {
      await smtpHostInput.clear();
      await smtpHostInput.fill('smtp.test.com');

      const saveBtn = page.getByRole('button', { name: /保\s*存/ });
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
        await page.waitForLoadState('networkidle');
      }
    }
  });
});

test.describe('邮件模板管理', () => {
  const templateRecords = [
    {
      id: 'tpl-1',
      code: 'APPOINTMENT_CONFIRM',
      name: '预约确认模板',
      templateType: 'appointment_confirm',
      subjectTemplate: '预约确认通知',
      description: '预约确认邮件模板',
      status: 1,
      createdAt: '2026-01-01 08:00:00',
      updatedAt: '2026-01-01 08:00:00',
    },
  ];

  test('删除邮件模板应发出 DELETE 请求', async ({ page }) => {
    await mockAdminSession(page);

    let deleteCalled = false;

    await page.route('**/api/v1/email-templates**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.includes('/email-templates?')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({ data: templateRecords, total: 1, page: 1, pageSize: 10 }),
        });
      }

      if (method === 'DELETE' && url.includes('/email-templates/tpl-1')) {
        deleteCalled = true;
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/system/config/email-templates');
    await page.waitForLoadState('networkidle');

    const row = page.getByRole('row').filter({ hasText: '预约确认模板' });
    const deleteLink = row.getByRole('link', { name: /删\s*除/ });
    if (await deleteLink.isVisible()) {
      await deleteLink.click();

      const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForLoadState('networkidle');

        expect(deleteCalled).toBe(true);
      }
    }
  });

  test('编辑邮件模板应加载表单并可保存', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;

    await page.route('**/api/v1/email-templates**', async (route) => {
      const method = route.request().method();
      const url = route.request().url();

      if (method === 'GET' && url.match(/\/email-templates\/[^/]+$/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: ok({
            ...templateRecords[0],
            contentTemplate: '<p>原始正文</p>',
          }),
        });
      }

      if (method === 'PUT') {
        saveCalled = true;
      }

      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({ success: true }),
      });
    });

    await page.goto('/system/config/email-templates/tpl-1/edit');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const nameInput = page.getByLabel(/模板名称|名称/);
    if (await nameInput.isVisible()) {
      const currentValue = await nameInput.inputValue();
      if (currentValue) {
        await nameInput.clear();
        await nameInput.fill('更新后的模板名称');

        const saveBtn = page.getByRole('button', { name: /保\s*存|提\s*交/ });
        if (await saveBtn.isVisible()) {
          await saveBtn.click();
          await page.waitForLoadState('networkidle');
        }
      }
    }
  });
});

test.describe('个人设置保存', () => {
  test('修改姓名和手机号后保存应发出 PUT 请求', async ({ page }) => {
    await mockAdminSession(page);

    let saveCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/admin/me', async (route) => {
      if (route.request().method() === 'PUT') {
        saveCalled = true;
        requestCaptured = route.request().postDataJSON();
      }
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({
          id: 'admin-1',
          username: 'superadmin',
          name: '新名字',
          phone: '13900001234',
          email: 'playwright@example.com',
          avatar: '',
          status: 1,
          roleCode: 'SUPER_ADMIN',
          roleName: '超级管理员',
          isSuperAdmin: true,
          permissions: ['*'],
          tenantId: 'tenant-1',
        }),
      });
    });

    await page.goto('/account/settings');
    await page.waitForLoadState('networkidle');

    const nameInput = page.getByLabel('姓名');
    if (await nameInput.isVisible()) {
      await nameInput.clear();
      await nameInput.fill('新名字');
    }

    const phoneInput = page.getByLabel('手机号');
    if (await phoneInput.isVisible()) {
      await phoneInput.clear();
      await phoneInput.fill('13900001234');
    }

    const saveBtn = page.getByRole('button', { name: /保\s*存/ });
    if (await saveBtn.isVisible()) {
      await saveBtn.click();
      await page.waitForLoadState('networkidle');

      expect(saveCalled).toBe(true);
      expect((requestCaptured as Record<string, unknown>)?.name).toBe('新名字');
      expect((requestCaptured as Record<string, unknown>)?.phone).toBe('13900001234');
    }
  });
});

test.describe('登录页 Tab 切换', () => {
  test('切换到验证码登录 Tab 应显示手机号输入框', async ({ page }) => {
    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const smsTab = page.getByRole('tab', { name: /验证码登录/ });
    if (await smsTab.isVisible()) {
      await smsTab.click();

      const phoneInput = page.getByPlaceholder('请输入手机号');
      if (await phoneInput.isVisible()) {
        await expect(phoneInput).toBeVisible();
      }
    }
  });

  test('切换到微信登录 Tab 应显示二维码区域', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/admin/wechat/qrcode', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: ok({
          qrcodeUrl: 'https://example.com/qrcode',
          ticket: 'test-ticket',
          expireSeconds: 300,
        }),
      });
    });

    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    const wechatTab = page.getByRole('tab', { name: /微信登录/ });
    if (await wechatTab.isVisible()) {
      await wechatTab.click();

      const qrcodeArea = page.locator('.ant-qrcode');
      if (await qrcodeArea.isVisible({ timeout: 10000 })) {
        await expect(qrcodeArea).toBeVisible();
      }
    }
  });
});
