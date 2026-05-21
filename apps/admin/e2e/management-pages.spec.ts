import { test, expect } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

/**
 * 候补队列 / 支付查询 / 退款管理 / 检查报告 页面 E2E 测试
 *
 * 覆盖四个 P2 新页面的基础可用性：
 * - 页面加载无报错
 * - 核心 UI 元素渲染
 * - 交互（搜索、抽屉打开）可用
 */

// ─── Mock 数据 ───────────────────────────────────────────────────────────────

const waitlistRecords = [
  {
    id: 'wl-1',
    tenantId: 'tenant-1',
    patientId: 'patient-1',
    patientName: '张三',
    patientPhone: '13900001111',
    status: 'WAITING',
    position: 1,
    symptomDescription: '头痛发热',
    schedule: {
      id: 'sch-1',
      scheduleDate: '2026-05-20',
      timeSlot: 'morning',
      storeId: 'store-1',
      storeName: '示例门店',
      departmentId: 'dept-1',
      departmentName: '中医科',
      doctorId: 'doctor-1',
      doctorName: '李医生',
    },
    createdAt: '2026-05-15 10:00:00',
  },
  {
    id: 'wl-2',
    tenantId: 'tenant-1',
    patientId: 'patient-2',
    patientName: '王五',
    patientPhone: '13900003333',
    status: 'PROMOTED',
    position: null,
    symptomDescription: '腰痛',
    schedule: {
      id: 'sch-2',
      scheduleDate: '2026-05-21',
      timeSlot: 'afternoon',
      storeId: 'store-1',
      storeName: '示例门店',
      departmentId: 'dept-1',
      departmentName: '中医科',
      doctorId: 'doctor-1',
      doctorName: '李医生',
    },
    createdAt: '2026-05-14 09:00:00',
  },
];

const waitlistStats = {
  totalWaiting: 5,
  totalPromoted: 12,
  totalCancelled: 3,
  totalExpired: 1,
};

const refundRecords = [
  {
    id: 'refund-1',
    refund_no: 'R20260515001',
    appointment_id: 'appt-1',
    out_trade_no: 'OUT20260515001',
    original_amount: 50.0,
    refund_amount: 50.0,
    refund_reason: '患者取消预约',
    status: 'success',
    wx_refund_id: 'wx_refund_001',
    mch_id: 'mch-demo',
    sub_mchid: '',
    failed_reason: '',
    created_at: '2026-05-15 11:00:00',
    updated_at: '2026-05-15 11:05:00',
  },
  {
    id: 'refund-2',
    refund_no: 'R20260514001',
    appointment_id: 'appt-2',
    out_trade_no: 'OUT20260514001',
    original_amount: 100.0,
    refund_amount: 100.0,
    refund_reason: '医生停诊',
    status: 'pending',
    wx_refund_id: '',
    mch_id: 'mch-demo',
    sub_mchid: '',
    failed_reason: '',
    created_at: '2026-05-14 15:00:00',
    updated_at: '2026-05-14 15:00:00',
  },
];

const examinationReports = [
  {
    id: 'er-1',
    title: '血常规检查报告',
    reportType: 'blood_test',
    fileName: 'blood_test_001.pdf',
    fileSize: 204800,
    fileUrl: 'https://example.com/reports/blood_test_001.pdf',
    patientId: 'patient-1',
    patientName: '张三',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    appointmentId: 'appt-1',
    storeId: 'store-1',
    storeName: '示例门店',
    createdAt: '2026-05-15 14:00:00',
    remark: '各项指标正常',
  },
  {
    id: 'er-2',
    title: '胸部CT检查报告',
    reportType: 'imaging',
    fileName: 'ct_chest_001.dicom',
    fileSize: 5242880,
    fileUrl: 'https://example.com/reports/ct_chest_001.dicom',
    patientId: 'patient-2',
    patientName: '王五',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    appointmentId: 'appt-2',
    storeId: 'store-1',
    storeName: '示例门店',
    createdAt: '2026-05-14 16:00:00',
    remark: '',
  },
];

const paymentOrderStatus = {
  appointment_id: 'appt-1',
  status: 1,
  payment_amount: 50.0,
  refund_status: 'none',
  paid_at: '2026-05-15 10:05:00',
  out_trade_no: 'OUT20260515001',
  transaction_id: 'WX20260515001',
};

// ─── 辅助函数 ────────────────────────────────────────────────────────────────

