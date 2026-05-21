import request from '../request';
import type { PageResult } from '@hospital/shared';

// ========== 平台公告 ==========

export interface PlatformAnnouncement {
  id: string;
  title: string;
  content: string;
  targetType: 'all' | 'specific';
  targetTenantIds?: string[];
  status: 'draft' | 'published' | 'revoked';
  priority: number; // 0=普通, 1=重要, 2=紧急
  publishAt?: string;
  expireAt?: string;
  publisherId?: string;
  publisherName?: string;
  readCount: number;
  totalCount: number;
  createdAt: string;
  updatedAt: string;
}

export interface PlatformAnnouncementCreateData {
  title: string;
  content: string;
  targetType?: 'all' | 'specific';
  targetTenantIds?: string[];
  priority?: number;
  publishAt?: string;
  expireAt?: string;
}

export interface PlatformAnnouncementListParams {
  status?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export const platformAnnouncementApi = {
  /** 获取公告列表 */
  getList: (params?: PlatformAnnouncementListParams): Promise<PageResult<PlatformAnnouncement>> => {
    return request.get('/platform-announcements', { params });
  },

  /** 获取公告详情 */
  getDetail: (id: string): Promise<PlatformAnnouncement> => {
    return request.get(`/platform-announcements/${id}`);
  },

  /** 创建公告（草稿） */
  create: (data: PlatformAnnouncementCreateData): Promise<PlatformAnnouncement> => {
    return request.post('/platform-announcements', data);
  },

  /** 更新公告（仅草稿状态） */
  update: (id: string, data: Partial<PlatformAnnouncementCreateData>): Promise<void> => {
    return request.put(`/platform-announcements/${id}`, data);
  },

  /** 删除公告 */
  delete: (id: string): Promise<void> => {
    return request.delete(`/platform-announcements/${id}`);
  },

  /** 发布公告 */
  publish: (id: string): Promise<void> => {
    return request.post(`/platform-announcements/${id}/publish`);
  },

  /** 撤回公告 */
  revoke: (id: string): Promise<void> => {
    return request.post(`/platform-announcements/${id}/revoke`);
  },
};
