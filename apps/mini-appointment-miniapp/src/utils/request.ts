import Taro from '@tarojs/taro';
import type { RequestConfig, ApiResponse } from '@/types/api';
import { STORAGE_KEYS } from '@/constants/index';
import { getToken, clearAuth, checkLogin } from '@/utils/auth';

// API 基础配置
const API_BASE_URL = process.env.TARO_APP_API_BASE_URL || 'https://api.example.com';
const API_VERSION = process.env.TARO_APP_API_VERSION || 'v1';

// 请求超时时间
const REQUEST_TIMEOUT = 30000;

// 存储 key
const STORE_ID_KEY = STORAGE_KEYS.STORE_ID;

/**
 * 获取完整的 API URL
 */
function getFullUrl(url: string): string {
  if (url.startsWith('http://') || url.startsWith('https://')) {
    return url;
  }
  
  // 移除开头的斜杠
  const cleanUrl = url.startsWith('/') ? url.slice(1) : url;
  
  return `${API_BASE_URL}/api/${API_VERSION}/${cleanUrl}`;
}

/**
 * 获取门店 ID
 */
function getStoreId(): string {
  try {
    // 优先从环境变量获取
    const envStoreId = process.env.TARO_APP_STORE_ID;
    if (envStoreId) {
      return envStoreId;
    }
    
    // 从缓存获取
    return Taro.getStorageSync(STORE_ID_KEY) || '';
  } catch (error) {
    console.error('Get store ID failed:', error);
    return '';
  }
}

/**
 * 设置门店 ID
 */
export function setStoreId(storeId: string): void {
  try {
    Taro.setStorageSync(STORE_ID_KEY, storeId);
  } catch (error) {
    console.error('Set store ID failed:', error);
  }
}

/**
 * 显示加载提示
 */
function showLoading(text: string = '加载中...'): void {
  Taro.showLoading({
    title: text,
    mask: true
  });
}

/**
 * 隐藏加载提示
 */
function hideLoading(): void {
  Taro.hideLoading();
}

/**
 * 显示错误提示
 */
function showError(message: string): void {
  Taro.showToast({
    title: message,
    icon: 'none',
    duration: 2000
  });
}

/**
 * 处理请求错误
 */
function handleError(error: any): void {
  console.error('Request error:', error);
  
  let message = '网络请求失败';
  
  if (error.errMsg) {
    if (error.errMsg.includes('timeout')) {
      message = '请求超时，请稍后重试';
    } else if (error.errMsg.includes('fail')) {
      message = '网络连接失败';
    }
  }
  
  showError(message);
}

/**
 * 跳转到登录页
 */
export function navigateToLogin(): void {
  Taro.navigateTo({
    url: '/pages/login/index'
  });
}

/**
 * HTTP 请求封装
 */
async function request<T = any>(config: RequestConfig): Promise<T> {
  const {
    url,
    method = 'GET',
    data,
    params,
    headers = {},
    needAuth = true,
    showLoading: shouldShowLoading = false,
    loadingText = '加载中...'
  } = config;

  // 显示加载提示
  if (shouldShowLoading) {
    showLoading(loadingText);
  }

  try {
    // 构建请求头
    const requestHeaders: Record<string, string> = {
      'Content-Type': 'application/json',
      ...headers
    };

    // 添加 Token
    if (needAuth) {
      const token = getToken();
      if (token) {
        requestHeaders['Authorization'] = `Bearer ${token}`;
      } else {
        // 需要认证但没有 token，跳转到登录页
        hideLoading();
        navigateToLogin();
        throw new Error('未登录');
      }
    }

    // 构建 URL 参数
    let fullUrl = getFullUrl(url);
    
    // 添加门店 ID 到 URL 参数
    const storeId = getStoreId();
    const urlParams: Record<string, any> = { ...params };
    
    if (storeId) {
      urlParams.storeId = storeId;
    }

    // 拼接 URL 参数
    if (Object.keys(urlParams).length > 0) {
      const queryString = Object.entries(urlParams)
        .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(value)}`)
        .join('&');
      fullUrl += (fullUrl.includes('?') ? '&' : '?') + queryString;
    }

    // 发起请求
    const response = await Taro.request({
      url: fullUrl,
      method,
      data,
      header: requestHeaders,
      timeout: REQUEST_TIMEOUT
    });

    // 隐藏加载提示
    if (shouldShowLoading) {
      hideLoading();
    }

    // 处理响应
    const result = response.data as ApiResponse<T>;

    // 检查业务状态码
    if (result.code === 0 || result.code === 200) {
      return result.data;
    } else if (result.code === 401) {
      // Token 过期或无效
      clearAuth();
      navigateToLogin();
      throw new Error('登录已过期，请重新登录');
    } else {
      // 业务错误
      showError(result.message || '请求失败');
      throw new Error(result.message || '请求失败');
    }
  } catch (error: any) {
    // 隐藏加载提示
    if (shouldShowLoading) {
      hideLoading();
    }

    // 处理错误
    if (error.message !== '未登录' && error.message !== '登录已过期，请重新登录') {
      handleError(error);
    }

    throw error;
  }
}

/**
 * GET 请求
 */
export function get<T = any>(url: string, params?: Record<string, any>, config?: Partial<RequestConfig>): Promise<T> {
  return request<T>({
    url,
    method: 'GET',
    params,
    ...config
  });
}

/**
 * POST 请求
 */
export function post<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
  return request<T>({
    url,
    method: 'POST',
    data,
    ...config
  });
}

/**
 * PUT 请求
 */
export function put<T = any>(url: string, data?: any, config?: Partial<RequestConfig>): Promise<T> {
  return request<T>({
    url,
    method: 'PUT',
    data,
    ...config
  });
}

/**
 * DELETE 请求
 */
export function del<T = any>(url: string, params?: Record<string, any>, config?: Partial<RequestConfig>): Promise<T> {
  return request<T>({
    url,
    method: 'DELETE',
    params,
    ...config
  });
}

export default {
  get,
  post,
  put,
  delete: del,
  setStoreId,
  checkLogin,
  navigateToLogin
};
