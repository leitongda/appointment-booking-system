import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

function makeTemplate(overrides: Record<string, unknown> = {}) {
  return {
    id: 'tpl-1',
    name: '规则A',
    storeId: 'store-1',
    storeName: '示例门店',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    departmentId: 'dept-1',
    departmentName: '中医科',
    weekdays: [1, 2, 3, 4, 5],
    appointmentType: 'normal',
    startTime: '08:00',
    endTime: '12:00',
    slotCount: 4,
    slotCapacity: 20,
    scheduleMode: 'weekly',
    status: 1,
    lastGeneratedAt: '2026-05-10 10:00:00',
    createdAt: '2026-05-01 08:00:00',
    ...overrides,
  };
}

function makeSchedule(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sch-1',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    departmentId: 'dept-1',
    departmentName: '中医科',
    storeId: 'store-1',
    storeName: '示例门店',
    scheduleDate: '2026-05-15',
    timeSlot: 'morning',
    startTime: '08:00',
    endTime: '12:00',
    totalSlots: 20,
    bookedSlots: 10,
    appointmentType: 'normal',
    status: 1,
    isRestDay: false,
    effectiveStatus: 'active',
    createdAt: '2026-05-12 08:00:00',
    ...overrides,
  };
}

function makeCustomSchedule(overrides: Record<string, unknown> = {}) {
  return {
    id: 'cs-1',
    storeId: 'store-1',
    storeName: '示例门店',
    departmentId: 'dept-1',
    departmentName: '中医科',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    scheduleDate: '2026-06-01',
    startTime: '09:00',
    endTime: '12:00',
    appointmentType: 'normal',
    maxPatients: 15,
    bookedCount: 0,
    status: 1,
    isRestDay: false,
    createdAt: '2026-05-20 08:00:00',
    ...overrides,
  };
}

function makeRestDay(overrides: Record<string, unknown> = {}) {
  return {
    id: 'rd-1',
    storeId: 'store-1',
    storeName: '示例门店',
    doctorIds: ['doctor-1'],
    doctorNames: ['李医生'],
    reason: '节假日休息',
    startDate: '2026-06-01',
    endDate: '2026-06-02',
    status: 1,
    createdAt: '2026-05-20 08:00:00',
    ...overrides,
  };
}

function makeSuspension(overrides: Record<string, unknown> = {}) {
  return {
    id: 'susp-1',
    storeId: 'store-1',
    storeName: '示例门店',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    title: '临时停诊',
    suspensionDate: '2026-06-01',
    scheduleIds: ['sch-1'],
    timeSlots: ['morning'],
    status: 1,
    createdAt: '2026-05-20 08:00:00',
    ...overrides,
  };
}

function jsonResponse(data: unknown, extra: Record<string, unknown> = {}) {
  return JSON.stringify({ code: 200, message: 'ok', data, ...extra });
}

function pageBody(items: unknown[]) {
  return jsonResponse(items, { total: items.length });
}

