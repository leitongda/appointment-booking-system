/** 低代码搭建 API 模块 */

import request from '../request';
import type {
  LowCodePage,
  LowCodePageCreateData,
  LowCodePageUpdateData,
  LowCodeTemplate,
  LowCodeTemplateCreateData,
  LowCodeTemplateUpdateData,
  LowCodeTemplateListParams,
  LowCodeTemplateVersionListResponse,
  LowCodeTemplateCategoryItem,
  LowCodeTemplateForkResponse,
} from '@hospital/shared';

export interface LowCodePageListParams {
  status?: number;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

// --- Version History ---

export interface VersionItem {
  id: string;
  version: number;
  snapshotLabel?: string;
  createdAt?: string;
  createdBy?: string;
}

export interface VersionListResponse {
  currentVersion: number;
  versions: VersionItem[];
}

export const lowcodeApi = {
  /** 获取页面列表 */
  getPages: (params?: LowCodePageListParams): Promise<{ data: LowCodePage[]; total: number; page: number; pageSize: number }> => {
    return request.get('/lowcode/pages', { params });
  },

  /** 创建页面 */
  createPage: (data: LowCodePageCreateData): Promise<LowCodePage> => {
    return request.post('/lowcode/pages', data);
  },

  /** 获取页面详情 */
  getPage: (id: string): Promise<LowCodePage> => {
    return request.get(`/lowcode/pages/${id}`);
  },

  /** 更新页面 */
  updatePage: (id: string, data: LowCodePageUpdateData): Promise<LowCodePage> => {
    return request.put(`/lowcode/pages/${id}`, data);
  },

  /** 删除页面 */
  deletePage: (id: string): Promise<void> => {
    return request.delete(`/lowcode/pages/${id}`);
  },

  /** 发布页面 */
  publishPage: (id: string): Promise<LowCodePage> => {
    return request.post(`/lowcode/pages/${id}/publish`);
  },

  /** 归档页面 */
  archivePage: (id: string): Promise<LowCodePage> => {
    return request.post(`/lowcode/pages/${id}/archive`);
  },

  /** 测试数据源 */
  testDataSource: (data: DataSourceTestRequest): Promise<DataSourceTestResponse> => {
    return request.post('/lowcode/data-sources/test', data);
  },

  /** 获取页面版本历史 */
  getVersions: (pageId: string): Promise<VersionListResponse> => {
    return request.get(`/lowcode/pages/${pageId}/versions`);
  },

  /** 回滚到指定版本 */
  rollbackVersion: (pageId: string, versionId: string): Promise<LowCodePage> => {
    return request.post(`/lowcode/pages/${pageId}/versions/rollback`, { versionId });
  },

  // --- Template Marketplace ---

  /** 获取模板市场列表 */
  getTemplates: (params?: LowCodeTemplateListParams): Promise<{ data: LowCodeTemplate[]; total: number; page: number; pageSize: number }> => {
    return request.get('/lowcode/templates', { params });
  },

  /** 获取模板详情 */
  getTemplate: (templateId: string): Promise<LowCodeTemplate> => {
    return request.get(`/lowcode/templates/${templateId}`);
  },

  /** 创建模板 */
  createTemplate: (data: LowCodeTemplateCreateData): Promise<LowCodeTemplate> => {
    return request.post('/lowcode/templates', data);
  },

  /** 更新模板元数据 */
  updateTemplate: (templateId: string, data: LowCodeTemplateUpdateData): Promise<LowCodeTemplate> => {
    return request.put(`/lowcode/templates/${templateId}`, data);
  },

  /** 删除模板 */
  deleteTemplate: (templateId: string): Promise<void> => {
    return request.delete(`/lowcode/templates/${templateId}`);
  },

  /** Fork 模板到当前租户 */
  forkTemplate: (
    templateId: string,
    data?: { name?: string; slug?: string },
  ): Promise<LowCodeTemplateForkResponse> => {
    return request.post(`/lowcode/templates/${templateId}/fork`, data);
  },

  /** 获取模板版本历史 */
  getTemplateVersions: (templateId: string): Promise<LowCodeTemplateVersionListResponse> => {
    return request.get(`/lowcode/templates/${templateId}/versions`);
  },

  /** 获取模板分类列表 */
  getTemplateCategories: (): Promise<LowCodeTemplateCategoryItem[]> => {
    return request.get('/lowcode/templates/categories');
  },

  /** 获取我发布的模板 */
  getMyTemplates: (params?: { page?: number; pageSize?: number }): Promise<{ data: LowCodeTemplate[]; total: number; page: number; pageSize: number }> => {
    return request.get('/lowcode/templates/my', { params });
  },

  // --- Deploy ---

  /** 触发页面部署流水线 */
  triggerDeploy: (pageId: string): Promise<DeployTriggerResponse> => {
    return request.post(`/lowcode/pages/${pageId}/deploy`);
  },

  /** 获取页面部署状态 */
  getDeployStatus: (pageId: string): Promise<DeployStatusResponse> => {
    return request.get(`/lowcode/pages/${pageId}/deploy/status`);
  },

  /** 生成预览二维码 */
  generatePreviewQr: (pageId: string): Promise<PreviewQrResponse> => {
    return request.post(`/lowcode/pages/${pageId}/deploy/preview`);
  },

  /** 回滚部署到上一个版本 */
  rollbackDeploy: (pageId: string, targetVersion?: string): Promise<RollbackDeployResponse> => {
    return request.post(`/lowcode/pages/${pageId}/deploy/rollback`, { target_version: targetVersion });
  },

  /** 获取部署历史记录 */
  getDeployHistory: (pageId: string): Promise<{ data: DeployHistoryItem[] }> => {
    return request.get(`/lowcode/pages/${pageId}/deploy/history`);
  },
};

// --- Deploy ---

export type DeployStatus =
  | 'idle'
  | 'building'
  | 'built'
  | 'uploading'
  | 'uploaded'
  | 'auditing'
  | 'published'
  | 'failed';

export interface DeployStatusResponse {
  page_id: string;
  deploy_status: DeployStatus;
  last_deploy_at: string | null;
  miniapp_instance_id: string | null;
  build_job: {
    id: string;
    status: string;
    build_log: string | null;
    artifact_url: string | null;
    started_at: string | null;
    finished_at: string | null;
  } | null;
}

export interface DeployTriggerResponse {
  build_job_id: string;
  audit_id: string;
  deploy_status: DeployStatus;
  artifact_url: string;
}

export interface PreviewQrResponse {
  page_id: string;
  qr_code_url: string;
  expires_at: string | null;
  message: string;
}

export interface RollbackDeployResponse {
  page_id: string;
  rollback_to_version: string;
  deploy_status: DeployStatus;
  release_job_id: string;
}

export interface DeployHistoryItem {
  id: string;
  status: string;
  artifact_url: string | null;
  build_log: string | null;
  trigger_source: string | null;
  started_at: string | null;
  finished_at: string | null;
  created_at: string | null;
}

// --- DataSource 测试类型 ---

export interface DataSourceTestRequest {
  url: string;
  method?: string;
  headers?: Record<string, string>;
  params?: Record<string, any>;
  body?: Record<string, any>;
  responsePath?: string;
}

export interface DataSourceFieldSuggestion {
  path: string;
  type: string;
  sample?: any;
}

export interface DataSourceTestResponse {
  success: boolean;
  statusCode?: number;
  sampleData?: any;
  fields?: DataSourceFieldSuggestion[];
  error?: string;
  elapsedMs: number;
}
