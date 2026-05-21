import { request } from '../request';
import type { PageResult } from '@hospital/shared';

// 积分流水项
export interface PointLogItem {
  id: string;
  userId?: string;
  userName?: string;
  userPhone?: string;
  changeAmount: number;
  balance: number;
  type: number; // 1消费 2充值 3赠送 4手动调整
  remark?: string;
  operatorId?: string;
  operatorName?: string;
  createdAt?: string;
}

// 用户积分排行项
export interface PointUserItem {
  id: string;
  nickname?: string;
  phone?: string;
  points: number;
  status: number;
  createdAt?: string;
}

// 积分调整参数
export interface PointAdjustData {
  amount: number;
  remark: string;
}

// 积分流水查询参数
export interface PointLogParams {
  keyword?: string;
  logType?: number;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

// 用户排行查询参数
export interface PointUserParams {
  keyword?: string;
  sortBy?: string;
  sortOrder?: string;
  page?: number;
  pageSize?: number;
}

const PREFIX = '/points';

export const pointApi = {
  /** 获取全局积分流水 */
  getLogs: (params?: PointLogParams): Promise<PageResult<PointLogItem>> => {
    return request.get(`${PREFIX}/logs`, { params });
  },

  /** 获取用户积分排行 */
  getUsers: (params?: PointUserParams): Promise<PageResult<PointUserItem>> => {
    return request.get(`${PREFIX}/users`, { params });
  },

  /** 调整用户积分 */
  adjust: (userId: string, data: PointAdjustData): Promise<{ data: PointLogItem }> => {
    return request.post(`${PREFIX}/${userId}/adjust`, data);
  },
};
