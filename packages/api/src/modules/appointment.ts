import request from '../request';
import type { Appointment, PageResult } from '@hospital/shared';

export interface AppointmentListParams {
  status?: number;
  patientId?: string;
  doctorId?: string;
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

export const appointmentApi = {
  getList: (params?: AppointmentListParams): Promise<PageResult<Appointment>> => {
    return request.get('/appointments', { params });
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
};
