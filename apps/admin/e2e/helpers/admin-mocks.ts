import { expect, type Page } from '@playwright/test';

const token = 'playwright-admin-token';
const publicKey = `-----BEGIN PUBLIC KEY-----
MFwwDQYJKoZIhvcNAQEBBQADSwAwSAJBAN4JQ9l8D1g0K1TKoEt1TGVtC6zqD2cE
s0v1a2Yj5l6t6n4Q8GxjG9j0t1mL0vT4w0J6vJxQxL6lY8hU5m2M0mMCAwEAAQ==
-----END PUBLIC KEY-----`;

const currentStore = {
  id: 'store-1',
  name: '示例门店',
  logo: '',
};

const currentAdmin = {
  id: 'admin-1',
  username: 'superadmin',
  name: 'Playwright 超级管理员',
  phone: '13800138000',
  email: 'playwright@example.com',
  avatar: '',
  status: 1,
  roleType: 'admin',
  roleCode: 'SUPER_ADMIN',
  roleName: '超级管理员',
  isAdmin: true,
  isSuperAdmin: true,
  canSwitchStores: true,
  permissions: ['*'],
  tenantId: 'tenant-1',
  tenantName: '演示租户',
  storeIds: [currentStore.id],
  stores: [currentStore],
  tenant: {
    id: 'tenant-1',
    name: '演示租户',
    tenantCode: 'demo-tenant',
    status: 1,
  },
};

const storeAdminUser = {
  ...currentAdmin,
  id: 'admin-store-admin',
  username: 'storeadmin',
  name: 'Playwright 门店管理员',
  phone: '13800138001',
  roleCode: 'STORE_ADMIN',
  roleName: '门店管理员',
  isAdmin: false,
  isSuperAdmin: false,
  isStoreAdmin: true,
  canSwitchStores: false,
  permissions: [
    'dashboard', 'dashboard:view',
    'store', 'store:list',
    'department', 'department:list', 'department:create', 'department:update',
    'doctor', 'doctor:list', 'doctor:detail', 'doctor:create', 'doctor:update',
    'schedule', 'schedule:list',
    'appointment', 'appointment:list', 'appointment:detail',
    'patient', 'patient:list', 'patient:detail',
    'content', 'content:news',
    'message', 'message:list',
    'feedback', 'feedback:list',
    'system:user',
  ],
};

const storeUser = {
  ...currentAdmin,
  id: 'admin-store-user',
  username: 'storeuser',
  name: 'Playwright 门店普通用户',
  phone: '13800138002',
  roleCode: 'STORE_USER',
  roleName: '门店普通用户',
  isAdmin: false,
  isSuperAdmin: false,
  isStoreAdmin: false,
  canSwitchStores: false,
  permissions: [
    'dashboard', 'dashboard:view',
    'doctor', 'doctor:list', 'doctor:detail',
    'schedule', 'schedule:list',
    'appointment', 'appointment:list', 'appointment:detail',
    'patient', 'patient:list', 'patient:detail',
  ],
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const roleUsers: Record<string, any> = {
  SUPER_ADMIN: currentAdmin,
  STORE_ADMIN: storeAdminUser,
  STORE_USER: storeUser,
};

type MockRoute = Parameters<Parameters<Page['route']>[1]>[0];

export interface MockAdminSessionOptions {
  authenticated?: boolean;
  role?: 'SUPER_ADMIN' | 'STORE_ADMIN' | 'STORE_USER';
}

function apiBody(data: unknown, extra: Record<string, unknown> = {}) {
  return JSON.stringify({
    code: 200,
    message: 'ok',
    data,
    ...extra,
  });
}

function fulfill(route: MockRoute, data: unknown, extra: Record<string, unknown> = {}) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json; charset=utf-8',
    body: apiBody(data, extra),
  });
}

function emptyPage(route: MockRoute, data: unknown[] = []) {
  return fulfill(route, data, { total: data.length, page: 1, pageSize: 20 });
}

function emptyOverview() {
  return {
    total_page_views: 0,
    total_unique_users: 0,
    total_clicks: 0,
    total_searches: 0,
    avg_duration: 0,
    top_pages: [],
    top_clicks: [],
    top_keywords: [],
    daily_stats: [],
  };
}

