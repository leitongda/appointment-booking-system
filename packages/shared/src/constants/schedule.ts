/**
 * 排班时段
 */
export const TIME_SLOT = {
  MORNING: 'morning',       // 上午
  AFTERNOON: 'afternoon',   // 下午
  EVENING: 'evening',       // 晚间
} as const;

export const TIME_SLOT_MAP: Record<string, string> = {
  [TIME_SLOT.MORNING]: '上午',
  [TIME_SLOT.AFTERNOON]: '下午',
  [TIME_SLOT.EVENING]: '晚上',
};

/**
 * 默认时段时间
 */
export const TIME_SLOT_RANGE: Record<string, { start: string; end: string }> = {
  [TIME_SLOT.MORNING]: { start: '08:00', end: '12:00' },
  [TIME_SLOT.AFTERNOON]: { start: '14:00', end: '17:30' },
  [TIME_SLOT.EVENING]: { start: '18:00', end: '21:00' },
};

/**
 * 时段显示标签（用于UI显示）
 */
export const TIME_SLOT_LABEL: Record<string, string> = {
  [TIME_SLOT.MORNING]: '上午',
  [TIME_SLOT.AFTERNOON]: '下午',
  [TIME_SLOT.EVENING]: '晚上',
};

/**
 * 排班状态
 */
export const SCHEDULE_STATUS = {
  DISABLED: 0,  // 停诊
  ACTIVE: 1,    // 正常
  FULL: 2,      // 已满
} as const;

export const SCHEDULE_STATUS_MAP: Record<number, string> = {
  [SCHEDULE_STATUS.DISABLED]: '停诊',
  [SCHEDULE_STATUS.ACTIVE]: '正常',
  [SCHEDULE_STATUS.FULL]: '已满',
};

/**
 * 星期
 */
export const WEEKDAY_MAP: Record<number, string> = {
  1: '周一',
  2: '周二',
  3: '周三',
  4: '周四',
  5: '周五',
  6: '周六',
  7: '周日',
};

/**
 * 预约类型
 */
export const APPOINTMENT_TYPE = {
  URGENT: 'urgent',           // 加急
  NORMAL: 'normal',           // 普通
  EXPERT: 'expert',           // 专家
  MEDICAL_INSURANCE: 'medical_insurance',  // 医保
  SELF_PAY: 'self_pay',       // 自费
} as const;

export const APPOINTMENT_TYPE_MAP: Record<string, string> = {
  [APPOINTMENT_TYPE.URGENT]: '加急',
  [APPOINTMENT_TYPE.NORMAL]: '普通',
  [APPOINTMENT_TYPE.EXPERT]: '专家',
  [APPOINTMENT_TYPE.MEDICAL_INSURANCE]: '医保',
  [APPOINTMENT_TYPE.SELF_PAY]: '自费',
};

export const APPOINTMENT_TYPE_OPTIONS = [
  { label: '加急', value: APPOINTMENT_TYPE.URGENT },
  { label: '普通', value: APPOINTMENT_TYPE.NORMAL },
  { label: '专家', value: APPOINTMENT_TYPE.EXPERT },
  { label: '医保', value: APPOINTMENT_TYPE.MEDICAL_INSURANCE },
  { label: '自费', value: APPOINTMENT_TYPE.SELF_PAY },
];

/**
 * 排班方式
 */
export const SCHEDULE_MODE = {
  WEEKLY: 'weekly',           // 每周循环
  MONTH_WEEK_1: 'month_week_1',  // 每月第一周
  MONTH_WEEK_2: 'month_week_2',  // 每月第二周
  MONTH_WEEK_3: 'month_week_3',  // 每月第三周
  MONTH_WEEK_4: 'month_week_4',  // 每月第四周
  MONTH_WEEK_5: 'month_week_5',  // 每月第五周
  YEAR_ODD_WEEK: 'year_odd_week',   // 本年奇数周
  YEAR_EVEN_WEEK: 'year_even_week', // 本年偶数周
} as const;

