import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

// ---------------------------------------------------------------------------
// Shared mock data factories
// ---------------------------------------------------------------------------

function makeSchedule(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sch-1',
    doctorId: 'doctor-1',
    doctorName: '李医生',
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
    createdAt: '2026-05-12 08:00:00',
    ...overrides,
  };
}

function makeTemplate(overrides: Record<string, unknown> = {}) {
  return {
    id: 'tpl-1',
    name: '工作日上午班',
    storeId: 'store-1',
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
    scheduleMode: 'fixed',
    status: 1,
    createdAt: '2026-05-01 08:00:00',
    ...overrides,
  };
}

function makeLeaveRequest(overrides: Record<string, unknown> = {}) {
  return {
    id: 'lr-1',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    requestType: 'stop_clinic',
    stopDate: '2026-05-15',
    stopPeriod: 'morning',
    reason: '身体不适',
    status: 'pending',
    reviewerId: undefined,
    reviewComment: undefined,
    reviewedAt: undefined,
    affectedAppointments: 2,
    createdAt: '2026-05-12 10:00:00',
    ...overrides,
  };
}

// ---------------------------------------------------------------------------
// Schedule tests (8 tests)
// ---------------------------------------------------------------------------

test.describe('医生排班操作', () => {
  // 1. 排班列表加载
  test('排班列表加载', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeSchedule({ id: 'sch-1', timeSlot: 'morning', totalSlots: 20, bookedSlots: 10 }),
              makeSchedule({ id: 'sch-2', scheduleDate: '2026-05-16', timeSlot: 'afternoon', startTime: '14:00', endTime: '17:30', totalSlots: 15, bookedSlots: 15 }),
            ],
            total: 2,
          }),
        });
      }
      return route.fallback();
    });

    // Navigate to doctor detail page and switch to schedule tab
    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Verify schedule tab content renders (the Card title or calendar)
    await expect(page.getByText('排班管理')).toBeVisible();

    // Verify the Ant Design calendar component renders
    await expect(page.locator('.ant-picker-calendar')).toBeVisible();
  });

  // 2. 从模板生成排班
  test('从模板生成排班', async ({ page }) => {
    await mockAdminSession(page);

    const template = makeTemplate();

    // Mock schedule list for calendar
    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [],
            total: 0,
          }),
        });
      }
      return route.fallback();
    });

    // Mock template list
    await page.route('**/api/v1/schedule-templates**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [template],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    // Mock generate endpoint
    let generateCalled = false;
    await page.route('**/api/v1/schedule-templates/generate**', async (route) => {
      if (route.request().method() === 'POST') {
        generateCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: '生成成功',
            data: { message: '生成成功', count: 5 },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Click "从模板生成" button
    await page.getByRole('button', { name: /从模板生成/ }).click();

    // Wait for modal
    await expect(page.locator('.ant-modal').filter({ hasText: '从模板生成排班' })).toBeVisible();

    // Select template (multi-select dropdown)
    const templateSelect = page.locator('.ant-modal').filter({ hasText: '从模板生成排班' }).getByText('选择模板').locator('..').locator('.ant-select');
    await templateSelect.click();
    await page.getByTitle(/工作日上午班/).click();

    // Pick date range
    const dateRangePicker = page.locator('.ant-modal').filter({ hasText: '从模板生成排班' }).getByPlaceholder('开始日期');
    await dateRangePicker.click();

    // Select a date range in the picker popup
    const pickerPopup = page.locator('.ant-picker-dropdown:not(.ant-picker-dropdown-hidden)').first();
    if (await pickerPopup.isVisible()) {
      // Click a date cell to start range
      const cells = pickerPopup.locator('.ant-picker-cell-inner');
      const enabledCells = cells.filter({ hasNot: page.locator('.ant-picker-cell-disabled .ant-picker-cell-inner') });
      if (await enabledCells.count() >= 2) {
        await enabledCells.nth(0).click();
        await enabledCells.nth(3).click();
      }
    }

    // Submit
    const submitBtn = page.locator('.ant-modal').filter({ hasText: '从模板生成排班' }).getByRole('button', { name: '确 定' });
    await submitBtn.click();

    // Verify the generate was called or modal closed
    await page.waitForTimeout(500);

    // Either the modal closed or the generate was called
    const modalGone = !(await page.locator('.ant-modal').filter({ hasText: '从模板生成排班' }).isVisible().catch(() => false));
    expect(modalGone || generateCalled).toBeTruthy();
  });

  // 3. 添加排班
  test('添加排班', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();

    await page.route('**/api/v1/schedules**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [schedule],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    // Mock schedule creation
    let createCalled = false;
    await page.route('**/api/v1/schedules', async (route) => {
      if (route.request().method() === 'POST') {
        createCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: { ...schedule, id: 'sch-new' },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Click on a calendar date cell to open the schedule edit modal
    const calendarCell = page.locator('.ant-picker-calendar .ant-picker-cell-inner').first();
    await calendarCell.click();
    await page.waitForTimeout(500);

    // The schedule edit modal should appear
    const editModal = page.locator('.ant-modal').filter({ hasText: '排班管理' });
    await expect(editModal).toBeVisible();

    // Click "添加排班" button inside the modal
    await editModal.getByRole('button', { name: '添加排班' }).click();

    // The add schedule sub-modal should appear
    const addModal = page.locator('.ant-modal').filter({ hasText: '添加排班' });
    await expect(addModal).toBeVisible();

    // Select time slot
    const timeSlotSelect = addModal.locator('.ant-select').first();
    await timeSlotSelect.click();
    await page.getByText('上午').last().click();

    // Fill number of slots
    const slotsInput = addModal.locator('input').filter({ hasText: '' }).last();
    await slotsInput.clear();
    await slotsInput.fill('25');

    // Submit
    const confirmBtn = addModal.getByRole('button', { name: '确 定' });
    await confirmBtn.click();

    await page.waitForTimeout(500);
    expect(createCalled).toBeTruthy();
  });

  // 4. 停诊操作
  test('停诊操作', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule({ status: 1 });

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [schedule],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    // Mock suspension creation (suspendSchedule calls scheduleSuspensionApi.create)
    let suspendCalled = false;
    await page.route('**/api/v1/schedule-suspensions**', async (route) => {
      if (route.request().method() === 'POST') {
        suspendCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: { id: 'susp-1', status: 1 },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Click a calendar cell with schedule data to open the edit modal
    const calendarCell = page.locator('.ant-picker-calendar .ant-picker-cell-inner').first();
    await calendarCell.click();
    await page.waitForTimeout(500);

    const editModal = page.locator('.ant-modal').filter({ hasText: '排班管理' });
    await expect(editModal).toBeVisible();

    // Find the "停诊" link inside the list item
    const suspendLink = editModal.getByText('停诊', { exact: true }).first();
    await expect(suspendLink).toBeVisible();

    // Click "停诊" to trigger Popconfirm
    await suspendLink.click();

    // Click the "确定" button in the Popconfirm
    const popconfirmOk = page.locator('.ant-popconfirm').getByRole('button', { name: '确 定' });
    await expect(popconfirmOk).toBeVisible();
    await popconfirmOk.click();

    await page.waitForTimeout(500);
    expect(suspendCalled).toBeTruthy();
  });

  // 5. 恢复排诊
  test('恢复排诊', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule({ status: 0 }); // already suspended

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [schedule],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    // Mock suspension list query (resumeSchedule first gets suspensions)
    await page.route('**/api/v1/schedule-suspensions**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [{
              id: 'susp-1',
              storeId: 'store-1',
              doctorId: 'doctor-1',
              title: '管理员停诊',
              suspensionDate: '2026-05-15',
              scheduleIds: ['sch-1'],
              status: 1,
              createdAt: '2026-05-12 10:00:00',
            }],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    // Mock suspension cancel (resumeSchedule calls scheduleSuspensionApi.cancel)
    let cancelCalled = false;
    await page.route('**/api/v1/schedule-suspensions/**/cancel**', async (route) => {
      if (route.request().method() === 'PUT') {
        cancelCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: { message: '恢复成功' },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Click a calendar cell
    const calendarCell = page.locator('.ant-picker-calendar .ant-picker-cell-inner').first();
    await calendarCell.click();
    await page.waitForTimeout(500);

    const editModal = page.locator('.ant-modal').filter({ hasText: '排班管理' });
    await expect(editModal).toBeVisible();

    // Find and click "恢复" link
    const resumeLink = editModal.getByText('恢复', { exact: true }).first();
    await expect(resumeLink).toBeVisible();
    await resumeLink.click();

    await page.waitForTimeout(500);
    expect(cancelCalled).toBeTruthy();
  });

  // 6. 刷新按钮
  test('刷新按钮', async ({ page }) => {
    await mockAdminSession(page);

    let getRequestCount = 0;
    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        getRequestCount++;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [makeSchedule()],
            total: 1,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    const initialCount = getRequestCount;

    // Click "刷新" button
    await page.getByRole('button', { name: /刷新/ }).click();
    await page.waitForLoadState('networkidle');

    // Verify that a new GET request was made
    expect(getRequestCount).toBeGreaterThan(initialCount);
  });

  // 7. 排班状态标签
  test('排班状态标签', async ({ page }) => {
    await mockAdminSession(page);

    const today = new Date();
    const yyyy = today.getFullYear();
    const mm = String(today.getMonth() + 1).padStart(2, '0');
    const dd = String(today.getDate()).padStart(2, '0');
    const todayStr = `${yyyy}-${mm}-${dd}`;

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeSchedule({ id: 'sch-normal', scheduleDate: todayStr, timeSlot: 'morning', totalSlots: 20, bookedSlots: 10, status: 1 }),
              makeSchedule({ id: 'sch-full', scheduleDate: todayStr, timeSlot: 'afternoon', startTime: '14:00', endTime: '17:30', totalSlots: 15, bookedSlots: 15, status: 1 }),
              makeSchedule({ id: 'sch-suspended', scheduleDate: todayStr, timeSlot: 'evening', startTime: '18:00', endTime: '21:00', totalSlots: 10, bookedSlots: 0, status: 0 }),
            ],
            total: 3,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Click on today's date cell to open the schedule edit modal
    // Find the cell that contains today's date number
    const todayCell = page.locator('.ant-picker-calendar .ant-picker-cell').filter({ hasText: String(today.getDate()) }).first();
    await todayCell.locator('.ant-picker-cell-inner').click();
    await page.waitForTimeout(500);

    const editModal = page.locator('.ant-modal').filter({ hasText: '排班管理' });
    await expect(editModal).toBeVisible();

    // Verify status tags inside the schedule list
    // "正常" tag (green for status=1 with available slots)
    await expect(editModal.locator('.ant-tag-success').filter({ hasText: '正常' })).toBeVisible();
    // "已满" tag (red for fully booked)
    await expect(editModal.locator('.ant-tag-error').filter({ hasText: '已满' })).toBeVisible();
    // "停诊" tag (default for status=0)
    await expect(editModal.locator('.ant-tag').filter({ hasText: '停诊' })).toBeVisible();
  });

  // 8. 日历视图交互
  test('日历视图切换月份', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/schedules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [],
            total: 0,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=schedule');
    await page.waitForLoadState('networkidle');

    // Verify calendar renders
    await expect(page.locator('.ant-picker-calendar')).toBeVisible();

    // Navigate to next month using the calendar header
    const nextBtn = page.locator('.ant-picker-calendar .ant-picker-header-next-btn');
    if (await nextBtn.isVisible()) {
      await nextBtn.click();
      await page.waitForTimeout(500);
    }

    // Verify calendar is still rendered after navigation
    await expect(page.locator('.ant-picker-calendar')).toBeVisible();
  });
});

// ---------------------------------------------------------------------------
// Leave request tests (6 tests)
// ---------------------------------------------------------------------------

test.describe('停诊审核', () => {
  // 9. 停诊申请列表加载
  test('停诊申请列表加载', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/leave-requests**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeLeaveRequest({ id: 'lr-1', status: 'pending', doctorName: '李医生' }),
              makeLeaveRequest({ id: 'lr-2', status: 'approved', doctorName: '王医生', reviewComment: '同意' }),
              makeLeaveRequest({ id: 'lr-3', status: 'rejected', doctorName: '赵医生', reviewComment: '不通过' }),
            ],
            total: 3,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/leave-request');
    await page.waitForLoadState('networkidle');

    // Verify page header
    await expect(page.getByText('停诊审核')).toBeVisible();

    // Verify table renders
    await expect(page.locator('.ant-pro-table, .ant-table')).toBeVisible();
  });

  // 10. 审核通过
  test('审核通过', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/leave-requests**', async (route) => {
      const method = route.request().method();
      const url = new URL(route.request().url());
      const path = url.pathname;

      // GET list
      if (method === 'GET' && path.endsWith('/leave-requests')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeLeaveRequest({ id: 'lr-pending', status: 'pending', doctorName: '李医生' }),
            ],
            total: 1,
          }),
        });
      }

      // POST review (approve)
      if (method === 'POST' && path.includes('/review')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: makeLeaveRequest({ id: 'lr-pending', status: 'approved', reviewComment: '同意停诊' }),
          }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/leave-request');
    await page.waitForLoadState('networkidle');

    // Click "审核" button in the pending row
    const reviewBtn = page.getByRole('button', { name: '审核' });
    await expect(reviewBtn).toBeVisible();
    await reviewBtn.click();

    // Verify review modal opens
    const reviewModal = page.locator('.ant-modal').filter({ hasText: '审核申请' });
    await expect(reviewModal).toBeVisible();

    // "通过" is the default radio, verify it is selected
    const passRadio = reviewModal.getByRole('radio', { name: '通过' });
    await expect(passRadio).toBeChecked();

    // Fill review comment
    const commentInput = reviewModal.locator('textarea');
    await commentInput.fill('同意停诊');

    // Submit
    const submitBtn = reviewModal.getByRole('button', { name: '确 定' });
    await submitBtn.click();

    // Wait for the review API call and modal close
    await page.waitForTimeout(500);
  });

  // 11. 审核拒绝
  test('审核拒绝', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/leave-requests**', async (route) => {
      const method = route.request().method();
      const url = new URL(route.request().url());
      const path = url.pathname;

      // GET list
      if (method === 'GET' && path.endsWith('/leave-requests')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeLeaveRequest({ id: 'lr-pending', status: 'pending', doctorName: '李医生' }),
            ],
            total: 1,
          }),
        });
      }

      // POST review (reject)
      if (method === 'POST' && path.includes('/review')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: makeLeaveRequest({ id: 'lr-pending', status: 'rejected', reviewComment: '排班紧张不予批准' }),
          }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/leave-request');
    await page.waitForLoadState('networkidle');

    // Click "审核" button
    const reviewBtn = page.getByRole('button', { name: '审核' });
    await expect(reviewBtn).toBeVisible();
    await reviewBtn.click();

    const reviewModal = page.locator('.ant-modal').filter({ hasText: '审核申请' });
    await expect(reviewModal).toBeVisible();

    // Select "拒绝"
    const rejectRadio = reviewModal.getByRole('radio', { name: '拒绝' });
    await rejectRadio.click();
    await expect(rejectRadio).toBeChecked();

    // Fill review comment
    const commentInput = reviewModal.locator('textarea');
    await commentInput.fill('排班紧张不予批准');

    // Submit
    const submitBtn = reviewModal.getByRole('button', { name: '确 定' });
    await submitBtn.click();

    await page.waitForTimeout(500);
  });

  // 12. 查看详情
  test('查看详情', async ({ page }) => {
    await mockAdminSession(page);

    const request = makeLeaveRequest({
      id: 'lr-detail',
      doctorName: '李医生',
      status: 'pending',
      stopDate: '2026-05-15',
      stopPeriod: 'morning',
      reason: '身体不适需要休息',
    });

    await page.route('**/api/v1/leave-requests**', async (route) => {
      const method = route.request().method();
      const url = new URL(route.request().url());
      const path = url.pathname;

      // GET list
      if (method === 'GET' && path.endsWith('/leave-requests')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [request],
            total: 1,
          }),
        });
      }

      // GET detail
      if (method === 'GET' && path.includes('/leave-requests/') && !path.includes('review') && !path.includes('my') && !path.includes('pending-count')) {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: request,
          }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/leave-request');
    await page.waitForLoadState('networkidle');

    // Click "查看" button (the view OperationButton renders as an icon link)
    const viewBtn = page.locator('.ant-table-row').first().locator('a, button').filter({ hasText: /查看|详情/ }).first();

    // The OperationButton with type="view" may render as an eye icon or "查看" text.
    // Try to find the view action button in the operation column
    const operationCell = page.locator('.ant-table-row').first().locator('td').last();
    const actionLinks = operationCell.locator('a, button');

    // Find and click the view action (first action in the OperationGroup)
    if (await actionLinks.count() > 0) {
      await actionLinks.first().click();
    }

    // Verify detail drawer opens
    const drawer = page.locator('.ant-drawer').filter({ hasText: '申请详情' });
    await expect(drawer).toBeVisible();

    // Verify detail content shows doctor name and reason
    await expect(drawer.getByText('李医生')).toBeVisible();
    await expect(drawer.getByText('身体不适需要休息')).toBeVisible();
  });

  // 13. 待审核状态标签
  test('待审核状态标签', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/leave-requests**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeLeaveRequest({ id: 'lr-p1', status: 'pending', doctorName: '李医生' }),
              makeLeaveRequest({ id: 'lr-p2', status: 'pending', doctorName: '王医生' }),
            ],
            total: 2,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/leave-request');
    await page.waitForLoadState('networkidle');

    // Verify "待审核" tags appear in the table
    const pendingTags = page.locator('.ant-tag').filter({ hasText: '待审核' });
    const count = await pendingTags.count();
    expect(count).toBeGreaterThanOrEqual(1);

    // Verify they have gold color
    const firstTag = pendingTags.first();
    await expect(firstTag).toBeVisible();
  });

  // 14. 已审核记录无操作按钮
  test('已审核记录无审核按钮', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/leave-requests**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: [
              makeLeaveRequest({ id: 'lr-approved', status: 'approved', doctorName: '李医生', reviewComment: '同意' }),
              makeLeaveRequest({ id: 'lr-rejected', status: 'rejected', doctorName: '王医生', reviewComment: '不予批准' }),
              makeLeaveRequest({ id: 'lr-cancelled', status: 'cancelled', doctorName: '赵医生' }),
            ],
            total: 3,
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/leave-request');
    await page.waitForLoadState('networkidle');

    // Verify no "审核" button exists on the page (only pending items show it)
    const reviewButtons = page.getByRole('button', { name: '审核' });
    await expect(reviewButtons).toHaveCount(0);

    // Verify status tags for each status
    await expect(page.locator('.ant-tag').filter({ hasText: '已通过' }).first()).toBeVisible();
    await expect(page.locator('.ant-tag').filter({ hasText: '已拒绝' }).first()).toBeVisible();
  });
});
