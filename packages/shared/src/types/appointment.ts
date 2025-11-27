import type { DoctorBrief } from './doctor';
import type { Patient } from './user';
import type { Schedule } from './schedule';

/**
 * 预约信息
 */
export interface Appointment {
  id: string;
  appointmentNo: string;
  userId: string;
  patientId: string;
  doctorId: string;
  scheduleId: string;
  appointmentDate: string;
  timeSlot: string;
  queueNumber?: number;
  fee?: number;
  paymentStatus: number;
  paymentTime?: string;
  status: number;
  signInTime?: string;
  callTime?: string;
  completeTime?: string;
  cancelReason?: string;
  source: string;
  createdAt: string;
  updatedAt: string;
  // 关联信息
  doctor?: DoctorBrief;
  patient?: Patient;
  schedule?: Schedule;
}

/**
 * 创建预约参数
 */
export interface CreateAppointmentParams {
  doctorId: string;
  scheduleId: string;
  patientId: string;
}

/**
 * 预约查询参数
 */
export interface AppointmentQueryParams {
  status?: number;
  doctorId?: string;
  departmentId?: string;
  startDate?: string;
  endDate?: string;
  keyword?: string;
}

/**
 * 预约统计
 */
export interface AppointmentStats {
  total: number;
  pending: number;
  confirmed: number;
  completed: number;
  cancelled: number;
}

