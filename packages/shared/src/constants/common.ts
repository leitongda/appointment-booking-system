/**
 * 通用状态
 */
export const STATUS = {
  DISABLED: 0,  // 禁用
  ENABLED: 1,   // 启用
} as const;

export const STATUS_MAP: Record<number, string> = {
  [STATUS.DISABLED]: '禁用',
  [STATUS.ENABLED]: '启用',
};

/**
 * 分页默认值
 */
export const PAGINATION = {
  DEFAULT_PAGE: 1,
  DEFAULT_PAGE_SIZE: 10,
  PAGE_SIZE_OPTIONS: [10, 20, 50, 100],
} as const;

/**
 * 日期格式
 */
export const DATE_FORMAT = {
  DATE: 'YYYY-MM-DD',
  TIME: 'HH:mm:ss',
  DATETIME: 'YYYY-MM-DD HH:mm:ss',
  DATE_CN: 'YYYY年MM月DD日',
  TIME_SHORT: 'HH:mm',
} as const;

/**
 * 正则表达式
 */
export const REGEX = {
  PHONE: /^1[3-9]\d{9}$/,
  ID_CARD: /^[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]$/,
  PASSWORD: /^(?=.*[a-zA-Z])(?=.*\d)[a-zA-Z\d]{6,20}$/,
} as const;

