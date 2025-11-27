import type { DoctorBrief } from './doctor';

/**
 * 排班信息
 */
export interface Schedule {
  id: string;
  doctorId: string;
  scheduleDate: string;
  timeSlot: 'AM' | 'PM' | 'NIGHT';
  startTime: string;
  endTime: string;
  totalSlots: number;
  bookedSlots: number;
  availableSlots: number;
  status: number;
  createdAt: string;
  updatedAt: string;
  // 关联信息
  doctor?: DoctorBrief;
}

/**
 * 排班查询参数
 */
export interface ScheduleQueryParams {
  doctorId?: string;
  departmentId?: string;
  startDate?: string;
  endDate?: string;
  timeSlot?: string;
  status?: number;
}

/**
 * 排班模板
 */
export interface ScheduleTemplate {
  id: string;
  doctorId: string;
  weekday: number;
  timeSlot: 'AM' | 'PM' | 'NIGHT';
  startTime: string;
  endTime: string;
  totalSlots: number;
  status: number;
}

