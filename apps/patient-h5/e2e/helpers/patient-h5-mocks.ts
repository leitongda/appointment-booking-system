import { expect, type Page } from '@playwright/test';

const token = 'playwright-patient-token';

const currentPatient = {
  id: 'user-1',
  userId: 'user-1',
  nickname: '测试用户',
  phone: '13900001111',
  avatar: '',
};

const defaultPatients = [
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
    idCardType: 1,
    idCard: '310101199105151234',
  },
  {
    id: 'patient-2',
    userId: 'user-1',
    cardNo: 'P20260002',
    name: '张小宝',
    phone: '13900001112',
    gender: 1,
    age: 8,
    birthday: '2018-03-20',
    relationship: '子女',
    isDefault: false,
    idCardType: 1,
    idCard: '310101201803201234',
  },
];

const defaultDepartments = [
  { id: 'dept-1', name: '神经内科', description: '诊治头痛、头晕等', keywords: ['头痛', '偏头痛', '头晕'] },
  { id: 'dept-2', name: '呼吸内科', description: '诊治咳嗽、哮喘等', keywords: ['咳嗽', '哮喘', '发烧'] },
  { id: 'dept-3', name: '消化内科', description: '诊治胃痛、腹泻等', keywords: ['胃痛', '腹泻', '恶心'] },
];

const defaultDoctors = [
  {
    id: 'doctor-1',
    name: '李医生',
    title: '主治医师',
    departmentId: 'dept-1',
    departmentName: '神经内科',
    specialty: '头痛、偏头痛',
    avatar: '',
    tags: '头痛,头晕',
  },
];

const defaultAppointments = [
  {
    id: 'appt-1',
    patientId: 'patient-1',
    patientName: '张三',
    doctorId: 'doctor-1',
    doctorName: '李医生',
    departmentName: '神经内科',
    storeName: '示例门店',
    appointmentDate: '2026-05-25',
    timeSlot: '09:00-09:30',
    status: 1,
    queueNumber: 1,
    fee: 50,
    createdAt: '2026-05-20 10:00:00',
  },
];

const defaultMessages = [
  {
    id: 'msg-1',
    title: '预约成功通知',
    content: '您已成功预约 2026-05-25 神经内科 李医生',
    type: 'appointment',
    isRead: false,
    createdAt: '2026-05-20 10:00:00',
  },
  {
    id: 'msg-2',
    title: '就诊提醒',
    content: '您明天有预约，请准时到达',
    type: 'reminder',
    isRead: true,
    createdAt: '2026-05-19 08:00:00',
  },
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type MockRoute = Parameters<Parameters<Page['route']>[1]>[0];

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
  return fulfill(route, data, { total: data.length, page: 1, pageSize: 10 });
}

export interface MockPatientSessionOptions {
  authenticated?: boolean;
}

