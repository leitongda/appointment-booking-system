/**
 * API 请求配置 - 医生端
 * 配置 @hospital/api 包的请求和响应拦截器
 */
import { setRequestInterceptor, setResponseInterceptor, ApiError } from '@hospital/api';
import { getToken, handleTokenExpired, markAuthExpired, shouldSilenceAuthExpiredFeedback } from '@hospital/shared';
import { history } from 'umi';
import { message, Modal } from 'antd';
import type { InternalAxiosRequestConfig } from 'axios';

/**
 * 错误消息映射
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
 * 不需要自动添加 token 的接口路径
 */
const EXCLUDE_TOKEN_PATHS = [
  '/doctors/login',
  '/auth/login',
  '/auth/register',
];

/**
 * 从 URL 中提取 pathname，用于精确路径匹配
 */
const getRequestPath = (url: string): string => {
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url.split('?')[0];
  }
};

/**
 * 检查是否需要添加 token
 * 使用精确路径匹配，避免 /auth/login 错误匹配 /auth/login-history
 */
const shouldAddToken = (url: string): boolean => {
  const requestPath = getRequestPath(url);
  return !EXCLUDE_TOKEN_PATHS.some(path =>
    requestPath === path || requestPath.startsWith(path + '/')
  );
};

/**
 * 配置请求拦截器
 */
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      if (config.url && shouldAddToken(config.url)) {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );
};

/**
 * 处理 401 错误的通用逻辑
 */
const handle401 = (errorMessage: string, requestUrl?: string) => {
  const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl);
  if (!isProtectedRequest) {
    return;
  }

  markAuthExpired();

  if (shouldSilenceAuthExpiredFeedback()) {
    handleTokenExpired();
    return;
  }

  handleTokenExpired(() => {
    Modal.confirm({
      title: '登录已过期',
      content: errorMessage || '您的登录已失效，请重新登录。',
      okText: '重新登录',
      cancelButtonProps: { style: { display: 'none' } },
      closable: false,
      maskClosable: false,
      onOk: () => {
        Modal.destroyAll();
        history.push('/login');
      },
    });
  });
};

/**
 * 配置响应拦截器
 */
export const setupResponseInterceptor = () => {
  setResponseInterceptor(
    undefined,
    (error) => {
      // 处理 ApiError（@hospital/api 响应拦截器已解析的业务错误）
      if (error instanceof ApiError) {
        const { code, message: errorMessage, url: requestUrl } = error;

        if (error.isUnauthorized()) {
          handle401(errorMessage || ERROR_MESSAGES[401], requestUrl);
          return Promise.reject(error);
        }

        if (error.isForbidden()) {
          message.error(errorMessage || ERROR_MESSAGES[403]);
          return Promise.reject(error);
        }

        if (error.isNotFound()) {
          message.error(errorMessage || ERROR_MESSAGES[404]);
          return Promise.reject(error);
        }

        if (error.isServerError()) {
          message.error(ERROR_MESSAGES[code] || ERROR_MESSAGES[500]);
          return Promise.reject(error);
        }

        // 其他业务错误
        if (errorMessage) {
          message.error(errorMessage);
        }
        return Promise.reject(error);
      }

      // 处理原始 Axios HTTP 错误
      const response = error?.response;
      if (response) {
        const { status, data } = response;
        const errorMsg = data?.detail || data?.data?.detail || data?.message || ERROR_MESSAGES[status] || '请求失败';
        const requestUrl = error?.config?.url || '';

        if (status === 401) {
          handle401(errorMsg, requestUrl);
          return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
        }

        if (status === 403) {
          message.error(errorMsg);
          return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
        }

        if (status === 404) {
          message.error(errorMsg);
          return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
        }

        if (status >= 500) {
          message.error(ERROR_MESSAGES[status] || ERROR_MESSAGES[500]);
          return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
        }

        message.error(errorMsg);
        return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
      }

      // 网络错误
      if (error instanceof Error) {
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
};
