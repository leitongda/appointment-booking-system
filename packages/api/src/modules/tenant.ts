import request from '../request';

// ========== 订阅计划 ==========

export interface SubscriptionPlan {
  id: string;
  planCode: string;
  name: string;
  description?: string;
  priceMonthly: number;
  priceYearly: number;
  currency: string;
  maxStores: number;
  maxAdmins: number;
  maxDoctors: number;
  maxAppointmentsPerMonth: number;
  maxStorageMb: number;
  features?: string;
  status: number;
  sortOrder: number;
  isDefault: boolean;
  createdAt: string;
  updatedAt?: string;
}

export interface SubscriptionPlanCreateData {
  planCode: string;
  name: string;
  description?: string;
  priceMonthly?: number;
  priceYearly?: number;
  currency?: string;
  maxStores?: number;
  maxAdmins?: number;
  maxDoctors?: number;
  maxAppointmentsPerMonth?: number;
  maxStorageMb?: number;
  features?: string;
  status?: number;
  sortOrder?: number;
  isDefault?: boolean;
}

export interface SubscriptionPlanUpdateData {
  name?: string;
  description?: string;
  priceMonthly?: number;
  priceYearly?: number;
  maxStores?: number;
  maxAdmins?: number;
  maxDoctors?: number;
  maxAppointmentsPerMonth?: number;
  maxStorageMb?: number;
  features?: string;
  status?: number;
  sortOrder?: number;
  isDefault?: boolean;
}

// ========== 租户 ==========

export interface Tenant {
  id: string;
  tenantCode: string;
  name: string;
  status: number; // 0-禁用 1-正常 2-欠费 3-试用
  subscriptionPlanId?: string;
  subscriptionPlanName?: string;
  subscriptionStartAt?: string;
  subscriptionEndAt?: string;
  billingCycle?: string;
  maxStores?: number;
  maxAdmins?: number;
  maxDoctors?: number;
  maxAppointmentsPerMonth?: number;
  features?: string;
  brandingConfig?: string;
  passwordPolicy?: string;
  tags?: string;
  logRetentionDays?: number;
  rateLimitPerMinute?: number;
  rateLimitPerSecond?: number;
  contactName?: string;
  contactPhone?: string;
  contactEmail?: string;
  address?: string;
  customDomain?: string;
  subdomain?: string;
  storeCount?: number;
  adminCount?: number;
  createdAt: string;
  updatedAt?: string;
}

export interface TenantListParams {
  keyword?: string;
  status?: number;
  subscriptionPlanId?: string;
  page?: number;
  pageSize?: number;
}

export interface TenantCreateData {
  tenantCode: string;
  name: string;
  subscriptionPlanId?: string;
  billingCycle?: string;
  maxStores?: number;
  maxAdmins?: number;
  maxDoctors?: number;
  maxAppointmentsPerMonth?: number;
  features?: string;
  brandingConfig?: string;
  passwordPolicy?: string;
  tags?: string;
  logRetentionDays?: number;
  contactName?: string;
  contactPhone?: string;
  contactEmail?: string;
  address?: string;
  customDomain?: string;
  subdomain?: string;
}

export interface TenantUpdateData {
  name?: string;
  status?: number;
  subscriptionPlanId?: string;
  billingCycle?: string;
  maxStores?: number;
  maxAdmins?: number;
  maxDoctors?: number;
  maxAppointmentsPerMonth?: number;
  features?: string;
  brandingConfig?: string;
  passwordPolicy?: string;
  tags?: string;
  logRetentionDays?: number;
  rateLimitPerMinute?: number;
  rateLimitPerSecond?: number;
  contactName?: string;
  contactPhone?: string;
  contactEmail?: string;
  address?: string;
  customDomain?: string;
  subdomain?: string;
}

// ========== 租户订阅 ==========

export interface TenantSubscription {
  id: string;
  tenantId: string;
  planId: string;
  planCode: string;
  planName: string;
  billingCycle: string;
  startAt: string;
  endAt: string;
  amount?: number;
  currency?: string;
  discountRate?: number;
  finalAmount?: number;
  paymentStatus: string;
  paymentMethod?: string;
  paymentTransactionId?: string;
  paidAt?: string;
  status: number;
  autoRenew: boolean;
  createdAt: string;
}

export interface TenantSubscriptionCreateData {
  planId: string;
  billingCycle: string;
  startAt?: string;
  endAt?: string;
  amount?: number;
  discountRate?: number;
  paymentMethod?: string;
  autoRenew?: boolean;
}

// ========== 租户用量 ==========

export interface TenantUsageLog {
  id: string;
  tenantId: string;
  usageDate: string;
  appointmentCount: number;
  appointmentCompletedCount: number;
  appointmentCancelledCount: number;
  newUserCount: number;
  activeUserCount: number;
  activeDoctorCount: number;
  storageUsedMb: number;
  smsSentCount: number;
  pushSentCount: number;
  createdAt: string;
}

