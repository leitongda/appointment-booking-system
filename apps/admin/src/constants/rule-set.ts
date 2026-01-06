/**
 * 规则管理常量配置
 */

// ==================== 时间来源选项 ====================
export const TIME_SOURCE_OPTIONS = [
  { label: '服务端时间', value: 'SERVER' },
  { label: '客户端时间', value: 'CLIENT' },
] as const;

// ==================== 时区来源选项 ====================
export const TIMEZONE_SOURCE_OPTIONS = [
  { label: '医院配置时区', value: 'HOSPITAL' },
  { label: '班次配置时区', value: 'SHIFT' },
  { label: '用户所在时区', value: 'USER' },
] as const;

// ==================== 比较精度选项 ====================
export const COMPARE_PRECISION_OPTIONS = [
  { label: '秒', value: 'SECOND' },
  { label: '毫秒', value: 'MILLISECOND' },
  { label: '分钟', value: 'MINUTE' },
] as const;

// ==================== 舍入模式选项 ====================
export const ROUNDING_MODE_OPTIONS = [
  { label: '不舍入', value: 'NONE' },
  { label: '向下取整到分钟', value: 'FLOOR_TO_MINUTE' },
  { label: '向上取整到分钟', value: 'CEIL_TO_MINUTE' },
] as const;

// ==================== 冲突策略选项 ====================
export const CONFLICT_STRATEGY_OPTIONS = [
  { label: '拒绝', value: 'REJECT' },
  { label: '替换', value: 'REPLACE' },
  { label: '允许', value: 'ALLOW' },
] as const;

// ==================== 签到状态选项 ====================
export const AFTER_GRACE_STATUS_OPTIONS = [
  { label: '迟到', value: 'LATE' },
  { label: '准时', value: 'ON_TIME' },
  { label: '不标记', value: null },
] as const;

// ==================== 未签到处理选项 ====================
export const NO_CHECKIN_AFTER_CLOSE_OPTIONS = [
  { label: '保持预约', value: 'KEEP_BOOKED' },
  { label: '自动取消', value: 'AUTO_CANCEL' },
  { label: '标记为爽约', value: 'ABSENT' },
] as const;

// ==================== 候补递补策略选项 ====================
export const WAITLIST_PROMOTE_POLICY_OPTIONS = [
  { label: '手动', value: 'MANUAL' },
  { label: '自动', value: 'AUTO' },
] as const;

// ==================== 时间窗动作类型选项 ====================
export const WINDOW_ACTION_OPTIONS = [
  { label: '预约', value: 'BOOK' },
  { label: '签到', value: 'CHECKIN' },
  { label: '取消', value: 'CANCEL' },
  { label: '释放', value: 'HOLD_RELEASE' },
] as const;

// ==================== 时间窗参考点选项 ====================
export const WINDOW_REFERENCE_POINT_OPTIONS = [
  { label: '班次开始时间', value: 'SHIFT_START' },
  { label: '班次结束时间', value: 'SHIFT_END' },
  { label: '预约创建时间', value: 'BOOKING_CREATED_AT' },
] as const;

// ==================== 时间窗失败策略选项 ====================
export const WINDOW_FAIL_POLICY_OPTIONS = [
  { label: '拒绝操作', value: 'REJECT' },
  { label: '允许并打标签', value: 'ALLOW_WITH_TAG' },
  { label: '自动进入候补', value: 'AUTO_TO_WAITLIST' },
] as const;

// ==================== 默认值配置 ====================

/**
 * 规则组默认值
 */
export const RULE_SET_DEFAULT_VALUES = {
  enabled: true,
  priority: 100,
  timeSource: 'SERVER' as const,
  timezoneSource: 'HOSPITAL' as const,
  comparePrecision: 'SECOND' as const,
  defaultOpenInclusive: true,
  defaultCloseInclusive: false,
  roundingMode: 'NONE' as const,
  clockSkewToleranceSec: 5,
  description: '',
} as const;

/**
 * 预约策略默认值
 */
export const BOOKING_POLICY_DEFAULT_VALUES = {
  requireAuth: true,
  requirePatientProfileComplete: true,
  perUserPerShift: 1,
  perUserPerDay: 3,
  perUserPerWeek: 10,
  conflictSameShift: 'REJECT' as const,
  conflictOverlapTime: 'REJECT' as const,
  conflictSameTypeSameDay: 'ALLOW' as const,
} as const;

/**
 * 签到策略默认值
 */
export const CHECKIN_POLICY_DEFAULT_VALUES = {
  requireBooking: true,
  allowOnsiteBooking: false,
  maxTimes: 1,
  auditLog: true,
  gracePeriodSec: 900,
  afterGraceStatus: 'LATE' as const,
  noCheckinAfterClose: 'KEEP_BOOKED' as const,
} as const;

/**
 * 容量策略默认值
 */
export const CAPACITY_POLICY_DEFAULT_VALUES = {
  totalCapacity: 50,
  perUserCapacity: 1,
  waitlistEnabled: false,
  waitlistMaxSize: 10,
  waitlistPromotePolicy: 'MANUAL' as const,
  overbookingEnabled: false,
  overbookingMax: 5,
} as const;

/**
 * 时间窗默认值
 */
export const WINDOW_DEFAULT_VALUES = {
  action: 'BOOK' as const,
  referencePoint: 'SHIFT_START' as const,
  openOffsetSec: -86400,
  closeOffsetSec: 0,
  openInclusive: true,
  closeInclusive: false,
  failPolicy: 'REJECT' as const,
  enabled: true,
} as const;

/**
 * 完整的规则组表单初始值
 */
export const RULE_SET_FORM_INITIAL_VALUES = {
  ...RULE_SET_DEFAULT_VALUES,
  bookingPolicy: BOOKING_POLICY_DEFAULT_VALUES,
  checkinPolicy: CHECKIN_POLICY_DEFAULT_VALUES,
  capacityPolicy: CAPACITY_POLICY_DEFAULT_VALUES,
  shiftTypeIds: [],
  windows: [],
} as const;
