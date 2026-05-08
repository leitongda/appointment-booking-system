import request from '../request';
import type { Schedule, PageResult } from '@hospital/shared';
import { formatTimeValue } from '../utils/formatTime';

export interface ScheduleListParams {
  doctorId?: string;
  storeId?: string;
  startDate?: string;
  endDate?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface ScheduleCreateData {
  doctorId: string;
  scheduleDate: string;
  timeSlot?: string;  // 可为空，可通过startTime自动计算
  startTime?: string;
  endTime?: string;
  totalSlots: number;
  appointmentType?: string;
  templateId?: string;
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
  appointmentType?: string;
  // 新增字段：规则引擎相关
  totalSlots?: number;
  bookingOpenAt?: string | null;
  bookingCloseAt?: string | null;
  bookingStatus?: 'available' | 'closing_soon' | 'full' | 'closed' | 'not_open';
  capacityPercent?: number;
  urgencyLevel?: 'normal' | 'medium' | 'high' | 'critical';
}

export interface ScheduleStatisticsItem {
  scheduleDate: string;
  doctorId: string;
  doctorName: string;
  morningSlots: number;
  afternoonSlots: number;
  eveningSlots: number;
  morningBooked: number;
  afternoonBooked: number;
  eveningBooked: number;
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

export interface UtilizationTrendItem {
  period: string;
  totalSlots: number;
  bookedSlots: number;
  utilizationRate: number;
}

export interface UtilizationTrendResponse {
  storeId: string;
  storeName: string;
  granularity: string;
  items: UtilizationTrendItem[];
}

export interface DoctorWorkloadItem {
  doctorId: string;
  doctorName: string;
  departmentName?: string;
  totalSlots: number;
  bookedSlots: number;
  completedAppointments: number;
  utilizationRate: number;
  scheduleDays: number;
}

export interface DoctorWorkloadResponse {
  storeId: string;
  storeName: string;
  startDate: string;
  endDate: string;
  items: DoctorWorkloadItem[];
}

export interface PeakHourCell {
  dayOfWeek: number;
  hour: number;
  totalSlots: number;
  bookedSlots: number;
  bookingRate: number;
}

export interface PeakHourHeatmapResponse {
  storeId: string;
  storeName: string;
  startDate: string;
  endDate: string;
  cells: PeakHourCell[];
}

export const scheduleApi = {
  /**
   * 获取医生端排班列表（doctor-portal 端点，自动限制为当前医生）
   */
  getMyList: (params?: { startDate?: string; endDate?: string; status?: number }): Promise<Schedule[]> => {
    return request.get('/doctor-portal/schedules', { params: {
      start_date: params?.startDate,
      end_date: params?.endDate,
      status: params?.status,
    }});
  },

  getList: (params?: ScheduleListParams): Promise<PageResult<Schedule>> => {
    // 转换 camelCase 到 snake_case
    // 确保 pageSize 不超过后端限制（500）
    const safePageSize = params?.pageSize && params.pageSize > 500 ? 500 : params?.pageSize;
    
    const queryParams = params ? {
      doctor_id: params.doctorId,
      store_id: params.storeId,
      start_date: params.startDate,
      end_date: params.endDate,
      status: params.status,
      page: params.page,
      page_size: safePageSize,
    } : undefined;
    return request.get('/schedules', { params: queryParams });
  },

  getAvailable: (doctorId: string, days?: number): Promise<AvailableSchedule[]> => {
    return request.get(`/schedules/available/${doctorId}`, { params: { days } });
  },

  getDetail: (id: string): Promise<Schedule> => {
    return request.get(`/schedules/${id}`);
  },

  create: (data: ScheduleCreateData): Promise<Schedule> => {
    // 转换 camelCase 到 snake_case
    const requestData: any = {
      doctor_id: data.doctorId,
      schedule_date: data.scheduleDate,
      total_slots: data.totalSlots,
    };
    
    // 可选字段
    if (data.timeSlot) requestData.time_slot = data.timeSlot;
    
    // 验证并格式化时间字段
    const formattedStartTime = formatTimeValue(data.startTime);
    if (formattedStartTime) {
      requestData.start_time = formattedStartTime;
    }
    
    const formattedEndTime = formatTimeValue(data.endTime);
    if (formattedEndTime) {
      requestData.end_time = formattedEndTime;
    }
    
    if (data.appointmentType) requestData.appointment_type = data.appointmentType;
    if (data.templateId) requestData.template_id = data.templateId;
    if (data.status !== undefined) requestData.status = data.status;
    
    return request.post('/schedules', requestData);
  },

  batchCreate: (data: ScheduleBatchCreateData): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/batch', data);
  },

