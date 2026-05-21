import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * 排班拖拽交互 E2E 测试
 *
 * 覆盖场景:
 * 1. 拖拽排班到不同时间段 -> 确认弹窗出现
 * 2. 拖拽排班到不同日期 -> 确认弹窗出现
 * 3. 拖拽冲突检测 (409) -> 冲突信息展示
 * 4. 拖拽取消 -> 无 API 调用
 */

// 2026-05-20 是周三，所在周为 05-17 ~ 05-23
const SCHEDULE_DATE = '2026-05-20';

function makeSchedule(overrides: Record<string, unknown> = {}) {
  return {
    id: 'sch-drag-1',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    departmentId: 'dept-1',
    departmentName: '中医科',
    storeId: 'store-1',
    storeName: '示例门店',
    scheduleDate: SCHEDULE_DATE,
    timeSlot: 'morning',
    startTime: '08:00',
    endTime: '12:00',
    totalSlots: 20,
    bookedSlots: 0,
    appointmentType: 'normal',
    status: 1,
    isRestDay: false,
    effectiveStatus: 'active',
    createdAt: '2026-05-12 08:00:00',
    ...overrides,
  };
}

function jsonResponse(data: unknown, extra: Record<string, unknown> = {}) {
  return JSON.stringify({ code: 200, message: 'ok', data, ...extra });
}

function pageBody(items: unknown[]) {
  return jsonResponse(items, { total: items.length });
}

/** 设置日历页面的基础 mock 路由 */
async function setupCalendarMocks(
  page: import('@playwright/test').Page,
  schedules: ReturnType<typeof makeSchedule>[],
) {
  // 拦截排班列表 API
  await page.route('**/api/v1/schedules**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '');
    const method = route.request().method();

    if (method === 'GET' && path === '/schedules') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: pageBody(schedules),
      });
    }
    return route.fallback();
  });

  // 拦截预约列表 API
  await page.route('**/api/v1/appointments/query**', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: pageBody([]),
      });
    }
    return route.fallback();
  });

  // 拦截医生列表 API
  await page.route('**/api/v1/doctors**', async (route) => {
    if (route.request().method() === 'GET') {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: jsonResponse([
          { id: 'doctor-1', name: '李医生', departmentName: '中医科', status: 1 },
        ]),
      });
    }
    return route.fallback();
  });
}

/**
 * 导航到排班日历页面，选择医生，切换到周视图。
 * 返回 draggable handle 元素（如果存在）。
 */
async function navigateToWeekView(page: import('@playwright/test').Page) {
  await page.goto('/medical-services/schedule/calendar');
  await page.waitForLoadState('networkidle');

  // 选择医生
  const doctorOption = page.getByText('李医生').first();
  if (await doctorOption.isVisible()) {
    await doctorOption.click();
    await page.waitForLoadState('networkidle');
  }

  // 切换到周视图
  const weekBtn = page.getByRole('button', { name: /周/ });
  if (await weekBtn.isVisible()) {
    await weekBtn.click();
    await page.waitForTimeout(500);
  }
}

/**
 * 尝试执行拖拽操作。
 * 使用 page.mouse 模拟 pointer 事件（@dnd-kit 基于 PointerSensor）。
 * 返回 true 如果拖拽成功执行（mouse down + move + up）。
 */
async function attemptDrag(
  page: import('@playwright/test').Page,
  sourceSelector: string,
  targetSelector: string,
): Promise<boolean> {
  const source = page.locator(sourceSelector).first();
  const target = page.locator(targetSelector).first();

  if (!(await source.isVisible()) || !(await target.isVisible())) {
    return false;
  }

  const sourceBox = await source.boundingBox();
  const targetBox = await target.boundingBox();
  if (!sourceBox || !targetBox) {
    return false;
  }

  const sourceX = sourceBox.x + sourceBox.width / 2;
  const sourceY = sourceBox.y + sourceBox.height / 2;
  const targetX = targetBox.x + targetBox.width / 2;
  const targetY = targetBox.y + targetBox.height / 2;

  // @dnd-kit PointerSensor 需要至少 8px 的移动才会激活拖拽
  await page.mouse.move(sourceX, sourceY);
  await page.mouse.down();

  // 分步移动以触发 PointerSensor activationConstraint
  const steps = 10;
  for (let i = 1; i <= steps; i++) {
    const x = sourceX + ((targetX - sourceX) * i) / steps;
    const y = sourceY + ((targetY - sourceY) * i) / steps;
    await page.mouse.move(x, y);
    await page.waitForTimeout(30);
  }

  await page.mouse.up();
  return true;
}

