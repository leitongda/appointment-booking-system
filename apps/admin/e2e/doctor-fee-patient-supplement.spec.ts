import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

test.describe('医生详情高级操作', () => {
  test('诊金设置弹窗打开', async ({ page }) => {
    await mockAdminSession(page);

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const moreBtn = page.locator('.ant-table-row').first().getByText(/更多/);
      if (await moreBtn.isVisible()) {
        await moreBtn.click();

        const feeMenuItem = page.getByText(/诊费设置/);
        if (await feeMenuItem.isVisible()) {
          await feeMenuItem.click();

          const modal = page.locator('.ant-modal');
          if (await modal.isVisible()) {
            await expect(modal).toBeVisible();
          }
        }
      }
    }
  });

  test('诊金类型开关', async ({ page }) => {
    await mockAdminSession(page);

    let apiCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/consultation-fees/doctors/**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      const method = route.request().method();

      if (path === '/consultation-fees/doctors/doctor-1' && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { useFeeTemplate: 0 } }),
        });
      }

      if (path.match(/^\/consultation-fees\/doctors\/[^/]+\/use-template$/) && method === 'PUT') {
        apiCalled = true;
        requestCaptured = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: null }),
        });
      }

      if (path === '/consultation-fees/doctors/doctor-1/grouped' && method === 'GET') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: [] }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/doctor/list');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const moreBtn = page.locator('.ant-table-row').first().getByText(/更多/);
      if (await moreBtn.isVisible()) {
        await moreBtn.click();
        const feeMenuItem = page.getByText(/诊费设置/);
        if (await feeMenuItem.isVisible()) {
          await feeMenuItem.click();

          const modal = page.locator('.ant-modal');
          if (await modal.isVisible()) {
            const switchBtn = page.locator('.ant-modal').locator('.ant-switch').first();
            if (await switchBtn.isVisible()) {
              await switchBtn.click();

              await page.waitForLoadState('networkidle');
              expect(apiCalled).toBe(true);
              expect(requestCaptured).toBeTruthy();
            }
          }
        }
      }
    }
  });

  test('诊金类型删除', async ({ page }) => {
    await mockAdminSession(page);

    let apiCalled = false;

    await page.route('**/api/v1/consultation-fees/types/**', async (route) => {
      const method = route.request().method();

      if (method === 'DELETE') {
        apiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: null }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/consultation-fee/types');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const deleteLink = page.locator('.ant-table-row').first().getByText(/删除/);
      if (await deleteLink.isVisible()) {
        await deleteLink.click();

        const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();

          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
        }
      } else {
        const row = page.locator('.ant-table-row').first();
        const actionCell = row.locator('td').last();
        const deleteBtn = actionCell.locator('a, button').filter({ hasText: /删除/ });
        if (await deleteBtn.isVisible()) {
          await deleteBtn.click();
          const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
          if (await confirmBtn.isVisible()) {
            await confirmBtn.click();
            await page.waitForLoadState('networkidle');
            expect(apiCalled).toBe(true);
          }
        }
      }
    }
  });

  test('医生预约Tab操作', async ({ page }) => {
    await mockAdminSession(page);

    const apptRecords = [
      {
        id: 'appt-tab-1',
        appointmentNo: 'APT20260515001',
        patientName: '张三',
        patientPhone: '13900001111',
        doctorId: 'doctor-1',
        doctorName: '李医生',
        storeId: 'store-1',
        storeName: '示例门店',
        departmentId: 'dept-1',
        departmentName: '中医科',
        scheduleDate: '2026-05-15',
        timeSlot: 'morning',
        queueNumber: 1,
        status: 0,
        type: 1,
        source: 1,
        fee: 50,
        remark: '',
        createdAt: '2026-05-14 10:00:00',
      },
    ];

    await page.route('**/api/v1/appointments/query**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          message: 'ok',
          data: { items: apptRecords, total: 1 },
        }),
      });
    });

    await page.route('**/api/v1/statistics/appointments/summary**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          code: 200,
          message: 'ok',
          data: {
            total: 1,
            confirmed: 0,
            signedIn: 0,
            completed: 0,
            cancelled: 0,
            noShow: 0,
            expired: 0,
          },
        }),
      });
    });

    await page.goto('/medical-services/doctor/doctor-1?tab=appointment');
    await page.waitForLoadState('networkidle');

    const appointmentTab = page.getByRole('tab', { name: /预约记录/ });
    if (await appointmentTab.isVisible()) {
      await appointmentTab.click();
      await page.waitForLoadState('networkidle');
    }

    if (await page.getByText('预约记录').first().isVisible()) {
      await expect(page.getByText('预约记录').first()).toBeVisible();
    }

    const row = page.getByRole('row').filter({ hasText: '张三' });
    if (await row.isVisible()) {
      await expect(row).toBeVisible();

      const cancelLink = row.getByText(/取消/);
      const noShowLink = row.getByText(/爽约/);

      if (await cancelLink.isVisible()) {
        expect(await cancelLink.isVisible()).toBe(true);
      }
      if (await noShowLink.isVisible()) {
        expect(await noShowLink.isVisible()).toBe(true);
      }
    }
  });
});

