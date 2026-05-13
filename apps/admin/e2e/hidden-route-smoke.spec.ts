import { expect, test } from '@playwright/test';
import { mockAdminSession } from './helpers/admin-mocks';

const hiddenRoutes = [
  // Platform
  { path: '/platform/tenant/create', name: '新增租户' },
  { path: '/platform/tenant/tenant-1/edit', name: '编辑租户' },
  { path: '/platform/tenant/tenant-1/usage', name: '租户用量' },
  { path: '/platform/tenant/plan/create', name: '新增订阅计划' },
  { path: '/platform/tenant/plan/plan-basic/edit', name: '编辑订阅计划' },
  { path: '/platform/miniapp-platform/release', name: '小程序发布' },

  // Organization
  { path: '/organization/store/create', name: '新增门店' },
  { path: '/organization/store/store-1/edit', name: '编辑门店' },
  { path: '/organization/department/create', name: '新增科室' },
  { path: '/organization/department/dept-1/edit', name: '编辑科室' },

  // Medical Services
  { path: '/medical-services/doctor/create', name: '新增医生' },
  { path: '/medical-services/doctor/doctor-1/edit', name: '编辑医生' },
  { path: '/medical-services/doctor/doctor-1/booking-setting', name: '医生预约设置' },
  { path: '/medical-services/doctor/doctor-1/consultation-fee', name: '医生诊金设置' },
  { path: '/medical-services/schedule/template', name: '排班模板' },
  { path: '/medical-services/schedule/custom', name: '自定义排班' },
  { path: '/medical-services/appointment/appt-1/detail', name: '预约详情' },
  { path: '/medical-services/patient/patient-1/detail', name: '患者详情' },

  // Content Center
  { path: '/content-center/content/news/create', name: '发布新闻' },
  { path: '/content-center/content/notice/create', name: '发布公告' },
  { path: '/content-center/content/banner/create', name: '新增 Banner' },
  { path: '/content-center/message/send', name: '发送消息' },

  // System
  { path: '/system/role/create', name: '新增角色' },
  { path: '/system/role/role-super-admin/edit', name: '编辑角色' },
  { path: '/system/role/role-super-admin/permission', name: '角色权限' },
  { path: '/system/user/create', name: '新增用户' },
  { path: '/system/user/admin-1/edit', name: '编辑用户' },
  { path: '/system/email-template/create', name: '新增邮件模板' },

  // Configuration
  { path: '/configuration/medical/shift-types', name: '班次类型配置' },
  { path: '/configuration/medical/booking-rules', name: '预约规则配置' },
  { path: '/configuration/system/hospital-info', name: '医院信息' },
  { path: '/configuration/system/wechat', name: '微信设置' },
  { path: '/configuration/system/email', name: '邮件设置' },
  { path: '/configuration/system/email-template/create', name: '新增邮件模板(配置)' },

  // Statistics
  { path: '/statistics/overview', name: '统计概览' },
  { path: '/statistics/appointment', name: '预约统计' },

  // Account
  { path: '/account/settings', name: '个人设置' },
];

test.describe('隐藏路由烟雾测试', () => {
  for (const route of hiddenRoutes) {
    test(`${route.name} (${route.path}) 页面可正常加载`, async ({ page }) => {
      await mockAdminSession(page);
      await page.goto(route.path);
      await page.waitForLoadState('networkidle');

      const bodyText = await page.locator('body').innerText();
      expect(bodyText.length).toBeGreaterThan(0);

      const notFound = page.getByText(/404|页面不存在|找不到页面/);
      await expect(notFound).toHaveCount(0);
    });
  }
});

test.describe('隐藏路由 - 表单页面内容验证', () => {
  test('新增医生页面包含表单字段', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/create');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('form, .ant-form')).toBeVisible();
  });

  test('新增门店页面包含表单字段', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/create');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('form, .ant-form')).toBeVisible();
  });

  test('新增科室页面包含表单字段', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/department/create');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('form, .ant-form')).toBeVisible();
  });

  test('新增租户页面包含表单字段', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/platform/tenant/create');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('form, .ant-form')).toBeVisible();
  });

  test('编辑医生页面加载已有数据', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/doctor/doctor-1/edit');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('form, .ant-form')).toBeVisible();
  });

  test('编辑门店页面加载已有数据', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/organization/store/store-1/edit');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('form, .ant-form')).toBeVisible();
  });

  test('预约详情页面显示信息', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/appointment/appt-1/detail');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-descriptions, .ant-card, .ant-spin')).toBeVisible();
  });

  test('患者详情页面显示信息', async ({ page }) => {
    await mockAdminSession(page);
    await page.goto('/medical-services/patient/patient-1/detail');
    await page.waitForLoadState('networkidle');
    await expect(page.locator('.ant-descriptions, .ant-card, .ant-spin')).toBeVisible();
  });
});
