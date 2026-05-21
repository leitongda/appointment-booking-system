import request from '../request';
import type { ScheduleTemplate, PageResult, BreakTime, SchedulePreviewGenerateResponse } from '@hospital/shared';
import { formatTimeValue } from '../utils/formatTime';

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
  shiftTypeId: string;
  weekdays: number[];
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  slotCapacity: number;
  scheduleMode: string;
  breakTimes?: BreakTime[];
  ruleSetId?: string;
}

export interface ScheduleTemplateUpdateData {
  name?: string;
  storeId?: string;
  doctorId?: string;
  departmentId?: string;
  shiftTypeId?: string;
  weekdays?: number[];
  appointmentType?: string;
  startTime?: string;
  endTime?: string;
  slotCount?: number;
  slotCapacity?: number;
  scheduleMode?: string;
  breakTimes?: BreakTime[];
  ruleSetId?: string;
  status?: number;
}

export interface ScheduleGenerateData {
  templateIds: string[];
  startDate?: string;  // 可选，默认今天
  endDate?: string;    // 可选，默认1年后
}

export interface BatchOperateData {
  startDate?: string;
  endDate?: string;
  futureOnly?: boolean;
}

export interface BatchOperateResult {
  success: boolean;
  affectedCount: number;
  message: string;
}

export interface CheckGeneratedResult {
  hasGenerated: boolean;
  scheduleCount: number;
  dateRangeCount: number;
  earliestDate?: string;
  latestDate?: string;
}

export interface ScheduleGenerationLog {
  id: string;
  templateId: string;
  operatorId?: string;
  operatorName?: string;
  actionType: string;
  startDate?: string;
  endDate?: string;
  affectedCount: number;
  remark?: string;
  createdAt: string;
}

export interface ScheduleBatchAddData {
  storeId: string;
  doctorId: string;
  departmentId: string;
  shiftTypeId: string;
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;
  slotCapacity: number;
  scheduleMode: string;
  breakTimes?: BreakTime[];
  weekdays: number[];
  startDate: string;
  endDate: string;
}

export interface SchedulePreviewGenerateData {
  templateIds: string[];
  startDate?: string;
  endDate?: string;
}

export interface SlotCapacityOverride {
  scheduleDate: string;
  startTime: string;
  endTime: string;
  slotCapacity: number;
}

export interface ScheduleGenerateWithCapacityData {
  templateIds: string[];
  startDate?: string;
  endDate?: string;
  slotCapacities?: SlotCapacityOverride[];
}

export interface ScheduleTemplateCopyData {
  targetDoctorIds: string[];
  name?: string;
  shiftTypeId?: string;
  weekdays?: number[];
  appointmentType?: string;
  startTime?: string;
  endTime?: string;
  slotCount?: number;
  slotCapacity?: number;
  scheduleMode?: string;
  breakTimes?: BreakTime[];
}

export interface ScheduleTemplateCopyResult {
  message: string;
  createdCount: number;
}

export interface CrossStoreDoctorMapping {
  sourceDepartmentId: string;
  targetDepartmentId: string;
  targetDoctorId: string;
}

export interface ScheduleTemplateCrossStoreCopyData {
  targetStoreId: string;
  mappings: CrossStoreDoctorMapping[];
  name?: string;
  shiftTypeId?: string;
  weekdays?: number[];
  appointmentType?: string;
  startTime?: string;
  endTime?: string;
  slotCount?: number;
  slotCapacity?: number;
  scheduleMode?: string;
  breakTimes?: BreakTime[];
}

export interface ScheduleTemplateCrossStoreCopyResult {
  message: string;
  createdCount: number;
  failedMappings?: CrossStoreDoctorMapping[];
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
    
    // 格式化 breakTimes
    const formattedBreakTimes = data.breakTimes?.map(bt => ({
      start_time: formatTimeValue(bt.startTime) || bt.startTime,
      end_time: formatTimeValue(bt.endTime) || bt.endTime,
    }));
    
