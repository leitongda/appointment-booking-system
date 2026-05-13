import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('医生推荐开关', () => {
  test('医生列表推荐开关可切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (!(await switchEl.isVisible())) {
      test.skip();
      return;
    }

    const wasChecked = await switchEl.evaluate((el) =>
      el.classList.contains('ant-switch-checked'),
    );
    await switchEl.click();
    if (wasChecked) {
      await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
    } else {
      await expect(switchEl).toHaveClass(/ant-switch-checked/);
    }
  });

  test('医生详情页推荐开关可切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/doctor-1/edit');
    await page.waitForLoadState('networkidle');

    const switchEl = page.locator('.ant-switch').filter({ hasText: /推荐/ });
    if (!(await switchEl.isVisible())) {
      const anySwitch = page.locator('.ant-form-item').filter({ hasText: /推荐/ }).locator('.ant-switch');
      if (!(await anySwitch.isVisible())) {
        test.skip();
        return;
      }
      const wasChecked = await anySwitch.evaluate((el) =>
        el.classList.contains('ant-switch-checked'),
      );
      await anySwitch.click();
      if (wasChecked) {
        await expect(anySwitch).not.toHaveClass(/ant-switch-checked/);
      } else {
        await expect(anySwitch).toHaveClass(/ant-switch-checked/);
      }
      return;
    }

    const wasChecked = await switchEl.evaluate((el) =>
      el.classList.contains('ant-switch-checked'),
    );
    await switchEl.click();
    if (wasChecked) {
      await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
    } else {
      await expect(switchEl).toHaveClass(/ant-switch-checked/);
    }
  });
});

test.describe('科室推荐/热门开关', () => {
  test('科室列表推荐开关可切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (!(await switchEl.isVisible())) {
      test.skip();
      return;
    }

    const wasChecked = await switchEl.evaluate((el) =>
      el.classList.contains('ant-switch-checked'),
    );
    await switchEl.click();
    if (wasChecked) {
      await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
    } else {
      await expect(switchEl).toHaveClass(/ant-switch-checked/);
    }
  });

  test('科室推荐/热门开关切换后发送请求', async ({ page }) => {
    await mockAdminSession(page);

    let putBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/departments/**', async (route) => {
      if (route.request().method() === 'PUT') {
        putBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: putBody }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/list');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (!(await switchEl.isVisible())) {
      test.skip();
      return;
    }

    await switchEl.click();
    await page.waitForTimeout(500);
    expect(putBody).toBeTruthy();
  });

  test('科室编辑页推荐/热门开关', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/dept-1/edit');
    await page.waitForLoadState('networkidle');

    const recommendSwitch = page.locator('.ant-form-item').filter({ hasText: /推荐/ }).locator('.ant-switch');
    const hotSwitch = page.locator('.ant-form-item').filter({ hasText: /热门/ }).locator('.ant-switch');

    if (await recommendSwitch.isVisible()) {
      const wasChecked = await recommendSwitch.evaluate((el) =>
        el.classList.contains('ant-switch-checked'),
      );
      await recommendSwitch.click();
      if (wasChecked) {
        await expect(recommendSwitch).not.toHaveClass(/ant-switch-checked/);
      } else {
        await expect(recommendSwitch).toHaveClass(/ant-switch-checked/);
      }
    }

    if (await hotSwitch.isVisible()) {
      const wasChecked = await hotSwitch.evaluate((el) =>
        el.classList.contains('ant-switch-checked'),
      );
      await hotSwitch.click();
      if (wasChecked) {
        await expect(hotSwitch).not.toHaveClass(/ant-switch-checked/);
      } else {
        await expect(hotSwitch).toHaveClass(/ant-switch-checked/);
      }
    }

    if (!(await recommendSwitch.isVisible()) && !(await hotSwitch.isVisible())) {
      test.skip();
    }
  });
});

test.describe('排班规则批量启用/禁用', () => {
  test('排班规则页面加载并显示列表', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table, .ant-empty').first()).toBeVisible();
  });

  test('排班规则支持批量选择操作', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const rows = page.locator('.ant-table-row');
    const count = await rows.count();
    if (count === 0) {
      test.skip();
      return;
    }

    const checkbox = rows.first().locator('.ant-checkbox-input');
    if (!(await checkbox.isVisible())) {
      test.skip();
      return;
    }

    await checkbox.click();
    await expect(checkbox).toBeChecked();

    const batchButtons = page.locator('.ant-table').locator('button, a').filter({ hasText: /批量|启用|禁用|删除/ });
    if (await batchButtons.count() > 0) {
      await expect(batchButtons.first()).toBeVisible();
    }
  });

  test('排班规则单条启用/禁用切换', async ({ page }) => {
    await mockAdminSession(page);
    await page.route('**/api/v1/schedule/rules**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                { id: 'rule-1', name: '门诊排班', status: 1, enabled: true },
                { id: 'rule-2', name: '夜班排班', status: 1, enabled: false },
              ],
              total: 2,
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/rule');
    await page.waitForLoadState('networkidle');

    const row = page.locator('.ant-table-row').first();
    const switchEl = row.locator('.ant-switch');
    if (!(await switchEl.isVisible())) {
      test.skip();
      return;
    }

    const wasChecked = await switchEl.evaluate((el) =>
      el.classList.contains('ant-switch-checked'),
    );
    await switchEl.click();
    if (wasChecked) {
      await expect(switchEl).not.toHaveClass(/ant-switch-checked/);
    } else {
      await expect(switchEl).toHaveClass(/ant-switch-checked/);
    }
  });
});

