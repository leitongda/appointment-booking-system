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
    
    // 业务错误
    if (data.code !== 200) {
      return Promise.reject(new Error(data.message || '请求失败'));
    }
    
    return data.data;
  },
  (error) => {
    // HTTP 错误
    const message = error.response?.data?.message || error.message || '网络错误';
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

