import request from '../request';
import type { Schedule, PageResult } from '@hospital/shared';

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
    const queryParams = params ? {
      doctor_id: params.doctorId,
      store_id: params.storeId,
      start_date: params.startDate,
      end_date: params.endDate,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
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
    if (data.startTime) requestData.start_time = data.startTime;
    if (data.endTime) requestData.end_time = data.endTime;
    if (data.appointmentType) requestData.appointment_type = data.appointmentType;
    if (data.templateId) requestData.template_id = data.templateId;
    if (data.status !== undefined) requestData.status = data.status;
    
    return request.post('/schedules', requestData);
  },

  batchCreate: (data: ScheduleBatchCreateData): Promise<{ message: string }> => {
    return request.post('/schedules/batch', data);
  },

  update: (id: string, data: Partial<ScheduleCreateData>): Promise<Schedule> => {
    return request.put(`/schedules/${id}`, data);
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
};
