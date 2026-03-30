/**
 * 规则管理常量配置
 */

import { ruleSetApi } from '@hospital/api';
import type { RuleSetPresetResponse } from '@hospital/api';

// 预设模板缓存
let _presetsCache: RuleSetPresetResponse[] | null = null;

/**
 * 获取预设模板列表。
 * 优先从后端加载，失败时回退到本地硬编码预设。
 */
export async function fetchPresets(): Promise<RuleSetPresetResponse[]> {
  if (_presetsCache) return _presetsCache;
  try {
    const presets = await ruleSetApi.getPresets();
    _presetsCache = presets;
    return presets;
  } catch {
    // 回退到本地硬编码预设
    return RULE_SET_PRESETS.map((p) => ({
      id: p.id,
      name: p.name,
      description: p.description,
      config: transformConfigToSnakeCase(p.config),
      isSystem: true,
      sortOrder: 0,
    }));
  }
}

/** 清除预设缓存（用于创建/删除预设后刷新） */
export function clearPresetsCache() {
  _presetsCache = null;
}

/** 将前端 camelCase 配置转为后端 snake_case */
function transformConfigToSnakeCase(config: typeof RULE_SET_FORM_INITIAL_VALUES): Record<string, any> {
  return JSON.parse(JSON.stringify(config));
}

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
// 每种动作类型对应不同的业务场景和验证规则
// 用于配置时间窗口限制的操作类型
export const WINDOW_ACTION_OPTIONS = [
  { label: '预约', value: 'BOOK' },           // 创建预约时的时间窗口限制
  { label: '签到', value: 'CHECKIN' },        // 签到操作的时间窗口限制
  { label: '取消', value: 'CANCEL' },         // 取消预约的时间窗口限制
  { label: '释放', value: 'HOLD_RELEASE' },   // 释放占位号的时间窗口限制
] as const;

// ==================== 时间窗参考点选项 ====================
// 参考点用于计算时间窗口的基准时间
// openOffsetSec/closeOffsetSec 是相对于参考点的偏移量
export const WINDOW_REFERENCE_POINT_OPTIONS = [
  { label: '班次开始时间', value: 'SHIFT_START' },         // 以班次开始时间为基准
  { label: '班次结束时间', value: 'SHIFT_END' },           // 以班次结束时间为基准
  { label: '预约创建时间', value: 'BOOKING_CREATED_AT' },  // 以创建预约的时间为基准
] as const;

// ==================== 时间窗失败策略选项 ====================
// 当操作不在时间窗内时的处理方式
export const WINDOW_FAIL_POLICY_OPTIONS = [
  { label: '拒绝操作', value: 'REJECT' },              // 直接拒绝操作，返回错误提示
  { label: '允许并打标签', value: 'ALLOW_WITH_TAG' },  // 允许操作但标记为特殊状态（如迟到预约）
  { label: '自动进入候补', value: 'AUTO_TO_WAITLIST' }, // 自动添加到候补队列
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
  name: '新时间窗',
  action: 'BOOK' as const,
  referencePoint: 'SHIFT_START' as const,
  openOffsetSec: -1800,  // 提前30分钟
  closeOffsetSec: 0,     // 截止偏移为0
  openInclusive: true,
  closeInclusive: false,
  failPolicy: 'REJECT' as const,
  enabled: true,
} as const;

/**
 * 默认时间窗配置 - 满足基本业务规则
 * 1. 预约必须在班次开始时间之前
 * 2. 签到必须在班次结束时间之前
 * 3. 签到不能早于预约时间前30分钟（即预约后30分钟才能签到）
 */
export const DEFAULT_WINDOWS = [
  // 预约时间窗：班次开始前24小时开放，班次开始时关闭（不包含开始时刻）
  {
    name: '预约时间窗',
    action: 'BOOK' as const,
    referencePoint: 'SHIFT_START' as const,
    openOffsetSec: -86400, // 提前24小时
    closeOffsetSec: 0,     // 班次开始时
    openInclusive: true,
    closeInclusive: false, // 不包含班次开始时刻
    failPolicy: 'REJECT' as const,
    enabled: true,
  },
  // 签到时间窗1：预约后30分钟才能签到（防止过早签到）
  {
    name: '签到时间窗（预约后）',
    action: 'CHECKIN' as const,
    referencePoint: 'BOOKING_CREATED_AT' as const,
    openOffsetSec: 1800,   // 预约后30分钟才能签到
    closeOffsetSec: null,  // 不限制最晚时间
    openInclusive: true,
    closeInclusive: false,
    failPolicy: 'REJECT' as const,
    enabled: true,
  },
  // 签到时间窗2：必须在班次结束时间前签到
  {
    name: '签到时间窗（班次结束前）',
    action: 'CHECKIN' as const,
    referencePoint: 'SHIFT_END' as const,
    openOffsetSec: null,   // 不限制最早时间
    closeOffsetSec: 0,     // 班次结束时
    openInclusive: true,
    closeInclusive: true,  // 包含班次结束时刻
    failPolicy: 'REJECT' as const,
    enabled: true,
  },
] as const;

