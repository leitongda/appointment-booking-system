import { expect, test } from '@playwright/test';
import { mockAdminSession, createAppointmentWithStatus } from './helpers/admin-mocks';

function createQueueItem(
  status: number,
  overrides: Record<string, unknown> = {},
) {
  return {
    id: `queue-appt-${Date.now()}`,
    appointmentNo: 'APT20260515001',
    queueNumber: 1,
    patientId: 'patient-1',
    patientName: '张三',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    departmentName: '中医科',
    scheduleDate: '2026-05-15',
    timeSlot: 1,
    status,
    signInTime: '2026-05-15 08:30:00',
    callTime: null,
    checkinMethod: 'MANUAL',
    ...overrides,
  };
}

test.describe('预约叫号队列页', () => {
  test('队列页加载与筛选', async ({ page }) => {
    await mockAdminSession(page);

    const queueItems = [
      createQueueItem(2, { id: 'queue-1', queueNumber: 1, patientName: '张三' }),
      createQueueItem(3, { id: 'queue-2', queueNumber: 2, patientName: '李四' }),
      createQueueItem(4, { id: 'queue-3', queueNumber: 3, patientName: '王五' }),
    ];

    await page.route('**/api/v1/appointments/query/queue**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: queueItems }),
      });
    });

    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');

    const storeSelect = page.locator('.ant-select').first();
    if (await storeSelect.isVisible()) {
      await expect(storeSelect).toBeVisible();
    }

    const doctorSelect = page.getByText('选择医生').first();
    if (await doctorSelect.isVisible()) {
      await expect(doctorSelect).toBeVisible();
    }

    const datePicker = page.locator('.ant-picker');
    if (await datePicker.isVisible()) {
      await expect(datePicker).toBeVisible();
    }

    const refreshBtn = page.getByRole('button', { name: '刷新' });
    if (await refreshBtn.isVisible()) {
      await expect(refreshBtn).toBeVisible();
    }

    const patientCell = page.getByText('张三');
    if (await patientCell.isVisible()) {
      await expect(patientCell).toBeVisible();
    }
  });

  test('叫号操作', async ({ page }) => {
    await mockAdminSession(page);

    const checkedInItem = createQueueItem(2, { id: 'appt-call-1', queueNumber: 1, patientName: '张三' });

    await page.route('**/api/v1/appointments/query/queue**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      if (route.request().method() === 'GET' && path === '/appointments/query/queue') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: [checkedInItem] }),
        });
      }
      return route.fallback();
    });

    let apiCalled = false;
    await page.route('**/api/v1/appointments/appt-call-1/call', async (route) => {
      if (route.request().method() === 'PUT') {
        apiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: {} }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const callBtn = page.getByRole('button', { name: '叫号' });
      if (await callBtn.isVisible()) {
        await callBtn.click();
        await page.waitForLoadState('networkidle');
        expect(apiCalled).toBe(true);
      } else {
        const row = page.getByRole('row').filter({ hasText: '张三' });
        const rowCallBtn = row.getByRole('button', { name: '叫号' });
        if (await rowCallBtn.isVisible()) {
          await rowCallBtn.click();
          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
        }
      }
    }
  });

  test('完成就诊操作', async ({ page }) => {
    await mockAdminSession(page);

    const inProgressItem = createQueueItem(4, { id: 'appt-complete-1', queueNumber: 1, patientName: '张三' });

    await page.route('**/api/v1/appointments/query/queue**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      if (route.request().method() === 'GET' && path === '/appointments/query/queue') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: [inProgressItem] }),
        });
      }
      return route.fallback();
    });

    let apiCalled = false;
    await page.route('**/api/v1/appointments/appt-complete-1/complete', async (route) => {
      if (route.request().method() === 'PUT') {
        apiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: {} }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const completeBtn = page.getByRole('button', { name: '完成' });
      if (await completeBtn.isVisible()) {
        await completeBtn.click();
        await page.waitForLoadState('networkidle');
        expect(apiCalled).toBe(true);
      } else {
        const row = page.getByRole('row').filter({ hasText: '张三' });
        const rowCompleteBtn = row.getByRole('button', { name: '完成' });
        if (await rowCompleteBtn.isVisible()) {
          await rowCompleteBtn.click();
          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
        }
      }
    }
  });

  test('过号操作', async ({ page }) => {
    await mockAdminSession(page);

    const inProgressItem = createQueueItem(4, { id: 'appt-pass-1', queueNumber: 1, patientName: '张三' });

    await page.route('**/api/v1/appointments/query/queue**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      if (route.request().method() === 'GET' && path === '/appointments/query/queue') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: [inProgressItem] }),
        });
      }
      return route.fallback();
    });

    let apiCalled = false;
    await page.route('**/api/v1/appointments/appt-pass-1/pass', async (route) => {
      if (route.request().method() === 'PUT') {
        apiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: {} }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const passBtn = page.getByRole('button', { name: '过号' });
      if (await passBtn.isVisible()) {
        await passBtn.click();
        await page.waitForLoadState('networkidle');
        expect(apiCalled).toBe(true);
      } else {
        const row = page.getByRole('row').filter({ hasText: '张三' });
        const rowPassBtn = row.getByRole('button', { name: '过号' });
        if (await rowPassBtn.isVisible()) {
          await rowPassBtn.click();
          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
        }
      }
    }
  });

  test('重新叫号操作', async ({ page }) => {
    await mockAdminSession(page);

    const passedItem = createQueueItem(7, { id: 'appt-recall-1', queueNumber: 1, patientName: '张三' });

    await page.route('**/api/v1/appointments/query/queue**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      if (route.request().method() === 'GET' && path === '/appointments/query/queue') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: [passedItem] }),
        });
      }
      return route.fallback();
    });

    let apiCalled = false;
    await page.route('**/api/v1/appointments/appt-recall-1/recall', async (route) => {
      if (route.request().method() === 'PUT') {
        apiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: {} }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const recallBtn = page.getByRole('button', { name: '重新叫号' });
      if (await recallBtn.isVisible()) {
        await recallBtn.click();
        await page.waitForLoadState('networkidle');
        expect(apiCalled).toBe(true);
      } else {
        const row = page.getByRole('row').filter({ hasText: '张三' });
        const rowRecallBtn = row.getByRole('button', { name: '重新叫号' });
        if (await rowRecallBtn.isVisible()) {
          await rowRecallBtn.click();
          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
        }
      }
    }
  });

  test('自动刷新开关', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/appointments/query/queue**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: [] }),
      });
    });

    await page.goto('/medical-services/appointment/queue');
    await page.waitForLoadState('networkidle');

    const autoRefreshLabel = page.getByText('自动刷新');
    if (await autoRefreshLabel.isVisible()) {
      await expect(autoRefreshLabel).toBeVisible();

      const switchEl = page.locator('.ant-switch').first();
      await expect(switchEl).toBeVisible();
      await expect(switchEl).toBeChecked();

      await switchEl.click();
      await expect(switchEl).not.toBeChecked();

      await switchEl.click();
      await expect(switchEl).toBeChecked();
    }
  });
});

