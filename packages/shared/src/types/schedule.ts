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
  appointmentType: string;  // 必填，默认 "normal"
  templateId?: string;
  status: number;
  createdAt?: string;  // 可选
  isRestDay: boolean;  // 必填，默认 false
  /**
   * 生效状态（后端计算）
   * - active: 正常生效
   * - suspended: 停诊
   * - rest_day: 在休息日（模板排班会被隐藏）
   * - custom: 自定义排班（最高优先级）
   * - overridden: 被自定义排班覆盖（模板排班）
   */
  effectiveStatus?: string;
}

export interface AvailableSchedule {
  id: string;
  scheduleDate: string;
  timeSlot?: string;
  availableSlots: number;
  startTime?: string;
  endTime?: string;
  appointmentType: string;
  // 规则引擎相关
  totalSlots: number;
  bookingOpenAt?: string;
  bookingCloseAt?: string;
  bookingStatus: string;  // available/closing_soon/full/closed/not_open
  capacityPercent: number;
  urgencyLevel: string;  // normal/medium/high/critical
  // 排班优先级相关
  templateId?: string;  // 模板ID，为null/undefined表示自定义排班
  isRestDay: boolean;  // 是否在休息日（后端计算，自定义排班始终为false）
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
  isRestDay?: boolean;  // 是否在休息日（后端计算）
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
  ruleValidation?: string[];  // 规则引擎校验警告信息
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