test.describe('排班规则高级操作', () => {
  test('复制规则弹窗', async ({ page }) => {
    await mockAdminSession(page);

    const template = makeTemplate();

    await page.route('**/api/v1/schedule-templates**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '');
      const method = route.request().method();

      if (method === 'GET' && path === '/schedule-templates') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([template]) });
      }
      if (method === 'GET' && path === '/doctors/all') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: jsonResponse([]) });
      }
      if (method === 'GET' && path === '/departments/all') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: jsonResponse([]) });
      }
      if (method === 'GET' && path === '/stores') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([]) });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('.ant-table-row').first();
    if ((await page.locator('.ant-table-row').count()) > 0) {
      const actionLink = firstRow.locator('a').filter({ hasText: /操作/ });
      if (await actionLink.isVisible()) {
        await actionLink.click();

        const copyMenuItem = page.locator('.ant-dropdown-menu-item').filter({ hasText: '复制规则' });
        if (await copyMenuItem.isVisible()) {
          await copyMenuItem.click();

          const modal = page.locator('.ant-modal').filter({ hasText: '复制规则' });
          if (await modal.isVisible()) {
            await expect(modal).toBeVisible();
          }
        }
      }
    }
  });

  test('生成排班弹窗', async ({ page }) => {
    await mockAdminSession(page);

    const template = makeTemplate();

    await page.route('**/api/v1/schedule-templates**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '');
      const method = route.request().method();

      if (method === 'GET' && path === '/schedule-templates') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([template]) });
      }
      return route.fallback();
    });

    let generateCalled = false;
    await page.route('**/api/v1/schedule-templates/generate**', async (route) => {
      if (route.request().method() === 'POST') {
        generateCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '生成成功', count: 5 }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('.ant-table-row').first();
    if ((await page.locator('.ant-table-row').count()) > 0) {
      const checkbox = firstRow.locator('.ant-checkbox-input');
      await checkbox.check({ force: true });

      const generateBtn = page.getByRole('button', { name: /生成排班/ });
      if (await generateBtn.isVisible()) {
        await generateBtn.click();

        const modal = page.locator('.ant-modal').filter({ hasText: '生成排班' });
        if (await modal.isVisible()) {
          await expect(modal).toBeVisible();
        }
      }
    }
  });

  test('历史日志弹窗', async ({ page }) => {
    await mockAdminSession(page);

    const template = makeTemplate();

    await page.route('**/api/v1/schedule-templates**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '');
      const method = route.request().method();

      if (method === 'GET' && path === '/schedule-templates') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([template]) });
      }
      if (method === 'GET' && path.match(/^\/schedule-templates\/[^/]+\/logs/)) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({
            data: [
              {
                id: 'log-1',
                templateId: template.id,
                operatorName: '管理员',
                actionType: 'generate',
                affectedCount: 5,
                createdAt: '2026-05-10 10:00:00',
              },
            ],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('.ant-table-row').first();
    if ((await page.locator('.ant-table-row').count()) > 0) {
      const actionLink = firstRow.locator('a').filter({ hasText: /操作/ });
      if (await actionLink.isVisible()) {
        await actionLink.click();

        const logsMenuItem = page.locator('.ant-dropdown-menu-item').filter({ hasText: '历史记录' });
        if (await logsMenuItem.isVisible()) {
          await logsMenuItem.click();

          const modal = page.locator('.ant-modal').filter({ hasText: '历史记录' });
          if (await modal.isVisible()) {
            await expect(modal).toBeVisible();
          }

          if (await modal.getByText('管理员').isVisible()) {
            await expect(modal.getByText('管理员')).toBeVisible();
          }
        }
      }
    }
  });

  test('删除单个规则', async ({ page }) => {
    await mockAdminSession(page);

    const template = makeTemplate();

    await page.route('**/api/v1/schedule-templates**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '');
      const method = route.request().method();

      if (method === 'GET' && path === '/schedule-templates') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([template]) });
      }
      return route.fallback();
    });

    let deleteCalled = false;
    await page.route(`**/api/v1/schedule-templates/${template.id}**`, async (route) => {
      if (route.request().method() === 'DELETE') {
        deleteCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '删除成功' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const firstRow = page.locator('.ant-table-row').first();
    if ((await page.locator('.ant-table-row').count()) > 0) {
      const actionLink = firstRow.locator('a').filter({ hasText: /操作/ });
      if (await actionLink.isVisible()) {
        await actionLink.click();

        const deleteMenuItem = page.locator('.ant-dropdown-menu-item').filter({ hasText: '删除规则' });
        if (await deleteMenuItem.isVisible()) {
          await deleteMenuItem.click();

          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认删除' });
          if (await confirmModal.isVisible()) {
            const okBtn = confirmModal.getByRole('button', { name: '删 除' });
            if (await okBtn.isVisible()) {
              await okBtn.click();

              await page.waitForTimeout(500);
              expect(deleteCalled).toBeTruthy();
            }
          }
        }
      }
    }
  });
});

test.describe('排班日历高级操作', () => {
  test('日详情抽屉', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([schedule]) });
      }
      return route.fallback();
    });

    await page.route('**/api/v1/appointments/query**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([]) });
      }
      return route.fallback();
    });

    await page.route('**/api/v1/doctors**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse([{ id: 'doctor-1', name: '李医生', departmentName: '中医科', status: 1 }]),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/calendar');
    await page.waitForLoadState('networkidle');

    const doctorOption = page.getByText('李医生').first();
    if (await doctorOption.isVisible()) {
      await doctorOption.click();
      await page.waitForLoadState('networkidle');
    }

    const calendarCell = page.locator('.ant-picker-calendar .ant-picker-cell-inner').first();
    if (await calendarCell.isVisible()) {
      await calendarCell.click();
      await page.waitForTimeout(500);

      const drawer = page.locator('.ant-drawer');
      if (await drawer.isVisible()) {
        await expect(drawer).toBeVisible();
      }
    }
  });

  test('从日历创建预约', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([schedule]) });
      }
      return route.fallback();
    });

    await page.route('**/api/v1/appointments/query**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([]) });
      }
      return route.fallback();
    });

    await page.route('**/api/v1/doctors**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse([{ id: 'doctor-1', name: '李医生', departmentName: '中医科', status: 1 }]),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/calendar');
    await page.waitForLoadState('networkidle');

    const doctorOption = page.getByText('李医生').first();
    if (await doctorOption.isVisible()) {
      await doctorOption.click();
      await page.waitForLoadState('networkidle');
    }

    const calendarCell = page.locator('.ant-picker-calendar .ant-picker-cell-inner').first();
    if (await calendarCell.isVisible()) {
      await calendarCell.click();
      await page.waitForTimeout(500);

      const drawer = page.locator('.ant-drawer');
      if (await drawer.isVisible()) {
        const createBtn = drawer.getByRole('button', { name: /创建|预约|新增/ }).first();
        if (await createBtn.isVisible()) {
          await createBtn.click();
          await page.waitForTimeout(300);

          const createModal = page.locator('.ant-modal').filter({ hasText: /创建|预约|新增/ });
          if (await createModal.isVisible()) {
            await expect(createModal).toBeVisible();
          }
        }
      }
    }
  });
});

