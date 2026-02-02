/**
 * 规则组格式化工具函数
 * 用于将规则配置转换为易读的可视化展示
 */

import type { RuleSet, RuleWindow, ShiftType } from '@hospital/shared';
import dayjs from 'dayjs';

// ==================== 类型定义 ====================

/**
 * 动作类型标签映射
 */
const ACTION_LABELS: Record<string, string> = {
  BOOK: '预约',
  CHECKIN: '签到',
  CANCEL: '取消',
  HOLD_RELEASE: '释放',
};

/**
 * 参考点标签映射
 */
const REFERENCE_POINT_LABELS: Record<string, string> = {
  SHIFT_START: '班次开始时间',
  SHIFT_END: '班次结束时间',
  BOOKING_CREATED_AT: '预约创建时间',
};

/**
 * 时间窗分组结果
 */
export interface GroupedWindows {
  book: RuleWindow[];
  checkin: RuleWindow[];
  cancel: RuleWindow[];
  holdRelease: RuleWindow[];
}

/**
 * 关键时间点
 */
export interface KeyTimes {
  bookOpen?: Date;
  bookClose?: Date;
  checkinOpen?: Date;
  checkinClose?: Date;
  cancelOpen?: Date;
  cancelClose?: Date;
}

/**
 * 时间轴范围
 */
export interface TimelineRange {
  min: Date;
  max: Date;
}

/**
 * 时间刻度
 */
export interface TimeTick {
  time: Date;
  position: number; // 0-1 之间的比例位置
  label: string;
}

// ==================== 格式化函数 ====================

/**
 * 将秒数转换为可读格式
 * @param seconds 秒数，null 表示不限制
 * @param referencePoint 参考点类型（可选，用于更精确的描述）
 * @returns 可读的时间偏移描述
 *
 * @example
 * formatOffset(3600) // "延后1小时"
 * formatOffset(-86400) // "提前24小时"
 * formatOffset(90) // "延后1分钟30秒"
 * formatOffset(null) // "不限制"
 */
export function formatOffset(seconds: number | null, referencePoint?: string): string {
  if (seconds === null) return '不限制';

  const abs = Math.abs(seconds);
  const hours = Math.floor(abs / 3600);
  const minutes = Math.floor((abs % 3600) / 60);
  const secs = abs % 60;

  const parts: string[] = [];
  if (hours > 0) parts.push(`${hours}小时`);
  if (minutes > 0) parts.push(`${minutes}分钟`);
  if (secs > 0) parts.push(`${secs}秒`);

  // 如果没有任何部分（比如秒数为0），返回"延后0秒"
  const str = parts.length > 0 ? parts.join('') : '0秒';
  return seconds >= 0 ? `延后${str}` : `提前${str}`;
}

/**
 * 格式化时间戳为可读格式
 * @param date 日期对象
 * @param format 格式字符串，默认 'YYYY-MM-DD HH:mm:ss'
 */
export function formatTime(date: Date, format: string = 'YYYY-MM-DD HH:mm:ss'): string {
  if (!date) return '无效时间';
  const dj = dayjs(date);
  if (!dj.isValid()) return '无效时间';
  return dj.format(format);
}

/**
 * 格式化时间段
 * @param start 开始时间
 * @param end 结束时间
 */
export function formatTimeRange(start: Date, end: Date): string {
  return `${formatTime(start, 'HH:mm:ss')} - ${formatTime(end, 'HH:mm:ss')}`;
}

// ==================== 计算函数 ====================

/**
 * 计算窗口的实际时间
 * @param referencePoint 参考点类型
 * @param offsetSec 偏移秒数
 * @param baseShiftStart 班次开始时间
 * @param baseShiftEnd 班次结束时间
 * @param bookingCreatedAt 预约创建时间（仅当参考点为 BOOKING_CREATED_AT 时使用）
 */
