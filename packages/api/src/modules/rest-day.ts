import request from '../request';
import type { PageResult } from '@hospital/shared';

export interface RestDayCreateData {
  storeId: string;
  doctorIds?: string[];
  reason?: string;
  startDate: string;
  endDate: string;
}

export interface RestDay {
  id: string;
  storeId: string;
  storeName?: string;
  doctorIds?: string[];
  doctorNames?: string[];
  reason?: string;
  startDate: string;
  endDate: string;
  status: number;
  createdAt: string;
}

export interface RestDayListParams {
  storeId?: string;
  doctorId?: string;
  startDate?: string;
  endDate?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export const restDayApi = {
  /**
   * 获取休息日列表
   */
  getList: (params?: RestDayListParams): Promise<PageResult<RestDay>> => {
    return request.get('/rest-days', { params });
  },

  /**
   * 添加休息日
   */
  create: (data: RestDayCreateData): Promise<RestDay> => {
    return request.post('/rest-days', data);
  },

  /**
   * 删除休息日
   */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`/rest-days/${id}`);
  },

  /**
   * 取消休息日
   */
  cancel: (id: string): Promise<{ message: string }> => {
    return request.put(`/rest-days/${id}/cancel`);
  },
};
