/**
 * API 请求配置
 * 配置 @hospital/api 包的请求和响应拦截器
 */
import { setRequestInterceptor, setResponseInterceptor } from '@hospital/api';
import { getToken, removeToken } from '@hospital/shared';
import { history } from '@umijs/max';
import type { InternalAxiosRequestConfig } from 'axios';
import type { AxiosResponse } from 'axios';

/**
 * 配置请求拦截器
 * 自动在请求头中添加 Authorization token
 */
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      const token = getToken();
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
    },
    (error) => {
      console.error('请求错误:', error);
      return Promise.reject(error);
    }
  );
};

/**
 * 配置响应拦截器
 * 只处理错误响应（如 401 未授权），不处理成功响应
 * 成功响应由 @hospital/api 的默认拦截器处理
 */
export const setupResponseInterceptor = () => {
  setResponseInterceptor(
    undefined,  // 不处理成功响应，避免干扰数据格式
    (error) => {
      // 如果 error 是 Error 对象（已被上游拦截器处理），直接传递
      if (error instanceof Error && !('response' in error)) {
        return Promise.reject(error);
      }
      
      const response = error?.response;
      
      if (response) {
        const { status, data } = response;
        
        // 401 未授权 - 清除 token 并跳转到登录页
        if (status === 401) {
          console.warn('Token 已过期或无效，请重新登录');
          removeToken();
          history.push('/login');
          return Promise.reject(new Error('未授权，请重新登录'));
        }
        
        // 403 禁止访问
        if (status === 403) {
          return Promise.reject(new Error(data?.data?.detail || '没有权限访问'));
        }
        
        // 404 未找到
        if (status === 404) {
          return Promise.reject(new Error('请求的资源不存在'));
        }
        
        // 500 服务器错误
        if (status >= 500) {
          return Promise.reject(new Error(data?.message || '服务器错误，请稍后重试'));
        }
      }
      
      return Promise.reject(error);
    }
  );
};

/**
 * 初始化所有请求配置
 */
export const initApiConfig = () => {
  setupRequestInterceptor();
  setupResponseInterceptor();
  console.log('✓ API 请求配置已初始化');
};