/**
 * 完整的规则组表单初始值
 */
export const RULE_SET_FORM_INITIAL_VALUES = {
  ...RULE_SET_DEFAULT_VALUES,
  bookingPolicy: BOOKING_POLICY_DEFAULT_VALUES,
  checkinPolicy: CHECKIN_POLICY_DEFAULT_VALUES,
  capacityPolicy: CAPACITY_POLICY_DEFAULT_VALUES,
  shiftTypeIds: [],
  windows: DEFAULT_WINDOWS,
} as const;

// ==================== 预设模板 ====================

/**
 * 预设模板类型
 */
export interface RuleSetPreset {
  id: string;
  name: string;
  description: string;
  config: typeof RULE_SET_FORM_INITIAL_VALUES;
}

/**
 * 标准门诊预设
 * 适用于普通门诊，宽松的预约限制
 */
export const PRESET_STANDARD_CLINIC: RuleSetPreset = {
  id: 'standard-clinic',
  name: '标准门诊',
  description: '适用于普通门诊，提前7天开放预约，每日可预约3次',
  config: {
    name: '标准门诊规则',
    enabled: true,
    priority: 100,
    timeSource: 'SERVER',
    timezoneSource: 'HOSPITAL',
    comparePrecision: 'MINUTE',
    defaultOpenInclusive: true,
    defaultCloseInclusive: false,
    roundingMode: 'NONE',
    clockSkewToleranceSec: 5,
    description: '适用于普通门诊的预约规则',
    shiftTypeIds: [],
    bookingPolicy: {
      requireAuth: true,
      requirePatientProfileComplete: false,
      perUserPerShift: 1,
      perUserPerDay: 3,
      perUserPerWeek: 10,
      conflictSameShift: 'REJECT',
      conflictOverlapTime: 'REJECT',
      conflictSameTypeSameDay: 'ALLOW',
    },
    checkinPolicy: {
      requireBooking: true,
      allowOnsiteBooking: false,
      maxTimes: 1,
      auditLog: true,
      gracePeriodSec: 900, // 15分钟宽限期
      afterGraceStatus: 'LATE',
      noCheckinAfterClose: 'KEEP_BOOKED',
    },
    capacityPolicy: {
      totalCapacity: 30,
      perUserCapacity: 1,
      waitlistEnabled: false,
      waitlistMaxSize: 10,
      waitlistPromotePolicy: 'MANUAL',
      overbookingEnabled: false,
      overbookingMax: 0,
    },
    windows: [
      {
        name: '预约时间窗',
        action: 'BOOK' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -604800, // 提前7天
        closeOffsetSec: 0,
        openInclusive: true,
        closeInclusive: false,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
      {
        name: '签到时间窗',
        action: 'CHECKIN' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -1800, // 班次开始前30分钟
        closeOffsetSec: 3600, // 班次开始后1小时
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
      {
        name: '取消时间窗',
        action: 'CANCEL' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -604800, // 提前7天
        closeOffsetSec: -7200, // 班次开始前2小时
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
    ],
  },
};

/**
 * 专家门诊预设
 * 适用于专家门诊，限制更严格
 */
export const PRESET_EXPERT_CLINIC: RuleSetPreset = {
  id: 'expert-clinic',
  name: '专家门诊',
  description: '适用于专家门诊，需完善档案，每日限约1次，支持候补',
  config: {
    name: '专家门诊规则',
    enabled: true,
    priority: 50,
    timeSource: 'SERVER',
    timezoneSource: 'HOSPITAL',
    comparePrecision: 'MINUTE',
    defaultOpenInclusive: true,
    defaultCloseInclusive: false,
    roundingMode: 'NONE',
    clockSkewToleranceSec: 5,
    description: '适用于专家门诊的预约规则，限制较严格',
    shiftTypeIds: [],
    bookingPolicy: {
      requireAuth: true,
      requirePatientProfileComplete: true, // 需要完善档案
      perUserPerShift: 1,
      perUserPerDay: 1, // 每日限约1次
      perUserPerWeek: 3,
      conflictSameShift: 'REJECT',
      conflictOverlapTime: 'REJECT',
      conflictSameTypeSameDay: 'REJECT', // 同类型同日不可重复预约
    },
    checkinPolicy: {
      requireBooking: true,
      allowOnsiteBooking: false,
      maxTimes: 1,
      auditLog: true,
      gracePeriodSec: 600, // 10分钟宽限期
      afterGraceStatus: 'LATE',
      noCheckinAfterClose: 'ABSENT', // 未签到标记爽约
    },
    capacityPolicy: {
      totalCapacity: 15, // 较少号源
      perUserCapacity: 1,
      waitlistEnabled: true, // 启用候补
      waitlistMaxSize: 5,
      waitlistPromotePolicy: 'AUTO',
      overbookingEnabled: false,
      overbookingMax: 0,
    },
    windows: [
      {
        name: '预约时间窗',
        action: 'BOOK' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -259200, // 提前3天
        closeOffsetSec: -3600, // 班次开始前1小时截止
        openInclusive: true,
        closeInclusive: false,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
      {
        name: '签到时间窗',
        action: 'CHECKIN' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -1800, // 班次开始前30分钟
        closeOffsetSec: 1800, // 班次开始后30分钟
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
      {
        name: '取消时间窗',
        action: 'CANCEL' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -259200, // 提前3天
        closeOffsetSec: -14400, // 班次开始前4小时
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
    ],
  },
};

/**
 * 体检预设
 * 适用于体检预约，需要提前预约
 */
export const PRESET_HEALTH_CHECK: RuleSetPreset = {
  id: 'health-check',
  name: '体检预约',
  description: '适用于体检中心，需提前1天预约，可超额预订',
  config: {
    name: '体检预约规则',
    enabled: true,
    priority: 80,
    timeSource: 'SERVER',
    timezoneSource: 'HOSPITAL',
    comparePrecision: 'MINUTE',
    defaultOpenInclusive: true,
    defaultCloseInclusive: false,
    roundingMode: 'NONE',
    clockSkewToleranceSec: 5,
    description: '适用于体检中心的预约规则',
    shiftTypeIds: [],
    bookingPolicy: {
      requireAuth: true,
      requirePatientProfileComplete: true, // 体检需要完整档案
      perUserPerShift: 1,
      perUserPerDay: 1,
      perUserPerWeek: 1, // 每周限约1次
      conflictSameShift: 'REJECT',
      conflictOverlapTime: 'REJECT',
      conflictSameTypeSameDay: 'REJECT',
    },
    checkinPolicy: {
      requireBooking: true,
      allowOnsiteBooking: false,
      maxTimes: 1,
      auditLog: true,
      gracePeriodSec: 1800, // 30分钟宽限期
      afterGraceStatus: 'LATE',
      noCheckinAfterClose: 'KEEP_BOOKED',
    },
    capacityPolicy: {
      totalCapacity: 50,
      perUserCapacity: 1,
      waitlistEnabled: false, // 体检场景按批次进行，超额机制更合适，候补与超额不并用
      waitlistMaxSize: 0,
      waitlistPromotePolicy: 'MANUAL',
      overbookingEnabled: true, // 允许超额
      overbookingMax: 5,
    },
    windows: [
      {
        name: '预约时间窗',
        action: 'BOOK' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -2592000, // 提前30天
        closeOffsetSec: -86400, // 班次开始前1天截止
        openInclusive: true,
        closeInclusive: false,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
      {
        name: '签到时间窗',
        action: 'CHECKIN' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -3600, // 班次开始前1小时
        closeOffsetSec: 7200, // 班次开始后2小时
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
      {
        name: '取消时间窗',
        action: 'CANCEL' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -2592000, // 提前30天
        closeOffsetSec: -172800, // 班次开始前2天
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'REJECT' as const,
        enabled: true,
      },
    ],
  },
};

/**
 * 急诊预设
 * 适用于急诊，宽松的限制，允许现场预约
 */
export const PRESET_EMERGENCY: RuleSetPreset = {
  id: 'emergency',
  name: '急诊',
  description: '适用于急诊，不限制预约次数，允许现场预约',
  config: {
    name: '急诊规则',
    enabled: true,
    priority: 10, // 高优先级
    timeSource: 'SERVER',
    timezoneSource: 'HOSPITAL',
    comparePrecision: 'MINUTE',
    defaultOpenInclusive: true,
    defaultCloseInclusive: true,
    roundingMode: 'NONE',
    clockSkewToleranceSec: 10,
    description: '适用于急诊的预约规则，限制最宽松',
    shiftTypeIds: [],
    bookingPolicy: {
      requireAuth: true,
      requirePatientProfileComplete: false,
      perUserPerShift: 3,
      perUserPerDay: 0, // 不限制
      perUserPerWeek: 0, // 不限制
      conflictSameShift: 'ALLOW',
      conflictOverlapTime: 'ALLOW',
      conflictSameTypeSameDay: 'ALLOW',
    },
    checkinPolicy: {
      requireBooking: false, // 不强制预约
      allowOnsiteBooking: true, // 允许现场预约
      maxTimes: 3,
      auditLog: true,
      gracePeriodSec: 3600, // 1小时宽限期
      afterGraceStatus: 'ON_TIME', // 不标记迟到
      noCheckinAfterClose: 'KEEP_BOOKED',
    },
    capacityPolicy: {
      totalCapacity: 0, // 不限制
      perUserCapacity: 3,
      waitlistEnabled: false,
      waitlistMaxSize: 0,
      waitlistPromotePolicy: 'MANUAL',
      overbookingEnabled: false, // 总容量为0（不限制）时超额无意义
      overbookingMax: 0,
    },
    windows: [
      {
        name: '预约时间窗',
        action: 'BOOK' as const,
        referencePoint: 'SHIFT_START' as const,
        openOffsetSec: -86400, // 提前1天
        closeOffsetSec: 7200, // 班次开始后2小时仍可预约
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'ALLOW_WITH_TAG' as const, // 超时允许但打标签
        failTag: '紧急预约',
        enabled: true,
      },
      {
        name: '签到时间窗',
        action: 'CHECKIN' as const,
        referencePoint: 'SHIFT_END' as const,
        openOffsetSec: -86400, // 不限制开始时间
        closeOffsetSec: 0, // 班次结束前
        openInclusive: true,
        closeInclusive: true,
        failPolicy: 'ALLOW_WITH_TAG' as const,
        failTag: '超时签到',
        enabled: true,
      },
    ],
  },
};

/**
 * 所有预设模板列表
 */
export const RULE_SET_PRESETS: RuleSetPreset[] = [
  PRESET_STANDARD_CLINIC,
  PRESET_EXPERT_CLINIC,
  PRESET_HEALTH_CHECK,
  PRESET_EMERGENCY,
];

// ==================== 可视化组件共享常量 ====================

/**
 * 动作类型颜色配置（统一版）
 * 各组件按需使用 primary/light/background/border/label 字段
 */
export const ACTION_COLORS = {
  BOOK: {
    primary: '#1890ff',
    light: '#e6f7ff',
    background: 'rgba(24, 144, 255, 0.2)',
    border: '#1890ff',
    label: '预约',
  },
  CHECKIN: {
    primary: '#52c41a',
    light: '#f6ffed',
    background: 'rgba(82, 196, 26, 0.2)',
    border: '#52c41a',
    label: '签到',
  },
  CANCEL: {
    primary: '#fa8c16',
    light: '#fff7e6',
    background: 'rgba(250, 140, 22, 0.2)',
    border: '#fa8c16',
    label: '取消',
  },
  HOLD_RELEASE: {
    primary: '#722ed1',
    light: '#f9f0ff',
    background: 'rgba(114, 46, 209, 0.2)',
    border: '#722ed1',
    label: '释放',
  },
} as const;

/**
 * 参考点标签映射
 */
export const REFERENCE_POINT_LABELS: Record<string, string> = {
  SHIFT_START: '班次开始时间',
  SHIFT_END: '班次结束时间',
  BOOKING_CREATED_AT: '预约创建时间',
};

/**
 * 判断偏移量是否为"不限制"
 * null 或非有限数字均视为不限制
 */
export const isUnlimitedOffset = (offset: number | null | undefined): boolean => {
  return offset == null || (typeof offset === 'number' && !isFinite(offset));
};