export interface TenantUsageSummary {
  tenantId: string;
  totalStores: number;
  totalAdmins: number;
  totalDoctors: number;
  monthAppointmentCount: number;
  monthCompletedCount: number;
  monthCancelledCount: number;
  monthNewUserCount: number;
  storageUsedMb: number;
  subscriptionPlanName?: string;
  subscriptionEndAt?: string;
  maxStores: number;
  maxAdmins: number;
  maxDoctors: number;
  maxAppointmentsPerMonth: number;
  maxStorageMb: number;
}

// ========== 当前租户信息（前端消费） ==========

export interface CurrentTenant {
  id: string;
  tenantCode: string;
  name: string;
  status: number;
  subscriptionPlanName?: string;
  subscriptionEndAt?: string;
  isSubscriptionActive: boolean;
  daysUntilExpiry?: number;
  billingCycle: string;
  contactPhone?: string;
}

export interface CurrentTenantPublic {
  status: number;
  subscriptionEndAt?: string;
  isSubscriptionActive: boolean;
  name?: string;
}

export interface TenantNotification {
  id: string;
  notificationType: string;
  title: string;
  content: string;
  isRead: boolean;
  readAt?: string;
  priority: number;
  extraMetadata?: string;
  createdAt: string;
}

export interface TenantNotificationList {
  items: TenantNotification[];
  unreadCount: number;
  total: number;
}

// ========== API ==========

// ========== 租户自注册 ==========

export interface TenantSelfRegisterData {
  tenantCode: string;
  name: string;
  contactName: string;
  contactPhone: string;
  contactEmail?: string;
  adminUsername: string;
  adminPassword: string;
}

export interface TenantSelfRegisterResult {
  id: string;
  tenantCode: string;
  name: string;
  status: number;
  subscriptionPlanId?: string;
  subscriptionPlanName?: string;
  subscriptionStartAt?: string;
  subscriptionEndAt?: string;
  contactName?: string;
  contactPhone?: string;
  adminUser?: {
    id: string;
    username: string;
    phone: string;
  };
}

// ========== 标签 ==========

export interface TenantTag {
  name: string;
  count: number;
}

// ========== 迁移 ==========

export interface MigrationPrecheckResult {
  compatible: boolean;
  warnings: string[];
  blockers: string[];
  estimatedDuration?: string;
}

export interface MigrationExecuteData {
  targetPlanId: string;
  dryRun?: boolean;
  confirmOverride?: boolean;
}

export interface MigrationResult {
  success: boolean;
  message: string;
  details?: Record<string, unknown>;
}

// ========== 密码策略 ==========

export interface PasswordPolicy {
  minLength: number;
  maxLength: number;
  requireUppercase: boolean;
  requireLowercase: boolean;
  requireDigit: boolean;
  requireSpecialChar: boolean;
  maxAge?: number;
  preventReuse?: number;
  lockoutThreshold?: number;
  lockoutDuration?: number;
}

// ========== 用量趋势 ==========

export interface TenantUsageTrend {
  date: string;
  appointmentCount: number;
  completedCount: number;
  cancelledCount: number;
  newUserCount: number;
  activeUserCount: number;
  storageUsedMb: number;
}