export const SCHEDULE_MODE_MAP: Record<string, string> = {
  [SCHEDULE_MODE.WEEKLY]: '每周循环',
  [SCHEDULE_MODE.MONTH_WEEK_1]: '每月第一周',
  [SCHEDULE_MODE.MONTH_WEEK_2]: '每月第二周',
  [SCHEDULE_MODE.MONTH_WEEK_3]: '每月第三周',
  [SCHEDULE_MODE.MONTH_WEEK_4]: '每月第四周',
  [SCHEDULE_MODE.MONTH_WEEK_5]: '每月第五周',
  [SCHEDULE_MODE.YEAR_ODD_WEEK]: '本年奇数周',
  [SCHEDULE_MODE.YEAR_EVEN_WEEK]: '本年偶数周',
};

export const SCHEDULE_MODE_OPTIONS = [
  { label: '每周循环', value: SCHEDULE_MODE.WEEKLY },
  { label: '每月第一周', value: SCHEDULE_MODE.MONTH_WEEK_1 },
  { label: '每月第二周', value: SCHEDULE_MODE.MONTH_WEEK_2 },
  { label: '每月第三周', value: SCHEDULE_MODE.MONTH_WEEK_3 },
  { label: '每月第四周', value: SCHEDULE_MODE.MONTH_WEEK_4 },
  { label: '每月第五周', value: SCHEDULE_MODE.MONTH_WEEK_5 },
  { label: '本年奇数周', value: SCHEDULE_MODE.YEAR_ODD_WEEK },
  { label: '本年偶数周', value: SCHEDULE_MODE.YEAR_EVEN_WEEK },
];

export const WEEKDAY_OPTIONS = [
  { label: '周一', value: 1 },
  { label: '周二', value: 2 },
  { label: '周三', value: 3 },
  { label: '周四', value: 4 },
  { label: '周五', value: 5 },
  { label: '周六', value: 6 },
  { label: '周日', value: 7 },
];

/**
 * 获取当前日期信息（用于显示）
 */
export function getDateInfo(date: Date = new Date()): {
  monthWeek: number;
  yearWeek: number;
  isOddWeek: boolean;
} {
  // 计算月内周数：1-7号为第1周，8-14号为第2周，以此类推
  const monthWeek = Math.ceil(date.getDate() / 7);
  
  // 计算年内周数
  const startOfYear = new Date(date.getFullYear(), 0, 1);
  const days = Math.floor((date.getTime() - startOfYear.getTime()) / (24 * 60 * 60 * 1000));
  const yearWeek = Math.ceil((days + startOfYear.getDay() + 1) / 7);
  
  return {
    monthWeek,
    yearWeek,
    isOddWeek: yearWeek % 2 === 1,
  };
}

// 时间格式验证正则：HH:mm
const TIME_FORMAT_REGEX = /^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$/;

// 复用 types/schedule.ts 中的 BreakTime
import type { BreakTime } from '../types/schedule';
export type { BreakTime };

/**
 * 时段配置类型
 */
export interface TimePeriod {
  key: string;       // 时段标识，如 morning, afternoon
  name: string;      // 时段名称，如 上午, 下午
  startTime: string; // 开始时间，格式 HH:mm
  endTime: string;   // 结束时间，格式 HH:mm
}

/**
 * 默认时段配置
 */
export const DEFAULT_TIME_PERIODS: TimePeriod[] = [
  { key: 'morning', name: '上午', startTime: '06:00', endTime: '12:00' },
  { key: 'afternoon', name: '下午', startTime: '12:00', endTime: '18:00' },
];

/**
 * 时间字符串转分钟数
 */
function timeToMinutes(timeStr: string): number {
  if (!timeStr || !TIME_FORMAT_REGEX.test(timeStr)) return 0;
  const [hours, minutes] = timeStr.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * 分钟数转时间字符串
 */
function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60) % 24;
  const mins = minutes % 60;
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

/**
 * 获取有效工作时间段（排除休息时间）
 */
