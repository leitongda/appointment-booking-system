import { get, post, put } from '@/utils/request';
import type { Appointment, PaginatedResponse } from '@/types/api';

/**
 * 重复预约检查响应
 */
export interface DuplicateCheckResponse {
  hasDuplicate: boolean;
  appointments: Array<{
    id: string;
    appointmentNo: string;
    scheduleDate: string;
    timeSlot: string;
    status: number;
  }>;
}

/**
 * 签到响应
 */
export interface SignInResponse {
  message: string;
  queueNumber: number;
}

/**
 * 待签到预约信息
 */
export interface PendingSignInAppointment {
  id: string;
  appointmentNo: string;
  patientName: string;
  doctorName: string;
  scheduleDate: string;
  timeSlot: string;
  signInStatus: 'early' | 'available' | 'late';
  signInMessage: string;
  checkinOpenAt: string;
  checkinCloseAt: string;
  minutesUntilOpen: number;
  minutesUntilClose: number;
}

/**
 * 获取预约列表
 */
export function getAppointments(params?: {
  status?: number;
  page?: number;
  pageSize?: number;
}) {
  return get<PaginatedResponse<Appointment>>('/appointments', params);
}

/**
 * 获取预约详情
 */
export function getAppointmentById(id: string) {
  return get<Appointment>(`/appointments/${id}`);
}

/**
 * 按预约号获取详情
 */
export function getAppointmentByNo(appointmentNo: string) {
  return get<Appointment>(`/appointments/by-no/${appointmentNo}`);
}

/**
 * 创建预约
 */
export function createAppointment(data: {
  scheduleId: string;
  patientId: string;
  symptomDescription?: string;
}) {
  return post<Appointment>('/appointments', data, {
    showLoading: true,
    loadingText: '预约中...'
  });
}

/**
 * 检查重复预约
 */
export function checkDuplicateAppointment(scheduleId: string, patientId: string) {
  return get<DuplicateCheckResponse>('/appointments/check-duplicate', {
    schedule_id: scheduleId,
    patient_id: patientId
  });
}

/**
 * 取消预约
 */
export function cancelAppointment(id: string, reason?: string) {
  return put(`/appointments/${id}/cancel`, { reason }, {
    showLoading: true,
    loadingText: '取消中...'
  });
}

/**
 * 签到
 */
export function signInAppointment(id: string) {
  return put<SignInResponse>(`/appointments/${id}/sign-in`, {}, {
    showLoading: true,
    loadingText: '签到中...'
  });
}

/**
 * 获取今日待签到预约
 */
export function getTodayPendingAppointments(storeId: string) {
  return get<PendingSignInAppointment[]>('/appointments/today-pending', {
    store_id: storeId
  });
}
