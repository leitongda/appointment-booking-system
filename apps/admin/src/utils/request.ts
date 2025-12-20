/**
 * API 请求配置
 * 配置 @hospital/api 包的请求和响应拦截器
 */
import { setRequestInterceptor, setResponseInterceptor, ApiError } from '@hospital/api';
import { getToken, handleTokenExpired } from '@hospital/shared';
import { history } from '@umijs/max';
import { message } from 'antd';
import type { InternalAxiosRequestConfig } from 'axios';

/**
 * 错误消息映射
 * 根据错误码返回用户友好的提示信息
 */
const ERROR_MESSAGES: Record<number, string> = {
  400: '请求参数错误',
  401: '登录已过期，请重新登录',
  403: '没有权限访问该资源',
  404: '请求的资源不存在',
  405: '请求方法不被允许',
  408: '请求超时，请稍后重试',
  429: '请求过于频繁，请稍后重试',
  500: '服务器错误，请稍后重试',
  502: '网关错误，请稍后重试',
  503: '服务暂时不可用，请稍后重试',
  504: '网关超时，请稍后重试',
};

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
 * 处理 API 业务错误和 HTTP 错误，提供用户友好的错误提示
 */
export const setupResponseInterceptor = () => {
  setResponseInterceptor(
    undefined,  // 不处理成功响应，避免干扰数据格式
    (error) => {
      // 处理 ApiError（包含业务错误码）
      if (error instanceof ApiError) {
        const { code, message: errorMessage } = error;
        
        // 401 未授权 - 清除 token 并跳转到登录页
        if (error.isUnauthorized()) {
          handleTokenExpired(() => {
            message.error(errorMessage || ERROR_MESSAGES[401]);
            history.push('/login');
          });
          return Promise.reject(error);
        }
        
        // 403 禁止访问
        if (error.isForbidden()) {
          message.error(errorMessage || ERROR_MESSAGES[403]);
          return Promise.reject(error);
        }
        
        // 404 未找到
        if (error.isNotFound()) {
          message.error(errorMessage || ERROR_MESSAGES[404]);
          return Promise.reject(error);
        }
        
        // 服务器错误 (5xx)
        if (error.isServerError()) {
          message.error(ERROR_MESSAGES[code] || ERROR_MESSAGES[500]);
          return Promise.reject(error);
        }
        
        // 其他业务错误，显示后端返回的消息
        if (errorMessage) {
          message.error(errorMessage);
        }
        
        return Promise.reject(error);
      }
      
      // 处理原始 Axios 错误（带 response 的 HTTP 错误）
      const response = error?.response;
      if (response) {
        const { status, data } = response;
        const errorMsg = data?.detail || data?.message || ERROR_MESSAGES[status] || '请求失败';
        
        // 401 未授权
        if (status === 401) {
          handleTokenExpired(() => {
            message.error(errorMsg);
            history.push('/login');
          });
          return Promise.reject(new ApiError(status, errorMsg, data));
        }
        
        // 显示错误消息
        message.error(errorMsg);
        return Promise.reject(new ApiError(status, errorMsg, data));
      }
      
      // 网络错误或其他错误
      if (error instanceof Error) {
        // 网络错误
        if (error.message === 'Network Error') {
          message.error('网络连接失败，请检查网络设置');
        } else if (error.message.includes('timeout')) {
          message.error('请求超时，请稍后重试');
        }
        return Promise.reject(error);
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