function getWorkingPeriods(
  startTime: string,
  endTime: string,
  breakTimes?: BreakTime[]
): Array<[number, number]> {
  const startMinutes = timeToMinutes(startTime);
  const endMinutes = timeToMinutes(endTime);
  
  if (!breakTimes || breakTimes.length === 0) {
    return [[startMinutes, endMinutes]];
  }
  
  // 解析并排序排除时间段
  const breaks: Array<[number, number]> = [];
  for (const bt of breakTimes) {
    const btStart = timeToMinutes(bt.startTime);
    const btEnd = timeToMinutes(bt.endTime);
    // 只保留与工作时间有交集的排除时间
    if (btEnd > startMinutes && btStart < endMinutes) {
      breaks.push([Math.max(btStart, startMinutes), Math.min(btEnd, endMinutes)]);
    }
  }
  
  // 按开始时间排序
  breaks.sort((a, b) => a[0] - b[0]);
  
  // 合并重叠的排除时间段
  const mergedBreaks: Array<[number, number]> = [];
  for (const bt of breaks) {
    if (mergedBreaks.length > 0 && bt[0] <= mergedBreaks[mergedBreaks.length - 1][1]) {
      mergedBreaks[mergedBreaks.length - 1][1] = Math.max(mergedBreaks[mergedBreaks.length - 1][1], bt[1]);
    } else {
      mergedBreaks.push([...bt]);
    }
  }
  
  // 生成有效工作时间段
  const periods: Array<[number, number]> = [];
  let currentStart = startMinutes;
  
  for (const [btStart, btEnd] of mergedBreaks) {
    if (currentStart < btStart) {
      periods.push([currentStart, btStart]);
    }
    currentStart = btEnd;
  }
  
  // 添加最后一个时间段
  if (currentStart < endMinutes) {
    periods.push([currentStart, endMinutes]);
  }
  
  return periods;
}

/**
 * 将时间区间均分为多个班次（考虑排除时间段）
 * @param startTime 开始时间，格式 "HH:mm"
 * @param endTime 结束时间，格式 "HH:mm"
 * @param count 班次数量
 * @param breakTimes 排除时间段列表
 * @returns 班次时间列表
 */
export function splitTimeRangeWithBreaks(
  startTime: string,
  endTime: string,
  count: number,
  breakTimes?: BreakTime[]
): Array<[string, string]> {
  // 验证输入格式
  if (!startTime || !endTime || !TIME_FORMAT_REGEX.test(startTime) || !TIME_FORMAT_REGEX.test(endTime)) {
    return [[startTime || '00:00', endTime || '00:00']];
  }
  
  if (count <= 0) {
    return [[startTime, endTime]];
  }
  
  // 如果没有排除时间，使用原来的函数
  if (!breakTimes || breakTimes.length === 0) {
    return splitTimeRange(startTime, endTime, count);
  }
  
  // 获取有效工作时间段
  const workingPeriods = getWorkingPeriods(startTime, endTime, breakTimes);
  
  if (workingPeriods.length === 0) {
    return [[startTime, endTime]];
  }
  
  // 计算总有效工作分钟数
  let totalWorkingMinutes = 0;
  for (const [start, end] of workingPeriods) {
    totalWorkingMinutes += end - start;
  }
  
  if (totalWorkingMinutes <= 0) {
    return [[startTime, endTime]];
  }
  
  // 每个班次的分钟数
  let slotMinutes = Math.floor(totalWorkingMinutes / count);
  if (slotMinutes <= 0) slotMinutes = 1;
  
  // 在有效时间段内分配班次
  const slots: Array<[string, string]> = [];
  let slotCount = 0;
  
  for (const [periodStart, periodEnd] of workingPeriods) {
    let currentPos = periodStart;
    
    while (currentPos < periodEnd && slotCount < count) {
      // 如果是最后一个班次
      if (slotCount === count - 1) {
        slots.push([minutesToTime(currentPos), minutesToTime(periodEnd)]);
        slotCount++;
        currentPos = periodEnd;
      } else {
        const availableInPeriod = periodEnd - currentPos;
        
        if (slotMinutes <= availableInPeriod) {
          const slotEnd = currentPos + slotMinutes;
          slots.push([minutesToTime(currentPos), minutesToTime(slotEnd)]);
          slotCount++;
          currentPos = slotEnd;
        } else {
          // 当前时间段不足，作为一个班次
          slots.push([minutesToTime(currentPos), minutesToTime(periodEnd)]);
          slotCount++;
          currentPos = periodEnd;
        }
      }
    }
  }
  
  return slots.length > 0 ? slots : [[startTime, endTime]];
}

