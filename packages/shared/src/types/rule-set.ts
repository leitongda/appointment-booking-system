/**
 * 规则管理系统类型定义
 */

/**
 * 班次类型
 */
export interface ShiftType {
  id: string;
  code: string;  // OPD/CHECKUP/EXAM/NURSING/SPECIAL
  name: string;
  description?: string;
  enabled: boolean;
  createdAt: string;
  updatedAt?: string;
}

/**
 * 规则组
 */
export interface RuleSet {
  id: string;
  name: string;
  enabled: boolean;
  priority: number;
  // 默认口径
  timeSource: 'SERVER' | 'CLIENT';
  timezoneSource: 'HOSPITAL' | 'SHIFT' | 'USER';
  comparePrecision: 'SECOND' | 'MILLISECOND' | 'MINUTE';
  defaultOpenInclusive: boolean;
  defaultCloseInclusive: boolean;
  roundingMode: 'NONE' | 'FLOOR_TO_MINUTE' | 'CEIL_TO_MINUTE';
  clockSkewToleranceSec: number;
  description?: string;
  storeId?: string;
  storeName?: string;
  departmentId?: string;
  departmentName?: string;
  doctorId?: string;
  doctorName?: string;
  // 生效状态
  isActive?: boolean;  // 是否为实际生效的规则组（优先级最高的启用规则）
  // 关联数据
  shiftTypes?: ShiftType[];
  windows?: RuleWindow[];
  bookingPolicy?: RuleBookingPolicy;
  checkinPolicy?: RuleCheckinPolicy;
  capacityPolicy?: RuleCapacityPolicy;
  scheduleTemplates?: ScheduleTemplateBrief[];
  createdAt: string;
  updatedAt?: string;
}

/**
 * 排班模板简要信息（用于规则组关联展示）
 */
export interface ScheduleTemplateBrief {
  id: string;
  name?: string;
  doctorName?: string;
  departmentName?: string;
  storeName?: string;
  shiftTypeName?: string;
  status?: number;
}

/**
 * 时间窗配置
 */
export interface RuleWindow {
  id: string;
  ruleSetId: string;
  action: 'BOOK' | 'CHECKIN' | 'CANCEL' | 'HOLD_RELEASE';
  referencePoint: 'SHIFT_START' | 'SHIFT_END' | 'BOOKING_CREATED_AT';
  openOffsetSec: number | null;  // null 表示不限制
  closeOffsetSec: number | null;  // null 表示不限制
  openInclusive?: boolean | null;
  closeInclusive?: boolean | null;
  failPolicy: 'REJECT' | 'ALLOW_WITH_TAG' | 'AUTO_TO_WAITLIST';
  failTag?: string | null;
  enabled: boolean;
  description?: string;
  createdAt: string;
  updatedAt?: string;
}

/**
 * 预约策略
 */
export interface RuleBookingPolicy {
  ruleSetId: string;
  requireAuth: boolean;
  requirePatientProfileComplete: boolean;
  perUserPerShift: number;
  perUserPerDay?: number | null;
  perUserPerWeek?: number | null;
  conflictSameShift: 'REJECT' | 'REPLACE';
  conflictOverlapTime: 'REJECT' | 'ALLOW';
  conflictSameTypeSameDay: 'REJECT' | 'ALLOW';
  createdAt: string;
  updatedAt?: string;
}

/**
 * 签到策略
 */
export interface RuleCheckinPolicy {
  ruleSetId: string;
  requireBooking: boolean;
  allowOnsiteBooking: boolean;
  maxTimes: number;
  auditLog: boolean;
  gracePeriodSec: number;
  afterGraceStatus?: 'LATE' | 'ON_TIME' | null;
  noCheckinAfterClose: 'KEEP_BOOKED' | 'AUTO_CANCEL' | 'ABSENT';
  createdAt: string;
  updatedAt?: string;
}

/**
 * 容量策略
 */
export interface RuleCapacityPolicy {
  ruleSetId: string;
  totalCapacity: number;
  perUserCapacity: number;
  waitlistEnabled: boolean;
  waitlistMaxSize: number;
  waitlistPromotePolicy: 'MANUAL' | 'AUTO';
  overbookingEnabled: boolean;
  overbookingMax: number;
  createdAt: string;
  updatedAt?: string;
}

/**
 * 规则预览请求
 */
export interface RulePreviewRequest {
  shiftTypeId: string;
  scheduleDate: string;  // YYYY-MM-DD
  startTime: string;     // HH:mm:ss
  endTime: string;       // HH:mm:ss
  currentTime?: string;  // ISO datetime string
}

/**
 * 规则预览响应 - 窗口检查结果
 */
export interface WindowCheckResult {
  allowed: boolean;
  openAt: string;
  closeAt: string;
  currentTime: string;
  failPolicy: string;
  failTag?: string | null;
  message: string;
}

/**
 * 规则组简要信息（用于预览匹配结果）
 */
export interface RuleSetBrief {
  id: string;
  name: string;
  priority: number;
  enabled: boolean;
}

/**
 * 规则预览响应
 */
export interface RulePreviewResponse {
  bookWindow: WindowCheckResult;
  checkinWindow: WindowCheckResult;
  cancelWindow: WindowCheckResult;
  matchedRuleSet: RuleSetBrief | null;
  candidateRuleSets: RuleSetBrief[];
}

/**
 * 时间窗偏移量配置（用于表单）
 */
export interface WindowOffsetConfig {
  value: number;
  unit: 'second' | 'minute' | 'hour' | 'day';
  direction: 'before' | 'after';  // 提前/延后
}

/**
 * 规则组审计日志
 */
export interface RuleSetAuditLog {
  id: string;
  ruleSetId: string;
  action: 'CREATE' | 'UPDATE' | 'DELETE' | 'ENABLE' | 'DISABLE';
  resourceType: string;
  resourceId: string;
  operatorId?: string;
  snapshotBefore?: string;
  snapshotAfter?: string;
  changes?: string;
  createdAt: string;
}
