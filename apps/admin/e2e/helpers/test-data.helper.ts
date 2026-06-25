/**
 * E2E 测试数据工厂
 *
 * 通过后端 API 创建测试数据，测试结束后自动清理。
 * 处理 FK 依赖顺序：创建时从父到子，删除时从子到父。
 */

const API_BASE = process.env.E2E_API_BASE_URL || 'http://localhost:9000';

/** 通用 API 响应 */
interface ApiResponse<T = unknown> {
  code: number;
  message: string;
  data: T;
}

/** 已创建的测试数据记录，用于清理 */
interface CreatedRecord {
  endpoint: string;
  id: string;
}

/**
 * 通用 API 请求
 */
async function apiRequest<T = unknown>(
  method: string,
  path: string,
  token: string,
  body?: unknown,
): Promise<T> {
  const url = `${API_BASE}/api/v1${path}`;
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    Authorization: `Bearer ${token}`,
  };

  const options: RequestInit = { method, headers };
  if (body) {
    options.body = JSON.stringify(body);
  }

  const response = await fetch(url, options);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(`API ${method} ${path} failed (${response.status}): ${text}`);
  }

  const json: ApiResponse<T> = await response.json();
  return json.data ?? (json as unknown as T);
}

/**
 * 测试数据工厂类
 *
 * 用法：
 * ```ts
 * const factory = new TestDataFactory(accessToken);
 * const store = await factory.createStore({ name: '测试门店' });
 * const dept = await factory.createDepartment(store.id);
 * // ... 测试 ...
 * await factory.cleanup(); // 逆序删除所有创建的数据
 * ```
 */
export class TestDataFactory {
  private token: string;
  private created: CreatedRecord[] = [];

  constructor(token: string) {
    this.token = token;
  }

  /** 更新 token（token 刷新后调用） */
  setToken(token: string): void {
    this.token = token;
  }

  // ==================== 创建方法 ====================

  async createStore(overrides: Record<string, unknown> = {}) {
    const data = {
      name: `E2E测试门店_${Date.now()}`,
      code: `E2E_${Date.now()}`,
      address: '测试地址 1 号',
      city: '上海市',
      phone: '021-12345678',
      contactPerson: '测试联系人',
      status: 1,
      sortOrder: 0,
      openingTime: '08:00:00',
      closingTime: '18:00:00',
      ...overrides,
    };
    const result = await this.create('/stores', data);
    this.track('/stores', result.id);
    return result;
  }

  async createDepartment(storeId: string, overrides: Record<string, unknown> = {}) {
    const data = {
      storeId,
      name: `E2E测试科室_${Date.now()}`,
      tag: '测试科室',
      sortOrder: 0,
      status: 1,
      isRecommended: 0,
      isHot: 0,
      enableBanner: 0,
      enableIntro: 0,
      isFinal: 0,
      ...overrides,
    };
    const result = await this.create('/departments', data);
    this.track('/departments', result.id);
    return result;
  }

