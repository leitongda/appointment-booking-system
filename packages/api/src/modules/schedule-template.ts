import request from '../request';
import type { ScheduleTemplate, PageResult } from '@hospital/shared';

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

export interface ScheduleTemplateListParams {
  storeId?: string;
  doctorId?: string;
  departmentId?: string;
  status?: number;
  page?: number;
  pageSize?: number;
}

export interface ScheduleTemplateCreateData {
  name: string;
  storeId: string;
  doctorId: string;
  departmentId: string;
  weekdays: number[];
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  slotCapacity: number;
  scheduleMode: string;
}

export interface ScheduleTemplateUpdateData {
  name?: string;
  storeId?: string;
  doctorId?: string;
  departmentId?: string;
  weekdays?: number[];
  appointmentType?: string;
  startTime?: string;
  endTime?: string;
  slotCount?: number;
  slotCapacity?: number;
  scheduleMode?: string;
  status?: number;
}

export interface ScheduleGenerateData {
  templateIds: string[];
  startDate: string;
  endDate: string;
}

export interface ScheduleBatchAddData {
  storeId: string;
  doctorId: string;
  departmentId: string;
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  slotCapacity: number;
  scheduleMode: string;
  weekdays: number[];
  startDate: string;
  endDate: string;
}

export const scheduleTemplateApi = {
  /**
   * 获取排班模板列表
   */
  getList: (params?: ScheduleTemplateListParams): Promise<PageResult<ScheduleTemplate>> => {
    const queryParams = params ? {
      store_id: params.storeId,
      doctor_id: params.doctorId,
      department_id: params.departmentId,
      status: params.status,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/schedule-templates', { params: queryParams });
  },

  /**
   * 获取排班模板详情
   */
  getDetail: (id: string): Promise<ScheduleTemplate> => {
    return request.get(`/schedule-templates/${id}`);
  },

  /**
   * 创建排班模板
   */
  create: (data: ScheduleTemplateCreateData): Promise<ScheduleTemplate> => {
    // 验证并格式化时间字段
    const formattedStartTime = formatTimeValue(data.startTime);
    const formattedEndTime = formatTimeValue(data.endTime);
    
    if (!formattedStartTime || !formattedEndTime) {
      throw new Error('开始时间和结束时间格式不正确，应为 HH:mm 格式');
    }
    
    return request.post('/schedule-templates', {
      name: data.name,
      store_id: data.storeId,
      doctor_id: data.doctorId,
      department_id: data.departmentId,
      weekdays: data.weekdays,
      appointment_type: data.appointmentType,
      start_time: formattedStartTime,
      end_time: formattedEndTime,
      slot_count: data.slotCount,
      slot_capacity: data.slotCapacity,
      schedule_mode: data.scheduleMode,
    });
  },

  /**
   * 更新排班模板
   */
  update: (id: string, data: ScheduleTemplateUpdateData): Promise<ScheduleTemplate> => {
    const requestData: Record<string, any> = {};
    if (data.name !== undefined) requestData.name = data.name;
    if (data.storeId !== undefined) requestData.store_id = data.storeId;
    if (data.doctorId !== undefined) requestData.doctor_id = data.doctorId;
    if (data.departmentId !== undefined) requestData.department_id = data.departmentId;
    if (data.weekdays !== undefined) requestData.weekdays = data.weekdays;
    if (data.appointmentType !== undefined) requestData.appointment_type = data.appointmentType;
    
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
    
    if (data.slotCount !== undefined) requestData.slot_count = data.slotCount;
    if (data.slotCapacity !== undefined) requestData.slot_capacity = data.slotCapacity;
    if (data.scheduleMode !== undefined) requestData.schedule_mode = data.scheduleMode;
    if (data.status !== undefined) requestData.status = data.status;
    return request.put(`/schedule-templates/${id}`, requestData);
  },

  /**
   * 删除排班模板
   */
  delete: (id: string): Promise<{ message: string }> => {
    return request.delete(`/schedule-templates/${id}`);
  },

  /**
   * 根据模板批量生成排班
   */
  generate: (data: ScheduleGenerateData): Promise<{ message: string; count: number }> => {
    return request.post('/schedule-templates/generate', {
      template_ids: data.templateIds,
      start_date: data.startDate,
      end_date: data.endDate,
    });
  },

  /**
   * 批量添加排班（不依赖模板）
   * @deprecated 请使用 scheduleApi.batchCreate() 代替
   * 此方法为了保持向后兼容，会将数据转换为新的API格式
   */
  batchAdd: async (data: ScheduleBatchAddData): Promise<{ message: string; count: number }> => {
    // 注意：新API不支持 slot_count, schedule_mode, appointment_type 等参数
    // 这里简化处理，只支持基本的批量创建
    const { scheduleApi } = await import('./schedule');
    const result = await scheduleApi.batchCreate({
      doctorId: data.doctorId,
      startDate: data.startDate,
      endDate: data.endDate,
      timeSlots: [`${data.startTime}-${data.endTime}`], // 简化处理，只支持单个时间段
      totalSlots: data.slotCapacity,
      weekdays: data.weekdays,
    });
    
    return {
      message: result.message || '批量添加成功',
      count: 0, // 新API不返回count，需要后续扩展
    };
  },
};