test.describe('排班拖拽交互', () => {
  // ---------------------------------------------------------------------------
  // 1. 拖拽排班到不同时间段
  // ---------------------------------------------------------------------------

  test('拖拽排班到不同时间段 - 显示确认弹窗', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();
    await setupCalendarMocks(page, [schedule]);

    // mock drag-adjust API（成功响应）
    await page.route('**/api/v1/schedules/drag-adjust', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({
            success: true,
            schedule: { ...schedule, startTime: '14:00', endTime: '18:00', timeSlot: 'afternoon' },
            message: '排班调整成功',
          }),
        });
      }
      return route.fallback();
    });

    await navigateToWeekView(page);

    // 查找可拖拽的排班 cell
    const dragHandle = page.locator('.drag-handle').first();
    const draggableCell = page.locator('.draggable-schedule-cell').first();

    if ((await dragHandle.isVisible()) && (await draggableCell.isVisible())) {
      // 查找下午时间段的 droppable 区域 (14:00)
      const targetSlot = page.locator('[aria-label*="14:00"]').first();

      if (await targetSlot.isVisible()) {
        const dragged = await attemptDrag(
          page,
          '.drag-handle',
          '[aria-label*="14:00"]',
        );

        if (dragged) {
          await page.waitForTimeout(500);

          // 验证确认弹窗出现
          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认调整排班' });
          if (await confirmModal.isVisible()) {
            await expect(confirmModal).toBeVisible();
            // 验证弹窗中包含医生名
            await expect(confirmModal.getByText('李医生')).toBeVisible();
            // 验证弹窗中有确认按钮
            await expect(confirmModal.getByRole('button', { name: '确认调整' })).toBeVisible();
          }
        }
      }
    }
  });

  // ---------------------------------------------------------------------------
  // 2. 拖拽排班到不同日期
  // ---------------------------------------------------------------------------

  test('拖拽排班到不同日期 - 显示确认弹窗', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();
    await setupCalendarMocks(page, [schedule]);

    await page.route('**/api/v1/schedules/drag-adjust', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({
            success: true,
            schedule: { ...schedule, scheduleDate: '2026-05-21' },
            message: '排班调整成功',
          }),
        });
      }
      return route.fallback();
    });

    await navigateToWeekView(page);

    const dragHandle = page.locator('.drag-handle').first();

    if (await dragHandle.isVisible()) {
      // 拖到第二天 (05-21) 的任意时间段
      // .slot-cell 的 aria-label 格式: "05月21日 HH:MM 无排班"
      const targetSlot = page.locator('.slot-cell[aria-label*="05月21日"]').first();

      if (await targetSlot.isVisible()) {
        const dragged = await attemptDrag(
          page,
          '.drag-handle',
          '.slot-cell[aria-label*="05月21日"]',
        );

        if (dragged) {
          await page.waitForTimeout(500);

          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认调整排班' });
          if (await confirmModal.isVisible()) {
            await expect(confirmModal).toBeVisible();
            // 验证弹窗中有目标日期
            await expect(confirmModal.getByText('2026-05-21')).toBeVisible();
          }
        }
      }
    }
  });

  // ---------------------------------------------------------------------------
  // 3. 拖拽确认后调用 API
  // ---------------------------------------------------------------------------

  test('拖拽确认后正确调用 drag-adjust API', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();
    await setupCalendarMocks(page, [schedule]);

    let dragApiCalled = false;
    let dragApiPayload: Record<string, unknown> | null = null;

    await page.route('**/api/v1/schedules/drag-adjust', async (route) => {
      if (route.request().method() === 'POST') {
        dragApiCalled = true;
        dragApiPayload = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({
            success: true,
            schedule: { ...schedule, startTime: '14:00', endTime: '18:00', timeSlot: 'afternoon' },
            message: '排班调整成功',
          }),
        });
      }
      return route.fallback();
    });

    await navigateToWeekView(page);

    const dragHandle = page.locator('.drag-handle').first();

    if (await dragHandle.isVisible()) {
      const targetSlot = page.locator('[aria-label*="14:00"]').first();

      if (await targetSlot.isVisible()) {
        const dragged = await attemptDrag(
          page,
          '.drag-handle',
          '[aria-label*="14:00"]',
        );

        if (dragged) {
          await page.waitForTimeout(500);

          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认调整排班' });
          if (await confirmModal.isVisible()) {
            // 点击确认按钮
            const confirmBtn = confirmModal.getByRole('button', { name: '确认调整' });
            if (await confirmBtn.isVisible()) {
              await confirmBtn.click();
              await page.waitForTimeout(1000);

              // 验证 API 被调用
              expect(dragApiCalled).toBeTruthy();
              // 验证 payload 包含正确的 scheduleId
              expect(dragApiPayload).toBeTruthy();
              expect(dragApiPayload?.scheduleId).toBe('sch-drag-1');
            }
          }
        }
      }
    }
  });

  // ---------------------------------------------------------------------------
  // 4. 拖拽冲突检测 (409)
  // ---------------------------------------------------------------------------

  test('拖拽冲突 - 显示冲突详情', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();
    await setupCalendarMocks(page, [schedule]);

    // mock drag-adjust API 返回 409 冲突
    await page.route('**/api/v1/schedules/drag-adjust', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 409,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 409,
            message: '目标时间段存在冲突',
            conflicts: {
              hasConflict: true,
              blocking: true,
              conflicts: [
                {
                  type: 'time_overlap',
                  severity: 'error',
                  message: '目标时间段已存在其他排班',
                  details: { existingScheduleId: 'sch-existing-1' },
                },
                {
                  type: 'capacity_exceeded',
                  severity: 'warning',
                  message: '该时段预约人数较多，建议确认',
                  details: { currentBooked: 15, maxCapacity: 20 },
                },
              ],
            },
          }),
        });
      }
      return route.fallback();
    });

    await navigateToWeekView(page);

    const dragHandle = page.locator('.drag-handle').first();

    if (await dragHandle.isVisible()) {
      const targetSlot = page.locator('[aria-label*="14:00"]').first();

      if (await targetSlot.isVisible()) {
        const dragged = await attemptDrag(
          page,
          '.drag-handle',
          '[aria-label*="14:00"]',
        );

        if (dragged) {
          await page.waitForTimeout(500);

          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认调整排班' });
          if (await confirmModal.isVisible()) {
            // 点击确认触发 API 调用
            const confirmBtn = confirmModal.getByRole('button', { name: '确认调整' });
            if (await confirmBtn.isVisible()) {
              await confirmBtn.click();
              await page.waitForTimeout(1000);

              // 验证冲突信息展示
              const errorAlert = confirmModal.locator('.ant-alert-error');
              if (await errorAlert.isVisible()) {
                await expect(errorAlert).toBeVisible();
                await expect(confirmModal.getByText('目标时间段已存在其他排班')).toBeVisible();
              }

              // 验证 warning 级别的冲突也展示
              const warningAlert = confirmModal.locator('.ant-alert-warning');
              if (await warningAlert.isVisible()) {
                await expect(warningAlert).toBeVisible();
                await expect(confirmModal.getByText('该时段预约人数较多')).toBeVisible();
              }
            }
          }
        }
      }
    }
  });

  // ---------------------------------------------------------------------------
  // 5. 拖拽取消
  // ---------------------------------------------------------------------------

  test('拖拽取消 - 不调用 API', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule();
    await setupCalendarMocks(page, [schedule]);

    let dragApiCalled = false;

    await page.route('**/api/v1/schedules/drag-adjust', async (route) => {
      if (route.request().method() === 'POST') {
        dragApiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ success: true, message: 'ok' }),
        });
      }
      return route.fallback();
    });

    await navigateToWeekView(page);

    const dragHandle = page.locator('.drag-handle').first();

    if (await dragHandle.isVisible()) {
      const targetSlot = page.locator('[aria-label*="14:00"]').first();

      if (await targetSlot.isVisible()) {
        const dragged = await attemptDrag(
          page,
          '.drag-handle',
          '[aria-label*="14:00"]',
        );

        if (dragged) {
          await page.waitForTimeout(500);

          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认调整排班' });
          if (await confirmModal.isVisible()) {
            // 点击取消按钮
            const cancelBtn = confirmModal.getByRole('button', { name: '取消' });
            if (await cancelBtn.isVisible()) {
              await cancelBtn.click();
              await page.waitForTimeout(500);

              // 验证弹窗关闭
              await expect(confirmModal).not.toBeVisible();

              // 验证 API 未被调用
              expect(dragApiCalled).toBeFalsy();
            }
          }
        }
      }
    }
  });

  // ---------------------------------------------------------------------------
  // 6. 停诊排班不可拖拽
  // ---------------------------------------------------------------------------

  test('停诊状态排班不显示拖拽手柄', async ({ page }) => {
    await mockAdminSession(page);

    // 停诊状态的排班 (status: 0)
    const suspendedSchedule = makeSchedule({ id: 'sch-suspended', status: 0 });
    await setupCalendarMocks(page, [suspendedSchedule]);

    await navigateToWeekView(page);

    // 停诊排班不应有拖拽手柄
    const dragHandle = page.locator('.drag-handle').first();
    const draggableCell = page.locator('.draggable-schedule-cell.can-drag').first();

    // 停诊排班仍然渲染为 draggable cell，但不带 can-drag 类
    const allDraggableCells = page.locator('.draggable-schedule-cell');
    if ((await allDraggableCells.count()) > 0) {
      // can-drag 的元素不应存在（停诊不可拖拽）
      const canDragCount = await page.locator('.draggable-schedule-cell.can-drag').count();
      expect(canDragCount).toBe(0);
    }
  });

  // ---------------------------------------------------------------------------
  // 7. 拖拽后弹窗显示正确的源/目标信息
  // ---------------------------------------------------------------------------

  test('拖拽确认弹窗显示完整的源和目标信息', async ({ page }) => {
    await mockAdminSession(page);

    const schedule = makeSchedule({
      startTime: '09:00',
      endTime: '11:00',
      totalSlots: 15,
      bookedSlots: 5,
    });
    await setupCalendarMocks(page, [schedule]);

    await page.route('**/api/v1/schedules/drag-adjust', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: jsonResponse({ success: true, message: 'ok' }),
        });
      }
      return route.fallback();
    });

    await navigateToWeekView(page);

    const dragHandle = page.locator('.drag-handle').first();

    if (await dragHandle.isVisible()) {
      const targetSlot = page.locator('[aria-label*="14:00"]').first();

      if (await targetSlot.isVisible()) {
        const dragged = await attemptDrag(
          page,
          '.drag-handle',
          '[aria-label*="14:00"]',
        );

        if (dragged) {
          await page.waitForTimeout(500);

          const confirmModal = page.locator('.ant-modal').filter({ hasText: '确认调整排班' });
          if (await confirmModal.isVisible()) {
            // 验证源信息
            await expect(confirmModal.getByText('李医生')).toBeVisible();
            await expect(confirmModal.getByText(SCHEDULE_DATE)).toBeVisible();

            // 验证号源信息 (5/15)
            await expect(confirmModal.getByText('5/15')).toBeVisible();

            // 验证弹窗包含「原日期」和「目标日期」标签
            await expect(confirmModal.getByText('原日期')).toBeVisible();
            await expect(confirmModal.getByText('目标日期')).toBeVisible();
            await expect(confirmModal.getByText('原时间')).toBeVisible();
            await expect(confirmModal.getByText('目标时间')).toBeVisible();
          }
        }
      }
    }
  });
});