export async function mockPatientSession(
  page: Page,
  options: MockPatientSessionOptions = {},
) {
  const { authenticated = true } = options;

  await page.addInitScript(
    ([accessToken, user, shouldAuth]) => {
      if (shouldAuth) {
        localStorage.setItem('patient_token', JSON.stringify(accessToken));
        localStorage.setItem('userId', user.id);
        localStorage.setItem('patient_user_info', JSON.stringify(user));
      } else {
        localStorage.removeItem('patient_token');
        localStorage.removeItem('userId');
        localStorage.removeItem('patient_user_info');
      }
    },
    [token, currentPatient, authenticated],
  );

  // Mutable copies for mutation tests
  const patients = [...defaultPatients];
  const appointments = [...defaultAppointments];
  const messages = [...defaultMessages];

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '') || '/';
    const method = request.method();

    // Auth
    if (path === '/user/info' || path === '/user/me') {
      return fulfill(route, currentPatient);
    }

    // Patients (family members)
    if (path === '/patients' && method === 'GET') {
      return fulfill(route, patients);
    }

    if (path === '/patients' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const newPatient = {
        id: `patient-${Date.now()}`,
        userId: 'user-1',
        cardNo: `P${Date.now().toString().slice(-8)}`,
        name: String(payload.name ?? ''),
        phone: String(payload.phone ?? ''),
        gender: Number(payload.gender ?? 0),
        age: 0,
        birthday: String(payload.birthday ?? ''),
        relationship: String(payload.relationship ?? '其他'),
        isDefault: false,
        idCardType: Number(payload.idCardType ?? 1),
        idCard: String(payload.idCard ?? ''),
      };
      patients.push(newPatient);
      return fulfill(route, newPatient);
    }

    if (path.match(/^\/patients\/[^/]+$/) && method === 'GET') {
      const patientId = path.split('/')[2];
      const matched = patients.find((p) => p.id === patientId);
      if (matched) return fulfill(route, matched);
    }

    if (path.match(/^\/patients\/[^/]+$/) && method === 'PUT') {
      const patientId = path.split('/')[2];
      const idx = patients.findIndex((p) => p.id === patientId);
      if (idx >= 0) {
        const payload = request.postDataJSON() as Record<string, unknown>;
        Object.assign(patients[idx], payload);
        return fulfill(route, patients[idx]);
      }
    }

    if (path.match(/^\/patients\/[^/]+$/) && method === 'DELETE') {
      const patientId = path.split('/')[2];
      const idx = patients.findIndex((p) => p.id === patientId);
      if (idx >= 0) {
        patients.splice(idx, 1);
        return fulfill(route, { success: true });
      }
    }

    if (path.match(/^\/patients\/[^/]+\/set-default/) && method === 'PUT') {
      const patientId = path.split('/')[2];
      patients.forEach((p) => { p.isDefault = p.id === patientId; });
      return fulfill(route, { success: true });
    }

    // Departments
    if (path === '/departments/tree') {
      return fulfill(route, defaultDepartments.map((d) => ({ ...d, children: [] })));
    }

    if (path === '/departments/hot') {
      return fulfill(route, defaultDepartments.slice(0, 2));
    }

    if (path.match(/^\/departments\/[^/]+$/) && method === 'GET') {
      const deptId = path.split('/')[2];
      const matched = defaultDepartments.find((d) => d.id === deptId);
      if (matched) return fulfill(route, matched);
    }

    // Symptom match
    if (path.startsWith('/departments/symptom-match')) {
      const q = url.searchParams.get('q') || '';
      const matched = defaultDepartments
        .filter((d) => d.keywords.some((kw: string) => kw.includes(q) || q.includes(kw)))
        .map((d) => ({
          id: d.id,
          name: d.name,
          description: d.description,
          icon: '',
          matchedKeywords: d.keywords.filter((kw: string) => kw.includes(q) || q.includes(kw)),
          score: d.keywords.filter((kw: string) => kw.includes(q) || q.includes(kw)).length,
        }));
      return fulfill(route, matched);
    }

    // Doctors
    if (path === '/doctors/recommended') {
      return fulfill(route, defaultDoctors);
    }

    if (path.match(/^\/departments\/[^/]+\/doctors/) && method === 'GET') {
      const deptId = path.split('/')[2];
      return fulfill(route, defaultDoctors.filter((d) => d.departmentId === deptId));
    }

    // Appointments
    if (path === '/appointments' && method === 'GET') {
      const status = url.searchParams.get('status');
      const filtered = appointments.filter((a) => !status || String(a.status) === status);
      return emptyPage(route, filtered);
    }

    if (path === '/appointments' && method === 'POST') {
      const payload = request.postDataJSON() as Record<string, unknown>;
      const newAppt = {
        id: `appt-${Date.now()}`,
        patientName: '张三',
        doctorName: '李医生',
        departmentName: '神经内科',
        storeName: '示例门店',
        appointmentDate: String(payload.appointmentDate ?? '2026-05-30'),
        timeSlot: String(payload.timeSlot ?? '09:00-09:30'),
        status: 1,
        queueNumber: appointments.length + 1,
        fee: 50,
        createdAt: new Date().toISOString(),
      };
      appointments.unshift(newAppt);
      return fulfill(route, newAppt);
    }

    if (path.match(/^\/appointments\/[^/]+$/) && method === 'GET') {
      const apptId = path.split('/')[2];
      const matched = appointments.find((a) => a.id === apptId);
      if (matched) return fulfill(route, matched);
    }

    if (path.match(/^\/appointments\/[^/]+\/cancel/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointments.find((a) => a.id === apptId);
      if (appt) {
        appt.status = 6;
        return fulfill(route, appt);
      }
    }

    if (path.match(/^\/appointments\/[^/]+\/sign-in/) && method === 'PUT') {
      const apptId = path.split('/')[2];
      const appt = appointments.find((a) => a.id === apptId);
      if (appt) {
        appt.status = 2;
        return fulfill(route, { message: '签到成功' });
      }
    }

    // Messages
    if (path === '/messages' && method === 'GET') {
      const type = url.searchParams.get('type');
      const filtered = messages.filter((m) => !type || type === 'all' || m.type === type);
      return emptyPage(route, filtered);
    }

    if (path === '/messages/unread-count') {
      const unread = messages.filter((m) => !m.isRead).length;
      return fulfill(route, { total: unread, appointment: unread, system: 0 });
    }

    if (path.match(/^\/messages\/[^/]+\/read/) && method === 'PUT') {
      const msgId = path.split('/')[2];
      const msg = messages.find((m) => m.id === msgId);
      if (msg) msg.isRead = true;
      return fulfill(route, { success: true });
    }

    if (path === '/messages/read-all' && method === 'PUT') {
      messages.forEach((m) => { m.isRead = true; });
      return fulfill(route, { success: true });
    }

    // Schedules
    if (path.startsWith('/schedules/available')) {
      return fulfill(route, [
        { id: 'slot-1', time: '09:00-09:30', available: 5 },
        { id: 'slot-2', time: '09:30-10:00', available: 3 },
        { id: 'slot-3', time: '10:00-10:30', available: 0 },
      ]);
    }

    // Catch-all
    if (method !== 'GET') {
      return fulfill(route, { success: true });
    }
    return emptyPage(route);
  });
}

export async function openPatientRoute(page: Page, path: string) {
  await page.goto(path);
  await page.waitForLoadState('networkidle');
}

export { currentPatient, defaultPatients, defaultAppointments, defaultMessages };
