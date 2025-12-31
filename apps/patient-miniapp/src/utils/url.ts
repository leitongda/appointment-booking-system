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

