import request from '../request';
import type { PageResult } from '@hospital/shared';

export type ProcessingMethod = 'auto_refund' | 'reschedule' | 'change_date' | 'manual';
export type ProcessingStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface ScheduleSuspensionCreateData {
  storeId: string;
  doctorId: string;
  title: string;
  suspensionDate: string;
  scheduleIds?: string[];
  timeSlots?: string[];
  processingMethod?: ProcessingMethod;
}

export interface SuspensionProcessResult {
  suspensionId: string;
  processingMethod: ProcessingMethod;
  processingStatus: ProcessingStatus;
  totalAffected: number;
  successCount: number;
  failedCount: number;
  details?: Array<{
    appointmentId: string;
    patientName?: string;
    processingMethod?: string;
    success: boolean;
    refunded?: boolean;
    paymentAmount?: number;
    error?: string;
  }>;
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
  suspensionType?: string;
  processingMethod?: ProcessingMethod;
  processingStatus?: ProcessingStatus;
  affectedAppointmentCount?: number;
  reason?: string;
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

  /**
   * 获取停诊影响的预约数
   */
  getAffectedCount: (id: string): Promise<{ affectedCount: number }> => {
    return request.get(`/schedule-suspensions/${id}/affected-count`);
  },

  /**
   * 执行停诊处置
   */
  process: (id: string, processingMethod: ProcessingMethod): Promise<SuspensionProcessResult> => {
    return request.post(`/schedule-suspensions/${id}/process`, {
      processing_method: processingMethod,
    });
  },
};
