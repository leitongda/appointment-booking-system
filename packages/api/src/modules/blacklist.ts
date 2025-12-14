import { request } from '../request';
import type { PageResult } from '@hospital/shared';

// 黑名单项
export interface BlacklistItem {
  id: string;
  userId?: string;
  userName?: string;
  userPhone?: string;
  storeId?: string;
  storeName?: string;
  keyword?: string;
  reason?: string;
  noShowCount: number;
  source: number; // 1手动 2自动
  expireAt?: string;
  releasedAt?: string;
  status: number; // 1生效 0已解禁
  createdAt: string;
}

// 黑名单列表查询参数
export interface BlacklistListParams {
  keyword?: string;
  storeId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

// 添加黑名单参数
export interface BlacklistCreateData {
  userId?: string;
  storeId?: string;
  keyword?: string;
  reason?: string;
  expireAt?: string;
}

// 黑名单检查结果
export interface BlacklistCheckResult {
  isBlacklisted: boolean;
  reason?: string;
  expireAt?: string;
}

const PREFIX = '/blacklists';

export const blacklistApi = {
  /**
   * 获取黑名单列表
   */
  getList: (params?: BlacklistListParams): Promise<PageResult<BlacklistItem>> => {
    return request.get(PREFIX, { params });
  },

  /**
   * 添加黑名单
   */
  add: (data: BlacklistCreateData): Promise<{ data: BlacklistItem }> => {
    return request.post(PREFIX, data);
  },

  /**
   * 移除黑名单（解禁）
   */
  remove: (id: string): Promise<void> => {
    return request.delete(`${PREFIX}/${id}`);
  },

  /**
   * 检查是否在黑名单中
   */
  check: (params: {
    userId?: string;
    phone?: string;
    idCard?: string;
    storeId?: string;
  }): Promise<BlacklistCheckResult> => {
    return request.post(`${PREFIX}/check`, null, { params });
  },
};