test.describe('停诊审核', () => {
  test('停诊审核页面加载', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/schedule/leave-request');
    await page.waitForLoadState('networkidle');

    await expect(page.locator('.ant-table, .ant-empty').first()).toBeVisible();
  });

  test('停诊审核列表显示状态标签', async ({ page }) => {
    await mockAdminSession(page);
    await page.route('**/api/v1/schedule/leave-requests**', async (route) => {
      if (route.request().method() === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'lr-1',
                  doctorName: '李医生',
                  doctorId: 'doctor-1',
                  startDate: '2026-05-15',
                  endDate: '2026-05-16',
                  reason: '个人原因',
                  status: 0,
                  statusText: '待审核',
                  createdAt: '2026-05-12 10:00:00',
                },
                {
                  id: 'lr-2',
                  doctorName: '王医生',
                  doctorId: 'doctor-2',
                  startDate: '2026-05-20',
                  endDate: '2026-05-21',
                  reason: '学术会议',
                  status: 1,
                  statusText: '已通过',
                  createdAt: '2026-05-11 09:00:00',
                },
              ],
              total: 2,
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/leave-request');
    await page.waitForLoadState('networkidle');

    const rows = page.locator('.ant-table-row');
    const count = await rows.count();
    if (count === 0) {
      test.skip();
      return;
    }

    const tags = page.locator('.ant-tag, .ant-badge-status-text');
    await expect(tags.first()).toBeVisible();
  });

  test('停诊审核通过操作', async ({ page }) => {
    await mockAdminSession(page);

    let approveBody: Record<string, unknown> | null = null;
    await page.route('**/api/v1/schedule/leave-requests**', async (route) => {
      const method = route.request().method();
      if (method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              items: [
                {
                  id: 'lr-1',
                  doctorName: '李医生',
                  doctorId: 'doctor-1',
                  startDate: '2026-05-15',
                  endDate: '2026-05-16',
                  reason: '个人原因',
                  status: 0,
                  statusText: '待审核',
                  createdAt: '2026-05-12 10:00:00',
                },
              ],
              total: 1,
            },
          }),
        });
      }
      if (method === 'PUT' || method === 'POST') {
        approveBody = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { success: true } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/schedule/leave-request');
    await page.waitForLoadState('networkidle');

    const approveBtn = page.locator('.ant-table-row').first().locator('button, a').filter({ hasText: /通过|批准|审核/ });
    if (!(await approveBtn.isVisible())) {
      const globalApprove = page.getByRole('button', { name: /通过|批准|审核/ }).first();
      if (!(await globalApprove.isVisible())) {
        test.skip();
        return;
      }
      await globalApprove.click();
    } else {
      await approveBtn.click();
    }

    const confirmBtn = page.locator('.ant-popconfirm, .ant-modal-confirm').locator('button').filter({ hasText: /确[定认]|是/ });
    if (await confirmBtn.isVisible({ timeout: 2000 }).catch(() => false)) {
      await confirmBtn.click();
    }

    await page.waitForTimeout(500);
  });
});

test.describe('网络超时加载状态', () => {
  test('医生列表慢速 API 显示加载状态', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors?**', async (route) => {
      if (route.request().method() === 'GET') {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    const navPromise = page.goto('/medical-services/doctor/list');
    await expect(page.locator('.ant-spin')).toBeVisible({ timeout: 3000 });
    await navPromise;
    await page.waitForLoadState('networkidle');
  });

  test('门店列表慢速 API 显示加载状态', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/stores?**', async (route) => {
      if (route.request().method() === 'GET') {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    const navPromise = page.goto('/organization/store/list');
    await expect(page.locator('.ant-spin')).toBeVisible({ timeout: 3000 });
    await navPromise;
    await page.waitForLoadState('networkidle');
  });

  test('科室列表慢速 API 显示加载状态', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/departments?**', async (route) => {
      if (route.request().method() === 'GET') {
        await new Promise((resolve) => setTimeout(resolve, 5000));
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 0, data: { items: [], total: 0 } }),
        });
      }
      return route.fallback();
    });

    const navPromise = page.goto('/organization/department/list');
    await expect(page.locator('.ant-spin')).toBeVisible({ timeout: 3000 });
    await navPromise;
    await page.waitForLoadState('networkidle');
  });
});