export function calculateWindowTime(
  referencePoint: string,
  offsetSec: number | null,
  baseShiftStart: Date,
  baseShiftEnd: Date,
  bookingCreatedAt?: Date
): Date | null {
  if (offsetSec === null) return null;

  // 确保 offsetSec 是有效数字
  if (typeof offsetSec !== 'number' || !isFinite(offsetSec)) {
    console.warn('Invalid offsetSec:', offsetSec);
    return null;
  }

  let baseTime: dayjs.Dayjs;

  switch (referencePoint) {
    case 'SHIFT_START':
      baseTime = dayjs(baseShiftStart);
      break;
    case 'SHIFT_END':
      baseTime = dayjs(baseShiftEnd);
      break;
    case 'BOOKING_CREATED_AT':
      baseTime = bookingCreatedAt ? dayjs(bookingCreatedAt) : dayjs();
      break;
    default:
      baseTime = dayjs();
  }

  // 检查 baseTime 是否有效
  if (!baseTime.isValid()) {
    console.warn('Invalid baseTime for referencePoint:', referencePoint);
    return null;
  }

  const result = baseTime.add(offsetSec, 'second');

  // 检查结果是否有效
  if (!result.isValid()) {
    console.warn('Invalid calculated time:', { referencePoint, offsetSec, baseTime: baseTime.toISOString() });
    return null;
  }

  return result.toDate();
}

/**
 * 计算所有关键时间点
 * @param ruleSet 规则组配置
 * @param baseShiftStart 班次开始时间
 * @param baseShiftEnd 班次结束时间
 * @param bookingCreatedAt 预约创建时间（可选）
 */
export function calculateKeyTimes(
  ruleSet: Partial<RuleSet>,
  baseShiftStart: Date,
  baseShiftEnd: Date,
  bookingCreatedAt?: Date
): KeyTimes {
  const result: KeyTimes = {};
  const windows = ruleSet.windows || [];

  windows.forEach((window) => {
    if (!window.enabled) return;

    const openTime = calculateWindowTime(
      window.referencePoint,
      window.openOffsetSec,
      baseShiftStart,
      baseShiftEnd,
      bookingCreatedAt
    );
    const closeTime = calculateWindowTime(
      window.referencePoint,
      window.closeOffsetSec,
      baseShiftStart,
      baseShiftEnd,
      bookingCreatedAt
    );

    switch (window.action) {
      case 'BOOK':
        if (openTime) result.bookOpen = openTime;
        if (closeTime) result.bookClose = closeTime;
        break;
      case 'CHECKIN':
        if (openTime) result.checkinOpen = openTime;
        if (closeTime) result.checkinClose = closeTime;
        break;
      case 'CANCEL':
        if (openTime) result.cancelOpen = openTime;
        if (closeTime) result.cancelClose = closeTime;
        break;
    }
  });

  return result;
}

/**
 * 按动作类型分组时间窗
 * @param windows 时间窗列表
 */
export function groupWindowsByAction(windows: RuleWindow[]): GroupedWindows {
  return windows.reduce<GroupedWindows>(
    (acc, window) => {
      if (!window.enabled) return acc;

      switch (window.action) {
        case 'BOOK':
          acc.book.push(window);
          break;
        case 'CHECKIN':
          acc.checkin.push(window);
          break;
        case 'CANCEL':
          acc.cancel.push(window);
          break;
        case 'HOLD_RELEASE':
          acc.holdRelease.push(window);
          break;
      }
      return acc;
    },
    { book: [], checkin: [], cancel: [], holdRelease: [] }
  );
}

// ==================== 摘要生成函数 ====================

/**
 * 生成单个时间窗的摘要文本
 * @param window 时间窗配置
 */
function generateWindowSummary(window: RuleWindow): string {
  const actionLabel = ACTION_LABELS[window.action] || window.action;
  const refPointLabel = REFERENCE_POINT_LABELS[window.referencePoint] || window.referencePoint;

  const openOffset = formatOffset(window.openOffsetSec);
  const closeOffset = formatOffset(window.closeOffsetSec);

  return `${actionLabel}：基于${refPointLabel}，${openOffset}开放，${closeOffset}截止`;
}

