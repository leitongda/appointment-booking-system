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