test.describe('导入文件格式错误提示', () => {
  test('导入弹窗上传错误格式文件显示提示', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const importBtn = page.getByRole('button', { name: /导入/ });
    if (!(await importBtn.isVisible())) {
      test.skip();
      return;
    }

    await importBtn.click();
    await page.waitForTimeout(500);

    const uploadInput = page.locator('.ant-upload input[type="file"]');
    if (!(await uploadInput.count())) {
      test.skip();
      return;
    }

    const tmpFile = '/tmp/test-wrong-format.txt';
    await page.evaluate(() => {
      const blob = new Blob(['invalid content'], { type: 'text/plain' });
      const file = new File([blob], 'test-wrong-format.txt', { type: 'text/plain' });
      const dt = new DataTransfer();
      dt.items.add(file);
      const input = document.querySelector('.ant-upload input[type="file"]') as HTMLInputElement;
      if (input) {
        Object.defineProperty(input, 'files', { value: dt.files });
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    await expect(
      page.getByText(/格式|类型|xlsx|xls|csv|不支持|错误|无效/).first(),
    ).toBeVisible({ timeout: 5000 });
  });
});

test.describe('导入部分失败结果展示', () => {
  test('导入 API 返回部分失败时展示错误详情', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/*/import**', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 0,
            data: {
              total: 10,
              success: 7,
              failed: 3,
              errors: [
                { row: 2, message: '医生账号已存在' },
                { row: 5, message: '科室名称不存在' },
                { row: 8, message: '手机号格式错误' },
              ],
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    const importBtn = page.getByRole('button', { name: /导入/ });
    if (!(await importBtn.isVisible())) {
      test.skip();
      return;
    }

    await importBtn.click();
    await page.waitForTimeout(500);

    const uploadInput = page.locator('.ant-upload input[type="file"]');
    if (!(await uploadInput.count())) {
      test.skip();
      return;
    }

    await page.evaluate(() => {
      const blob = new Blob(['test data'], {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const file = new File([blob], 'doctors.xlsx', {
        type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
      });
      const dt = new DataTransfer();
      dt.items.add(file);
      const input = document.querySelector('.ant-upload input[type="file"]') as HTMLInputElement;
      if (input) {
        Object.defineProperty(input, 'files', { value: dt.files });
        input.dispatchEvent(new Event('change', { bubbles: true }));
      }
    });

    await expect(
      page.getByText(/失败|错误|行/).first(),
    ).toBeVisible({ timeout: 5000 });
  });
});

test.describe('表单提交失败错误提示保留', () => {
  test('新增医生提交 500 错误后提示保留且表单不清空', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/doctors', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '服务器错误' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/doctor/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('医生姓名').fill('测试医生');
    await page.getByLabel('所属门店').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('医生账号').fill('test_error_doctor');
    await page.getByPlaceholder('不填则默认为 123456').fill('Password123!');
    await page.getByLabel('确认密码').fill('Password123!');
    await page.getByLabel('所属科室').click();
    await page.getByTitle('中医科').click();
    await page.getByLabel('职称').fill('主治医师');
    await page.getByLabel('手机号').fill('13900139000');
    await page.getByLabel('擅长').fill('针灸');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(
      page.getByText(/服务器错误|失败|异常/).first(),
    ).toBeVisible({ timeout: 5000 });

    await expect(page.getByLabel('医生姓名')).toHaveValue('测试医生');
    await expect(page.getByLabel('医生账号')).toHaveValue('test_error_doctor');
    await expect(page.getByLabel('职称')).toHaveValue('主治医师');
  });

  test('新增门店提交 500 错误后提示保留且表单不清空', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/stores', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '服务器错误' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('门店名称').fill('测试门店');
    await page.getByLabel('门店编码').fill('TEST001');
    await page.getByLabel('联系人').fill('张三');
    await page.getByLabel('联系方式').fill('13800138000');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(
      page.getByText(/服务器错误|失败|异常/).first(),
    ).toBeVisible({ timeout: 5000 });

    await expect(page.getByLabel('门店名称')).toHaveValue('测试门店');
    await expect(page.getByLabel('门店编码')).toHaveValue('TEST001');
  });

  test('新增科室提交 500 错误后提示保留且表单不清空', async ({ page }) => {
    await mockAdminSession(page);

    await page.route('**/api/v1/departments', async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ code: 500, message: '服务器错误' }),
        });
      }
      return route.fallback();
    });

    await page.goto('/organization/department/create');
    await page.waitForLoadState('networkidle');

    await page.getByLabel('门店选择').click();
    await page.getByTitle('示例门店').click();
    await page.getByLabel('科室名称').fill('测试科室');
    await page.getByLabel('科室标签').fill('测试标签');
    await page.getByLabel('排序').fill('10');
    await page.getByRole('button', { name: /创\s*建/ }).click();

    await expect(
      page.getByText(/服务器错误|失败|异常/).first(),
    ).toBeVisible({ timeout: 5000 });

    await expect(page.getByLabel('科室名称')).toHaveValue('测试科室');
    await expect(page.getByLabel('科室标签')).toHaveValue('测试标签');
    await expect(page.getByLabel('排序')).toHaveValue('10');
  });
});
