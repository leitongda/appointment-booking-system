import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import type { ApiResponse } from '@hospital/shared';

// 创建 axios 实例
const instance: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // Token 由各端自行设置
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
instance.interceptors.response.use(
  (response: AxiosResponse<ApiResponse>) => {
    const { data } = response;
    
    // 如果 data 不是对象，直接返回
    if (!data || typeof data !== 'object') {
      return data;
    }
    
    // 业务错误
    if (data.code && data.code !== 200) {
      return Promise.reject(new Error(data.message || '请求失败'));
    }
    
    // 分页响应：包含 total 字段，返回 ProTable 直接可用的格式
    if ('total' in data && typeof data.total === 'number' && 'data' in data) {
      return {
        data: data.data,
        total: data.total,
        success: true,  // ProTable 需要的字段
        page: data.page ?? 1,
        pageSize: data.pageSize ?? data.page_size ?? 10,
      };
    }
    
    // 统一响应格式：包含 code 和 data 字段
    if ('code' in data && 'data' in data) {
      return data.data;
    }
    
    // 其他情况直接返回
    return data;
  },
  (error) => {
    // HTTP 错误
    // 后端错误格式: { code: 400, message: "error", data: { detail: "实际错误信息" } }
    const responseData = error.response?.data;
    const message = responseData?.data?.detail || responseData?.message || error.message || '网络错误';
    return Promise.reject(new Error(message));
  }
);

/**
 * 设置基础 URL
 */
export const setBaseURL = (baseURL: string) => {
  instance.defaults.baseURL = baseURL;
};

/**
 * 设置请求拦截器（用于各端设置 Token）
 */
export const setRequestInterceptor = (
  onFulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig,
  onRejected?: (error: any) => any
) => {
  instance.interceptors.request.use(onFulfilled, onRejected);
};

/**
 * 设置响应拦截器（用于各端处理错误）
 */
export const setResponseInterceptor = (
  onFulfilled?: (response: AxiosResponse) => any,
  onRejected?: (error: any) => any
) => {
  instance.interceptors.response.use(onFulfilled, onRejected);
};

/**
 * 封装请求方法
 */
export const request = {
  get: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return instance.get(url, config);
  },
  
  post: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return instance.post(url, data, config);
  },
  
  put: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return instance.put(url, data, config);
  },
  
  delete: <T = any>(url: string, config?: AxiosRequestConfig): Promise<T> => {
    return instance.delete(url, config);
  },
  
  patch: <T = any>(url: string, data?: any, config?: AxiosRequestConfig): Promise<T> => {
    return instance.patch(url, data, config);
  },
};

export default instance;

