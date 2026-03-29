/**
 * 验证并格式化时间值
 * @param timeValue 时间值（可能是字符串、dayjs对象、Date对象或其他格式）
 * @returns 格式化后的 "HH:mm" 字符串，如果无效则返回 undefined
 */
export function formatTimeValue(timeValue: any): string | undefined {
  if (!timeValue) return undefined;

  // 如果已经是有效的 "HH:mm" 格式字符串，直接返回
  if (typeof timeValue === 'string') {
    // 检查是否是 "Invalid Date" 字符串
    if (timeValue === 'Invalid Date' || timeValue.toLowerCase().includes('invalid')) {
      return undefined;
    }
    // 检查是否符合 "HH:mm" 格式
    const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
    if (timeRegex.test(timeValue)) {
      return timeValue;
    }
    // 尝试从其他格式中提取时间（如 "HH:mm:ss"）
    const timeMatch = timeValue.match(/([01]\d|2[0-3]):([0-5]\d)/);
    if (timeMatch) {
      return timeMatch[0];
    }
    return undefined;
  }

  // 如果是 Date 对象
  if (timeValue instanceof Date) {
    if (!isNaN(timeValue.getTime())) {
      const hours = String(timeValue.getHours()).padStart(2, '0');
      const minutes = String(timeValue.getMinutes()).padStart(2, '0');
      return `${hours}:${minutes}`;
    }
    return undefined;
  }

  // 如果是对象且有 format 方法（可能是 dayjs 对象）
  if (timeValue && typeof timeValue.format === 'function') {
    try {
      // 检查是否有 isValid 方法
      if (timeValue.isValid && !timeValue.isValid()) {
        return undefined;
      }
      const formatted = timeValue.format('HH:mm');
      // 验证格式化后的结果
      const timeRegex = /^([01]\d|2[0-3]):([0-5]\d)$/;
      if (timeRegex.test(formatted)) {
        return formatted;
      }
    } catch (e) {
      // 如果格式化失败，返回 undefined
      return undefined;
    }
  }

  return undefined;
}