/**
 * 生成预约策略摘要
 */
function generateBookingPolicySummary(ruleSet: Partial<RuleSet>): string[] {
  const summaries: string[] = [];
  const policy = ruleSet.bookingPolicy;

  if (!policy) return summaries;

  if (policy.requireAuth) {
    summaries.push('• 需要登录');
  }
  if (policy.requirePatientProfileComplete) {
    summaries.push('• 需要完善就诊人档案');
  }

  const limits: string[] = [];
  if (policy.perUserPerShift) {
    limits.push(`每班次限约${policy.perUserPerShift}次`);
  }
  if (policy.perUserPerDay) {
    limits.push(`每天限约${policy.perUserPerDay}次`);
  }
  if (policy.perUserPerWeek) {
    limits.push(`每周限约${policy.perUserPerWeek}次`);
  }
  if (limits.length > 0) {
    summaries.push(`• ${limits.join('，')}`);
  }

  return summaries;
}

/**
 * 生成签到策略摘要
 */
function generateCheckinPolicySummary(ruleSet: Partial<RuleSet>): string[] {
  const summaries: string[] = [];
  const policy = ruleSet.checkinPolicy;

  if (!policy) return summaries;

  if (policy.requireBooking) {
    summaries.push('• 必须先预约才能签到');
  }
  if (policy.allowOnsiteBooking) {
    summaries.push('• 允许现场预约');
  }

  if (policy.gracePeriodSec) {
    const gracePeriod = formatOffset(policy.gracePeriodSec);
    summaries.push(`• 允许迟到${gracePeriod}（宽限期）`);
  }

  const noCheckinLabels: Record<string, string> = {
    KEEP_BOOKED: '保持预约',
    AUTO_CANCEL: '自动取消',
    ABSENT: '标记为爽约',
  };
  if (policy.noCheckinAfterClose) {
    summaries.push(`• 超时未签到：${noCheckinLabels[policy.noCheckinAfterClose] || policy.noCheckinAfterClose}`);
  }

  return summaries;
}

/**
 * 生成容量策略摘要
 */
function generateCapacityPolicySummary(ruleSet: Partial<RuleSet>): string[] {
  const summaries: string[] = [];
  const policy = ruleSet.capacityPolicy;

  if (!policy) return summaries;

  summaries.push(`• 总容量：${policy.totalCapacity}人`);
  if (policy.perUserCapacity) {
    summaries.push(`• 每人限约：${policy.perUserCapacity}个`);
  }

  if (policy.waitlistEnabled) {
    summaries.push(`• 启用候补：队列大小${policy.waitlistMaxSize}`);
  }
  if (policy.overbookingEnabled) {
    summaries.push(`• 允许超额预约：最多${policy.overbookingMax}人`);
  }

  return summaries;
}

/**
 * 生成规则组的完整摘要
 * @param ruleSet 规则组配置
 * @returns 结构化的摘要文本
 */
export function generateRuleSummary(ruleSet: Partial<RuleSet>): {
  basic: string[];
  windows: string[];
  policies: {
    booking?: string[];
    checkin?: string[];
    capacity?: string[];
  };
} {
  const summary = {
    basic: [] as string[],
    windows: [] as string[],
    policies: {
      booking: undefined as string[] | undefined,
      checkin: undefined as string[] | undefined,
      capacity: undefined as string[] | undefined,
    },
  };

  // 基础信息
  if (ruleSet.name) {
    summary.basic.push(`规则组：${ruleSet.name}`);
  }
  if (ruleSet.priority) {
    summary.basic.push(`优先级：${ruleSet.priority}`);
  }
  if (ruleSet.shiftTypes && ruleSet.shiftTypes.length > 0) {
    const shiftTypeNames = ruleSet.shiftTypes.map((st) => st.name).join('、');
    summary.basic.push(`适用班次：${shiftTypeNames}`);
  }

  // 时间窗摘要
  const windows = ruleSet.windows || [];
  windows.forEach((window) => {
    if (window.enabled) {
      summary.windows.push(generateWindowSummary(window));
    }
  });

  // 策略摘要
  summary.policies.booking = generateBookingPolicySummary(ruleSet);
  summary.policies.checkin = generateCheckinPolicySummary(ruleSet);
  summary.policies.capacity = generateCapacityPolicySummary(ruleSet);

  return summary;
}

