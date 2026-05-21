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
  timeSlot?: string;
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
  // 排班优先级相关
  templateId?: string;
  isRestDay?: boolean;
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
   * 批量发布排班
   */
  batchPublish: (scheduleIds: string[]): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/batch-publish', {
      schedule_ids: scheduleIds,
    });
  },

  /**
   * 批量撤回排班
   */
  batchWithdraw: (scheduleIds: string[], reason?: string): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/batch-withdraw', {
      schedule_ids: scheduleIds,
      reason,
    });
  },

  /**
   * 检查排班冲突
   */
  checkConflicts: (data: {
    doctorId: string;
    scheduleDate: string;
    startTime?: string;
    endTime?: string;
    timeSlot?: string;
    storeId?: string;
    roomId?: string;
    excludeScheduleId?: string;
  }): Promise<{
    hasConflict: boolean;
    blocking: boolean;
    conflicts: Array<{ type: string; severity: string; message: string; details?: any }>;
  }> => {
    return request.post('/schedules/conflicts', data);
  },

  /**
   * 拖拽调整排班位置
   */
  dragAdjust: (data: {
    scheduleId: string;
    targetDate: string;
    targetStartTime?: string;
    targetEndTime?: string;
    targetTimeSlot?: string;
  }): Promise<{
    success: boolean;
    schedule?: Schedule;
    conflicts?: {
      hasConflict: boolean;
      blocking: boolean;
      conflicts: Array<{
        type: string;
        severity: string;
        message: string;
        details: Record<string, unknown>;
      }>;
    };
    message: string;
  }> => {
    return request.post('/schedules/drag-adjust', {
      schedule_id: data.scheduleId,
      target_date: data.targetDate,
      target_start_time: data.targetStartTime,
      target_end_time: data.targetEndTime,
      target_time_slot: data.targetTimeSlot,
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

  /**
   * 批量复制排班
   */
  copySchedules: (data: {
    sourceStartDate: string;
    sourceEndDate: string;
    targetStartDate: string;
    targetEndDate: string;
    doctorIds?: string[];
    copyQuota?: boolean;
    copyRoom?: boolean;
    copyFee?: boolean;
    skipHolidays?: boolean;
    conflictStrategy?: 'skip' | 'overwrite' | 'manual';
  }): Promise<{ success: boolean; affectedCount: number; message: string }> => {
    return request.post('/schedules/copy', {
      source_start_date: data.sourceStartDate,
      source_end_date: data.sourceEndDate,
      target_start_date: data.targetStartDate,
      target_end_date: data.targetEndDate,
      doctor_ids: data.doctorIds,
      copy_quota: data.copyQuota,
      copy_room: data.copyRoom,
      copy_fee: data.copyFee,
      skip_holidays: data.skipHolidays,
      conflict_strategy: data.conflictStrategy,
    });
  },

  /**
   * 创建加号申请
   */
  createExtraQuotaRequest: (data: {
    scheduleId: string;
    quantity: number;
    quotaType: 'normal' | 'special' | 'green_channel';
    openToPublic?: boolean;
    patientId?: string;
    reason?: string;
  }) => {
    return request.post('/schedules/extra-quota', {
      schedule_id: data.scheduleId,
      quantity: data.quantity,
      quota_type: data.quotaType,
      open_to_public: data.openToPublic,
      patient_id: data.patientId,
      reason: data.reason,
    });
  },

  /**
   * 查询加号申请列表
   */
  getExtraQuotaRequests: (params: {
    storeId?: string;
    doctorId?: string;
    approvalStatus?: string;
    startDate?: string;
    endDate?: string;
    page?: number;
    pageSize?: number;
  }) => {
    return request.get('/schedules/extra-quota', {
      params: {
        store_id: params.storeId,
        doctor_id: params.doctorId,
        approval_status: params.approvalStatus,
        start_date: params.startDate,
        end_date: params.endDate,
        page: params.page,
        page_size: params.pageSize,
      },
    });
  },

  /**
   * 审批加号（通过）
   */
  approveExtraQuota: (requestId: string, data?: { remark?: string }) => {
    return request.post(`/schedules/extra-quota/${requestId}/approve`, {
      remark: data?.remark,
    });
  },

  /**
   * 审批加号（拒绝）
   */
  rejectExtraQuota: (requestId: string, data: { remark: string }) => {
    return request.post(`/schedules/extra-quota/${requestId}/reject`, {
      remark: data.remark,
    });
  },

  /**
   * 导入排班数据
   */
  importSchedules: (
    file: File,
    conflictStrategy?: 'skip' | 'overwrite' | 'report',
  ): Promise<{
    totalCount: number;
    successCount: number;
    skippedCount: number;
    conflictCount: number;
    errors: Array<{ row: number; errors: string[] }>;
  }> => {
    const formData = new FormData();
    formData.append('file', file);
    if (conflictStrategy) {
      formData.append('conflict_strategy', conflictStrategy);
    }
    return request.post('/data/import/schedules', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  // ==================== 诊室管理 ====================

  /**
   * 获取诊室列表
   */
  getRoomList: (params?: {
    name?: string;
    status?: number;
    storeId?: string;
    departmentId?: string;
    page?: number;
    pageSize?: number;
  }): Promise<PageResult<any>> => {
    return request.get('/schedule-rooms', { params: {
      name: params?.name,
      status: params?.status,
      store_id: params?.storeId,
      department_id: params?.departmentId,
      page: params?.page,
      page_size: params?.pageSize,
    }});
  },

  /**
   * 创建诊室
   */
  createRoom: (data: {
    name: string;
    storeId: string;
    roomNumber?: string;
    floor?: string;
    departmentId?: string;
    capacity?: number;
    status?: number;
    remark?: string;
  }): Promise<any> => {
    return request.post('/schedule-rooms', {
      name: data.name,
      store_id: data.storeId,
      room_number: data.roomNumber,
      floor: data.floor,
      department_id: data.departmentId,
      capacity: data.capacity,
      status: data.status,
      remark: data.remark,
    });
  },

  /**
   * 更新诊室
   */
  updateRoom: (id: string, data: {
    name?: string;
    storeId?: string;
    roomNumber?: string;
    floor?: string;
    departmentId?: string;
    capacity?: number;
    status?: number;
    remark?: string;
  }): Promise<any> => {
    return request.put(`/schedule-rooms/${id}`, {
      name: data.name,
      store_id: data.storeId,
      room_number: data.roomNumber,
      floor: data.floor,
      department_id: data.departmentId,
      capacity: data.capacity,
      status: data.status,
      remark: data.remark,
    });
  },

  /**
   * 删除诊室
   */
  deleteRoom: (id: string): Promise<{ message: string }> => {
    return request.delete(`/schedule-rooms/${id}`);
  },

  /**
   * 下载排班导入模板
   */
  downloadImportTemplate: async (): Promise<void> => {
    const response = await request.get('/data/import/schedules/template', {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'schedule_import_template.xlsx');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  /**
   * 导出排班数据
   */
  exportSchedules: async (params: {
    storeId: string;
    doctorId?: string;
    startDate?: string;
    endDate?: string;
    status?: number;
  }): Promise<void> => {
    const response = await request.get('/data/export/schedules', {
      params: {
        store_id: params.storeId,
        doctor_id: params.doctorId,
        start_date: params.startDate,
        end_date: params.endDate,
        status: params.status,
      },
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `schedules_${params.startDate || 'all'}_${params.endDate || 'all'}.xlsx`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
};
