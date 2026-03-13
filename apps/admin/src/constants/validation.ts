/**
 * 验证常量
 *
 * 统一管理表单验证相关的正则表达式和消息模板
 */

/**
 * 正则表达式集合
 */
export const PATTERNS = {
  /**
   * 手机号
   * 1开头的11位数字，第二位为3-9
   */
  PHONE: /^1[3-9]\d{9}$/,

  /**
   * 座机号
   * 支持以下格式：
   * - 区号-号码: 010-12345678, 0755-1234567
   * - 直接号码: 12345678 (7-8位)
   */
  LANDLINE: /^(?:\d{3,4}-)?\d{7,8}$/,

  /**
   * 手机或座机
   * 支持手机号或座机号格式
   */
  PHONE_OR_LANDLINE: /^(?:(?:\d{3,4}-)?\d{7,8}|1[3-9]\d{9})$/,

  /**
   * 时间格式 (HH:mm)
   * 24小时制，小时 00-23，分钟 00-59
   */
  TIME: /^([01]\d|2[0-3]):([0-5]\d)$/,

  /**
   * 编码格式 - 小写字母、数字、下划线
   * 长度 2-50 位
   */
  CODE_LOWER: /^[a-z0-9_]{2,50}$/,

  /**
   * 编码格式 - 大写字母、数字、下划线
   * 长度 2-50 位
   */
  CODE_UPPER: /^[A-Z0-9_]{2,50}$/,

  /**
   * 编码格式 - 字母、数字、下划线、连字符
   * 长度 2-50 位
   */
  CODE_SLUG: /^[a-zA-Z0-9_-]{2,50}$/,

  /**
   * 编码格式 - 中文、字母、数字、下划线、连字符
   * 长度 2-50 位
   */
  CODE_UNICODE: /^[\u4e00-\u9fa5a-zA-Z0-9_-]{2,50}$/,

  /**
   * 用户名 - 小写字母、数字、下划线
   * 长度 4-20 位
   */
  USERNAME: /^[a-z0-9_]{4,20}$/,

  /**
   * 身份证号
   * 支持15位或18位（最后一位可能是X）
   */
  ID_CARD: /(^\d{15}$)|(^\d{18}$)|(^\d{17}(\d|X|x)$)/,

  /**
   * 邮箱
   */
  EMAIL: /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/,

  /**
   * URL
   */
  URL: /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$/,

  /**
   * IP地址 (IPv4)
   */
  IPV4: /^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/,

  /**
   * 邮政编码
   * 6位数字
   */
  ZIP_CODE: /^\d{6}$/,

  /**
   * 车牌号
   * 支持普通车牌和新能源车牌
   */
  PLATE_NUMBER: /^[京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领][A-Z][A-Z0-9]{5,6}[A-Z0-9]?$/,

  /**
   * QQ号
   * 5-11位数字
   */
  QQ: /^[1-9][0-9]{4,10}$/,

  /**
   * 微信号
   * 6-20位，以字母开头，可包含字母、数字、下划线、连字符
   */
  WECHAT: /^[a-zA-Z][-a-zA-Z0-9_]{5,19}$/,

  /**
   * 银行卡号
   * 10-30位数字
   */
  BANK_CARD: /^\d{10,30}$/,

  /**
   * 数字（整数或小数）
   */
  NUMBER: /^-?\d+(\.\d+)?$/,

  /**
   * 正整数
   */
  POSITIVE_INTEGER: /^[1-9]\d*$/,

  /**
   * 负整数
   */
  NEGATIVE_INTEGER: /^-[1-9]\d*$/,

  /**
   * RGB颜色
   */
  RGB: /^rgb\(\s*\d{1,3}\s*,\s*\d{1,3}\s*,\s*\d{1,3}\s*\)$/,

  /**
   * 十六进制颜色
   */
  HEX_COLOR: /^#?([a-fA-F0-9]{6}|[a-fA-F0-9]{3})$/,
};

/**
 * 验证消息模板
 */
export const MESSAGES = {
  /** 手机号 */
  PHONE: '请输入正确的手机号',

  /** 座机号 */
  LANDLINE: '请输入正确的座机号（格式：区号-号码，如 010-12345678）',

  /** 手机或座机 */
  PHONE_OR_LANDLINE: '请输入正确的手机号或座机号',

  /** 时间格式 */
  TIME: '请输入正确的时间格式（HH:mm，如 09:30）',

  /** 编码格式 */
  CODE: {
    LOWER: '编码只能包含小写字母、数字、下划线，长度2-50位',
    UPPER: '编码只能包含大写字母、数字、下划线，长度2-50位',
    SLUG: '编码只能包含字母、数字、下划线、连字符，长度2-50位',
    UNICODE: '编码只能包含中文、字母、数字、下划线、连字符，长度2-50位',
  },

  /** 用户名 */
  USERNAME: '用户名只能包含小写字母、数字、下划线，长度4-20位',

  /** 身份证号 */
  ID_CARD: '请输入正确的身份证号',

  /** 邮箱 */
  EMAIL: '请输入正确的邮箱地址',

  /** URL */
  URL: '请输入正确的URL地址',

  /** IP地址 */
  IPV4: '请输入正确的IP地址',

  /** 邮政编码 */
  ZIP_CODE: '请输入正确的邮政编码（6位数字）',

  /** 车牌号 */
  PLATE_NUMBER: '请输入正确的车牌号',

  /** QQ号 */
  QQ: '请输入正确的QQ号（5-11位数字）',

  /** 微信号 */
  WECHAT: '请输入正确的微信号（6-20位，字母开头）',

  /** 银行卡号 */
  BANK_CARD: '请输入正确的银行卡号（10-30位数字）',

  /** 数字 */
  NUMBER: '请输入有效的数字',

  /** 正整数 */
  POSITIVE_INTEGER: '请输入有效的正整数',

  /** RGB颜色 */
  RGB: '请输入正确的RGB颜色值（如 rgb(255, 0, 0)）',

  /** 十六进制颜色 */
  HEX_COLOR: '请输入正确的颜色值（如 #ff0000 或 #f00）',

  /** 通用 */
  REQUIRED: '该字段为必填项',
  INVALID_FORMAT: '格式不正确',
  OUT_OF_RANGE: '值超出允许范围',
  TOO_SHORT: '长度过短',
  TOO_LONG: '长度过长',
} as const;

/**
 * 编码格式类型
 */
export type CodeFormatType = 'lower' | 'upper' | 'slug' | 'unicode';

/**
 * 获取编码格式的正则表达式
 *
 * @param format - 编码格式类型
 * @returns 正则表达式
 *
 * @example
 * ```ts
 * const pattern = getCodePattern('lower'); // PATTERNS.CODE_LOWER
 * ```
 */
export function getCodePattern(format: CodeFormatType): RegExp {
  const patternMap = {
    lower: PATTERNS.CODE_LOWER,
    upper: PATTERNS.CODE_UPPER,
    slug: PATTERNS.CODE_SLUG,
    unicode: PATTERNS.CODE_UNICODE,
  };
  return patternMap[format];
}

/**
 * 获取编码格式的错误消息
 *
 * @param format - 编码格式类型
 * @returns 错误消息
 *
 * @example
 * ```ts
 * const message = getCodeMessage('lower'); // MESSAGES.CODE.LOWER
 * ```
 */
export function getCodeMessage(format: CodeFormatType): string {
  return MESSAGES.CODE[format.toUpperCase()];
}