    return request.post('/schedule-templates', {
      name: data.name,
      store_id: data.storeId,
      doctor_id: data.doctorId,
      department_id: data.departmentId,
      shift_type_id: data.shiftTypeId,
      weekdays: data.weekdays,
      appointment_type: data.appointmentType,
      start_time: formattedStartTime,
      end_time: formattedEndTime,
      slot_count: data.slotCount,
      slot_capacity: data.slotCapacity,
      schedule_mode: data.scheduleMode,
      break_times: formattedBreakTimes,
      rule_set_id: data.ruleSetId || undefined,
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
    if (data.shiftTypeId !== undefined) requestData.shift_type_id = data.shiftTypeId;
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
    if (data.breakTimes !== undefined) {
      requestData.break_times = data.breakTimes?.map(bt => ({
        start_time: formatTimeValue(bt.startTime) || bt.startTime,
        end_time: formatTimeValue(bt.endTime) || bt.endTime,
      }));
    }
    if (data.ruleSetId !== undefined) requestData.rule_set_id = data.ruleSetId || null;
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
    const requestData: Record<string, any> = {
      template_ids: data.templateIds,
    };
    if (data.startDate) {
      requestData.start_date = data.startDate;
    }
    if (data.endDate) {
      requestData.end_date = data.endDate;
    }
    return request.post('/schedule-templates/generate', requestData);
  },

  /**
   * 批量添加排班（不依赖模板）
   */
  batchAdd: async (data: ScheduleBatchAddData): Promise<{ message: string; count: number }> => {
    // 验证并格式化时间字段
    const formattedStartTime = formatTimeValue(data.startTime);
    const formattedEndTime = formatTimeValue(data.endTime);
    
    if (!formattedStartTime || !formattedEndTime) {
      throw new Error('开始时间和结束时间格式不正确，应为 HH:mm 格式');
    }
    
    // 格式化 breakTimes
    const formattedBreakTimes = data.breakTimes?.map(bt => ({
      start_time: formatTimeValue(bt.startTime) || bt.startTime,
      end_time: formatTimeValue(bt.endTime) || bt.endTime,
    }));
    
    // 转换 camelCase 到 snake_case
    return request.post('/schedule-templates/batch-add', {
      store_id: data.storeId,
      doctor_id: data.doctorId,
      department_id: data.departmentId,
      shift_type_id: data.shiftTypeId,
      appointment_type: data.appointmentType,
      start_time: formattedStartTime,
      end_time: formattedEndTime,
      slot_count: data.slotCount,
      slot_capacity: data.slotCapacity,
      schedule_mode: data.scheduleMode,
      break_times: formattedBreakTimes,
      weekdays: data.weekdays,
      start_date: data.startDate,
      end_date: data.endDate,
    });
  },

  /**
   * 检查规则是否已生成过排班
   */
  checkGenerated: (id: string, startDate?: string, endDate?: string): Promise<CheckGeneratedResult> => {
    const params: Record<string, string> = {};
    if (startDate) params.start_date = startDate;
    if (endDate) params.end_date = endDate;
    return request.get(`/schedule-templates/${id}/check-generated`, { params });
  },

  /**
   * 批量删除规则生成的排班
   */
  batchDelete: (id: string, data?: BatchOperateData): Promise<BatchOperateResult> => {
    const requestData = data ? {
      start_date: data.startDate,
      end_date: data.endDate,
      future_only: data.futureOnly ?? true,
    } : undefined;
    return request.post(`/schedule-templates/${id}/batch-delete`, requestData);
  },

  /**
   * 批量停诊规则生成的排班
   */
  batchSuspend: (id: string, data?: BatchOperateData): Promise<BatchOperateResult> => {
    const requestData = data ? {
      start_date: data.startDate,
      end_date: data.endDate,
      future_only: data.futureOnly ?? true,
    } : undefined;
    return request.post(`/schedule-templates/${id}/batch-suspend`, requestData);
  },

  /**
   * 获取规则的生成历史记录
   */
  getLogs: (id: string, page: number = 1, pageSize: number = 10): Promise<{ data: ScheduleGenerationLog[]; total: number }> => {
    return request.get(`/schedule-templates/${id}/logs`, { params: { page, page_size: pageSize } });
  },

  /**
   * 预览生成排班（不实际写入数据库）
   */
  previewGenerate: (data: SchedulePreviewGenerateData): Promise<SchedulePreviewGenerateResponse[]> => {
    const requestData: Record<string, any> = {
      template_ids: data.templateIds,
    };
    if (data.startDate) {
      requestData.start_date = data.startDate;
    }
    if (data.endDate) {
      requestData.end_date = data.endDate;
    }
    return request.post('/schedule-templates/preview-generate', requestData);
  },

  /**
   * 根据模板批量生成排班（支持自定义班次容量）
   */
  generateWithCapacity: (data: ScheduleGenerateWithCapacityData): Promise<{ message: string; count: number }> => {
    const requestData: Record<string, any> = {
      template_ids: data.templateIds,
    };
    if (data.startDate) {
      requestData.start_date = data.startDate;
    }
    if (data.endDate) {
      requestData.end_date = data.endDate;
    }
    if (data.slotCapacities) {
      requestData.slot_capacities = data.slotCapacities.map(sc => ({
        schedule_date: sc.scheduleDate,
        start_time: sc.startTime,
        end_time: sc.endTime,
        slot_capacity: sc.slotCapacity,
      }));
    }
    return request.post('/schedule-templates/generate-with-capacity', requestData);
  },

  /**
   * 复制排班规则给其他医生
   */
  copy: (id: string, data: ScheduleTemplateCopyData): Promise<ScheduleTemplateCopyResult> => {
    const requestData: Record<string, any> = {
      target_doctor_ids: data.targetDoctorIds,
    };
    if (data.name !== undefined) requestData.name = data.name;
    if (data.shiftTypeId !== undefined) requestData.shift_type_id = data.shiftTypeId;
    if (data.weekdays !== undefined) requestData.weekdays = data.weekdays;
    if (data.appointmentType !== undefined) requestData.appointment_type = data.appointmentType;
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
    if (data.breakTimes !== undefined) {
      requestData.break_times = data.breakTimes?.map(bt => ({
        start_time: formatTimeValue(bt.startTime) || bt.startTime,
        end_time: formatTimeValue(bt.endTime) || bt.endTime,
      }));
    }
    return request.post(`/schedule-templates/${id}/copy`, requestData);
  },

  /**
   * 跨院区复制排班规则
   */
  copyCrossStore: (id: string, data: ScheduleTemplateCrossStoreCopyData): Promise<ScheduleTemplateCrossStoreCopyResult> => {
    const requestData: Record<string, any> = {
      target_store_id: data.targetStoreId,
      mappings: data.mappings.map(m => ({
        source_department_id: m.sourceDepartmentId,
        target_department_id: m.targetDepartmentId,
        target_doctor_id: m.targetDoctorId,
      })),
    };
    if (data.name !== undefined) requestData.name = data.name;
    if (data.shiftTypeId !== undefined) requestData.shift_type_id = data.shiftTypeId;
    if (data.weekdays !== undefined) requestData.weekdays = data.weekdays;
    if (data.appointmentType !== undefined) requestData.appointment_type = data.appointmentType;
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
    if (data.breakTimes !== undefined) {
      requestData.break_times = data.breakTimes?.map(bt => ({
        start_time: formatTimeValue(bt.startTime) || bt.startTime,
        end_time: formatTimeValue(bt.endTime) || bt.endTime,
      }));
    }
    return request.post(`/schedule-templates/${id}/copy-cross-store`, requestData);
  },
};