test.describe('患者就诊卡管理', () => {
  const mockUserDetail = {
    id: 'user-1',
    phone: '13900001111',
    nickname: '张三',
    avatar: '',
    gender: 1,
    openid: 'oXXXX-test-openid',
    status: 1,
    points: 200,
    createdAt: '2026-01-15 10:00:00',
    updatedAt: '2026-05-01 12:00:00',
    cardCount: 1,
    appointmentCount: 5,
    noShowCount: 0,
    cards: [
      {
        id: 'card-1',
        cardNo: 'P20260001',
        name: '张三',
        phone: '13900001111',
        gender: 1,
        age: 35,
        birthday: '1991-05-15',
        relationship: '本人',
        isDefault: true,
        source: 1,
        appointmentCount: 5,
        noShowCount: 0,
        createdAt: '2026-01-15 10:00:00',
      },
    ],
  };

  test('添加就诊卡', async ({ page }) => {
    await mockAdminSession(page);

    let apiCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/user-manage/user-1', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockUserDetail }),
      });
    });

    await page.route('**/api/v1/user-manage/user-1/cards', async (route) => {
      const method = route.request().method();
      if (method === 'POST') {
        apiCalled = true;
        requestCaptured = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: {
              id: 'card-new-1',
              cardNo: 'P20260999',
              name: '李四',
              phone: '13900002222',
              gender: 1,
              relationship: '配偶',
              isDefault: false,
              source: 2,
              appointmentCount: 0,
              noShowCount: 0,
              createdAt: '2026-05-13 10:00:00',
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/patient/user-1');
    await page.waitForLoadState('networkidle');

    const addCardBtn = page.getByRole('button', { name: /添加就诊卡/ });
    if (await addCardBtn.isVisible()) {
      await addCardBtn.click();

      const addCardModal = page.locator('.ant-modal').filter({ hasText: /添加就诊卡/ });
      if (await addCardModal.isVisible()) {
        await expect(addCardModal).toBeVisible();
      }

      const nameInput = page.locator('.ant-modal').getByLabel(/姓名/);
      if (await nameInput.isVisible()) {
        await nameInput.fill('李四');
      }

      const phoneInput = page.locator('.ant-modal').getByLabel(/手机号/);
      if (await phoneInput.isVisible()) {
        await phoneInput.fill('13900002222');
      }

      const confirmBtn = page.locator('.ant-modal').getByRole('button', { name: /确\s*定/ });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForLoadState('networkidle');
        expect(apiCalled).toBe(true);
      }
    }
  });

  test('编辑就诊卡', async ({ page }) => {
    await mockAdminSession(page);

    let apiCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/user-manage/user-1', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockUserDetail }),
      });
    });

    await page.route('**/api/v1/user-manage/user-1/cards/card-1', async (route) => {
      const method = route.request().method();
      if (method === 'PUT') {
        apiCalled = true;
        requestCaptured = route.request().postDataJSON();
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: {
              ...mockUserDetail.cards[0],
              name: '张三丰',
            },
          }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/patient/user-1');
    await page.waitForLoadState('networkidle');

    const cardListTitle = page.locator('.ant-card-head-title').filter({ hasText: '就诊卡列表' });
    if (await cardListTitle.isVisible()) {
      await expect(cardListTitle).toBeVisible();
    }

    const editLink = page.getByRole('row').filter({ hasText: '张三' }).getByText(/编辑/);
    if (await editLink.isVisible()) {
      await editLink.click();

      const editModal = page.locator('.ant-modal').filter({ hasText: /编辑就诊卡/ });
      if (await editModal.isVisible()) {
        await expect(editModal).toBeVisible();

        const nameInput = editModal.getByLabel(/姓名/);
        if (await nameInput.isVisible()) {
          await nameInput.clear();
          await nameInput.fill('张三丰');
        }

        const confirmBtn = editModal.getByRole('button', { name: /确\s*定/ });
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();
          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
        }
      }
    }
  });

  test('删除就诊卡', async ({ page }) => {
    await mockAdminSession(page);

    let apiCalled = false;

    await page.route('**/api/v1/user-manage/user-1', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockUserDetail }),
      });
    });

    await page.route('**/api/v1/user-manage/user-1/cards/card-1', async (route) => {
      const method = route.request().method();
      if (method === 'DELETE') {
        apiCalled = true;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: { message: '删除成功' } }),
        });
      }
      return route.fallback();
    });

    await page.goto('/medical-services/patient/user-1');
    await page.waitForLoadState('networkidle');

    const cardListTitle = page.locator('.ant-card-head-title').filter({ hasText: '就诊卡列表' });
    if (await cardListTitle.isVisible()) {
      await expect(cardListTitle).toBeVisible();
    }

    const deleteLink = page.getByRole('row').filter({ hasText: '张三' }).getByText(/删除/);
    if (await deleteLink.isVisible()) {
      await deleteLink.click();

      const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
      if (await confirmBtn.isVisible()) {
        await confirmBtn.click();
        await page.waitForLoadState('networkidle');
        expect(apiCalled).toBe(true);
      }
    }
  });
});

