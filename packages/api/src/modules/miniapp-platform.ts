import request from '../request';

// ========== Company (公司/结算主体) ==========

export interface Company {
  id: string;
  name: string;
  code?: string;
  unifiedSocialCreditCode?: string;
  contactName?: string;
  contactPhone?: string;
  status: number; // 0-禁用 1-启用
  createdAt: string;
  updatedAt?: string;
}

export interface CompanyCreateData {
  name: string;
  code?: string;
  unifiedSocialCreditCode?: string;
  contactName?: string;
  contactPhone?: string;
}

export interface CompanyUpdateData {
  name?: string;
  code?: string;
  unifiedSocialCreditCode?: string;
  contactName?: string;
  contactPhone?: string;
  status?: number;
}

export interface CompanyListParams {
  keyword?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

// ========== PaymentProfile (支付配置) ==========

export interface PaymentProfile {
  id: string;
  name: string;
  code?: string;
  mode: 'direct' | 'service_provider';
  appId?: string;
  mchId?: string;
  subMchid?: string;
  notifyUrl?: string;
  refundNotifyUrl?: string;
  apiV3KeyRef?: string;
  certSerialNo?: string;
  privateKeyRef?: string;
  companyId?: string;
  isDefault: boolean;
  status: number; // 0-禁用 1-启用
  createdAt: string;
  updatedAt?: string;
  company?: {
    id: string;
    name: string;
  };
}

export interface PaymentProfileCreateData {
  name: string;
  code?: string;
  mode?: 'direct' | 'service_provider';
  appId?: string;
  mchId?: string;
  subMchid?: string;
  notifyUrl?: string;
  refundNotifyUrl?: string;
  apiV3KeyRef?: string;
  certSerialNo?: string;
  privateKeyRef?: string;
  companyId?: string;
}

export interface PaymentProfileUpdateData {
  name?: string;
  code?: string;
  mode?: 'direct' | 'service_provider';
  appId?: string;
  mchId?: string;
  subMchid?: string;
  notifyUrl?: string;
  refundNotifyUrl?: string;
  apiV3KeyRef?: string;
  certSerialNo?: string;
  privateKeyRef?: string;
  companyId?: string;
  isDefault?: boolean;
  status?: number;
}

export interface PaymentProfileListParams {
  keyword?: string;
  status?: number;
  companyId?: string;
  page?: number;
  pageSize?: number;
}

// ========== MiniappInstance (小程序实例) ==========

export interface MiniappInstance {
  id: string;
  code?: string;
  name: string;
  appId: string;
  appSecretRef?: string;
  uploadPrivateKeyRef?: string;
  templateId?: string;
  templateVersionId?: string;
  defaultStoreId?: string;
  defaultPaymentProfileId?: string;
  appConfig?: string;
  status: number; // 0-禁用 1-启用 2-归档
  createdAt: string;
  updatedAt?: string;
  template?: {
    id: string;
    code: string;
    name: string;
  };
  templateVersion?: {
    id: string;
    version: string;
  };
  defaultStore?: {
    id: string;
    name: string;
  };
  defaultPaymentProfile?: {
    id: string;
    name: string;
  };
}

export interface MiniappInstanceCreateData {
  code?: string;
  name: string;
  appId: string;
  appSecretRef?: string;
  uploadPrivateKeyRef?: string;
  templateId?: string;
  templateVersionId?: string;
  defaultStoreId?: string;
  defaultPaymentProfileId?: string;
  appConfig?: string;
}

export interface MiniappInstanceUpdateData {
  code?: string;
  name?: string;
  appId?: string;
  appSecretRef?: string;
  uploadPrivateKeyRef?: string;
  templateId?: string;
  templateVersionId?: string;
  defaultStoreId?: string;
  defaultPaymentProfileId?: string;
  appConfig?: string;
  status?: number;
}

export interface MiniappInstanceListParams {
  keyword?: string;
  status?: number;
  templateId?: string;
  page?: number;
  pageSize?: number;
}

// ========== AppTemplate (小程序模板) ==========

export interface AppTemplate {
  id: string;
  code: string;
  name: string;
  description?: string;
  category: string;
  defaultConfig?: Record<string, any>;
  status: number; // 0-禁用 1-启用
  createdAt: string;
  updatedAt?: string;
}

export interface AppTemplateCreateData {
  name: string;
  code: string;
  description?: string;
  category: string;
  defaultConfig?: Record<string, any>;
}

export interface AppTemplateUpdateData {
  name?: string;
  description?: string;
  defaultConfig?: Record<string, any>;
  status?: number;
}

export interface AppTemplateListParams {
  category?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

// ========== TemplateVersion (模板版本) ==========

export interface TemplateVersion {
  id: string;
  templateId: string;
  version: string;
  sourceRef?: string;
  schemaVersion?: string;
  changelog?: string;
  status: number;
  createdAt: string;
  updatedAt?: string;
}

export interface TemplateVersionCreateData {
  version: string;
  sourceRef?: string;
  schemaVersion?: string;
  changelog?: string;
}

// ========== BuildJob (构建任务) ==========

export interface BuildJob {
  id: string;
  tenantId: string;
  miniappInstanceId: string;
  templateVersionId?: string;
  triggerSource?: string;
  buildParams?: Record<string, any>;
  status: string;
  startedAt?: string;
  finishedAt?: string;
  createdAt: string;
  updatedAt?: string;
  miniappInstance?: {
    id: string;
    name: string;
  };
  templateVersion?: {
    id: string;
    version: string;
  };
}

export interface BuildJobCreateData {
  miniappInstanceId: string;
  templateVersionId?: string;
  triggerSource?: string;
  buildParams?: Record<string, any>;
}

export interface BuildJobListParams {
  instanceId?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

// ========== ReleaseJob (发布任务) ==========

export interface ReleaseJob {
  id: string;
  miniappInstanceId: string;
  artifactId?: string;
  action: 'upload' | 'submit_audit' | 'publish' | 'rollback';
  targetVersion?: string;
  result?: Record<string, any>;
  status: string;
  createdAt: string;
  updatedAt?: string;
  miniappInstance?: {
    id: string;
    name: string;
  };
  artifact?: {
    id: string;
    filePath: string;
    checksum?: string;
  };
}

export interface ReleaseJobCreateData {
  miniappInstanceId: string;
  artifactId?: string;
  action: 'upload' | 'submit_audit' | 'publish' | 'rollback';
  targetVersion?: string;
}

export interface ReleaseJobListParams {
  instanceId?: string;
  action?: string;
  status?: string;
  page?: number;
  pageSize?: number;
}

// ========== API ==========

export const miniappPlatformApi = {
  // ========== Company ==========
  getCompanies: (params: CompanyListParams): Promise<{
    data: Company[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      keyword: params.keyword,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    };
    return request.get('/miniapp-platform/companies', { params: queryParams });
  },

  getCompany: (companyId: string): Promise<Company> => {
    return request.get(`/miniapp-platform/companies/${companyId}`);
  },

  createCompany: (data: CompanyCreateData): Promise<Company> => {
    return request.post('/miniapp-platform/companies', data);
  },

  updateCompany: (companyId: string, data: CompanyUpdateData): Promise<Company> => {
    return request.put(`/miniapp-platform/companies/${companyId}`, data);
  },

  deleteCompany: (companyId: string): Promise<{ message: string }> => {
    return request.delete(`/miniapp-platform/companies/${companyId}`);
  },

  checkCompanyCodeUnique: (code: string, excludeId?: string): Promise<{ exists: boolean }> => {
    return request.get('/miniapp-platform/companies/check-unique', {
      params: { code, exclude_id: excludeId },
    });
  },

  // ========== PaymentProfile ==========
  getPaymentProfiles: (params: PaymentProfileListParams): Promise<{
    data: PaymentProfile[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      keyword: params.keyword,
      status: params.status,
      company_id: params.companyId,
      page: params.page,
      page_size: params.pageSize,
    };
    return request.get('/miniapp-platform/payment-profiles', { params: queryParams });
  },

  getPaymentProfile: (profileId: string): Promise<PaymentProfile> => {
    return request.get(`/miniapp-platform/payment-profiles/${profileId}`);
  },

  createPaymentProfile: (data: PaymentProfileCreateData): Promise<PaymentProfile> => {
    return request.post('/miniapp-platform/payment-profiles', data);
  },

  updatePaymentProfile: (profileId: string, data: PaymentProfileUpdateData): Promise<PaymentProfile> => {
    return request.put(`/miniapp-platform/payment-profiles/${profileId}`, data);
  },

  deletePaymentProfile: (profileId: string): Promise<{ message: string }> => {
    return request.delete(`/miniapp-platform/payment-profiles/${profileId}`);
  },

  setDefaultPaymentProfile: (profileId: string): Promise<{ message: string }> => {
    return request.post(`/miniapp-platform/payment-profiles/${profileId}/set-default`);
  },

  checkPaymentProfileCodeUnique: (code: string, excludeId?: string): Promise<{ exists: boolean }> => {
    return request.get('/miniapp-platform/payment-profiles/check-unique', {
      params: { code, exclude_id: excludeId },
    });
  },

  // ========== MiniappInstance ==========
  getMiniappInstances: (params: MiniappInstanceListParams): Promise<{
    data: MiniappInstance[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      keyword: params.keyword,
      status: params.status,
      template_id: params.templateId,
      page: params.page,
      page_size: params.pageSize,
    };
    return request.get('/miniapp-platform/instances', { params: queryParams });
  },

  getMiniappInstance: (instanceId: string): Promise<MiniappInstance> => {
    return request.get(`/miniapp-platform/instances/${instanceId}`);
  },

  createMiniappInstance: (data: MiniappInstanceCreateData): Promise<MiniappInstance> => {
    return request.post('/miniapp-platform/instances', data);
  },

  updateMiniappInstance: (instanceId: string, data: MiniappInstanceUpdateData): Promise<MiniappInstance> => {
    return request.put(`/miniapp-platform/instances/${instanceId}`, data);
  },

  deleteMiniappInstance: (instanceId: string): Promise<{ message: string }> => {
    return request.delete(`/miniapp-platform/instances/${instanceId}`);
  },

  activateMiniappInstance: (instanceId: string): Promise<{ message: string }> => {
    return request.post(`/miniapp-platform/instances/${instanceId}/activate`);
  },

  archiveMiniappInstance: (instanceId: string): Promise<{ message: string }> => {
    return request.post(`/miniapp-platform/instances/${instanceId}/archive`);
  },

  checkInstanceUnique: (
    code?: string,
    appId?: string,
    excludeId?: string
  ): Promise<{ code_exists?: boolean; app_id_exists?: boolean }> => {
    return request.get('/miniapp-platform/instances/check-unique', {
      params: { code, app_id: appId, exclude_id: excludeId },
    });
  },

  // ========== AppTemplate ==========
  getTemplates: (params?: AppTemplateListParams): Promise<{
    data: AppTemplate[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      category: params?.category,
      status: params?.status,
      page: params?.page,
      page_size: params?.pageSize,
    };
    return request.get('/miniapp-platform/templates', { params: queryParams });
  },

  getTemplate: (templateId: string): Promise<AppTemplate> => {
    return request.get(`/miniapp-platform/templates/${templateId}`);
  },

  createTemplate: (data: AppTemplateCreateData): Promise<AppTemplate> => {
    return request.post('/miniapp-platform/templates', data);
  },

  updateTemplate: (templateId: string, data: AppTemplateUpdateData): Promise<AppTemplate> => {
    return request.put(`/miniapp-platform/templates/${templateId}`, data);
  },

  getTemplateVersions: (templateId: string, params?: { page?: number; pageSize?: number }): Promise<{
    data: TemplateVersion[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      page: params?.page,
      page_size: params?.pageSize,
    };
    return request.get(`/miniapp-platform/templates/${templateId}/versions`, { params: queryParams });
  },

  createTemplateVersion: (templateId: string, data: TemplateVersionCreateData): Promise<TemplateVersion> => {
    return request.post(`/miniapp-platform/templates/${templateId}/versions`, data);
  },

  // ========== BuildJob ==========
  getBuildJobs: (params: BuildJobListParams): Promise<{
    data: BuildJob[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      instance_id: params.instanceId,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    };
    return request.get('/miniapp-platform/build-jobs', { params: queryParams });
  },

  getBuildJob: (jobId: string): Promise<BuildJob> => {
    return request.get(`/miniapp-platform/build-jobs/${jobId}`);
  },

  createBuildJob: (data: BuildJobCreateData): Promise<BuildJob> => {
    return request.post('/miniapp-platform/build-jobs', data);
  },

  // ========== ReleaseJob ==========
  getReleaseJobs: (params: ReleaseJobListParams): Promise<{
    data: ReleaseJob[];
    total: number;
    page: number;
    pageSize: number;
    message?: string;
  }> => {
    const queryParams = {
      instance_id: params.instanceId,
      action: params.action,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    };
    return request.get('/miniapp-platform/release-jobs', { params: queryParams });
  },

  getReleaseJob: (jobId: string): Promise<ReleaseJob> => {
    return request.get(`/miniapp-platform/release-jobs/${jobId}`);
  },

  createReleaseJob: (data: ReleaseJobCreateData): Promise<ReleaseJob> => {
    return request.post('/miniapp-platform/release-jobs', data);
  },
};
