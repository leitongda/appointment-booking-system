import { request } from '../request';

export interface OverviewData {
  todayAppointments: number;
  todayVisits: number;
  totalPatients: number;
  totalDoctors: number;
  monthAppointments: number;
  monthRevenue: number;
}

export interface TrendItem {
  date: string;
  count: number;
}

export interface RevenueTrendItem {
  date: string;
  revenue: number;
}

export interface StatusStatItem {
  status: number;
  name: string;
  count: number;
}

export interface DepartmentRankingItem {
  departmentId: string;
  departmentName: string;
  count: number;
}

export interface DoctorRankingItem {
  doctorId: string;
  doctorName: string;
  title: string;
  departmentName: string;
  count: number;
}

export interface TimeSlotItem {
  timeSlot: string;
  name: string;
  count: number;
}

export interface WeekdayItem {
  weekday: number;
  name: string;
  count: number;
}

export interface AppointmentSummary {
  total: number;
  completed: number;
  noShow: number;
  cancelled: number;
  completedRate: number;
  noShowRate: number;
  cancelledRate: number;
}

export interface StoreRankingItem {
  storeId: string;
  storeName: string;
  count: number;
}

export const statisticsApi = {
  /**
   * 获取概览数据
   */
  getOverview: () => request.get<OverviewData>('/statistics/overview'),

  /**
   * 获取预约趋势
   */
  getAppointmentTrend: (days = 7) =>
    request.get<TrendItem[]>('/statistics/appointments/trend', { params: { days } }),

  /**
   * 获取预约状态统计
   */
  getAppointmentStatusStats: (params?: { startDate?: string; endDate?: string }) =>
    request.get<StatusStatItem[]>('/statistics/appointments/status', { params }),

  /**
   * 获取科室排行
   */
  getDepartmentRanking: (limit = 10) =>
    request.get<DepartmentRankingItem[]>('/statistics/departments/ranking', { params: { limit } }),

  /**
   * 获取医生排行
   */
  getDoctorRanking: (limit = 10) =>
    request.get<DoctorRankingItem[]>('/statistics/doctors/ranking', { params: { limit } }),

  /**
   * 获取时段分布
   */
  getTimeSlotDistribution: () =>
    request.get<TimeSlotItem[]>('/statistics/time-slots/distribution'),

  /**
   * 获取星期分布
   */
  getWeekdayDistribution: () =>
    request.get<WeekdayItem[]>('/statistics/weekday/distribution'),

  /**
   * 获取收入趋势
   */
  getRevenueTrend: (days = 7) =>
    request.get<RevenueTrendItem[]>('/statistics/revenue/trend', { params: { days } }),

  /**
   * 获取预约汇总统计（完成率/爽约率/取消率）
   */
  getAppointmentSummary: (params?: { startDate?: string; endDate?: string; storeId?: string }) =>
    request.get<AppointmentSummary>('/statistics/appointments/summary', { params }),

  /**
   * 获取门店预约排行
   */
  getStoreRanking: (params?: { limit?: number; startDate?: string; endDate?: string }) =>
    request.get<StoreRankingItem[]>('/statistics/stores/ranking', { params }),
};

