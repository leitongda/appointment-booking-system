/**
 * 低代码模板市场 API 模块
 *
 * 独立于 lowcode.ts 中的页面管理 API，
 * 专注于模板的 CRUD、Fork、版本管理、分类等。
 */

import request from '../request';
import type {
  LowCodeTemplate,
  LowCodeTemplateCreateData,
  LowCodeTemplateUpdateData,
  LowCodeTemplateListParams,
  LowCodeTemplateVersionListResponse,
  LowCodeTemplateCategoryItem,
  LowCodeTemplateForkResponse,
} from '@hospital/shared';

// --- 模板版本创建数据 ---

export interface TemplateVersionCreateData {
  /** 版本快照标签 */
  snapshotLabel?: string;
  /** 版本描述 */
  description?: string;
  /** 模板页面数据快照 */
  snapshot?: Record<string, unknown>;
}

// --- Template Marketplace API ---

export const lowcodeTemplateApi = {
  /** 获取模板市场列表 */
  getTemplates: (
    params?: LowCodeTemplateListParams,
  ): Promise<{ data: LowCodeTemplate[]; total: number; page: number; pageSize: number }> => {
    return request.get('/lowcode/templates', { params });
  },

  /** 获取模板详情 */
  getTemplate: (id: string): Promise<LowCodeTemplate> => {
    return request.get(`/lowcode/templates/${id}`);
  },

  /** 创建模板 */
  createTemplate: (data: LowCodeTemplateCreateData): Promise<LowCodeTemplate> => {
    return request.post('/lowcode/templates', data);
  },

  /** 更新模板元数据 */
  updateTemplate: (id: string, data: LowCodeTemplateUpdateData): Promise<LowCodeTemplate> => {
    return request.put(`/lowcode/templates/${id}`, data);
  },

  /** 删除模板 */
  deleteTemplate: (id: string): Promise<void> => {
    return request.delete(`/lowcode/templates/${id}`);
  },

  /** Fork 模板到当前租户 */
  forkTemplate: (
    id: string,
    data?: { name?: string; slug?: string },
  ): Promise<LowCodeTemplateForkResponse> => {
    return request.post(`/lowcode/templates/${id}/fork`, data);
  },

  /** 获取模板版本历史 */
  getTemplateVersions: (id: string): Promise<LowCodeTemplateVersionListResponse> => {
    return request.get(`/lowcode/templates/${id}/versions`);
  },

  /** 创建模板新版本 */
  createVersion: (
    id: string,
    data?: TemplateVersionCreateData,
  ): Promise<LowCodeTemplateVersionListResponse> => {
    return request.post(`/lowcode/templates/${id}/versions`, data);
  },

  /** 获取我发布的模板 */
  getMyTemplates: (
    params?: { page?: number; pageSize?: number },
  ): Promise<{ data: LowCodeTemplate[]; total: number; page: number; pageSize: number }> => {
    return request.get('/lowcode/templates/my', { params });
  },

  /** 获取模板分类列表 */
  getTemplateCategories: (): Promise<LowCodeTemplateCategoryItem[]> => {
    return request.get('/lowcode/templates/categories');
  },
};
