/**
 * 考勤管理 API
 */
import request from '../request';
import type { PageResult } from '@hospital/shared';

// ==================== 类型定义 ====================

export interface CheckInData {
  lat: number;
  lng: number;
  deviceInfo?: string;
  groupId?: string;
  wifiSsid?: string;
  deviceId?: string;
  remark?: string;
}

export interface CheckOutData {
  lat: number;
  lng: number;
  deviceInfo?: string;
  remark?: string;
}

export interface AttendanceRecord {
  id: string;
  accountId: string;
  accountName?: string;
  shiftId?: string;
  shiftName?: string;
  groupId?: string;
  checkDate: string;
  checkInTime?: string;
  checkOutTime?: string;
  status: string;
  lateMinutes: number;
  earlyMinutes: number;
  workHours?: number;
  remark?: string;
}

export interface AttendanceRecordListParams {
  startDate?: string;
  endDate?: string;
  keyword?: string;
  page?: number;
  pageSize?: number;
}

export interface DailyStat {
  date: string;
  total: number;
  normal: number;
  late: number;
  early: number;
  absent: number;
  leave: number;
  expected: number;
}

// ==================== 班次类型定义 ====================

export interface AttendanceShift {
  id: string;
  name: string;
  code: string;
  startTime: string;
  endTime: string;
  breakStart?: string;
  breakEnd?: string;
  graceMinutes: number;
  lateThresholdMinutes: number;
  earlyThresholdMinutes: number;
  isFlexible: boolean;
  enabled: boolean;
  createdAt?: string;
  updatedAt?: string;
}

export interface AttendanceShiftCreateData {
  name: string;
  code: string;
  startTime: string;
  endTime: string;
  breakStart?: string;
  breakEnd?: string;
  graceMinutes?: number;
  lateThresholdMinutes?: number;
  earlyThresholdMinutes?: number;
  isFlexible?: boolean;
  enabled?: boolean;
}

export type AttendanceShiftUpdateData = Partial<AttendanceShiftCreateData>;

// ==================== 签到组类型定义 ====================

export interface AttendanceGroup {
  id: string;
  name: string;
  description?: string;
  checkMethod: string;
  locationLat?: number;
  locationLng?: number;
  locationRadius: number;
  wifiSsid?: string;
  wifiSsids?: string;
  deviceWhitelist?: string;
  requireDeviceBind: boolean;
  enabled: boolean;
  memberCount: number;
  createdAt?: string;
}

export interface AttendanceGroupCreateData {
  name: string;
  description?: string;
  checkMethod?: string;
  locationLat?: number;
  locationLng?: number;
  locationRadius?: number;
  wifiSsid?: string;
  wifiSsids?: string;
  deviceWhitelist?: string;
  requireDeviceBind?: boolean;
  enabled?: boolean;
}

export type AttendanceGroupUpdateData = Partial<AttendanceGroupCreateData>;

export interface GroupMember {
  id: string;
  accountId: string;
  accountName?: string;
  createdAt?: string;
}

// ==================== 考勤规则类型定义 ====================

export interface AttendanceRule {
  id: string;
  name: string;
  description?: string;
  latePolicy: string;
  earlyPolicy: string;
  absentPolicy: string;
  overtimeEnabled: boolean;
  overtimeMinMinutes: number;
  enabled: boolean;
  createdAt?: string;
}

export interface AttendanceRuleCreateData {
  name: string;
  description?: string;
  latePolicy?: string;
  earlyPolicy?: string;
  absentPolicy?: string;
  overtimeEnabled?: boolean;
  overtimeMinMinutes?: number;
  enabled?: boolean;
}

export type AttendanceRuleUpdateData = Partial<AttendanceRuleCreateData>;

// ==================== 假期类型定义 ====================

export interface LeaveType {
  id: string;
  tenantId?: string;
  name: string;
  code: string;
  paid: boolean;
  defaultDays: number;
  enabled: boolean;
  sortOrder: number;
  createdAt?: string;
  updatedAt?: string;
}