  async createDoctor(departmentId: string, overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      name: `E2E医生_${ts}`,
      username: `e2e_doc_${ts}`,
      gender: 1,
      departmentId,
      title: '主治医师',
      phone: `138${String(ts).slice(-8)}`,
      yearsOfExperience: 5,
      maxDailyAppointments: 20,
      status: 1,
      sortOrder: 0,
      isRecommended: 0,
      onlineConsultEnabled: 0,
      ...overrides,
    };
    const result = await this.create('/doctors', data);
    this.track('/doctors', result.id);
    return result;
  }

  async createScheduleRule(doctorId: string, overrides: Record<string, unknown> = {}) {
    const data = {
      doctorId,
      name: `E2E排班规则_${Date.now()}`,
      scheduleType: 1,
      timePeriods: [
        { startTime: '08:00', endTime: '12:00', maxAppointments: 10 },
      ],
      weekdays: [1, 2, 3, 4, 5],
      effectiveFrom: '2026-01-01',
      effectiveTo: '2026-12-31',
      status: 1,
      ...overrides,
    };
    const result = await this.create('/schedule/rules', data);
    this.track('/schedule/rules', result.id);
    return result;
  }

  async createPatient(overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      name: `E2E患者_${ts}`,
      phone: `139${String(ts).slice(-8)}`,
      gender: 1,
      birthday: '1990-01-15',
      idCardType: 1,
      idCard: `31010119900115${String(ts).slice(-4)}`,
      relationship: '本人',
      ...overrides,
    };
    const result = await this.create('/patients', data);
    this.track('/patients', result.id);
    return result;
  }

  async createNews(overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      title: `E2E新闻_${ts}`,
      type: 1,
      summary: 'E2E 测试摘要',
      content: '<p>E2E 测试内容</p>',
      status: 1,
      ...overrides,
    };
    const result = await this.create('/content/news', data);
    this.track('/content/news', result.id);
    return result;
  }

  async createNotice(overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      title: `E2E公告_${ts}`,
      content: '<p>E2E 测试公告内容</p>',
      status: 1,
      ...overrides,
    };
    const result = await this.create('/content/notices', data);
    this.track('/content/notices', result.id);
    return result;
  }

  async createRole(overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      name: `E2E角色_${ts}`,
      code: `E2E_ROLE_${ts}`,
      description: 'E2E 测试角色',
      permissions: ['dashboard', 'dashboard:view'],
      status: 1,
      ...overrides,
    };
    const result = await this.create('/admin/roles', data);
    this.track('/admin/roles', result.id);
    return result;
  }

  async createTenant(overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      tenantCode: `e2e_tenant_${ts}`,
      name: `E2E租户_${ts}`,
      contactName: '测试联系人',
      contactPhone: `138${String(ts).slice(-8)}`,
      subscriptionPlanId: 'plan-basic',
      ...overrides,
    };
    const result = await this.create('/tenants', data);
    this.track('/tenants', result.id);
    return result;
  }

  async createFeeType(overrides: Record<string, unknown> = {}) {
    const ts = Date.now();
    const data = {
      name: `E2E诊费_${ts}`,
      code: `e2e_fee_${ts}`,
      description: 'E2E 测试诊费类型',
      sortOrder: 0,
      status: 1,
      ...overrides,
    };
    const result = await this.create('/consultation-fees/types', data);
    this.track('/consultation-fees/types', result.id);
    return result;
  }

  // ==================== 批量创建 ====================

  async createStores(count: number, overrides: Record<string, unknown> = {}) {
    return Promise.all(
      Array.from({ length: count }, (_, i) =>
        this.createStore({
          name: `E2E批量门店_${i + 1}_${Date.now()}`,
          code: `E2E_B${i + 1}_${Date.now()}`,
          ...overrides,
        }),
      ),
    );
  }

  async createDoctors(
    departmentId: string,
    count: number,
    overrides: Record<string, unknown> = {},
  ) {
    return Promise.all(
      Array.from({ length: count }, (_, i) =>
        this.createDoctor(departmentId, {
          name: `E2E批量医生_${i + 1}`,
          ...overrides,
        }),
      ),
    );
  }

  // ==================== 清理 ====================

  /**
   * 逆序删除所有创建的测试数据
   * 后创建的先删除，避免 FK 约束冲突
   */
  async cleanup(): Promise<void> {
    const errors: Error[] = [];

    // 逆序删除
    for (let i = this.created.length - 1; i >= 0; i--) {
      const { endpoint, id } = this.created[i];
      try {
        await this.delete(endpoint, id);
      } catch (e) {
        // 记录但不中断，尽量清理更多数据
        errors.push(e instanceof Error ? e : new Error(String(e)));
      }
    }

    this.created = [];

    if (errors.length > 0) {
      console.warn(`[TestDataFactory] ${errors.length} 个清理操作失败:`, errors.map(e => e.message));
    }
  }

  /** 获取已创建的记录列表 */
  getCreatedRecords(): CreatedRecord[] {
    return [...this.created];
  }

  // ==================== 内部方法 ====================

  private async create(endpoint: string, data: unknown): Promise<any> {
    return apiRequest('POST', endpoint, this.token, data);
  }

  private async delete(endpoint: string, id: string): Promise<void> {
    await apiRequest('DELETE', `${endpoint}/${id}`, this.token);
  }

  private track(endpoint: string, id: string): void {
    this.created.push({ endpoint, id });
  }
}
