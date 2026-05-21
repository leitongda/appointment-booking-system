/**
 * 预约状态
 */
export const APPOINTMENT_STATUS = {
  PENDING_PAYMENT: 0,  // 待支付
  CONFIRMED: 1,        // 已预约
  SIGNED: 2,           // 已签到
  WAITING: 3,          // 历史候诊（遗留死状态，仅兼容展示）
  SEEING: 4,           // 就诊中
  COMPLETED: 5,        // 已完成
  CANCELLED: 6,        // 已取消
  EXPIRED: 7,          // 已过期
  NO_SHOW: 8,          // 已爽约
} as const;

export const APPOINTMENT_STATUS_MAP: Record<number, string> = {
  [APPOINTMENT_STATUS.PENDING_PAYMENT]: '待支付',
  [APPOINTMENT_STATUS.CONFIRMED]: '已预约',
  [APPOINTMENT_STATUS.SIGNED]: '已签到',
  [APPOINTMENT_STATUS.WAITING]: '历史候诊',
  [APPOINTMENT_STATUS.SEEING]: '就诊中',
  [APPOINTMENT_STATUS.COMPLETED]: '已完成',
  [APPOINTMENT_STATUS.CANCELLED]: '已取消',
  [APPOINTMENT_STATUS.EXPIRED]: '已过期',
  [APPOINTMENT_STATUS.NO_SHOW]: '已爽约',
};

/**
 * 预约状态颜色
 */
export const APPOINTMENT_STATUS_COLOR: Record<number, string> = {
  [APPOINTMENT_STATUS.PENDING_PAYMENT]: 'orange',
  [APPOINTMENT_STATUS.CONFIRMED]: 'blue',
  [APPOINTMENT_STATUS.SIGNED]: 'cyan',
  [APPOINTMENT_STATUS.WAITING]: 'default',
  [APPOINTMENT_STATUS.SEEING]: 'processing',
  [APPOINTMENT_STATUS.COMPLETED]: 'green',
  [APPOINTMENT_STATUS.CANCELLED]: 'default',
  [APPOINTMENT_STATUS.EXPIRED]: 'default',
  [APPOINTMENT_STATUS.NO_SHOW]: 'red',
};

/**
 * 预约来源
 */
export const APPOINTMENT_SOURCE = {
  MINI_PROGRAM: 'MINI_PROGRAM',   // 小程序
  H5: 'H5',                       // H5
  APP: 'APP',                     // APP
  WEB: 'WEB',                     // Web
  SELF_SERVICE: 'SELF_SERVICE',   // 自助机
  OFFLINE: 'OFFLINE',             // 线下
} as const;

export const APPOINTMENT_SOURCE_MAP: Record<string, string> = {
  [APPOINTMENT_SOURCE.MINI_PROGRAM]: '小程序',
  [APPOINTMENT_SOURCE.H5]: 'H5',
  [APPOINTMENT_SOURCE.APP]: 'APP',
  [APPOINTMENT_SOURCE.WEB]: 'Web',
  [APPOINTMENT_SOURCE.SELF_SERVICE]: '自助机',
  [APPOINTMENT_SOURCE.OFFLINE]: '线下',
};

/**
 * 退款状态
 */
export const REFUND_STATUS = {
  NONE: 'none',
  PARTIAL_REFUNDED: 'partial_refunded',
  REFUNDED: 'refunded',
} as const;

export const REFUND_STATUS_MAP: Record<string, string> = {
  none: '未退款',
  partial_refunded: '部分退款',
  refunded: '已退款',
};

export const REFUND_STATUS_COLOR: Record<string, string> = {
  none: 'default',
  partial_refunded: 'orange',
  refunded: 'green',
};

/**
 * 预约状态标签（text + color 组合，供 Tag 组件直接使用）
 */
export const APPOINTMENT_STATUS_TAG: Record<number, { text: string; color: string }> = {
  [APPOINTMENT_STATUS.PENDING_PAYMENT]: { text: '待支付', color: 'orange' },
  [APPOINTMENT_STATUS.CONFIRMED]: { text: '已预约', color: 'blue' },
  [APPOINTMENT_STATUS.SIGNED]: { text: '已签到', color: 'cyan' },
  [APPOINTMENT_STATUS.WAITING]: { text: '历史候诊', color: 'default' },
  [APPOINTMENT_STATUS.SEEING]: { text: '就诊中', color: 'processing' },
  [APPOINTMENT_STATUS.COMPLETED]: { text: '已完成', color: 'green' },
  [APPOINTMENT_STATUS.CANCELLED]: { text: '已取消', color: 'default' },
  [APPOINTMENT_STATUS.EXPIRED]: { text: '已过期', color: 'default' },
  [APPOINTMENT_STATUS.NO_SHOW]: { text: '已爽约', color: 'red' },
};

export const REFUNDABLE_APPOINTMENT_STATUSES = new Set([1, 2, 4, 5]);
