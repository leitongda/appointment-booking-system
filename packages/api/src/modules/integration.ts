import { request } from '../request';

// 支持的第三方平台
export type IntegrationProvider = 'dingtalk' | 'wecom' | 'feishu';

// 集成配置
export interface IntegrationConfig {
  id: string;
  tenant_id: string;
  provider: IntegrationProvider;
  name: string;
  app_id?: string | null;
  app_secret_ref?: string | null;
  webhook_url?: string | null;
  webhook_secret_ref?: string | null;
  extra_config?: Record<string, unknown> | null;
  status: number; // 0-禁用 1-启用
}

// 创建/更新集成配置的入参
export interface IntegrationUpsertInput {
  provider: IntegrationProvider;
  name: string;
  app_id?: string | null;
  app_secret_ref?: string | null; // env:VAR 形式
  webhook_url?: string | null;
  webhook_secret_ref?: string | null;
  extra_config?: Record<string, unknown> | null;
  status?: number;
}

// 平台信息（列表展示用）
export interface ProviderInfo {
  provider: IntegrationProvider;
  name: string;
  description: string;
  configured: boolean;
  status: number;
}

// 账号绑定关系
export interface IntegrationBinding {
  id: string;
  user_id: string;
  user_type: string;
  provider: IntegrationProvider;
  external_id: string;
  union_id?: string | null;
  name?: string | null;
}

// 连接测试结果
export interface TestConnectionResult {
  success: boolean;
  message: string;
  detail?: Record<string, unknown> | null;
}

const PREFIX = '/integration';

export const integrationApi = {
  // ========== 平台列表 ==========
  listProviders: (): Promise<ProviderInfo[]> => {
    return request.get(`${PREFIX}/providers`);
  },

  // ========== 集成配置 ==========
  list: (): Promise<IntegrationConfig[]> => {
    return request.get(`${PREFIX}`);
  },

  get: (provider: IntegrationProvider): Promise<IntegrationConfig> => {
    return request.get(`${PREFIX}/${provider}`);
  },

  upsert: (data: IntegrationUpsertInput): Promise<IntegrationConfig> => {
    return request.post(`${PREFIX}`, data);
  },

  update: (
    provider: IntegrationProvider,
    data: Partial<IntegrationUpsertInput>,
  ): Promise<IntegrationConfig> => {
    return request.put(`${PREFIX}/${provider}`, data);
  },

  remove: (provider: IntegrationProvider): Promise<void> => {
    return request.delete(`${PREFIX}/${provider}`);
  },

  // ========== 连接测试 ==========
  testConnection: (provider: IntegrationProvider): Promise<TestConnectionResult> => {
    return request.post(`${PREFIX}/test/${provider}`);
  },

  // ========== 账号绑定 ==========
  listBindings: (provider: IntegrationProvider): Promise<IntegrationBinding[]> => {
    return request.get(`${PREFIX}/bindings/${provider}`);
  },

  removeBinding: (provider: IntegrationProvider, bindingId: string): Promise<void> => {
    return request.delete(`${PREFIX}/bindings/${provider}/${bindingId}`);
  },

  // ========== 组织架构同步 ==========
  syncOrganization: (
    provider: IntegrationProvider,
  ): Promise<{ message: string; task_id: string; provider: string }> => {
    return request.post(`${PREFIX}/sync/${provider}`);
  },
};
