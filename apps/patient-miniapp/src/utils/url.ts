/**
 * URL 工具函数
 * 用于处理小程序中的资源 URL
 */

// 获取 API Host（与 app.tsx 保持一致）
const getApiHost = (): string => {
  if (process.env.TARO_APP_API_URL) {
    // 从完整的 API URL 中提取 host
    // 例如 http://127.0.0.1:8000/api/v1 -> http://127.0.0.1:8000
    const url = process.env.TARO_APP_API_URL;
    const match = url.match(/^(https?:\/\/[^/]+)/);
    return match ? match[1] : url;
  }
  return process.env.NODE_ENV === 'production' 
    ? 'https://api.example.com' 
    : 'http://127.0.0.1:8000';
};

/**
 * 将相对路径转换为完整的 URL
 * 小程序中的 Image 组件需要完整的 URL 才能正确加载远程图片
 * 
 * @param path 图片路径，可能是相对路径（如 /uploads/xxx）或完整 URL
 * @returns 完整的图片 URL
 * 
 * @example
 * getFullUrl('/uploads/doctor/202512/xxx.jpg')
 * // => 'http://127.0.0.1:8000/uploads/doctor/202512/xxx.jpg'
 * 
 * getFullUrl('https://example.com/image.jpg')
 * // => 'https://example.com/image.jpg'
 * 
 * getFullUrl(null)
 * // => ''
 */
export const getFullUrl = (path: string | null | undefined): string => {
  if (!path) {
    return '';
  }
  
  // 如果已经是完整的 URL（http:// 或 https://），直接返回
  if (path.startsWith('http://') || path.startsWith('https://')) {
    return path;
  }
  
  // 如果是相对路径，拼接服务器地址
  const host = getApiHost();
  // 确保路径以 / 开头
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${host}${normalizedPath}`;
};

/**
 * 获取图片 URL（getFullUrl 的别名，语义更明确）
 */
export const getImageUrl = getFullUrl;

/**
 * 格式化时间字符串为 HH:MM 格式
 * 后端返回的时间可能是 "HH:MM:SS" 或 "HH:MM" 格式
 * 
 * @param time 时间字符串
 * @returns 格式化后的时间 "HH:MM"
 * 
 * @example
 * formatTime('09:00:00') // => '09:00'
 * formatTime('09:00') // => '09:00'
 * formatTime(null) // => ''
 */
export const formatTime = (time: string | null | undefined): string => {
  if (!time) return '';
  // 如果是 "HH:MM:SS" 格式，截取前5个字符
  if (time.length > 5 && time[5] === ':') {
    return time.substring(0, 5);
  }
  return time;
};

/**
 * 判断预约是否已过期
 * 如果预约日期+结束时间已经过去，则视为过期
 * 
 * @param scheduleDate 预约日期（格式：YYYY-MM-DD）
 * @param endTime 结束时间（格式：HH:MM 或 HH:MM:SS）
 * @param timeSlot 时段（AM/PM），当没有 endTime 时使用
 * @returns 是否已过期
 */
export const isAppointmentExpired = (
  scheduleDate: string | undefined,
  endTime: string | undefined,
  timeSlot: string | undefined
): boolean => {
  if (!scheduleDate) return false;
  
  const now = new Date();
  
  // 如果有具体的结束时间，使用结束时间判断
  if (endTime) {
    const formattedEndTime = formatTime(endTime);
    const appointmentEnd = new Date(`${scheduleDate}T${formattedEndTime}:00`);
    return now > appointmentEnd;
  }
  
  // 没有具体结束时间，根据时段判断
  // 上午时段：12:00 前有效
  // 下午/其他时段：当天 23:59 前有效
  const endHour = timeSlot === 'morning' ? 12 : 23;
  const endMinute = timeSlot === 'morning' ? 0 : 59;
  const appointmentEnd = new Date(`${scheduleDate}T${String(endHour).padStart(2, '0')}:${String(endMinute).padStart(2, '0')}:00`);
  
  return now > appointmentEnd;
};

