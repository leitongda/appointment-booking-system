import request from '../request';
import type { PageResult } from '@hospital/shared';

export interface ScheduleSuspensionCreateData {
  storeId: string;
  doctorId: string;
  title: string;
  suspensionDate: string;
  scheduleIds?: string[];
  timeSlots?: string[];
}

export interface ScheduleSuspension {
  id: string;
  storeId: string;
  storeName?: string;
  doctorId: string;
  doctorName?: string;
  title: string;
  suspensionDate: string;
  scheduleIds?: string[];
  timeSlots?: string[];
  status: number;
  createdAt: string;
}

export interface ScheduleSuspensionListParams {
  storeId?: string;
  doctorId?: string;
  startDate?: string;
  endDate?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface AvailableScheduleForSuspension {
  scheduleId: string;
  timeSlot: string;
  scheduleType: string;
  bookedCount: number;
  maxPatients: number;
}

export const scheduleSuspensionApi = {
  /**
   * 获取停诊列表
   */
  getList: (params?: ScheduleSuspensionListParams): Promise<PageResult<ScheduleSuspension>> => {
    return request.get('/schedule-suspensions', { params });
  },

  /**
   * 获取指定日期的可选排班（用于停诊选择）
   */
  getAvailableSchedules: (
    storeId: string,
    doctorId: string,
    suspensionDate: string
  ): Promise<AvailableScheduleForSuspension[]> => {
    return request.get('/schedule-suspensions/schedules', {
      params: { storeId, doctorId, suspensionDate },
    });
  },

  /**
   * 创建停诊
   */
  create: (data: ScheduleSuspensionCreateData): Promise<ScheduleSuspension> => {
    return request.post('/schedule-suspensions', data);
  },

  /**
   * 删除停诊记录
   */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`/schedule-suspensions/${id}`);
  },

  /**
   * 取消停诊
   */
  cancel: (id: string): Promise<{ message: string }> => {
    return request.put(`/schedule-suspensions/${id}/cancel`);
  },
};