/**
 * 生成单行简短摘要（用于卡片展示）
 * @param ruleSet 规则组配置
 */
export function generateShortSummary(ruleSet: Partial<RuleSet>): string {
  const parts: string[] = [];

  // 从预约时间窗提取关键信息
  const bookWindows = (ruleSet.windows || []).filter(
    (w) => w.action === 'BOOK' && w.enabled
  );
  if (bookWindows.length > 0) {
    const window = bookWindows[0];
    const closeOffset = formatOffset(window.closeOffsetSec);
    parts.push(`需${closeOffset}预约`);
  }

  // 从签到策略提取宽限期信息
  if (ruleSet.checkinPolicy?.gracePeriodSec) {
    const gracePeriod = formatOffset(ruleSet.checkinPolicy.gracePeriodSec);
    parts.push(`迟到${gracePeriod}内可签到`);
  }

  // 从预约策略提取限约信息
  if (ruleSet.bookingPolicy?.perUserPerShift) {
    parts.push(`每班次限约${ruleSet.bookingPolicy.perUserPerShift}次`);
  }

  return parts.length > 0 ? parts.join('，') : '暂无配置';
}

// ==================== 时间轴计算函数 ====================

/**
 * 计算时间轴的完整范围
 * 需要考虑所有时间窗可能超出班次范围的情况
 * @param shiftStart 班次开始时间
 * @param shiftEnd 班次结束时间
 * @param windows 时间窗配置
 * @param bookingCreatedAt 预约创建时间（可选）
 * @returns 时间轴范围
 */
export function calculateTimelineRange(
  shiftStart: Date,
  shiftEnd: Date,
  windows: RuleWindow[],
  bookingCreatedAt?: Date
): TimelineRange {
  let minDate = dayjs(shiftStart);
  let maxDate = dayjs(shiftEnd);

  // 遍历所有时间窗，找出最早和最晚时间
  windows.forEach((window) => {
    if (!window.enabled) return;

    // 计算开放时间（使用 != null 同时处理 null 和 undefined）
    const openTime =
      window.openOffsetSec != null && isFinite(window.openOffsetSec)
        ? calculateWindowTime(
            window.referencePoint,
            window.openOffsetSec,
            shiftStart,
            shiftEnd,
            bookingCreatedAt
          )
        : null;

    // 计算关闭时间
    const closeTime =
      window.closeOffsetSec != null && isFinite(window.closeOffsetSec)
        ? calculateWindowTime(
            window.referencePoint,
            window.closeOffsetSec,
            shiftStart,
            shiftEnd,
            bookingCreatedAt
          )
        : null;

    // 更新范围 - 需要同时考虑 openTime 和 closeTime 对 minDate 和 maxDate 的影响
    // 当开放偏移为正时，openTime 可能晚于 shiftEnd，需要扩展 maxDate
    // 当截止偏移为负时，closeTime 可能早于 shiftStart，需要扩展 minDate
    if (openTime) {
      const openDayjs = dayjs(openTime);
      if (openDayjs.isBefore(minDate)) {
        minDate = openDayjs;
      }
      if (openDayjs.isAfter(maxDate)) {
        maxDate = openDayjs;
      }
    }
    if (closeTime) {
      const closeDayjs = dayjs(closeTime);
      if (closeDayjs.isBefore(minDate)) {
        minDate = closeDayjs;
      }
      if (closeDayjs.isAfter(maxDate)) {
        maxDate = closeDayjs;
      }
    }
  });

  // 添加 10% 的边距
  const totalSeconds = maxDate.diff(minDate, 'second');
  const paddingSeconds = Math.max(totalSeconds * 0.1, 300); // 至少 5 分钟边距

  return {
    min: minDate.subtract(paddingSeconds, 'second').toDate(),
    max: maxDate.add(paddingSeconds, 'second').toDate(),
  };
}