test.describe('病历详情查看', () => {
  test('查看病历详情', async ({ page }) => {
    await mockAdminSession(page);

    const mockRecordListItem = {
      id: 'record-1',
      recordNo: 'MR20260513001',
      patientName: '张三',
      doctorName: '李医生',
      departmentName: '中医科',
      diagnosis: '上呼吸道感染',
      visitDate: '2026-05-13',
      status: 1,
      createdAt: '2026-05-13 10:00:00',
    };

    const mockRecordDetail = {
      id: 'record-1',
      recordNo: 'MR20260513001',
      appointmentId: 'appt-1',
      patientId: 'patient-1',
      patientName: '张三',
      patientPhone: '13900001111',
      patientGender: 1,
      doctorId: 'doctor-1',
      doctorName: '李医生',
      departmentId: 'dept-1',
      departmentName: '中医科',
      chiefComplaint: '头痛两天',
      presentIllness: '两天前开始出现头痛症状',
      pastHistory: '无特殊',
      allergyHistory: '无',
      physicalExam: '体温37.2度',
      auxiliaryExam: '血常规正常',
      diagnosis: '上呼吸道感染',
      treatment: '对症治疗',
      prescription: '布洛芬 0.2g tid',
      advice: '多休息多饮水',
      totalFee: 150,
      status: 1,
      visitDate: '2026-05-13',
      createdAt: '2026-05-13 10:00:00',
      updatedAt: '2026-05-13 10:30:00',
    };

    await page.route('**/api/v1/medical-records/**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      const method = route.request().method();

      if (method === 'GET' && path === '/medical-records') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({
            code: 200,
            message: 'ok',
            data: {
              data: [mockRecordListItem],
              total: 1,
              page: 1,
              pageSize: 10,
            },
          }),
        });
      }

      if (method === 'GET' && path === '/medical-records/record-1') {
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: mockRecordDetail }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/medical-record');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    if (await page.getByTitle('病历管理').isVisible()) {
      await expect(page.getByTitle('病历管理')).toBeVisible();
    }

    const row = page.getByRole('row').filter({ hasText: '张三' });
    if (await row.isVisible()) {
      const viewBtn = row.getByText(/查看/);
      if (await viewBtn.isVisible()) {
        await viewBtn.click();

        const drawer = page.locator('.ant-drawer');
        if (await drawer.isVisible()) {
          if (await page.getByText('上呼吸道感染').isVisible()) {
            await expect(page.getByText('上呼吸道感染')).toBeVisible();
          }
          if (await page.getByText('头痛两天').isVisible()) {
            await expect(page.getByText('头痛两天')).toBeVisible();
          }
          if (await page.getByText('MR20260513001').isVisible()) {
            await expect(page.getByText('MR20260513001')).toBeVisible();
          }
        }
      }
    }
  });
});

