import request from '../request';
import type { LeaveRequest, PageResult, Period } from '@hospital/shared';

export interface StopClinicData {
  doctorId: string;
  scheduleId?: string;
  stopDate: string;
  stopPeriod: Period;
  reason: string;
}

export interface ScheduleChangeData {
  doctorId: string;
  originalDate: string;
  originalPeriod: Period;
  targetDate: string;
  targetPeriod: Period;
  reason: string;
}

export interface LeaveRequestListParams {
  doctorId?: string;
  requestType?: string;
  status?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

export const leaveRequestApi = {
  // 获取申请列表（管理端）
  getList: (params?: LeaveRequestListParams): Promise<PageResult<LeaveRequest>> => {
    return request.get('/leave-requests', { 
      params: {
        doctor_id: params?.doctorId,
        request_type: params?.requestType,
        status: params?.status,
        start_date: params?.startDate,
        end_date: params?.endDate,
        page: params?.page,
        page_size: params?.pageSize,
      }
    });
  },

  // 获取我的申请列表（医生端）
  getMyList: (doctorId: string, status?: string): Promise<LeaveRequest[]> => {
    return request.get('/leave-requests/my', { 
      params: { doctor_id: doctorId, status } 
    });
  },

  // 获取待审核数量
  getPendingCount: (): Promise<{ count: number }> => {
    return request.get('/leave-requests/pending-count');
  },

  // 获取申请详情
  getDetail: (id: string): Promise<LeaveRequest> => {
    return request.get(`/leave-requests/${id}`);
  },

  // 创建停诊申请
  createStopClinic: (data: StopClinicData): Promise<LeaveRequest> => {
    return request.post('/leave-requests/stop-clinic', {
      doctor_id: data.doctorId,
      schedule_id: data.scheduleId,
      stop_date: data.stopDate,
      stop_period: data.stopPeriod,
      reason: data.reason,
    });
  },

  // 创建调班申请
  createScheduleChange: (data: ScheduleChangeData): Promise<LeaveRequest> => {
    return request.post('/leave-requests/schedule-change', {
      doctor_id: data.doctorId,
      original_date: data.originalDate,
      original_period: data.originalPeriod,
      target_date: data.targetDate,
      target_period: data.targetPeriod,
      reason: data.reason,
    });
  },

  // 审核申请
  review: (
    id: string, 
    reviewerId: string, 
    status: string, 
    comment?: string
  ): Promise<LeaveRequest> => {
    return request.post(`/leave-requests/${id}/review`, 
      { status, review_comment: comment },
      { params: { reviewer_id: reviewerId } }
    );
  },

  // 取消申请
  cancel: (id: string, doctorId: string): Promise<void> => {
    return request.post(`/leave-requests/${id}/cancel`, null, {
      params: { doctor_id: doctorId }
    });
  },
};
