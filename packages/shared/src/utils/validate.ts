import { REGEX } from '../constants';

/**
 * 验证手机号
 */
export const isValidPhone = (phone: string): boolean => {
  return REGEX.PHONE.test(phone);
};

/**
 * 验证身份证号
 */
export const isValidIdCard = (idCard: string): boolean => {
  return REGEX.ID_CARD.test(idCard);
};

/**
 * 验证密码
 */
export const isValidPassword = (password: string): boolean => {
  return REGEX.PASSWORD.test(password);
};

/**
 * 验证是否为空
 */
export const isEmpty = (value: any): boolean => {
  if (value === null || value === undefined) return true;
  if (typeof value === 'string') return value.trim() === '';
  if (Array.isArray(value)) return value.length === 0;
  if (typeof value === 'object') return Object.keys(value).length === 0;
  return false;
};

/**
 * 验证是否为数字
 */
export const isNumber = (value: any): boolean => {
  return typeof value === 'number' && !isNaN(value);
};

/**
 * 验证是否为正整数
 */
export const isPositiveInteger = (value: any): boolean => {
  return isNumber(value) && Number.isInteger(value) && value > 0;
};