export interface LeaveTypeCreateData {
  name: string;
  code: string;
  paid?: boolean;
  defaultDays?: number;
  enabled?: boolean;
  sortOrder?: number;
}

export type LeaveTypeUpdateData = Partial<LeaveTypeCreateData>;

// ==================== 假期余额定义 ====================

export interface LeaveBalance {
  id: string;
  accountId: string;
  leaveTypeId: string;
  leaveTypeName?: string;
  year: number;
  totalDays: number;
  usedDays: number;
  remainingDays: number;
}

export interface LeaveBalanceUpdateData {
  accountId: string;
  leaveTypeId: string;
  year: number;
  totalDays: number;
}

// ==================== 假期申请定义 ====================

export interface LeaveRequest {
  id: string;
  tenantId?: string;
  accountId: string;
  leaveTypeId: string;
  leaveTypeName?: string;
  startDate: string;
  endDate: string;
  durationDays: number;
  reason?: string;
  status: string;
  reviewerId?: string;
  reviewComment?: string;
  reviewedAt?: string;
  createdAt?: string;
  updatedAt?: string;
  accountName?: string;
}

export interface LeaveRequestCreateData {
  leaveTypeId: string;
  startDate: string;
  endDate: string;
  reason?: string;
}

// ==================== API 方法 ====================