/** 拦截候补队列相关 API */
async function mockWaitlistApis(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/waitlist/stats**', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ code: 200, message: 'ok', data: waitlistStats }),
    });
  });

  await page.route('**/api/v1/waitlist**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '');
    const method = route.request().method();

    // GET /waitlist/:id — 详情
    if (method === 'GET' && /^\/waitlist\/[^/]+$/.test(path) && !path.includes('stats')) {
      const id = path.split('/')[2];
      const entry = waitlistRecords.find((r) => r.id === id);
      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify({ code: 200, message: 'ok', data: entry ?? waitlistRecords[0] }),
      });
    }

    // GET /waitlist (列表)
    if (method === 'GET' && (path === '/waitlist' || path.startsWith('/waitlist?'))) {
      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify({
          code: 200,
          message: 'ok',
          data: waitlistRecords,
          total: waitlistRecords.length,
          page: 1,
          pageSize: 20,
        }),
      });
    }

    // 其他请求返回成功
    return route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ code: 200, message: 'ok', data: {} }),
    });
  });
}

/** 拦截退款相关 API */
async function mockRefundApis(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/refunds**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '');
    const method = route.request().method();

    // GET /refunds/:id — 详情
    if (method === 'GET' && /^\/refunds\/[^/]+$/.test(path)) {
      const id = path.split('/')[2];
      const record = refundRecords.find((r) => r.id === id);
      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify({ code: 200, message: 'ok', data: record ?? refundRecords[0] }),
      });
    }

    // GET /refunds (列表)
    return route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({
        code: 200,
        message: 'ok',
        data: refundRecords,
        total: refundRecords.length,
        page: 1,
        pageSize: 20,
      }),
    });
  });
}

/** 拦截支付查询 API */
async function mockPaymentApis(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/payments/orders/**', async (route) => {
    return route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({ code: 200, message: 'ok', data: paymentOrderStatus }),
    });
  });
}

/** 拦截检查报告 API */
async function mockExaminationReportApis(page: import('@playwright/test').Page) {
  await page.route('**/api/v1/examination-reports**', async (route) => {
    const url = new URL(route.request().url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '');
    const method = route.request().method();

    // GET /examination-reports/:id — 详情
    if (method === 'GET' && /^\/examination-reports\/[^/]+$/.test(path)) {
      const id = path.split('/')[2];
      const report = examinationReports.find((r) => r.id === id);
      return route.fulfill({
        status: 200,
        contentType: 'application/json; charset=utf-8',
        body: JSON.stringify({ code: 200, message: 'ok', data: report ?? examinationReports[0] }),
      });
    }

    // GET /examination-reports (列表)
    return route.fulfill({
      status: 200,
      contentType: 'application/json; charset=utf-8',
      body: JSON.stringify({
        code: 200,
        message: 'ok',
        data: examinationReports,
        total: examinationReports.length,
        page: 1,
        pageSize: 20,
      }),
    });
  });
}

// ─── 候补队列页面测试 ─────────────────────────────────────────────────────────

test.describe('候补队列页面', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await mockWaitlistApis(page);
  });

  test('页面应成功加载并展示统计卡片', async ({ page }) => {
    await page.goto('/medical-services/appointment/waitlist');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/medical-services\/appointment\/waitlist/);

    // 验证统计卡片
    await expect(page.getByText('等待中')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('已递补')).toBeVisible();
    await expect(page.getByText('已取消')).toBeVisible();
    await expect(page.getByText('已过期')).toBeVisible();

    // 验证统计数值
    await expect(page.getByText('5').first()).toBeVisible();
  });

  test('ProTable 应渲染候补数据', async ({ page }) => {
    await page.goto('/medical-services/appointment/waitlist');
    await page.waitForLoadState('networkidle');

    // 等待表格渲染
    const table = page.locator('.ant-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    // 验证表头列
    await expect(page.getByText('患者').first()).toBeVisible();
    await expect(page.getByText('排班日期').first()).toBeVisible();
    await expect(page.getByText('医生').first()).toBeVisible();

    // 验证数据行
    await expect(page.getByText('张三').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('头痛发热').first()).toBeVisible();
  });

  test('点击详情应打开抽屉', async ({ page }) => {
    await page.goto('/medical-services/appointment/waitlist');
    await page.waitForLoadState('networkidle');

    // 等待数据加载
    await expect(page.getByText('张三').first()).toBeVisible({ timeout: 10_000 });

    // 点击详情链接
    const detailLink = page.locator('a:has-text("详情")').first();
    await detailLink.click();

    // 验证抽屉出现
    const drawer = page.locator('.ant-drawer');
    await expect(drawer).toBeVisible({ timeout: 5_000 });
  });
});

// ─── 支付查询页面测试 ─────────────────────────────────────────────────────────

