export interface Schedule {
  id: string;
  doctorId: string;
  doctorName?: string;
  departmentName?: string;
  storeId?: string;
  storeName?: string;
  scheduleDate: string;
  timeSlot?: string;  // 可为空，可通过startTime自动计算
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

/**
 * 排除时间段（如午休时间）
 */
export interface BreakTime {
  startTime: string;
  endTime: string;
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
  weekdays: number[];  // 星期数组，如 [1,2,3,4,5]
  appointmentType: string;
  startTime: string;
  endTime: string;
  slotCount: number;  // 班次数量
  slotCapacity: number;  // 每班次人数
  scheduleMode: string;
  breakTimes?: BreakTime[];  // 排除时间段（如午休时间）
  status: number;
  lastGeneratedAt?: string;  // 上一次生成排班时间
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

/**
 * 班次预览项
 */
export interface ScheduleSlotPreview {
  scheduleDate: string;
  startTime: string;
  endTime: string;
  timeSlot: string;
  periodName: string;  // 时段名称：上午/下午/晚上 或自定义
  slotCapacity: number;
  weekday: number;
  weekdayName: string;
}

/**
 * 预览生成排班响应
 */
export interface SchedulePreviewGenerateResponse {
  slots: ScheduleSlotPreview[];
  totalCount: number;
  templateId: string;
  templateName: string;
  doctorName?: string;
  departmentName?: string;
  dailyDurationHours?: number;   // 每日总时长（小时）
  dailyDurationMinutes?: number; // 每日总时长（剩余分钟数）
}
