import request from '../request';
import type { Schedule, PageResult } from '@hospital/shared';

/**
 * 验证并格式化时间值
 * @param timeValue 时间值（可能是字符串、dayjs对象、Date对象或其他格式）
 * @returns 格式化后的 "HH:mm" 字符串，如果无效则返回 undefined
 */
function formatTimeValue(timeValue: any): string | undefined {
  if (!timeValue) return undefined;
  
  // 如果已经是有效的 "HH:mm" 格式字符串，直接返回
  if (typeof timeValue === 'string') {
    // 检查是否是 "Invalid Date" 字符串
    if (timeValue === 'Invalid Date' || timeValue.toLowerCase().includes('invalid')) {
      return undefined;
    }
    // 检查是否符合 "HH:mm" 格式
    const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
    if (timeRegex.test(timeValue)) {
      return timeValue;
    }
    // 尝试从其他格式中提取时间（如 "HH:mm:ss"）
    const timeMatch = timeValue.match(/([01]\d|2[0-3]):([0-5]\d)/);
    if (timeMatch) {
      return timeMatch[0];
    }
    return undefined;
  }
  
  // 如果是 Date 对象
  if (timeValue instanceof Date) {
    if (!isNaN(timeValue.getTime())) {
      const hours = String(timeValue.getHours()).padStart(2, '0');
      const minutes = String(timeValue.getMinutes()).padStart(2, '0');
      return `${hours}:${minutes}`;
    }
    return undefined;
  }
  
  // 如果是对象且有 format 方法（可能是 dayjs 对象）
  if (timeValue && typeof timeValue.format === 'function') {
    try {
      // 检查是否有 isValid 方法
      if (timeValue.isValid && !timeValue.isValid()) {
        return undefined;
      }
      const formatted = timeValue.format('HH:mm');
      // 验证格式化后的结果
      const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
      if (timeRegex.test(formatted)) {
        return formatted;
      }
    } catch (e) {
      // 如果格式化失败，返回 undefined
      return undefined;
    }
  }
  
  return undefined;
}

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
   * 停诊
   * @deprecated 请使用 scheduleSuspensionApi.create() 代替
   * 此方法为了保持向后兼容，内部会先获取排班详情，然后创建停诊记录
   */
  suspend: async (id: string, reason?: string, notifyPatients: boolean = true): Promise<{
    message: string;
    notification?: {
      notifiedCount: number;
      failedCount: number;
      message: string;
    };
  }> => {
    // 先获取排班详情
    const schedule: Schedule = await request.get(`/schedules/${id}`);
    
    if (!schedule.storeId) {
      throw new Error('排班缺少门店信息，无法停诊');
    }
    
    // 使用新的停诊API
    const { scheduleSuspensionApi } = await import('./schedule-suspension');
    await scheduleSuspensionApi.create({
      storeId: schedule.storeId,
      doctorId: schedule.doctorId,
      title: reason || '管理员停诊',
      suspensionDate: schedule.scheduleDate,
      scheduleIds: [id],
    });
    
    return {
      message: '停诊成功',
      // 注意：新API不返回notification信息，如果需要可以后续扩展
      // notifyPatients 参数暂时忽略，因为新API会自动通知患者
    };
  },

  /**
   * 恢复排班
   * @deprecated 请使用 scheduleSuspensionApi.cancel() 代替
   * 此方法为了保持向后兼容，会查找对应的停诊记录并取消
   */
  resume: async (id: string): Promise<{ message: string }> => {
    // 先获取排班详情
    const schedule: Schedule = await request.get(`/schedules/${id}`);
    
    // 查找该排班的停诊记录
    const { scheduleSuspensionApi } = await import('./schedule-suspension');
    const suspensions = await scheduleSuspensionApi.getList({
      doctorId: schedule.doctorId,
      startDate: schedule.scheduleDate,
      endDate: schedule.scheduleDate,
      status: 1, // 生效中的停诊
      pageSize: 100, // 获取足够多的记录
    });
    
    // 查找包含该排班ID的停诊记录，或者全天停诊的记录
    const suspension = suspensions.data?.find(s => {
      if (s.scheduleIds && s.scheduleIds.length > 0) {
        return s.scheduleIds.includes(id);
      }
      // 如果没有指定scheduleIds，说明是全天停诊
      return s.suspensionDate === schedule.scheduleDate;
    });
    
    if (suspension) {
      await scheduleSuspensionApi.cancel(suspension.id);
      return { message: '恢复成功' };
    } else {
      // 如果没有找到停诊记录，直接返回成功（可能排班状态已经是正常的）
      return { message: '恢复成功' };
    }
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
};
