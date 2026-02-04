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
  appointmentId: string;
  checkinTime: string;
  checkinMethod: string;
  deviceInfo?: string;
  locationInfo?: string;
  operatorId?: string;
  operatorType?: string;
  status: string;
  failReason?: string;
  patientName?: string;
  patientPhone?: string;
  doctorName?: string;
  departmentName?: string;
  createdAt?: string;
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