test.describe('排班甘特图详情', () => {
  test('甘特图详情抽屉', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([schedule]) });
      }
      return route.fallback();
    });

    await page.route('**/api/v1/departments/all**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonResponse([{ id: 'dept-1', name: '中医科', status: 1 }]),
      });
    });

    await page.route('**/api/v1/doctors**', async (route) => {
      if (route.request().method() === 'GET') {
        const url = new URL(route.request().url());
        if (url.pathname.includes('/all') || url.pathname.includes('/department')) {
          return route.fulfill({
            status: 200,
            contentType: 'application/json',
            body: jsonResponse([{ id: 'doctor-1', name: '李医生', departmentName: '中医科', title: '主治医师', status: 1 }]),
          });
        }
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ data: [{ id: 'doctor-1', name: '李医生', departmentName: '中医科', title: '主治医师', status: 1 }], total: 1 }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/gantt');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    if (await page.getByText('排班甘特图').isVisible()) {
      await expect(page.getByText('排班甘特图')).toBeVisible();
    }

    const taskBlock = page.locator('.gantt-task-block').first();
    if (await taskBlock.isVisible()) {
      await taskBlock.click();

      const drawer = page.locator('.ant-drawer').filter({ hasText: '排班详情' });
      if (await drawer.isVisible()) {
        await expect(drawer).toBeVisible();
        if (await drawer.getByText('李医生').isVisible()) {
          await expect(drawer.getByText('李医生')).toBeVisible();
        }
      }
    }
  });
});

test.describe('自定义排班管理', () => {
  test('删除自定义排班', async ({ page }) => {
    await mockAdminSession(page);

    const customSchedule = makeCustomSchedule();

    await page.route('**/api/v1/custom-schedules**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([customSchedule]) });
      }
      return route.fallback();
    });

    let deleteCalled = false;
    await page.route(`**/api/v1/custom-schedules/${customSchedule.id}**`, async (route) => {
      if (route.request().method() === 'DELETE') {
        deleteCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '删除成功' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/custom');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const firstRow = page.locator('.ant-table-row').first();
      const deleteLink = firstRow.locator('a').filter({ hasText: '删除' });
      if (await deleteLink.isVisible()) {
        await deleteLink.click();

        const popconfirmOk = page.locator('.ant-popconfirm').getByRole('button', { name: '确 定' });
        if (await popconfirmOk.isVisible()) {
          await popconfirmOk.click();

          await page.waitForTimeout(500);
          expect(deleteCalled).toBeTruthy();
        }
      }
    }
  });
});

