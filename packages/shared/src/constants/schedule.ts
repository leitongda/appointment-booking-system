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