export const tenantApi = {
  // 租户自注册（公开接口，无需认证）
  selfRegister: (data: TenantSelfRegisterData): Promise<TenantSelfRegisterResult> => {
    return request.post('/tenants/register', data);
  },

  // 订阅计划
  getPlans: (status?: number): Promise<SubscriptionPlan[]> => {
    return request.get('/tenants/plans', { params: { status } });
  },

  getPlan: (planId: string): Promise<SubscriptionPlan> => {
    return request.get(`/tenants/plans/${planId}`);
  },

  createPlan: (data: SubscriptionPlanCreateData): Promise<SubscriptionPlan> => {
    return request.post('/tenants/plans', data);
  },

  updatePlan: (planId: string, data: SubscriptionPlanUpdateData): Promise<SubscriptionPlan> => {
    return request.put(`/tenants/plans/${planId}`, data);
  },

  deletePlan: (planId: string): Promise<{ message: string }> => {
    return request.delete(`/tenants/plans/${planId}`);
  },

  // 租户管理
  getTenants: (params: TenantListParams): Promise<{ data: Tenant[]; total: number; page: number; pageSize: number }> => {
    const queryParams = {
      keyword: params.keyword,
      status: params.status,
      subscription_plan_id: params.subscriptionPlanId,
      page: params.page,
      page_size: params.pageSize,
    };
    return request.get('/tenants', { params: queryParams });
  },

  getTenant: (tenantId: string): Promise<Tenant> => {
    return request.get(`/tenants/${tenantId}`);
  },

  createTenant: (data: TenantCreateData): Promise<Tenant> => {
    return request.post('/tenants', data);
  },

  updateTenant: (tenantId: string, data: TenantUpdateData): Promise<Tenant> => {
    return request.put(`/tenants/${tenantId}`, data);
  },

  deleteTenant: (tenantId: string): Promise<{ message: string }> => {
    return request.delete(`/tenants/${tenantId}`);
  },

  activateTenant: (tenantId: string): Promise<{ message: string }> => {
    return request.post(`/tenants/${tenantId}/activate`);
  },

  suspendTenant: (tenantId: string): Promise<{ message: string }> => {
    return request.post(`/tenants/${tenantId}/suspend`);
  },

  checkTenantCodeUnique: (tenantCode: string, excludeId?: string): Promise<{ exists: boolean }> => {
    return request.get('/tenants/check-unique', { params: { tenant_code: tenantCode, exclude_id: excludeId } });
  },

  // 租户订阅
  getTenantSubscriptions: (tenantId: string, limit?: number): Promise<TenantSubscription[]> => {
    return request.get(`/tenants/${tenantId}/subscriptions`, { params: { limit } });
  },

  createTenantSubscription: (tenantId: string, data: TenantSubscriptionCreateData): Promise<TenantSubscription> => {
    return request.post(`/tenants/${tenantId}/subscriptions`, data);
  },

  // 租户用量
  getTenantUsage: (tenantId: string): Promise<TenantUsageSummary> => {
    return request.get(`/tenants/${tenantId}/usage`);
  },

  getTenantUsageLogs: (tenantId: string, params?: { startDate?: string; endDate?: string; limit?: number }): Promise<TenantUsageLog[]> => {
    const queryParams = params ? {
      start_date: params.startDate,
      end_date: params.endDate,
      limit: params.limit,
    } : undefined;
    return request.get(`/tenants/${tenantId}/usage/logs`, { params: queryParams });
  },

  // 当前租户信息（前端消费）
  getCurrentTenant: (): Promise<CurrentTenant> => {
    return request.get('/tenants/me');
  },

  getCurrentTenantPublic: (): Promise<CurrentTenantPublic> => {
    return request.get('/tenants/me/public');
  },

  getMyNotifications: (params?: { unread?: boolean; page?: number; pageSize?: number }): Promise<TenantNotificationList> => {
    const queryParams = params ? {
      unread: params.unread,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/tenants/me/notifications', { params: queryParams });
  },

  markNotificationRead: (notificationId: string): Promise<{ message: string }> => {
    return request.post(`/tenants/me/notifications/${notificationId}/read`);
  },

  markAllNotificationsRead: (): Promise<{ message: string }> => {
    return request.post('/tenants/me/notifications/read-all');
  },

  // 标签管理
  getAllTags: (): Promise<string[]> => {
    return request.get('/tenants/tags');
  },

  updateTenantTags: (tenantId: string, tags: string[]): Promise<void> => {
    return request.put(`/tenants/${tenantId}/tags`, { tags });
  },

  // 数据迁移
  precheckMigration: (tenantId: string, targetPlanId: string): Promise<MigrationPrecheckResult> => {
    return request.post(`/tenants/${tenantId}/migration/precheck`, { targetPlanId });
  },

  executeMigration: (tenantId: string, data: MigrationExecuteData): Promise<MigrationResult> => {
    return request.post(`/tenants/${tenantId}/migration/migrate`, data);
  },

  // 密码策略
  getPasswordPolicy: (tenantId: string): Promise<PasswordPolicy> => {
    return request.get(`/tenants/${tenantId}/password-policy`);
  },

  updatePasswordPolicy: (tenantId: string, data: Partial<PasswordPolicy>): Promise<PasswordPolicy> => {
    return request.put(`/tenants/${tenantId}/password-policy`, data);
  },

  // 用量趋势
  getTenantUsageTrends: (tenantId: string, params?: { period?: string; limit?: number }): Promise<TenantUsageTrend[]> => {
    return request.get(`/tenants/${tenantId}/usage/trends`, { params });
  },

  // 数据备份/恢复
  exportTenantBackup: (tenantId: string): Promise<Blob> => {
    return request.post(`/backup/${tenantId}/export`, null, { responseType: 'blob' as any });
  },

  precheckTenantImport: (tenantId: string, file: File): Promise<{ compatible: boolean; warnings: string[]; blockers: string[] }> => {
    const formData = new FormData();
    formData.append('file', file);
    return request.post(`/backup/${tenantId}/import/precheck`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  importTenantBackup: (tenantId: string, file: File, overwrite?: boolean): Promise<{ success: boolean; message: string; details?: Record<string, unknown> }> => {
    const formData = new FormData();
    formData.append('file', file);
    return request.post(`/backup/${tenantId}/import`, formData, {
      params: { overwrite: overwrite || false },
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};