test.describe('支付查询页面', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await mockPaymentApis(page);
  });

  test('页面应成功加载', async ({ page }) => {
    await page.goto('/finance/payment');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/finance\/payment/);
  });

  test('搜索框应存在并可输入', async ({ page }) => {
    await page.goto('/finance/payment');
    await page.waitForLoadState('networkidle');

    // 验证搜索输入框
    const searchInput = page.locator('input[placeholder*="预约ID"]');
    await expect(searchInput).toBeVisible({ timeout: 10_000 });

    // 输入预约 ID
    await searchInput.fill('appt-1');

    // 验证输入值
    await expect(searchInput).toHaveValue('appt-1');
  });

  test('查询按钮应触发搜索并展示结果', async ({ page }) => {
    await page.goto('/finance/payment');
    await page.waitForLoadState('networkidle');

    // 输入预约 ID
    const searchInput = page.locator('input[placeholder*="预约ID"]');
    await expect(searchInput).toBeVisible({ timeout: 10_000 });
    await searchInput.fill('appt-1');

    // 点击查询按钮
    const searchBtn = page.locator('button:has-text("查询")');
    await searchBtn.click();

    // 等待结果加载
    await page.waitForLoadState('networkidle');

    // 验证支付信息卡片出现
    await expect(page.getByText('支付信息')).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('已预约').first()).toBeVisible();
  });
});

// ─── 退款管理页面测试 ─────────────────────────────────────────────────────────

test.describe('退款管理页面', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await mockRefundApis(page);
  });

  test('页面应成功加载', async ({ page }) => {
    await page.goto('/finance/refund');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/finance\/refund/);
  });

  test('ProTable 应渲染退款记录', async ({ page }) => {
    await page.goto('/finance/refund');
    await page.waitForLoadState('networkidle');

    // 等待表格渲染
    const table = page.locator('.ant-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    // 验证表头列
    await expect(page.getByText('退款单号').first()).toBeVisible();
    await expect(page.getByText('退款金额').first()).toBeVisible();
    await expect(page.getByText('状态').first()).toBeVisible();

    // 验证数据行
    await expect(page.getByText('R20260515001').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('患者取消预约').first()).toBeVisible();
  });

  test('点击查看应打开详情抽屉', async ({ page }) => {
    await page.goto('/finance/refund');
    await page.waitForLoadState('networkidle');

    // 等待数据加载
    await expect(page.getByText('R20260515001').first()).toBeVisible({ timeout: 10_000 });

    // 点击查看按钮（OperationButton type="view"）
    const viewBtn = page.locator('a').filter({ has: page.locator('[class*="eye"]') }).first();
    // 备用：直接找带 "查看详情" 提示的元素或眼睛图标
    if (await viewBtn.isVisible()) {
      await viewBtn.click();
    } else {
      // Fallback: 找操作列中的链接
      const actionLinks = page.locator('.ant-table-tbody a').first();
      await actionLinks.click();
    }

    // 验证抽屉出现
    const drawer = page.locator('.ant-drawer');
    await expect(drawer).toBeVisible({ timeout: 5_000 });

    // 验证抽屉内容
    await expect(page.getByText('退款详情')).toBeVisible();
  });
});

// ─── 检查报告页面测试 ─────────────────────────────────────────────────────────

test.describe('检查报告页面', () => {
  test.beforeEach(async ({ page }) => {
    await mockAdminSession(page);
    await mockExaminationReportApis(page);
  });

  test('页面应成功加载', async ({ page }) => {
    await page.goto('/medical-services/examination-report');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveURL(/\/medical-services\/examination-report/);
  });

  test('ProTable 应渲染报告列表', async ({ page }) => {
    await page.goto('/medical-services/examination-report');
    await page.waitForLoadState('networkidle');

    // 等待表格渲染
    const table = page.locator('.ant-table');
    await expect(table).toBeVisible({ timeout: 15_000 });

    // 验证表头列
    await expect(page.getByText('报告标题').first()).toBeVisible();
    await expect(page.getByText('报告类型').first()).toBeVisible();
    await expect(page.getByText('文件名').first()).toBeVisible();

    // 验证数据行
    await expect(page.getByText('血常规检查报告').first()).toBeVisible({ timeout: 10_000 });
    await expect(page.getByText('血液检验').first()).toBeVisible();
  });

  test('点击详情应打开抽屉', async ({ page }) => {
    await page.goto('/medical-services/examination-report');
    await page.waitForLoadState('networkidle');

    // 等待数据加载
    await expect(page.getByText('血常规检查报告').first()).toBeVisible({ timeout: 10_000 });

    // 点击详情链接
    const detailLink = page.locator('a:has-text("详情")').first();
    await detailLink.click();

    // 验证抽屉出现
    const drawer = page.locator('.ant-drawer');
    await expect(drawer).toBeVisible({ timeout: 5_000 });
  });
});