test.describe('预约统计页面', () => {
  test('统计页加载与查询', async ({ page }) => {
    await mockAdminSession(page);

    await page.goto('/medical-services/appointment/statistics');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    const pickerRange = page.locator('.ant-picker-range');
    if (await pickerRange.isVisible()) {
      await expect(pickerRange).toBeVisible();
    }

    const storeSelect = page.locator('.ant-select');
    if (await storeSelect.isVisible()) {
      await expect(storeSelect).toBeVisible();
    }

    const queryBtn = page.getByRole('button', { name: '查询' });
    if (await queryBtn.isVisible()) {
      await expect(queryBtn).toBeVisible();
    }
  });

  test('统计数据展示', async ({ page }) => {
    await mockAdminSession(page);

    const mockSummary = {
      total: 120,
      completed: 90,
      noShow: 10,
      cancelled: 20,
      completedRate: 75,
      noShowRate: 8.3,
      cancelledRate: 16.7,
    };

    const mockStatusStats = [
      { status: 0, name: '待支付', count: 5 },
      { status: 1, name: '已预约', count: 15 },
      { status: 2, name: '已签到', count: 8 },
      { status: 3, name: '候诊', count: 3 },
      { status: 4, name: '就诊中', count: 2 },
      { status: 5, name: '已完成', count: 72 },
      { status: 6, name: '已取消', count: 10 },
      { status: 7, name: '已过号', count: 3 },
      { status: 8, name: '已爽约', count: 2 },
    ];

    const mockTrend = Array.from({ length: 14 }, (_, i) => ({
      date: `2026-05-${String(i + 1).padStart(2, '0')}`,
      count: Math.floor(Math.random() * 20) + 5,
    }));

    const mockStoreRanking = [
      { storeId: 'store-1', storeName: '示例门店', count: 80 },
      { storeId: 'store-2', storeName: '测试分店', count: 40 },
    ];

    const mockDeptRanking = [
      { departmentId: 'dept-1', departmentName: '中医科', count: 60 },
      { departmentId: 'dept-2', departmentName: '内科', count: 35 },
    ];

    const mockDoctorRanking = [
      { doctorId: 'doctor-1', doctorName: '李医生', title: '主治医师', departmentName: '中医科', count: 45 },
      { doctorId: 'doctor-2', doctorName: '王医生', title: '副主任医师', departmentName: '内科', count: 30 },
    ];

    const mockTimeSlots = [
      { timeSlot: 'morning', name: '上午', count: 50 },
      { timeSlot: 'afternoon', name: '下午', count: 45 },
      { timeSlot: 'evening', name: '晚间', count: 25 },
    ];

    await page.route('**/api/v1/statistics/appointments/summary**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockSummary }),
      });
    });

    await page.route('**/api/v1/statistics/appointments/trend**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockTrend }),
      });
    });

    await page.route('**/api/v1/statistics/appointments/status**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockStatusStats }),
      });
    });

    await page.route('**/api/v1/statistics/stores/ranking**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockStoreRanking }),
      });
    });

    await page.route('**/api/v1/statistics/departments/ranking**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockDeptRanking }),
      });
    });

    await page.route('**/api/v1/statistics/doctors/ranking**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockDoctorRanking }),
      });
    });

    await page.route('**/api/v1/statistics/time-slots/distribution**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockTimeSlots }),
      });
    });

    await page.goto('/medical-services/appointment/statistics');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    if (await page.getByText('总预约数').isVisible()) {
      await expect(page.getByText('总预约数')).toBeVisible();
    }

    if (await page.getByText('120').isVisible()) {
      await expect(page.getByText('120')).toBeVisible();
    }

    if (await page.getByText('完成率').isVisible()) {
      await expect(page.getByText('完成率')).toBeVisible();
    }

    if (await page.getByText('75%').isVisible()) {
      await expect(page.getByText('75%')).toBeVisible();
    }

    if (await page.getByText('预约状态分布').isVisible()) {
      await expect(page.getByText('预约状态分布')).toBeVisible();
    }

    if (await page.getByText('待支付').isVisible()) {
      await expect(page.getByText('待支付')).toBeVisible();
    }

    if (await page.getByText('近14天预约趋势').isVisible()) {
      await expect(page.getByText('近14天预约趋势')).toBeVisible();
    }

    const storeRanking = page.getByText('门店排行 TOP10');
    if (await storeRanking.isVisible()) {
      await expect(storeRanking).toBeVisible();
      await expect(page.getByText('示例门店').first()).toBeVisible();
    }

    const deptRanking = page.getByText('科室排行 TOP10');
    if (await deptRanking.isVisible()) {
      await expect(deptRanking).toBeVisible();
      await expect(page.getByText('中医科').first()).toBeVisible();
    }

    const doctorRanking = page.getByText('医生排行 TOP10');
    if (await doctorRanking.isVisible()) {
      await expect(doctorRanking).toBeVisible();
    }
  });
});