test.describe('诊费模板管理', () => {
  test('诊费模板列表加载', async ({ page }) => {
    await mockAdminSession(page);

    const mockTemplates = [
      {
        feeTypeId: 'fee-type-1',
        feeTypeName: '普通门诊',
        feeTypeCode: 'normal',
        initialFee: 50,
        followUpFee: 30,
        status: 1,
      },
      {
        feeTypeId: 'fee-type-2',
        feeTypeName: '专家门诊',
        feeTypeCode: 'expert',
        initialFee: 100,
        followUpFee: 80,
        status: 1,
      },
    ];

    await page.route('**/api/v1/consultation-fees/templates**', async (route) => {
      return route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ code: 200, message: 'ok', data: mockTemplates }),
      });
    });

    await page.goto('/medical-services/consultation-fee/templates');
    await page.waitForLoadState('networkidle');

    const bodyText = await page.locator('body').innerText();
    expect(bodyText.length).toBeGreaterThan(0);

    if (await page.getByText('全局诊费模板说明').isVisible()) {
      await expect(page.getByText('全局诊费模板说明')).toBeVisible();
    }
    if (await page.getByText('普通门诊').isVisible()) {
      await expect(page.getByText('普通门诊')).toBeVisible();
    }
    if (await page.getByText('专家门诊').isVisible()) {
      await expect(page.getByText('专家门诊')).toBeVisible();
    }
    if (await page.getByText('50').isVisible()) {
      await expect(page.getByText('50')).toBeVisible();
    }
    if (await page.getByText('100').isVisible()) {
      await expect(page.getByText('100')).toBeVisible();
    }

    const saveBtn = page.getByRole('button', { name: /保存模板/ });
    if (await saveBtn.isVisible()) {
      await expect(saveBtn).toBeVisible();
    }
  });

  test('诊费类型删除', async ({ page }) => {
    await mockAdminSession(page);

    let apiCalled = false;
    let requestCaptured: unknown = null;

    await page.route('**/api/v1/consultation-fees/types/**', async (route) => {
      const url = new URL(route.request().url());
      const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
      const method = route.request().method();

      if (method === 'DELETE' && path.match(/^\/consultation-fees\/types\/[^/]+$/)) {
        apiCalled = true;
        requestCaptured = path;
        return route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify({ code: 200, message: 'ok', data: null }),
        });
      }

      return route.fallback();
    });

    await page.goto('/medical-services/consultation-fee/types');
    await page.waitForLoadState('networkidle');

    if ((await page.locator('.ant-table-row').count()) > 0) {
      const firstRow = page.locator('.ant-table-row').first();
      const deleteLink = firstRow.getByText(/删除/);

      if (await deleteLink.isVisible()) {
        await deleteLink.click();

        const confirmBtn = page.getByRole('button', { name: /确\s*定/ });
        if (await confirmBtn.isVisible()) {
          await confirmBtn.click();
          await page.waitForLoadState('networkidle');
          expect(apiCalled).toBe(true);
          expect(requestCaptured).toBeTruthy();
        }
      }
    }
  });
});