/**
 * 将时间转换为时间轴上的像素位置
 * @param time 要转换的时间
 * @param timelineRange 时间轴范围
 * @param containerWidth 容器宽度（像素）
 * @returns 像素位置
 */
export function timeToPosition(
  time: Date,
  timelineRange: TimelineRange,
  containerWidth: number
): number {
  const totalSeconds = dayjs(timelineRange.max).diff(dayjs(timelineRange.min), 'second');
  if (totalSeconds === 0) return 0;

  const timeSeconds = dayjs(time).diff(dayjs(timelineRange.min), 'second');
  return (timeSeconds / totalSeconds) * containerWidth;
}

/**
 * 将时间转换为时间轴上的比例位置（0-1）
 * @param time 要转换的时间
 * @param timelineRange 时间轴范围
 * @returns 比例位置（0-1）
 */
export function timeToRatio(time: Date, timelineRange: TimelineRange): number {
  const totalSeconds = dayjs(timelineRange.max).diff(dayjs(timelineRange.min), 'second');
  if (totalSeconds === 0) return 0;

  const timeSeconds = dayjs(time).diff(dayjs(timelineRange.min), 'second');
  return timeSeconds / totalSeconds;
}

/**
 * 生成时间刻度
 * @param range 时间轴范围
 * @param containerWidth 容器宽度（像素）
 * @param maxTicks 最大刻度数量
 * @param alignTo 对齐参考时间（如班次开始时间），刻度将对齐到此时间的整数倍间隔
 * @returns 时间刻度数组
 */
export function generateTimeTicks(
  range: TimelineRange,
  containerWidth: number,
  maxTicks: number = 10,
  alignTo?: Date
): TimeTick[] {
  const ticks: TimeTick[] = [];
  const totalSeconds = dayjs(range.max).diff(dayjs(range.min), 'second');

  if (totalSeconds === 0) {
    return [
      {
        time: range.min,
        position: 0,
        label: dayjs(range.min).format('HH:mm'),
      },
    ];
  }

  // 固定使用 30 分钟刻度间隔
  const intervalSeconds = 1800;

  // 生成刻度
  const minTime = dayjs(range.min);
  const maxTime = dayjs(range.max);

  let currentTime: dayjs.Dayjs;

  if (alignTo) {
    // 关键修复：刻度对齐到参考时间（如班次开始时间）的整数倍间隔
    // 这样可以确保班次边界和时间窗边界与刻度对齐
    const alignTime = dayjs(alignTo);
    const diff = minTime.diff(alignTime, 'second');
    const intervalsBefore = Math.floor(diff / intervalSeconds);
    currentTime = alignTime.add(intervalsBefore * intervalSeconds, 'second');

    // 确保第一个刻度在范围内
    while (currentTime.isBefore(minTime)) {
      currentTime = currentTime.add(intervalSeconds, 'second');
    }
  } else {
    // 没有对齐参考时，使用默认对齐方式（对齐到 Unix 时间戳的整数倍）
    currentTime = minTime.startOf('minute');
    const secondsFromEpoch = currentTime.unix();
    const offsetFromInterval = secondsFromEpoch % intervalSeconds;
    if (offsetFromInterval !== 0) {
      currentTime = currentTime.add(intervalSeconds - offsetFromInterval, 'second');
    }

    // 确保第一个刻度不早于范围起始时间
    if (currentTime.isBefore(minTime)) {
      currentTime = currentTime.add(intervalSeconds, 'second');
    }
  }

  // 生成所有刻度
  while (currentTime.isBefore(maxTime) || currentTime.isSame(maxTime, 'second')) {
    const ratio = timeToRatio(currentTime.toDate(), range);
    ticks.push({
      time: currentTime.toDate(),
      position: ratio,
      label: currentTime.format('HH:mm'),
    });

    currentTime = currentTime.add(intervalSeconds, 'second');
  }

  return ticks;
}