export async function mockAdminSession(
  page: Page,
  options: MockAdminSessionOptions = {},
) {
  const { authenticated = true, role = 'SUPER_ADMIN' } = options;
  const currentUser = roleUsers[role] ?? currentAdmin;

  await page.addInitScript(
    ([accessToken, admin, store, rsaKey, shouldAuthenticate]) => {
      localStorage.setItem('rsa_public_key', rsaKey);
      localStorage.setItem('rsa_public_key_timestamp', Date.now().toString());

      if (!shouldAuthenticate) {
        localStorage.removeItem('hospital_token');
        localStorage.removeItem('hospital_refresh_token');
        localStorage.removeItem('hospital_current_tenant_id');
        localStorage.removeItem('hospital_current_store');
        localStorage.removeItem('hospital_user_info');
        return;
      }

      localStorage.setItem('hospital_token', JSON.stringify(accessToken));
      localStorage.setItem('hospital_refresh_token', JSON.stringify('playwright-refresh-token'));
      localStorage.setItem('hospital_current_tenant_id', 'tenant-1');
      localStorage.setItem('hospital_current_store', JSON.stringify(store));
      localStorage.setItem('hospital_user_info', JSON.stringify(admin));
    },
    [token, currentUser, currentStore, publicKey, authenticated],
  );

  const storeRecords = [
    {
      ...currentStore,
      code: 'DEMO1001',
      city: '上海市',
      address: '上海市测试路 1 号',
      phone: '021-12345678',
      status: 1,
      themeStyle: '现代-蓝',
      maxCardsPerUser: 5,
    },
  ];
  const roleList = [
    {
      id: 'role-super-admin',
      name: '超级管理员',
      code: 'SUPER_ADMIN',
      description: '系统内置角色',
      permissions: ['*'],
      status: 1,
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const departmentRecords = [
    {
      id: 'dept-1',
      storeId: currentStore.id,
      name: '中医科',
      tag: '专家科室',
      sortOrder: 1,
      status: 1,
      isRecommended: 0,
      isHot: 0,
      enableBanner: 0,
      enableIntro: 0,
      isFinal: 0,
      parentId: '',
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const doctorRecords = [
    {
      id: 'doctor-1',
      name: '李医生',
      username: 'liys',
      gender: 0,
      storeId: currentStore.id,
      storeName: currentStore.name,
      departmentId: 'dept-1',
      departmentName: '中医科',
      title: '主治医师',
      status: 1,
      isRecommended: 0,
      onlineConsultEnabled: 0,
      sortOrder: 1,
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const newsRecords = [
    {
      id: 'news-1',
      title: '示例新闻',
      type: 1,
      summary: '示例摘要',
      content: '<p>示例内容</p>',
      viewCount: 10,
      isTop: false,
      status: 1,
      publishTime: '2026-01-01 08:00:00',
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const tenantRecords = [
    {
      id: 'tenant-1',
      tenantCode: 'tenant-1',
      name: '演示租户',
      status: 1,
      subscriptionPlanId: 'plan-basic',
      subscriptionPlanName: '基础版',
      subscriptionEndAt: '2026-12-31',
      storeCount: 1,
      adminCount: 1,
      contactName: '王管理员',
      contactPhone: '13800138000',
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const planList = [
    {
      id: 'plan-basic',
      planCode: 'basic',
      name: '基础版',
      code: 'basic',
      description: '基础版订阅计划',
      status: 1,
      priceMonthly: 199,
      priceYearly: 1990,
      currency: 'CNY',
      maxStores: 3,
      maxAdmins: 10,
      maxDoctors: 50,
      maxAppointmentsPerMonth: 5000,
      maxStorageMb: 1024,
      isDefault: true,
      sortOrder: 0,
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const feeTypeRecords = [
    {
      id: 'fee-type-1',
      name: '普通门诊',
      code: 'normal',
      description: '普通门诊诊费',
      sortOrder: 1,
      status: 1,
      isGlobal: true,
      createdAt: '2026-01-01 08:00:00',
    },
    {
      id: 'fee-type-2',
      name: '专家门诊',
      code: 'expert',
      description: '专家门诊诊费',
      sortOrder: 2,
      status: 1,
      isGlobal: true,
      createdAt: '2026-01-01 08:00:00',
    },
  ];
  const patientRecords = [
    {
      id: 'patient-1',
      userId: 'user-1',
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
      isBlacklist: false,
      totalConsumption: 1500,
      idCardType: 1,
      idCard: '310101199105151234',
      ethnicity: '汉族',
      province: '上海市',
      city: '上海市',
      district: '浦东新区',
      street: '张江镇',
      address: '测试路 100 号',
      createdAt: '2026-01-15 10:00:00',
      nickname: '微信用户',
      points: 200,
      statistics: {
        appointmentCount: 5,
        completedCount: 4,
        noShowCount: 0,
      },
      familyMembers: [],
    },
  ];
  const appointmentRecords = [
    {
      id: 'appt-1',
      patientId: 'patient-1',
      patientName: '张三',
      patientPhone: '13900001111',
      doctorId: 'doctor-1',
      doctorName: '李医生',
      storeId: 'store-1',
      storeName: '示例门店',
      departmentId: 'dept-1',
      departmentName: '中医科',
      appointmentDate: '2026-05-15',
      timeSlot: '09:00-09:30',
      status: 1,
      type: 1,
      source: 1,
      fee: 50,
      remark: '',
      createdAt: '2026-05-14 10:00:00',
    },
  ];

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
    const method = request.method();

    if (path === '/admin/public-key') {
      return fulfill(route, { publicKey });
    }

    if (path === '/admin/login' && method === 'POST') {
      return fulfill(route, {
        accessToken: token,
        refreshToken: 'playwright-refresh-token',
        expiresIn: 7200,
        admin: currentAdmin,
        store: currentStore,
        stores: [currentStore],
      });
    }

    if (path === '/admin/me') {
      return fulfill(route, currentUser);
    }

    if (path === '/admin/roles/all') {
      return fulfill(route, roleList);
    }

    if (path === '/admin/roles' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const createdRole = {
        id: `role-${roleList.length + 1}`,
        name: String(payload.name ?? ''),
        code: String(payload.code ?? ''),
        description: String(payload.description ?? ''),
        permissions: [],
        status: Number(payload.status ?? 1),
        createdAt: '2026-05-12 10:00:00',
      };
      roleList.unshift(createdRole);
      return fulfill(route, createdRole);
    }

    if (path.startsWith('/admin/roles/') && method === 'PUT') {
      const roleId = path.split('/')[3];
      const idx = roleList.findIndex((r) => r.id === roleId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(roleList[idx], payload);
        return fulfill(route, roleList[idx]);
      }
    }

    if (path.startsWith('/admin/roles/') && method === 'DELETE') {
      const roleId = path.split('/')[3];
      const idx = roleList.findIndex((r) => r.id === roleId);
      if (idx >= 0) {
        roleList.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path === '/admin/roles') {
      return emptyPage(route, roleList);
    }

    if (path === '/admin/admins') {
      return emptyPage(route, [currentAdmin]);
    }

    if (path === '/stores') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const createdStore = {
          id: `store-${storeRecords.length + 1}`,
          name: String(payload.name ?? ''),
          code: String(payload.code ?? ''),
          address: String(payload.address ?? ''),
          city: '上海市',
          phone: String(payload.phone ?? ''),
          contactPerson: String(payload.contactPerson ?? ''),
          email: String(payload.email ?? ''),
          themeStyle: String(payload.themeStyle ?? '现代-蓝'),
          sortOrder: Number(payload.sortOrder ?? 0),
          status: Number(payload.status ?? 1),
          maxCardsPerUser: Number(payload.maxCardsPerUser ?? 5),
          openingTime: String(payload.openingTime ?? '08:00:00'),
          closingTime: String(payload.closingTime ?? '18:00:00'),
          description: String(payload.description ?? ''),
          logo: '',
        };
        storeRecords.unshift(createdStore);
        return fulfill(route, createdStore);
      }

      return emptyPage(route, storeRecords);
    }

    if (path === '/stores/check-unique') {
      const field = url.searchParams.get('field');
      const value = url.searchParams.get('value');
      const exists = storeRecords.some((record) => {
        if (field === 'name') return record.name === value;
        if (field === 'code') return record.code === value;
        return false;
      });
      return fulfill(route, { exists });
    }

    if (path.startsWith('/stores/') && method === 'GET') {
      const storeId = path.split('/')[2];
      const matched = storeRecords.find((record) => record.id === storeId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.startsWith('/stores/') && method === 'PUT') {
      const storeId = path.split('/')[2];
      const idx = storeRecords.findIndex((r) => r.id === storeId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(storeRecords[idx], payload);
        return fulfill(route, storeRecords[idx]);
      }
    }

    if (path.startsWith('/stores/') && method === 'DELETE') {
      const storeId = path.split('/')[2];
      const idx = storeRecords.findIndex((r) => r.id === storeId);
      if (idx >= 0) {
        storeRecords.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path === '/departments/tree') {
      return fulfill(route, departmentRecords.map((record) => ({
        id: record.id,
        name: record.name,
        children: [],
      })));
    }

    if (path === '/departments/all') {
      return fulfill(route, departmentRecords);
    }

    if (path === '/departments') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const storeName = storeRecords.find((item) => item.id === payload.storeId)?.name ?? currentStore.name;
        const createdDepartment = {
          id: `dept-${departmentRecords.length + 1}`,
          storeId: String(payload.storeId ?? currentStore.id),
          storeName,
          parentId: String(payload.parentId ?? ''),
          name: String(payload.name ?? ''),
          tag: String(payload.tag ?? ''),
          description: String(payload.description ?? ''),
          sortOrder: Number(payload.sortOrder ?? 0),
          status: Number(payload.status ?? 1),
          isRecommended: Number(payload.isRecommended ?? 0),
          isHot: Number(payload.isHot ?? 0),
          enableBanner: Number(payload.enableBanner ?? 0),
          enableIntro: Number(payload.enableIntro ?? 0),
          isFinal: Number(payload.isFinal ?? 0),
          phone: String(payload.phone ?? ''),
          location: String(payload.location ?? ''),
          workingHours: String(payload.workingHours ?? ''),
          createdAt: '2026-05-12 10:00:00',
        };
        departmentRecords.unshift(createdDepartment);
        return fulfill(route, createdDepartment);
      }

      const name = url.searchParams.get('name');
      const storeId = url.searchParams.get('store_id');
      const filtered = departmentRecords.filter((record) => {
        const matchesName = !name || record.name.includes(name);
        const matchesStore = !storeId || record.storeId === storeId;
        return matchesName && matchesStore;
      });
      return emptyPage(route, filtered);
    }

    if (path.startsWith('/departments/') && method === 'GET') {
      const departmentId = path.split('/')[2];
      const matched = departmentRecords.find((record) => record.id === departmentId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.startsWith('/departments/') && method === 'PUT') {
      const departmentId = path.split('/')[2];
      const idx = departmentRecords.findIndex((r) => r.id === departmentId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(departmentRecords[idx], payload);
        return fulfill(route, departmentRecords[idx]);
      }
    }

    if (path.startsWith('/departments/') && method === 'DELETE') {
      const departmentId = path.split('/')[2];
      const idx = departmentRecords.findIndex((r) => r.id === departmentId);
      if (idx >= 0) {
        departmentRecords.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path === '/doctors/generate-username' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const baseName = String(payload.name ?? 'doctor').toLowerCase();
      return fulfill(route, { username: `${baseName.replace(/\s+/g, '')}${doctorRecords.length + 1}` });
    }

    if (path === '/doctors/check-username' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const username = String(payload.username ?? '');
      const exists = doctorRecords.some((record) => record.username === username);
      return fulfill(route, { exists, suggestions: exists ? [`${username}01`, `${username}02`] : [] });
    }

    if (path === '/doctors/all') {
      return fulfill(route, doctorRecords);
    }

    if (path === '/doctors/recommended') {
      return fulfill(route, doctorRecords.filter((record) => record.isRecommended === 1));
    }

    if (path === '/doctors') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const storeId = String(payload.store_id ?? currentStore.id);
        const departmentId = String(payload.department_id ?? 'dept-1');
        const createdDoctor = {
          id: `doctor-${doctorRecords.length + 1}`,
          name: String(payload.name ?? ''),
          username: String(payload.username ?? ''),
          gender: Number(payload.gender ?? 0),
          storeId,
          storeName: storeRecords.find((item) => item.id === storeId)?.name ?? currentStore.name,
          departmentId,
          departmentName: departmentRecords.find((item) => item.id === departmentId)?.name ?? '未分配',
          title: String(payload.title ?? ''),
          phone: String(payload.phone ?? ''),
          yearsOfExperience: Number(payload.years_of_experience ?? 0),
          maxDailyAppointments: Number(payload.max_daily_appointments ?? 0),
          onlineConsultEnabled: Number(payload.online_consult_enabled ?? 0),
          onlineConsultFee: Number(payload.online_consult_fee ?? 0),
          pageStyle: Number(payload.page_style ?? 1),
          tags: String(payload.tags ?? ''),
          specialty: String(payload.specialty ?? ''),
          introduction: String(payload.introduction ?? ''),
          isRecommended: Number(payload.is_recommended ?? 0),
          sortOrder: Number(payload.sort_order ?? 0),
          status: Number(payload.status ?? 1),
          createdAt: '2026-05-12 10:00:00',
        };
        doctorRecords.unshift(createdDoctor);
        return fulfill(route, createdDoctor);
      }

      const name = url.searchParams.get('name');
      const filtered = doctorRecords.filter((record) => !name || record.name.includes(name));
      return emptyPage(route, filtered);
    }

    if (path.startsWith('/doctors/') && method === 'GET') {
      const doctorId = path.split('/')[2];
      const matched = doctorRecords.find((record) => record.id === doctorId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.startsWith('/doctors/') && method === 'PUT') {
      const doctorId = path.split('/')[2];
      const idx = doctorRecords.findIndex((r) => r.id === doctorId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(doctorRecords[idx], payload);
        return fulfill(route, doctorRecords[idx]);
      }
    }

    if (path.startsWith('/doctors/') && method === 'DELETE') {
      const doctorId = path.split('/')[2];
      const idx = doctorRecords.findIndex((r) => r.id === doctorId);
      if (idx >= 0) {
        doctorRecords.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path === '/content/news') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const createdNews = {
          id: `news-${newsRecords.length + 1}`,
          title: String(payload.title ?? ''),
          type: Number(payload.type ?? 1),
          coverImage: String(payload.coverImage ?? ''),
          summary: String(payload.summary ?? ''),
          content: String(payload.content ?? ''),
          viewCount: 0,
          isTop: Number(payload.isTop ?? 0) === 1,
          status: Number(payload.status ?? 1),
          publishTime: '2026-05-12 10:00:00',
          createdAt: '2026-05-12 10:00:00',
        };
        newsRecords.unshift(createdNews);
        return fulfill(route, createdNews);
      }

      const title = url.searchParams.get('title') ?? url.searchParams.get('keyword');
      const filtered = newsRecords.filter((record) => !title || record.title.includes(title));
      return emptyPage(route, filtered);
    }

    if (path.startsWith('/content/news/') && method === 'GET') {
      const newsId = path.split('/')[3];
      const matched = newsRecords.find((record) => record.id === newsId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path === '/tenants/plans') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const createdPlan = {
          id: `plan-${planList.length + 1}`,
          planCode: String(payload.planCode ?? ''),
          name: String(payload.name ?? ''),
          code: String(payload.planCode ?? ''),
          description: String(payload.description ?? ''),
          status: Number(payload.status ?? 1),
          priceMonthly: Number(payload.priceMonthly ?? 0),
          priceYearly: Number(payload.priceYearly ?? 0),
          currency: String(payload.currency ?? 'CNY'),
          maxStores: Number(payload.maxStores ?? 1),
          maxAdmins: Number(payload.maxAdmins ?? 5),
          maxDoctors: Number(payload.maxDoctors ?? 50),
          maxAppointmentsPerMonth: Number(payload.maxAppointmentsPerMonth ?? 1000),
          maxStorageMb: Number(payload.maxStorageMb ?? 1024),
          isDefault: Boolean(payload.isDefault ?? false),
          sortOrder: Number(payload.sortOrder ?? 0),
          createdAt: '2026-05-12 10:00:00',
        };
        planList.unshift(createdPlan);
        return fulfill(route, createdPlan);
      }
      return fulfill(route, planList);
    }

    if (path.match(/^\/tenants\/plans\/[^/]+$/) && method === 'GET') {
      const planId = path.split('/')[3];
      const matched = planList.find((p) => p.id === planId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.match(/^\/tenants\/plans\/[^/]+$/) && method === 'PUT') {
      const planId = path.split('/')[3];
      const idx = planList.findIndex((p) => p.id === planId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(planList[idx], payload);
        return fulfill(route, planList[idx]);
      }
    }

    if (path.match(/^\/tenants\/plans\/[^/]+$/) && method === 'DELETE') {
      const planId = path.split('/')[3];
      const idx = planList.findIndex((p) => p.id === planId);
      if (idx >= 0) {
        planList.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path.match(/^\/tenants\/[^/]+\/usage\/logs/) && method === 'GET') {
      return fulfill(route, []);
    }

    if (path.match(/^\/tenants\/[^/]+\/usage/) && method === 'GET') {
      return fulfill(route, {
        tenantId: 'tenant-1',
        totalStores: 1,
        totalAdmins: 1,
        totalDoctors: 1,
        monthAppointmentCount: 0,
        monthCompletedCount: 0,
        monthCancelledCount: 0,
        monthNewUserCount: 0,
        storageUsedMb: 0,
        maxStores: 3,
        maxAdmins: 10,
        maxDoctors: 50,
        maxAppointmentsPerMonth: 5000,
        maxStorageMb: 1024,
      });
    }

    if (path.match(/^\/tenants\/[^/]+\/subscriptions/) && method === 'GET') {
      return fulfill(route, []);
    }

    if (path === '/tenants/check-unique') {
      const code = url.searchParams.get('tenant_code');
      const exists = tenantRecords.some((record) => record.tenantCode === code);
      return fulfill(route, { exists });
    }

    if (path === '/tenants') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const subscriptionPlanId = String(payload.subscriptionPlanId ?? 'plan-basic');
        const planName = planList.find((item) => item.id === subscriptionPlanId)?.name ?? '基础版';
        const createdTenant = {
          id: `tenant-${tenantRecords.length + 1}`,
          tenantCode: String(payload.tenantCode ?? ''),
          name: String(payload.name ?? ''),
          status: 1,
          subscriptionPlanId,
          subscriptionPlanName: planName,
          subscriptionEndAt: '2026-12-31',
          storeCount: 0,
          adminCount: 0,
          contactName: String(payload.contactName ?? ''),
          contactPhone: String(payload.contactPhone ?? ''),
          createdAt: '2026-05-12 10:00:00',
        };
        tenantRecords.unshift(createdTenant);
        return fulfill(route, createdTenant);
      }

      const keyword = url.searchParams.get('keyword');
      const filtered = tenantRecords.filter((record) => {
        return !keyword || record.name.includes(keyword) || record.tenantCode.includes(keyword);
      });
      return emptyPage(route, filtered);
    }

    if (path.startsWith('/tenants/') && method === 'GET') {
      const tenantId = path.split('/')[2];
      const matched = tenantRecords.find((record) => record.id === tenantId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.startsWith('/tenants/') && method === 'PUT') {
      const tenantId = path.split('/')[2];
      const idx = tenantRecords.findIndex((r) => r.id === tenantId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(tenantRecords[idx], payload);
        return fulfill(route, tenantRecords[idx]);
      }
    }

    if (path.startsWith('/tenants/') && method === 'DELETE') {
      const tenantId = path.split('/')[2];
      const idx = tenantRecords.findIndex((r) => r.id === tenantId);
      if (idx >= 0) {
        tenantRecords.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path === '/statistics/overview') {
      return fulfill(route, {
        todayAppointments: 0,
        todayVisits: 0,
        totalPatients: 0,
        totalDoctors: 0,
        monthAppointments: 0,
        monthRevenue: 0,
      });
    }

    if (path === '/statistics/appointments/summary') {
      return fulfill(route, {
        total: 0,
        completed: 0,
        noShow: 0,
        cancelled: 0,
        completedRate: 0,
        noShowRate: 0,
        cancelledRate: 0,
      });
    }

    if (
      path === '/statistics/appointments/trend' ||
      path === '/statistics/revenue/trend' ||
      path === '/statistics/appointments/status' ||
      path === '/statistics/departments/ranking' ||
      path === '/statistics/doctors/ranking' ||
      path === '/statistics/stores/ranking' ||
      path === '/statistics/time-slots/distribution' ||
      path === '/statistics/weekday/distribution'
    ) {
      return fulfill(route, []);
    }

    if (path === '/statistics/store-dashboard') {
      return fulfill(route, {
        users: {
          total: 0,
          todayNew: 0,
          yesterdayNew: 0,
          weekNew: 0,
          lastWeekNew: 0,
          weekGrowthRate: 0,
        },
        visitors: {
          todayPV: 0,
          todayUV: 0,
          yesterdayPV: 0,
          yesterdayUV: 0,
          pvWeekGrowthRate: 0,
          uvWeekGrowthRate: 0,
        },
        appointments: {
          todayCount: 0,
          yesterdayCount: 0,
          totalCheckins: 0,
        },
      });
    }

    if (path === '/analytics/overview') {
      return fulfill(route, emptyOverview());
    }

    if (path === '/analytics/batch') {
      return fulfill(route, { accepted: true });
    }

    if (path === '/settings/booking') {
      return fulfill(route, {
        advanceDays: 10,
        sameDayBooking: true,
        cancelHours: 2,
        perDayLimit: 3,
        perDoctorLimit: 1,
        noShowLimit: 3,
        blacklistDays: 30,
        advanceBookingMinutes: 0,
        advanceBookingDirection: 'before',
        advanceBookingReference: 'end',
        signInAdvanceMinutes: 30,
        signInLateMinutes: 30,
      });
    }

    if (path === '/settings/hospital') {
      return fulfill(route, {
        hospitalName: 'Playwright 演示医院',
        hospitalLevel: '三级甲等',
        address: '上海市测试路 1 号',
        phone: '021-12345678',
        workTime: '08:00-18:00',
        introduction: '用于自动化测试的演示数据',
        logo: '',
      });
    }

    if (path === '/settings/wechat') {
      return fulfill(route, {
        appId: 'wx-demo',
        appSecret: 'secret',
        mchId: 'mch-demo',
        apiKey: 'api-key',
        notifyUrl: 'https://example.com/api/v1/wechat/pay/notify',
      });
    }

    if (path === '/settings/booking-fields') {
      return fulfill(route, []);
    }

    if (path === '/settings/patient-card') {
      return fulfill(route, {
        cardName: '就诊卡',
        cardDescription: '',
        maxCardsPerUser: 5,
        showOnHomepage: false,
      });
    }

    if (path === '/settings/email') {
      return fulfill(route, {
        smtpHost: '',
        smtpPort: 465,
        smtpUser: '',
        smtpPassword: '',
        smtpSsl: true,
        senderName: '',
        senderEmail: '',
      });
    }

    if (path === '/settings/image') {
      return fulfill(route, {
        thumbnailSizes: [
          { name: 'small', width: 200, height: 200 },
          { name: 'medium', width: 800, height: 800 },
        ],
        compressQuality: 85,
      });
    }

    if (path === '/settings/time-periods') {
      return fulfill(route, {
        periods: [],
        isCustom: false,
      });
    }

    if (path === '/consultation-fees/types') {
      return fulfill(route, feeTypeRecords);
    }

    if (path.match(/^\/consultation-fees\/types\/[^/]+$/) && method === 'GET') {
      const typeId = path.split('/')[3];
      const matched = feeTypeRecords.find((ft) => ft.id === typeId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path === '/patients') {
      if (method === 'POST') {
        const payload = request.postDataJSON() as Record<string, unknown>;
        const createdPatient = {
          id: `patient-${patientRecords.length + 1}`,
          userId: `user-${patientRecords.length + 1}`,
          cardNo: `P${Date.now().toString().slice(-8)}`,
          name: String(payload.name ?? ''),
          phone: String(payload.phone ?? ''),
          gender: Number(payload.gender ?? 0),
          age: 0,
          birthday: String(payload.birthday ?? ''),
          relationship: String(payload.relationship ?? '本人'),
          isDefault: Boolean(payload.isDefault ?? true),
          source: 2,
          appointmentCount: 0,
          noShowCount: 0,
          isBlacklist: false,
          totalConsumption: 0,
          idCardType: Number(payload.idCardType ?? 1),
          idCard: String(payload.idCard ?? ''),
          ethnicity: String(payload.ethnicity ?? '汉族'),
          province: String(payload.province ?? ''),
          city: String(payload.city ?? ''),
          district: String(payload.district ?? ''),
          street: String(payload.street ?? ''),
          address: String(payload.address ?? ''),
          createdAt: '2026-05-12 10:00:00',
          nickname: '微信用户',
          points: 0,
          statistics: { appointmentCount: 0, completedCount: 0, noShowCount: 0 },
          familyMembers: [],
        };
        patientRecords.unshift(createdPatient);
        return fulfill(route, createdPatient);
      }

      const keyword = url.searchParams.get('keyword');
      const filtered = patientRecords.filter((record) => {
        return !keyword || record.name.includes(keyword) || record.phone.includes(keyword);
      });
      return emptyPage(route, filtered);
    }

    if (path.match(/^\/patients\/[^/]+$/) && method === 'GET') {
      const patientId = path.split('/')[2];
      const matched = patientRecords.find((record) => record.id === patientId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.match(/^\/patients\/[^/]+\/appointments/) && method === 'GET') {
      return emptyPage(route, []);
    }

    if (path.match(/^\/patients\/[^/]+\/consumption-records/) && method === 'GET') {
      return emptyPage(route, []);
    }

    if (path.match(/^\/patients\/[^/]+\/points/) && method === 'GET') {
      return fulfill(route, { data: [], total: 0, currentPoints: 0 });
    }

    if (path.match(/^\/patients\/[^/]+\/family-members/) && method === 'GET') {
      return fulfill(route, []);
    }

    // Appointment endpoints
    if (path === '/appointments/query') {
      const status = url.searchParams.get('status');
      const filtered = appointmentRecords.filter((record) => {
        return status === null || String(record.status) === status;
      });
      return emptyPage(route, filtered);
    }

    if (path.match(/^\/appointments\/query\/[^/]+$/) && method === 'GET') {
      const apptId = path.split('/')[3];
      const matched = appointmentRecords.find((record) => record.id === apptId);
      if (matched) {
        return fulfill(route, matched);
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/cancel$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        appt.status = 6;
        appt.cancelReason = String(payload.reason ?? '');
        return fulfill(route, appt);
      }
    }

    if (path === '/refunds' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const apptId = String(payload.appointment_id ?? '');
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 6;
        appt.refundStatus = 'refunded';
        appt.refundedAmount = Number(payload.refund_amount ?? 0);
      }
      return fulfill(route, { id: `refund-${Date.now()}`, status: 'approved' });
    }

    if (path.match(/^\/refunds/) && method === 'GET') {
      return fulfill(route, []);
    }

    if (path.match(/^\/appointments\/[^/]+\/sign-in$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 2;
        return fulfill(route, { message: '签到成功', queueNumber: 1 });
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/cancel-sign-in$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 1;
        return fulfill(route, { message: '取消签到成功' });
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/call$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 4;
        return fulfill(route, appt);
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/pass$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 7;
        return fulfill(route, appt);
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/recall$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 4;
        return fulfill(route, appt);
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/no-show$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 8;
        return fulfill(route, appt);
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/complete$/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointmentRecords.find((record) => record.id === apptId);
      if (appt) {
        appt.status = 5;
        return fulfill(route, appt);
      }
    }

    if (path.startsWith('/appointments/query/')) {
      return emptyPage(route, []);
    }

    if (path.startsWith('/data/')) {
      return fulfill(route, []);
    }

    if (method !== 'GET') {
      return fulfill(route, { success: true });
    }

    return emptyPage(route);
  });
}

export async function openAdminRoute(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

export async function expectAdminRouteReady(page: Page, path: string, label?: string) {
  await openAdminRoute(page, path);
  await expect(page).toHaveURL(new RegExp(path.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')));
  if (label) {
    await expect(page.getByText(label).first()).toBeVisible();
  }
}

export { currentAdmin, storeAdminUser, storeUser };

export function createAppointmentWithStatus(status: number, overrides: Record<string, unknown> = {}) {
  return {
    id: `appt-${Date.now()}`,
    patientId: 'patient-1',
    patientName: '张三',
    patientPhone: '13900001111',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    storeId: 'store-1',
    storeName: '示例门店',
    departmentId: 'dept-1',
    departmentName: '中医科',
    appointmentDate: '2026-05-15',
    timeSlot: '09:00-09:30',
    status,
    type: 1,
    source: 1,
    fee: 50,
    remark: '',
    createdAt: '2026-05-14 10:00:00',
    ...overrides,
  };
}
