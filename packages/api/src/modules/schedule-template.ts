import request from '../request';
import type { ScheduleTemplate, PageResult } from '@hospital/shared';

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
    return request.post('/schedule-templates', {
      name: data.name,
      store_id: data.storeId,
      doctor_id: data.doctorId,
      department_id: data.departmentId,
      weekdays: data.weekdays,
      appointment_type: data.appointmentType,
      start_time: data.startTime,
      end_time: data.endTime,
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
    if (data.startTime !== undefined) requestData.start_time = data.startTime;
    if (data.endTime !== undefined) requestData.end_time = data.endTime;
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