/**
 * 计算有效工作时长（分钟）
 * @param startTime 开始时间
 * @param endTime 结束时间
 * @param breakTimes 排除时间段列表
 * @returns 有效工作分钟数
 */
export function calculateWorkingDuration(
  startTime: string,
  endTime: string,
  breakTimes?: BreakTime[]
): number {
  if (!startTime || !endTime || !TIME_FORMAT_REGEX.test(startTime) || !TIME_FORMAT_REGEX.test(endTime)) {
    return 0;
  }
  
  const startMinutes = timeToMinutes(startTime);
  const endMinutes = timeToMinutes(endTime);
  let totalMinutes = endMinutes - startMinutes;
  
  if (totalMinutes <= 0) return 0;
  
  if (!breakTimes || breakTimes.length === 0) {
    return totalMinutes;
  }
  
  // 计算排除时间段的总时长
  let excludedMinutes = 0;
  for (const bt of breakTimes) {
    const btStart = timeToMinutes(bt.startTime);
    const btEnd = timeToMinutes(bt.endTime);
    
    // 计算与工作时间的交集
    const overlapStart = Math.max(btStart, startMinutes);
    const overlapEnd = Math.min(btEnd, endMinutes);
    
    if (overlapEnd > overlapStart) {
      excludedMinutes += overlapEnd - overlapStart;
    }
  }
  
  return Math.max(0, totalMinutes - excludedMinutes);
}

/**
 * 格式化工作时长为易读格式
 * @param minutes 分钟数
 * @returns 格式化字符串，如 "2小时30分钟"
 */
export function formatDuration(minutes: number): string {
  if (minutes <= 0) return '0分钟';
  
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  
  if (hours === 0) {
    return `${mins}分钟`;
  } else if (mins === 0) {
    return `${hours}小时`;
  } else {
    return `${hours}小时${mins}分钟`;
  }
}

/**
 * 根据开始时间获取时段名称
 * @param startTime 开始时间，格式 "HH:mm"
 * @param periods 自定义时段配置
 * @returns 时段名称
 */
export function getPeriodNameFromTime(
  startTime: string,
  periods?: TimePeriod[]
): string {
  if (!startTime || !TIME_FORMAT_REGEX.test(startTime)) {
    return '上午';
  }
  
  const startMinutes = timeToMinutes(startTime);
  const periodsToUse = periods && periods.length > 0 ? periods : DEFAULT_TIME_PERIODS;
  
  for (const period of periodsToUse) {
    const periodStart = timeToMinutes(period.startTime);
    let periodEnd = timeToMinutes(period.endTime);
    
    // 处理跨越午夜的情况
    if (periodEnd <= periodStart) {
      periodEnd += 24 * 60;
    }
    
    if (startMinutes >= periodStart && startMinutes < periodEnd) {
      return period.name;
    }
  }
  
  // 默认根据小时判断
  const hour = Math.floor(startMinutes / 60);
  if (hour < 12) return '上午';
  if (hour < 18) return '下午';
  return '晚上';
}

/**
 * 根据开始时间获取时段标识
 * @param startTime 开始时间，格式 "HH:mm"
 * @param periods 自定义时段配置
 * @returns 时段标识
 */
export function getTimeSlotFromTime(
  startTime: string,
  periods?: TimePeriod[]
): string {
  if (!startTime || !TIME_FORMAT_REGEX.test(startTime)) {
    return 'morning';
  }
  
  const startMinutes = timeToMinutes(startTime);
  const periodsToUse = periods && periods.length > 0 ? periods : DEFAULT_TIME_PERIODS;
  
  for (const period of periodsToUse) {
    const periodStart = timeToMinutes(period.startTime);
    let periodEnd = timeToMinutes(period.endTime);
    
    if (periodEnd <= periodStart) {
      periodEnd += 24 * 60;
    }
    
    if (startMinutes >= periodStart && startMinutes < periodEnd) {
      return period.key;
    }
  }
  
  // 默认根据小时判断
  const hour = Math.floor(startMinutes / 60);
  if (hour < 12) return 'morning';
  if (hour < 18) return 'afternoon';
  return 'evening';
}

