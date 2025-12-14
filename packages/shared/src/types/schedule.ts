export interface Schedule {
  id: string;
  doctorId: string;
  doctorName?: string;
  departmentName?: string;
  storeId?: string;
  storeName?: string;
  scheduleDate: string;
  timeSlot: string;
  startTime?: string;
  endTime?: string;
  totalSlots: number;
  bookedSlots: number;
  appointmentType?: string;
  templateId?: string;
  status: number;
  createdAt: string;
}

export interface AvailableSchedule {
  id: string;
  scheduleDate: string;
  timeSlot: string;
  availableSlots: number;
  startTime?: string;
  endTime?: string;
  appointmentType?: string;
}

export interface ScheduleTemplate {
  id: string;
  name: string;
  storeId: string;
  storeName?: string;
  doctorId: string;
  doctorName?: string;
  departmentId: string;
  departmentName?: string;
  weekday: number;
  appointmentType: string;
  startTime: string;
  endTime: string;
  totalSlots: number;
  scheduleMode: string;
  status: number;
  createdAt: string;
  updatedAt?: string;
}

/**
 * 自定义排班
 */
export interface CustomSchedule {
  id: string;
  storeId: string;
  storeName?: string;
  departmentId: string;
  departmentName?: string;
  doctorId: string;
  doctorName?: string;
  scheduleDate: string;
  startTime: string;
  endTime: string;
  appointmentType: string;
  maxPatients: number;
  bookedCount: number;
  status: number;
  createdAt: string;
}

/**
 * 休息日
 */
export interface RestDay {
  id: string;
  storeId: string;
  storeName?: string;
  doctorIds?: string[];
  doctorNames?: string[];
  reason?: string;
  startDate: string;
  endDate: string;
  status: number;
  createdAt: string;
}

/**
 * 停诊记录
 */
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
}

/**
 * 排班统计项
 */
export interface ScheduleStatisticsItem {
  scheduleDate: string;
  doctorId: string;
  doctorName: string;
  morningSlots: number;
  afternoonSlots: number;
  morningBooked: number;
  afternoonBooked: number;
}

/**
 * 排班统计响应
 */
export interface ScheduleStatisticsResponse {
  storeId: string;
  storeName: string;
  year: number;
  month: number;
  items: ScheduleStatisticsItem[];
}
