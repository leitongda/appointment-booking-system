/**
 * 排班时段
 */
export const TIME_SLOT = {
  AM: 'AM',       // 上午
  PM: 'PM',       // 下午
  NIGHT: 'NIGHT', // 夜间
} as const;

export const TIME_SLOT_MAP: Record<string, string> = {
  [TIME_SLOT.AM]: '上午',
  [TIME_SLOT.PM]: '下午',
  [TIME_SLOT.NIGHT]: '夜间',
  'morning': '上午',
  'afternoon': '下午',
  'evening': '晚上',
};

/**
 * 默认时段时间
 */
export const TIME_SLOT_RANGE: Record<string, { start: string; end: string }> = {
  [TIME_SLOT.AM]: { start: '08:00', end: '12:00' },
  [TIME_SLOT.PM]: { start: '14:00', end: '17:30' },
  [TIME_SLOT.NIGHT]: { start: '18:00', end: '21:00' },
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
