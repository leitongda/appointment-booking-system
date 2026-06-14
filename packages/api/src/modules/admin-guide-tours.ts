import { request } from '../request';
import type { TourStep } from './guide-tours';

// ==================== 类型定义 ====================

/** 管理端：指引详情 */
export interface GuideTourDetail {
  id: string;
  code: string;
  title: Record<string, string>;
  description?: Record<string, string>;
  steps: TourStep[];
  status: number;
  sortOrder: number;
  tenantId?: string;
  createdAt?: string;
  updatedAt?: string;
}

/** 管理端：指引列表项 */
export interface GuideTourListItem {
  id: string;
  code: string;
  title: Record<string, string>;
  status: number;
  sortOrder: number;
  stepCount: number;
  createdAt?: string;
}

/** 管理端：创建/更新请求 */
export interface GuideTourFormData {
  code: string;
  title: Record<string, string>;
  description?: Record<string, string>;
  steps: TourStep[];
  sortOrder?: number;
  tenantId?: string;
}

// ==================== API ====================

const PREFIX = '/admin/guide-tours';

export const adminGuideToursApi = {
  /** 分页获取指引列表 */
  getList: (params?: { page?: number; pageSize?: number; status?: number }): Promise<{ data: GuideTourListItem[]; total: number }> => {
    return request.get(PREFIX, { params });
  },

  /** 获取指引详情 */
  getById: (id: string): Promise<GuideTourDetail> => {
    return request.get(`${PREFIX}/${id}`);
  },

  /** 创建指引 */
  create: (data: GuideTourFormData): Promise<{ id: string }> => {
    return request.post(PREFIX, data);
  },

  /** 更新指引 */
  update: (id: string, data: Partial<GuideTourFormData>): Promise<{ id: string }> => {
    return request.put(`${PREFIX}/${id}`, data);
  },

  /** 更新发布状态 */
  updateStatus: (id: string, status: number): Promise<{ id: string; status: number }> => {
    return request.patch(`${PREFIX}/${id}/status`, { status });
  },

  /** 删除指引 */
  delete: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/${id}`);
  },
};
