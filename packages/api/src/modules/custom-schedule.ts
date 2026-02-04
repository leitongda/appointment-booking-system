import request from '../request';
import type { PageResult } from '@hospital/shared';

export interface TimePeriod {
  startTime: string;
  endTime: string;
  appointmentType: string;
  slotCount?: number;
  maxPatients: number;
}

export interface CustomScheduleCreateData {
  storeId: string;
  departmentId: string;
  doctorId: string;
  scheduleDates: string[];
  timePeriods: TimePeriod[];
}

export interface CustomSchedule {
  id: string;
  storeId: string;
  storeName?: string;
  departmentId: string;
  departmentName?: string;
  doctorId: string;
  doctorName?: string;
  scheduleDate: string;
  startTime: string;
  endTime: string;
  appointmentType: string;
  maxPatients: number;
  bookedCount: number;
  status: number;
  createdAt: string;
  isRestDay?: boolean;  // 是否在休息日（后端计算）
}

export interface CustomScheduleListParams {
  storeId?: string;
  departmentId?: string;
  doctorId?: string;
  startDate?: string;
  endDate?: string;
  appointmentType?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface EffectiveScheduleParams {
  storeId?: string;
  doctorId?: string;
  startDate: string;
  endDate: string;
}

export const customScheduleApi = {
  /**
   * 获取自定义排班列表
   */
  getList: (params?: CustomScheduleListParams): Promise<PageResult<CustomSchedule>> => {
    return request.get('/custom-schedules', { params });
  },

  /**
   * 获取生效的自定义排班
   */
  getEffective: (params: EffectiveScheduleParams): Promise<CustomSchedule[]> => {
    return request.get('/custom-schedules/effective', { params });
  },

  /**
   * 创建自定义排班（支持批量）
   */
  create: (data: CustomScheduleCreateData): Promise<CustomSchedule[]> => {
    return request.post('/custom-schedules', data);
  },

  /**
   * 删除自定义排班
   */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`/custom-schedules/${id}`);
  },
};
