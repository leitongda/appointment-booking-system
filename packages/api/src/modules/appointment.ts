import request from '../request';
import type { Appointment, PageResult } from '@hospital/shared';

export interface AppointmentListParams {
  status?: number;
  patientId?: string;
  doctorId?: string;
  storeId?: string;
  startDate?: string;
  endDate?: string;
  page?: number;
  pageSize?: number;
}

export interface AppointmentCreateData {
  scheduleId: string;
  patientId: string;
}

export interface AppointmentStatistics {
  total: number;
  pending: number;
  signedIn: number;
  inProgress: number;
  completed: number;
  cancelled: number;
  noShow: number;
}

export interface QueueInfo {
  current: {
    id: string;
    queueNumber: number;
    patientName: string;
    callTime: string;
  } | null;
  waitingCount: number;
  waitingList: {
    id: string;
    queueNumber: number;
    patientName: string;
    signInTime: string;
  }[];
  passedCount: number;
  passedList: {
    id: string;
    queueNumber: number;
    patientName: string;
  }[];
}

export const appointmentApi = {
  getList: (params?: AppointmentListParams): Promise<PageResult<Appointment>> => {
    // 转换 camelCase 到 snake_case
    const queryParams = params ? {
      status: params.status,
      patient_id: params.patientId,
      doctor_id: params.doctorId,
      store_id: params.storeId,
      start_date: params.startDate,
      end_date: params.endDate,
      page: params.page,
      page_size: params.pageSize,
    } : undefined;
    return request.get('/appointments', { params: queryParams });
  },

  getToday: (): Promise<Appointment[]> => {
    return request.get('/appointments/today');
  },

  getStatistics: (params?: { doctorId?: string; startDate?: string; endDate?: string }): Promise<AppointmentStatistics> => {
    return request.get('/appointments/statistics', { params });
  },

  getDetail: (id: string): Promise<Appointment> => {
    return request.get(`/appointments/${id}`);
  },

  create: (data: AppointmentCreateData): Promise<Appointment> => {
    return request.post('/appointments', data);
  },

  cancel: (id: string, reason?: string): Promise<void> => {
    return request.put(`/appointments/${id}/cancel`, { reason });
  },

  signIn: (id: string): Promise<{ message: string; queueNumber: number }> => {
    return request.put(`/appointments/${id}/sign-in`);
  },

  call: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/call`);
  },

  complete: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/complete`);
  },

  /**
   * 过号
   */
  pass: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/pass`);
  },

  /**
   * 重新叫号
   */
  recall: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/recall`);
  },

  /**
   * 标记爽约
   */
  markNoShow: (id: string): Promise<void> => {
    return request.put(`/appointments/${id}/no-show`);
  },

  /**
   * 获取叫号队列信息
   */
  getQueueInfo: (): Promise<QueueInfo> => {
    return request.get('/appointments/queue/info');
  },
};