  update: (id: string, data: Partial<ScheduleCreateData>): Promise<Schedule> => {
    // 转换 camelCase 到 snake_case，并验证时间格式
    const requestData: any = {};
    
    if (data.doctorId !== undefined) requestData.doctor_id = data.doctorId;
    if (data.scheduleDate !== undefined) requestData.schedule_date = data.scheduleDate;
    if (data.totalSlots !== undefined) requestData.total_slots = data.totalSlots;
    if (data.timeSlot !== undefined) requestData.time_slot = data.timeSlot;
    
    // 验证并格式化时间字段
    if (data.startTime !== undefined) {
      const formattedStartTime = formatTimeValue(data.startTime);
      if (formattedStartTime) {
        requestData.start_time = formattedStartTime;
      }
    }
    
    if (data.endTime !== undefined) {
      const formattedEndTime = formatTimeValue(data.endTime);
      if (formattedEndTime) {
        requestData.end_time = formattedEndTime;
      }
    }
    
    if (data.appointmentType !== undefined) requestData.appointment_type = data.appointmentType;
    if (data.templateId !== undefined) requestData.template_id = data.templateId;
    if (data.status !== undefined) requestData.status = data.status;
    
    return request.put(`/schedules/${id}`, requestData);
  },

  /**
   * 停诊（直接使用排班数据创建停诊记录）
   */
  suspendSchedule: async (schedule: { id: string; storeId?: string; doctorId: string; scheduleDate: string }, reason?: string): Promise<{ message: string }> => {
    if (!schedule.storeId) {
      throw new Error('排班缺少门店信息，无法停诊');
    }

    const { scheduleSuspensionApi } = await import('./schedule-suspension');
    await scheduleSuspensionApi.create({
      storeId: schedule.storeId,
      doctorId: schedule.doctorId,
      title: reason || '管理员停诊',
      suspensionDate: schedule.scheduleDate,
      scheduleIds: [schedule.id],
    });

    return { message: '停诊成功' };
  },

  /**
   * 恢复排班（查找对应停诊记录并取消）
   */
  resumeSchedule: async (schedule: { id: string; doctorId: string; scheduleDate: string }): Promise<{ message: string }> => {
    const { scheduleSuspensionApi } = await import('./schedule-suspension');
    const suspensions = await scheduleSuspensionApi.getList({
      doctorId: schedule.doctorId,
      startDate: schedule.scheduleDate,
      endDate: schedule.scheduleDate,
      status: 1,
      pageSize: 100,
    });

    const suspension = suspensions.data?.find(s => {
      if (s.scheduleIds && s.scheduleIds.length > 0) {
        return s.scheduleIds.includes(schedule.id);
      }
      return s.suspensionDate === schedule.scheduleDate;
    });

    if (suspension) {
      await scheduleSuspensionApi.cancel(suspension.id);
    }

    return { message: '恢复成功' };
  },

  /**
   * 获取排班统计
   */
  getStatistics: (params: ScheduleStatisticsParams): Promise<ScheduleStatisticsResponse> => {
    return request.get('/schedules/statistics', { params });
  },

  /**
   * 批量停诊
   */
  batchSuspend: (scheduleIds: string[], reason?: string): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/batch-suspend', {
      schedule_ids: scheduleIds,
      reason,
    });
  },

  /**
   * 批量恢复
   */
  batchResume: (scheduleIds: string[]): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/batch-resume', {
      schedule_ids: scheduleIds,
    });
  },

  /**
   * 批量删除
   */
  batchDelete: (scheduleIds: string[]): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/batch-delete', {
      schedule_ids: scheduleIds,
    });
  },

  /**
   * 排班利用率趋势
   */
  getUtilizationTrend: (params: {
    storeId: string;
    startDate: string;
    endDate: string;
    granularity?: string;
  }): Promise<UtilizationTrendResponse> => {
    return request.get('/schedules/statistics/utilization-trend', { params });
  },

  /**
   * 医生工作量对比
   */
  getDoctorWorkload: (params: {
    storeId: string;
    startDate: string;
    endDate: string;
  }): Promise<DoctorWorkloadResponse> => {
    return request.get('/schedules/statistics/doctor-workload', { params });
  },

  /**
   * 高峰时段热力图
   */
  getPeakHours: (params: {
    storeId: string;
    startDate: string;
    endDate: string;
  }): Promise<PeakHourHeatmapResponse> => {
    return request.get('/schedules/statistics/peak-hours', { params });
  },
};
