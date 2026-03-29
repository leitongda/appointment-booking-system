// API 响应通用结构
export interface ApiResponse<T = any> {
  code: number;
  message: string;
  data: T;
}

// 分页响应
export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  pageSize: number;
}

// 请求配置
export interface RequestConfig {
  url: string;
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE';
  data?: any;
  params?: Record<string, any>;
  headers?: Record<string, string>;
  needAuth?: boolean;
  showLoading?: boolean;
  loadingText?: string;
}

// 预约状态枚举（与后端API保持一致）
export enum AppointmentStatus {
  PENDING = 0,      // 待支付
  CONFIRMED = 1,    // 已预约
  SIGNED_IN = 2,    // 已签到
  WAITING = 3,      // 候诊中
  IN_PROGRESS = 4,  // 就诊中
  COMPLETED = 5,    // 已完成
  CANCELLED = 6,    // 已取消
  EXPIRED = 7,      // 已过期
  NO_SHOW = 8,      // 爽约
}

// 预约信息
export interface Appointment {
  id: string;
  appointmentNo: string;
  patientId: string;
  patientName: string;
  scheduleId: string;
  doctorId: string;
  doctorName: string;
  doctorTitle: string;
  departmentId: string;
  departmentName: string;
  scheduleDate: string;
  timeSlot: string;
  startTime: string;
  endTime: string;
  status: AppointmentStatus;
  queueNumber?: number;
  symptomDescription?: string;
  createdAt: string;
  updatedAt: string;
}

// 医生信息
export interface Doctor {
  id: string;
  name: string;
  title: string;
  departmentId: string;
  departmentName: string;
  avatar?: string;
  introduction?: string;
  specialty?: string;
  isRecommended: boolean;
  sortOrder: number;
}

// 科室信息
export interface Department {
  id: string;
  name: string;
  parentId?: string;
  isFinal: boolean;
  icon?: string;
  description?: string;
  isHot: boolean;
  sortOrder: number;
}

// 科室树节点
export interface DepartmentTreeNode extends Department {
  children?: DepartmentTreeNode[];
}

// 排班信息
export interface Schedule {
  id: string;
  doctorId: string;
  scheduleDate: string;
  timeSlot: string;
  startTime: string;
  endTime: string;
  availableSlots: number;
  totalSlots: number;
  bookingStatus: 'available' | 'closing_soon' | 'full' | 'closed' | 'not_open';
  bookingOpenAt: string;
  bookingCloseAt: string;
  capacityPercent: number;
  urgencyLevel: 'normal' | 'medium' | 'high' | 'critical';
}

// 就诊人信息
export interface Patient {
  id: string;
  userId: string;
  name: string;
  phone: string;
  idCard?: string;
  gender?: number;
  birthday?: string;
  relationship?: string;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

// 用户信息
export interface User {
  id: string;
  openid: string;
  nickname?: string;
  avatar?: string;
  phone?: string;
  createdAt: string;
  updatedAt: string;
}

// 收藏信息
export interface Favorite {
  id: string;
  userId: string;
  targetType: 'doctor' | 'department';
  targetId: string;
  createdAt: string;
}

// 轮播图
export interface Banner {
  id: string;
  title?: string;
  imageUrl: string;
  linkType: number;
  linkUrl?: string;
  position?: string;
}

// 公告
export interface Notice {
  id: string;
  title: string;
  content: string;
  publishedAt: string;
}

// 预约规则
export interface BookingRules {
  advanceDays: number;
  sameDayBooking: boolean;
  cancelHours: number;
  perDayLimit: number;
  advanceBookingMinutes: number;
  signInAdvanceMinutes: number;
  signInLateMinutes: number;
}

// 医院信息
export interface HospitalInfo {
  hospitalName: string;
  hospitalLevel: string;
  address: string;
  phone: string;
  workTime: string;
  introduction: string;
  logo: string;
}

// 时段配置
export interface TimePeriod {
  key: string;
  name: string;
  startTime: string;
  endTime: string;
}

export interface TimePeriodsConfig {
  periods: TimePeriod[];
  isCustom: boolean;
}

// 门店信息
export interface Store {
  id: string;
  code: string;
  name: string;
  address?: string;
  phone?: string;
  status: number;
}

// 反馈信息
export interface Feedback {
  id: string;
  userId: string;
  userType?: string;
  feedbackType?: string;
  title: string;
  content: string;
  images?: string[];
  contact?: string;
  status: number;
  createdAt: string;
}
