import request from '../request';
import type { Schedule, PageResult } from '@hospital/shared';

export interface ScheduleListParams {
  doctorId?: string;
  startDate?: string;
  endDate?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface ScheduleCreateData {
  doctorId: string;
  scheduleDate: string;
  timeSlot: string;
  startTime?: string;
  endTime?: string;
  totalSlots: number;
  status?: number;
}

export interface ScheduleBatchCreateData {
  doctorId: string;
  startDate: string;
  endDate: string;
  timeSlots: string[];
  totalSlots: number;
  weekdays: number[];
}

export interface AvailableSchedule {
  id: string;
  scheduleDate: string;
  timeSlot: string;
  availableSlots: number;
  startTime?: string;
  endTime?: string;
}

export interface ScheduleStatisticsItem {
  scheduleDate: string;
  doctorId: string;
  doctorName: string;
  morningSlots: number;
  afternoonSlots: number;
  morningBooked: number;
  afternoonBooked: number;
}

export interface ScheduleStatisticsResponse {
  storeId: string;
  storeName: string;
  year: number;
  month: number;
  items: ScheduleStatisticsItem[];
}

export interface ScheduleStatisticsParams {
  storeId: string;
  year: number;
  month: number;
}

export const scheduleApi = {
  getList: (params?: ScheduleListParams): Promise<PageResult<Schedule>> => {
    return request.get('/schedules', { params });
  },

  getAvailable: (doctorId: string, days?: number): Promise<AvailableSchedule[]> => {
    return request.get(`/schedules/available/${doctorId}`, { params: { days } });
  },

  getDetail: (id: string): Promise<Schedule> => {
    return request.get(`/schedules/${id}`);
  },

  create: (data: ScheduleCreateData): Promise<Schedule> => {
    return request.post('/schedules', data);
  },

  batchCreate: (data: ScheduleBatchCreateData): Promise<{ message: string }> => {
    return request.post('/schedules/batch', data);
  },

  update: (id: string, data: Partial<ScheduleCreateData>): Promise<Schedule> => {
    return request.put(`/schedules/${id}`, data);
  },

  /**
   * 停诊
   */
  suspend: (id: string, reason?: string, notifyPatients: boolean = true): Promise<{
    message: string;
    notification?: {
      notifiedCount: number;
      failedCount: number;
      message: string;
    };
  }> => {
    return request.put(`/schedules/${id}/suspend`, { reason, notify_patients: notifyPatients });
  },

  /**
   * 恢复排班
   */
  resume: (id: string): Promise<{ message: string }> => {
    return request.put(`/schedules/${id}/resume`);
  },

  /**
   * 获取排班统计
   */
  getStatistics: (params: ScheduleStatisticsParams): Promise<ScheduleStatisticsResponse> => {
    return request.get('/schedules/statistics', { params });
  },
};
