/**
 * 排班模块设计 token -- 统一管理所有颜色常量
 *
 * 与 global.less 中的 Less 变量 / CSS custom properties 保持同步。
 * TSX 中的 inline style 和图表配置优先使用此文件导出的常量。
 */

// ── 排班状态颜色 ──────────────────────────────────────────────
export const SCHEDULE_STATUS_ACTIVE = '#1677ff'; // 正常/可预约 (antd primary)
export const SCHEDULE_STATUS_SUSPENDED = '#ff4d4f'; // 停诊 (antd error)
export const SCHEDULE_STATUS_FULL = '#fa8c16'; // 已满 (antd warning)
export const SCHEDULE_STATUS_DRAFT = '#8c8c8c'; // 草稿 (antd text tertiary)
export const SCHEDULE_STATUS_HOLIDAY = '#722ed1'; // 节假日 (antd purple)
export const SCHEDULE_STATUS_FINISHED = '#d9d9d9'; // 已过期 (antd disabled)

// ── 预约状态颜色 ──────────────────────────────────────────────
export const APPOINTMENT_PENDING = '#faad14'; // 待确认
export const APPOINTMENT_CONFIRMED = '#1677ff'; // 已确认
export const APPOINTMENT_CANCELLED = '#ff4d4f'; // 已取消
export const APPOINTMENT_COMPLETED = '#52c41a'; // 已完成

// ── 甘特图时段颜色 ────────────────────────────────────────────
export const GANTT_MORNING = '#1677ff'; // 上午 (原 #1890ff)
export const GANTT_AFTERNOON = '#52c41a'; // 下午
export const GANTT_EVENING = '#722ed1'; // 晚上
export const GANTT_UNKNOWN = '#8c8c8c'; // 未知时段

// ── 日历状态颜色 ──────────────────────────────────────────────
export const CALENDAR_AVAILABLE = '#4CAF50'; // 可预约 (绿色)
export const CALENDAR_BOOKED = '#1677ff'; // 已预约 (原 #2196F3)
export const CALENDAR_FULL = '#F44336'; // 已满
export const CALENDAR_SUSPENDED = '#9E9E9E'; // 已停诊
export const CALENDAR_REST_DAY = '#fa8c16'; // 休息日
export const CALENDAR_OVERRIDDEN = '#b0b0b0'; // 被覆盖

// ── 通用颜色 ──────────────────────────────────────────────────
export const TEXT_SECONDARY = '#8c8c8c'; // 次要文字 (原 #999)
export const TEXT_TERTIARY = '#666'; // 三级文字
export const BORDER_COLOR = '#f0f0f0'; // 边框色
export const BORDER_LIGHT = '#e8e8e8'; // 浅边框
export const BG_LIGHT = '#fafafa'; // 浅背景
export const BG_HOVER = '#f5f5f5'; // 悬停背景
export const COLOR_DISABLED = '#d9d9d9'; // 禁用/已过期 (原 #ccc)
export const COLOR_DANGER = '#ff4d4f'; // 危险/删除
export const COLOR_SUCCESS = '#52c41a'; // 成功
export const COLOR_WARNING = '#fa8c16'; // 警告

// ── 时间窗操作颜色 ────────────────────────────────────────────
/** 时间窗颜色配置类型 */
export interface WindowColorConfig {
  fill: string;
  stroke: string;
  label: string;
  gradientStart: string;
  gradientEnd: string;
  unlimitedPattern?: string;
}

/** 时间窗操作颜色 (统一 antd 色系) */
export const WINDOW_ACTION_COLORS: Record<string, WindowColorConfig> = {
  BOOK: {
    fill: 'rgba(24, 144, 255, 0.2)',
    stroke: '#1890ff',
    label: '预约',
    gradientStart: 'rgba(24, 144, 255, 0.4)',
    gradientEnd: 'rgba(24, 144, 255, 0.1)',
    unlimitedPattern: 'rgba(24, 144, 255, 0.08)',
  },
  CHECKIN: {
    fill: 'rgba(82, 196, 26, 0.2)',
    stroke: '#52c41a',
    label: '签到',
    gradientStart: 'rgba(82, 196, 26, 0.4)',
    gradientEnd: 'rgba(82, 196, 26, 0.1)',
    unlimitedPattern: 'rgba(82, 196, 26, 0.08)',
  },
  CANCEL: {
    fill: 'rgba(250, 140, 22, 0.2)',
    stroke: '#fa8c16',
    label: '取消',
    gradientStart: 'rgba(250, 140, 22, 0.4)',
    gradientEnd: 'rgba(250, 140, 22, 0.1)',
    unlimitedPattern: 'rgba(250, 140, 22, 0.08)',
  },
  HOLD_RELEASE: {
    fill: 'rgba(114, 46, 209, 0.2)',
    stroke: '#722ed1',
    label: '释放',
    gradientStart: 'rgba(114, 46, 209, 0.4)',
    gradientEnd: 'rgba(114, 46, 209, 0.1)',
    unlimitedPattern: 'rgba(114, 46, 209, 0.08)',
  },
};