/**
 * 将时间区间均分为多个班次
 * @param startTime 开始时间，格式 "HH:mm"
 * @param endTime 结束时间，格式 "HH:mm"
 * @param count 班次数量
 * @returns 班次时间列表，如 [["09:00", "11:00"], ["11:00", "13:00"], ...]
 */
export function splitTimeRange(
  startTime: string,
  endTime: string,
  count: number
): Array<[string, string]> {
  // 验证输入格式
  if (!startTime || !endTime || !TIME_FORMAT_REGEX.test(startTime) || !TIME_FORMAT_REGEX.test(endTime)) {
    return [[startTime || '00:00', endTime || '00:00']];
  }

  if (count <= 0) {
    return [[startTime, endTime]];
  }

  const [startHour, startMinute] = startTime.split(':').map(Number);
  const [endHour, endMinute] = endTime.split(':').map(Number);
  
  // 验证解析后的数值是否有效
  if (
    isNaN(startHour) || isNaN(startMinute) || 
    isNaN(endHour) || isNaN(endMinute) ||
    startHour < 0 || startHour > 23 ||
    startMinute < 0 || startMinute > 59 ||
    endHour < 0 || endHour > 23 ||
    endMinute < 0 || endMinute > 59
  ) {
    return [[startTime, endTime]];
  }

  const startMinutes = startHour * 60 + startMinute;
  const endMinutes = endHour * 60 + endMinute;
  const totalMinutes = endMinutes - startMinutes;

  if (totalMinutes <= 0) {
    return [[startTime, endTime]];
  }

  const slotMinutes = Math.floor(totalMinutes / count);
  const slots: Array<[string, string]> = [];

  let currentStartMinutes = startMinutes;

  for (let i = 0; i < count; i++) {
    const currentEndMinutes = i === count - 1 
      ? endMinutes 
      : currentStartMinutes + slotMinutes;

    const startH = Math.floor(currentStartMinutes / 60);
    const startM = currentStartMinutes % 60;
    const endH = Math.floor(currentEndMinutes / 60);
    const endM = currentEndMinutes % 60;

    const startStr = `${String(startH).padStart(2, '0')}:${String(startM).padStart(2, '0')}`;
    const endStr = `${String(endH).padStart(2, '0')}:${String(endM).padStart(2, '0')}`;

    slots.push([startStr, endStr]);
    currentStartMinutes = currentEndMinutes;
  }

  return slots;
}

/**
 * 判断指定日期是否应该生成排班
 * @param date 日期
 * @param scheduleMode 排班方式
 * @returns 是否应该生成排班
 */
export function shouldGenerateSchedule(
  date: Date,
  scheduleMode: string
): boolean {
  const dateInfo = getDateInfo(date);
  const monthWeek = dateInfo.monthWeek;
  const yearWeek = dateInfo.yearWeek;

  switch (scheduleMode) {
    case 'weekly':
      return true;
    case 'month_week_1':
      return monthWeek === 1;
    case 'month_week_2':
      return monthWeek === 2;
    case 'month_week_3':
      return monthWeek === 3;
    case 'month_week_4':
      return monthWeek === 4;
    case 'month_week_5':
      return monthWeek === 5;
    case 'year_odd_week':
      return yearWeek % 2 === 1;
    case 'year_even_week':
      return yearWeek % 2 === 0;
    default:
      return false;
  }
}

/**
 * 生成排班预览数据
 * @param config 排班配置
 * @param startDate 开始日期
 * @param endDate 结束日期
 * @returns 预览日期列表（会生成排班的日期）
 */
export function generateSchedulePreview(
  config: {
    weekdays: number[];
    scheduleMode: string;
  },
  startDate: Date,
  endDate: Date
): Date[] {
  const previewDates: Date[] = [];
  const currentDate = new Date(startDate);

  while (currentDate <= endDate) {
    const weekday = currentDate.getDay() === 0 ? 7 : currentDate.getDay(); // 转换为1-7格式

    if (config.weekdays.includes(weekday)) {
      if (shouldGenerateSchedule(new Date(currentDate), config.scheduleMode)) {
        previewDates.push(new Date(currentDate));
      }
    }

    currentDate.setDate(currentDate.getDate() + 1);
  }

  return previewDates;
}