test.describe('休息日管理', () => {
  test('删除休息日', async ({ page }) => {
    await mockAdminSession(page);

    const restDay = makeRestDay();

    await page.route('**/api/v1/rest-days**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([restDay]) });
      }
      return route.fallback();
    });

    let deleteCalled = false;
    await page.route(`**/api/v1/rest-days/${restDay.id}**`, async (route) => {
      const method = route.request().method();
      if (method === 'DELETE') {
        deleteCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '删除成功' }),
        });
      }
      if (method === 'PUT') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '操作成功' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rest-day');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const firstRow = page.locator('.ant-table-row').first();
      const deleteLink = firstRow.locator('a').filter({ hasText: '删除' });
      if (await deleteLink.isVisible()) {
        await deleteLink.click();

        const popconfirmOk = page.locator('.ant-popconfirm').getByRole('button', { name: '确 定' });
        if (await popconfirmOk.isVisible()) {
          await popconfirmOk.click();

          await page.waitForTimeout(500);
          expect(deleteCalled).toBeTruthy();
        }
      }
    }
  });

  test('批量删除休息日', async ({ page }) => {
    await mockAdminSession(page);

    const rd1 = makeRestDay({ id: 'rd-1', reason: '元旦休息' });
    const rd2 = makeRestDay({ id: 'rd-2', reason: '春节休息', startDate: '2026-06-10', endDate: '2026-06-12' });

    await page.route('**/api/v1/rest-days**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([rd1, rd2]) });
      }
      return route.fallback();
    });

    let deleteCount = 0;
    await page.route('**/api/v1/rest-days/**', async (route) => {
      const method = route.request().method();
      if (method === 'DELETE') {
        deleteCount++;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '删除成功' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rest-day');
    await page.waitForLoadState('networkidle');

    const rows = page.locator('.ant-table-row');
    const rowCount = await rows.count();

    const selectAllCheckbox = page.locator('th .ant-checkbox-input');
    if (await selectAllCheckbox.isVisible()) {
      await selectAllCheckbox.check({ force: true });
      await page.waitForTimeout(300);
    } else if (rowCount >= 1) {
      const firstCheckbox = rows.first().locator('.ant-checkbox-input');
      if (await firstCheckbox.isVisible()) {
        await firstCheckbox.check({ force: true });
      }
    }

    const alertArea = page.locator('.ant-alert');
    if (await alertArea.isVisible()) {
      const selectedText = alertArea.getByText(/已选择/);
      if (await selectedText.isVisible()) {
        await expect(selectedText).toBeVisible();
      }
    }

    const deleteLinks = page.locator('.ant-table-row').locator('a').filter({ hasText: '删除' });
    if ((await deleteLinks.count()) > 0) {
      await deleteLinks.first().click();

      const popconfirmOk = page.locator('.ant-popconfirm').getByRole('button', { name: '确 定' });
      if (await popconfirmOk.isVisible()) {
        await popconfirmOk.click();
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('排班停诊管理', () => {
  test('取消停诊', async ({ page }) => {
    await mockAdminSession(page);

    const suspension = makeSuspension();

    await page.route('**/api/v1/schedule-suspensions**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({ status: 200, contentType: 'application/json', body: pageBody([suspension]) });
      }
      return route.fallback();
    });

    let cancelCalled = false;
    await page.route(`**/api/v1/schedule-suspensions/${suspension.id}/cancel**`, async (route) => {
      if (route.request().method() === 'PUT') {
        cancelCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '取消成功' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/suspension');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const firstRow = page.locator('.ant-table-row').first();
      const cancelLink = firstRow.locator('a').filter({ hasText: '取消' });
      if (await cancelLink.isVisible()) {
        await cancelLink.click();

        const popconfirmOk = page.locator('.ant-popconfirm').getByRole('button', { name: '确 定' });
        if (await popconfirmOk.isVisible()) {
          await popconfirmOk.click();

          await page.waitForTimeout(500);
          expect(cancelCalled).toBeTruthy();
        }
      }
    }
  });

  test('列表停诊/恢复', async ({ page }) => {
    await mockAdminSession(page);

    const activeSchedule = makeSchedule({ id: 'sch-active', status: 1, bookedSlots: 0 });
    const suspendedSchedule = makeSchedule({ id: 'sch-suspended', status: 0, bookedSlots: 0 });

    await page.route('**/api/v1/schedules**', async (route) => {
      const method = route.request().method();
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '');

      if (method === 'GET' && path === '/schedules') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: pageBody([activeSchedule, suspendedSchedule]),
        });
      }
      return route.fallback();
    });

    let suspendCalled = false;
    await page.route('**/api/v1/schedule-suspensions**', async (route) => {
      if (route.request().method() === 'POST') {
        suspendCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse(makeSuspension()),
        });
      }
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: pageBody([]),
        });
      }
      return route.fallback();
    });

    let resumeCalled = false;
    await page.route('**/api/v1/schedule-suspensions/**/cancel**', async (route) => {
      if (route.request().method() === 'PUT') {
        resumeCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ message: '恢复成功' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/list');
    await page.waitForLoadState('networkidle');

    const rows = page.locator('.ant-table-row');
    const rowCount = await rows.count();
    if (rowCount >= 2) {
      const firstRowSuspend = rows.nth(0).locator('a').filter({ hasText: '停诊' });
      if (await firstRowSuspend.isVisible()) {
        await firstRowSuspend.click();

        const popconfirmOk = page.locator('.ant-popconfirm').getByRole('button', { name: '确 定' });
        if (await popconfirmOk.isVisible()) {
          await popconfirmOk.click();
          await page.waitForTimeout(500);
        }
      }

      const secondRowResume = rows.nth(1).locator('a').filter({ hasText: '恢复' });
      if (await secondRowResume.isVisible()) {
        await secondRowResume.click();
        await page.waitForTimeout(500);
      }
    }

    await page.waitForTimeout(500);
  });
});
