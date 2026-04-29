import dayjs from 'dayjs';
import { DATE_FORMAT } from '../constants';

/**
 * 格式化日期
 */
export const formatDate = (
  date: string | Date | number | undefined,
  format: string = DATE_FORMAT.DATE
): string => {
  if (!date) return '';
  return dayjs(date).format(format);
};

/**
 * 格式化日期时间
 */
export const formatDateTime = (date: string | Date | number | undefined): string => {
  return formatDate(date, DATE_FORMAT.DATETIME);
};

/**
 * 格式化时间
 */
export const formatTime = (date: string | Date | number | undefined): string => {
  return formatDate(date, DATE_FORMAT.TIME_SHORT);
};

/**
 * 手机号脱敏
 */
export const maskPhone = (phone: string): string => {
  if (!phone || phone.length !== 11) return phone;
  return phone.replace(/(\d{3})\d{4}(\d{4})/, '$1****$2');
};

/**
 * 身份证号脱敏
 */
export const maskIdCard = (idCard: string): string => {
  if (!idCard || idCard.length < 15) return idCard;
  return idCard.replace(/(\d{6})\d+(\d{4})/, '$1********$2');
};

/**
 * 格式化金额
 */
export const formatMoney = (amount: number | undefined, decimals: number = 2): string => {
  if (amount === undefined || amount === null) return '0.00';
  return amount.toFixed(decimals);
};

/**
 * 根据身份证获取性别
 */
export const getGenderByIdCard = (idCard: string): number => {
  if (!idCard || idCard.length < 17) return 0;
  const genderCode = parseInt(idCard.charAt(16), 10);
  return genderCode % 2 === 0 ? 2 : 1; // 偶数女，奇数男
};

/**
 * 根据身份证获取生日
 */
export const getBirthdayByIdCard = (idCard: string): string => {
  if (!idCard || idCard.length < 14) return '';
  const year = idCard.substring(6, 10);
  const month = idCard.substring(10, 12);
  const day = idCard.substring(12, 14);
  return `${year}-${month}-${day}`;
};

/**
 * 格式化相对时间（消息列表常用）
 *
 * 1小时内: "刚刚" / "X分钟前"
 * 24小时内: "X小时前"
 * 7天内: "X天前"
 * 超过7天: 返回日期部分 (YYYY-MM-DD)
 */
export const formatRelativeTime = (dateStr: string): string => {
  if (!dateStr) return '';
  const date = new Date(dateStr);
  const diff = Date.now() - date.getTime();

  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return minutes <= 0 ? '刚刚' : `${minutes}分钟前`;
  }
  if (diff < 86400000) {
    return `${Math.floor(diff / 3600000)}小时前`;
  }
  if (diff < 604800000) {
    return `${Math.floor(diff / 86400000)}天前`;
  }
  return dateStr.substring(0, 10);
};