export const attendanceApi = {
  /** 签到 */
  checkIn: (data: CheckInData) =>
    request.post<AttendanceRecord>('/attendance/records/check-in', data),

  /** 签退 */
  checkOut: (data: CheckOutData) =>
    request.post<AttendanceRecord>('/attendance/records/check-out', data),

  /** 我的考勤记录 */
  getMyRecords: (params?: { startDate?: string; endDate?: string; page?: number; pageSize?: number }) =>
    request.get<PageResult<AttendanceRecord>>('/attendance/records/my', { params }),

  /** 每日考勤统计（管理员） */
  getDailyStats: (date: string) =>
    request.get<DailyStat>(`/attendance/records/daily-stats/${date}`),

  /** 全部考勤记录（管理员） */
  getAllRecords: (params?: AttendanceRecordListParams) =>
    request.get<PageResult<AttendanceRecord>>('/attendance/records', { params }),

  /** 导出考勤报表（管理员） */
  exportRecords: (params: { startDate: string; endDate: string; keyword?: string }) => {
    const query = new URLSearchParams();
    query.set('start_date', params.startDate);
    query.set('end_date', params.endDate);
    if (params.keyword) query.set('keyword', params.keyword);
    return `/attendance/records/export?${query.toString()}`;
  },

  // ==================== 班次管理 ====================

  /** 获取班次列表 */
  getShiftList: (params?: { keyword?: string; enabled?: boolean; page?: number; pageSize?: number }) =>
    request.get<PageResult<AttendanceShift>>('/attendance/shifts', { params }),

  /** 获取所有启用班次 */
  getAllShifts: () =>
    request.get<AttendanceShift[]>('/attendance/shifts/all'),

  /** 获取班次详情 */
  getShiftById: (id: string) =>
    request.get<AttendanceShift>(`/attendance/shifts/${id}`),

  /** 创建班次 */
  createShift: (data: AttendanceShiftCreateData) =>
    request.post<AttendanceShift>('/attendance/shifts', data),

  /** 更新班次 */
  updateShift: (id: string, data: AttendanceShiftUpdateData) =>
    request.put<AttendanceShift>(`/attendance/shifts/${id}`, data),

  /** 删除班次 */
  deleteShift: (id: string) =>
    request.delete<void>(`/attendance/shifts/${id}`),

  // ==================== 签到组管理 ====================

  /** 获取签到组列表 */
  getGroupList: (params?: { keyword?: string; page?: number; pageSize?: number }) =>
    request.get<PageResult<AttendanceGroup>>('/attendance/groups', { params }),

  /** 获取签到组详情 */
  getGroupById: (id: string) =>
    request.get<AttendanceGroup>(`/attendance/groups/${id}`),

  /** 创建签到组 */
  createGroup: (data: AttendanceGroupCreateData) =>
    request.post<AttendanceGroup>('/attendance/groups', data),

  /** 更新签到组 */
  updateGroup: (id: string, data: AttendanceGroupUpdateData) =>
    request.put<AttendanceGroup>(`/attendance/groups/${id}`, data),

  /** 删除签到组 */
  deleteGroup: (id: string) =>
    request.delete<void>(`/attendance/groups/${id}`),

  /** 获取签到组成员列表 */
  getGroupMembers: (groupId: string, params?: { page?: number; pageSize?: number }) =>
    request.get<PageResult<GroupMember>>(`/attendance/groups/${groupId}/members`, { params }),

  /** 添加签到组成员 */
  addGroupMembers: (groupId: string, accountIds: string[]) =>
    request.post<{ added: number }>(`/attendance/groups/${groupId}/members`, { accountIds }),

  /** 移除签到组成员 */
  removeGroupMember: (groupId: string, accountId: string) =>
    request.delete<void>(`/attendance/groups/${groupId}/members/${accountId}`),

  // ==================== 考勤规则管理 ====================

  /** 获取考勤规则列表 */
  getRuleList: (params?: { keyword?: string; page?: number; pageSize?: number }) =>
    request.get<PageResult<AttendanceRule>>('/attendance/rules', { params }),

  /** 获取考勤规则详情 */
  getRuleById: (id: string) =>
    request.get<AttendanceRule>(`/attendance/rules/${id}`),

  /** 创建考勤规则 */
  createRule: (data: AttendanceRuleCreateData) =>
    request.post<AttendanceRule>('/attendance/rules', data),

  /** 更新考勤规则 */
  updateRule: (id: string, data: AttendanceRuleUpdateData) =>
    request.put<AttendanceRule>(`/attendance/rules/${id}`, data),

  /** 删除考勤规则 */
  deleteRule: (id: string) =>
    request.delete<void>(`/attendance/rules/${id}`),

  // ==================== 假期类型管理 ====================

  /** 获取假期类型列表 */
  getLeaveTypeList: (params?: { enabled?: boolean; page?: number; pageSize?: number }) =>
    request.get<PageResult<LeaveType>>('/attendance/leave/types', { params }),

  /** 创建假期类型 */
  createLeaveType: (data: LeaveTypeCreateData) =>
    request.post<LeaveType>('/attendance/leave/types', data),

  /** 更新假期类型 */
  updateLeaveType: (id: string, data: LeaveTypeUpdateData) =>
    request.put<LeaveType>(`/attendance/leave/types/${id}`, data),

  /** 删除假期类型 */
  deleteLeaveType: (id: string) =>
    request.delete<void>(`/attendance/leave/types/${id}`),

  // ==================== 假期余额 ====================

  /** 获取假期余额 */
  getLeaveBalances: (accountId: string, year?: number) =>
    request.get<LeaveBalance[]>('/attendance/leave/balances', { params: { accountId, year } }),

  /** 更新假期余额 */
  updateLeaveBalance: (data: LeaveBalanceUpdateData) =>
    request.put<LeaveBalance>('/attendance/leave/balances', data),

  // ==================== 假期申请 ====================

  /** 创建假期申请 */
  createLeaveRequest: (data: LeaveRequestCreateData) =>
    request.post<LeaveRequest>('/attendance/leave/requests', data),

  /** 我的假期申请 */
  getMyLeaveRequests: (params?: { page?: number; pageSize?: number }) =>
    request.get<PageResult<LeaveRequest>>('/attendance/leave/requests/my', { params }),

  /** 所有假期申请（管理员） */
  getAllLeaveRequests: (params?: { keyword?: string; status?: string; page?: number; pageSize?: number }) =>
    request.get<PageResult<LeaveRequest>>('/attendance/leave/requests', { params }),

  /** 审批通过 */
  approveLeaveRequest: (id: string, comment?: string) =>
    request.post<LeaveRequest>(`/attendance/leave/requests/${id}/approve`, { comment }),

  /** 驳回 */
  rejectLeaveRequest: (id: string, comment?: string) =>
    request.post<LeaveRequest>(`/attendance/leave/requests/${id}/reject`, { comment }),
};
