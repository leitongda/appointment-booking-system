/**
 * 日期时间工具函数
 */

/**
 * 格式化日期
 * @param date 日期对象或字符串
 * @param format 格式字符串，默认 'YYYY-MM-DD'
 */
export function formatDate(date: Date | string, format: string = 'YYYY-MM-DD'): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  const seconds = String(d.getSeconds()).padStart(2, '0');

  return format
    .replace('YYYY', String(year))
    .replace('MM', month)
    .replace('DD', day)
    .replace('HH', hours)
    .replace('mm', minutes)
    .replace('ss', seconds);
}

/**
 * 格式化时间
 * @param date 日期对象或字符串
 * @param format 格式字符串，默认 'HH:mm'
 */
export function formatTime(date: Date | string, format: string = 'HH:mm'): string {
  return formatDate(date, format);
}

/**
 * 格式化日期时间
 * @param date 日期对象或字符串
 * @param format 格式字符串，默认 'YYYY-MM-DD HH:mm:ss'
 */
export function formatDateTime(date: Date | string, format: string = 'YYYY-MM-DD HH:mm:ss'): string {
  return formatDate(date, format);
}

/**
 * 获取星期几
 * @param date 日期对象或字符串
 */
export function getWeekDay(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const weekDays = ['日', '一', '二', '三', '四', '五', '六'];
  return `星期${weekDays[d.getDay()]}`;
}

/**
 * 获取相对时间描述
 * @param date 日期对象或字符串
 */
export function getRelativeTime(date: Date | string): string {
  const d = typeof date === 'string' ? new Date(date) : date;
  const now = new Date();
  const diff = now.getTime() - d.getTime();

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (days > 7) {
    return formatDate(d);
  } else if (days > 0) {
    return `${days}天前`;
  } else if (hours > 0) {
    return `${hours}小时前`;
  } else if (minutes > 0) {
    return `${minutes}分钟前`;
  } else {
    return '刚刚';
  }
}

/**
 * 判断是否为今天
 * @param date 日期对象或字符串
 */
export function isToday(date: Date | string): boolean {
  const d = typeof date === 'string' ? new Date(date) : date;
  const today = new Date();
  return (
    d.getFullYear() === today.getFullYear() &&
    d.getMonth() === today.getMonth() &&
    d.getDate() === today.getDate()
  );
}

/**
 * 判断是否为明天
 * @param date 日期对象或字符串
 */
export function isTomorrow(date: Date | string): boolean {
  const d = typeof date === 'string' ? new Date(date) : date;
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  return (
    d.getFullYear() === tomorrow.getFullYear() &&
    d.getMonth() === tomorrow.getMonth() &&
    d.getDate() === tomorrow.getDate()
  );
}

/**
 * 获取友好的日期描述
 * @param date 日期对象或字符串
 */
export function getFriendlyDate(date: Date | string): string {
  if (isToday(date)) {
    return '今天';
  } else if (isTomorrow(date)) {
    return '明天';
  } else {
    const d = typeof date === 'string' ? new Date(date) : date;
    return `${formatDate(d, 'MM-DD')} ${getWeekDay(d)}`;
  }
}

/**
 * 计算两个日期之间的天数差
 * @param date1 日期1
 * @param date2 日期2
 */
export function getDaysDiff(date1: Date | string, date2: Date | string): number {
  const d1 = typeof date1 === 'string' ? new Date(date1) : date1;
  const d2 = typeof date2 === 'string' ? new Date(date2) : date2;
  const diff = d2.getTime() - d1.getTime();
  return Math.floor(diff / (1000 * 60 * 60 * 24));
}

/**
 * 获取指定天数后的日期
 * @param days 天数
 * @param baseDate 基准日期，默认为今天
 */
export function getDateAfterDays(days: number, baseDate?: Date | string): Date {
  const base = baseDate
    ? typeof baseDate === 'string'
      ? new Date(baseDate)
      : baseDate
    : new Date();
  const result = new Date(base);
  result.setDate(result.getDate() + days);
  return result;
}

/**
 * 解析时间字符串（HH:mm）为分钟数
 * @param time 时间字符串，格式 'HH:mm'
 */
export function parseTimeToMinutes(time: string): number {
  const [hours, minutes] = time.split(':').map(Number);
  return hours * 60 + minutes;
}

/**
 * 将分钟数转换为时间字符串
 * @param minutes 分钟数
 */
export function minutesToTime(minutes: number): string {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, '0')}:${String(mins).padStart(2, '0')}`;
}

/**
 * 计算两个时间之间的分钟差
 * @param time1 时间1，格式 'HH:mm'
 * @param time2 时间2，格式 'HH:mm'
 */
export function getTimeDiffInMinutes(time1: string, time2: string): number {
  const minutes1 = parseTimeToMinutes(time1);
  const minutes2 = parseTimeToMinutes(time2);
  return minutes2 - minutes1;
}
