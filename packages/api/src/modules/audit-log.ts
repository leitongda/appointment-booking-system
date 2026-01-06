/**
 * 审计日志 API
 */
import request from '../request';

export interface CheckinLogListParams {
  appointmentId?: string;
  patientId?: string;
  status?: string;
  checkinMethod?: string;
  startTime?: string;
  endTime?: string;
  page?: number;
  pageSize?: number;
}

export interface CheckinLog {
  id: string;
  appointment_id: string;
  checkin_time: string;
  checkin_method: string;
  device_info?: string;
  location_info?: string;
  operator_id?: string;
  operator_type?: string;
  status: string;
  fail_reason?: string;
  patient_name?: string;
  patient_phone?: string;
  doctor_name?: string;
  department_name?: string;
  created_at?: string;
}

export interface CheckinLogListResponse {
  data: CheckinLog[];
  total: number;
  page: number;
  page_size: number;
}

export interface CheckinLogStatistics {
  data: {
    status: string;
    count: number;
  }[];
  total: number;
}

/**
 * 审计日志 API
 */
export const auditLogApi = {
  /**
   * 获取签到审计日志列表
   */
  async getCheckinLogs(params?: CheckinLogListParams): Promise<CheckinLogListResponse> {
    return request.get('/audit-logs/checkin-logs', { params });
  },

  /**
   * 获取签到审计日志统计
   */
  async getCheckinStatistics(params?: {
    startDate?: string;
    endDate?: string;
  }): Promise<CheckinLogStatistics> {
    return request.get('/audit-logs/checkin-logs/statistics', { params });
  },
};
