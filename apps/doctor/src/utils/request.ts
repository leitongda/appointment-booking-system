/**
 * API 请求配置 - 医生端
 * 配置 @hospital/api 包的请求和响应拦截器
 */
import {
  setRequestInterceptor,
  setResponseInterceptor,
  ApiError,
  ERROR_MESSAGES,
  shouldAddToken,
  handleNetworkError,
} from '@hospital/api';
import { getToken, handleTokenExpired, markAuthExpired, shouldSilenceAuthExpiredFeedback, parseTenantError, markTenantSuspended } from '@hospital/shared';
import { history } from 'umi';
import { message, Modal } from 'antd';
import type { InternalAxiosRequestConfig } from 'axios';

/**
 * 不需要自动添加 token 的接口路径
 */
const EXCLUDE_TOKEN_PATHS = [
  '/doctors/login',
  '/auth/login',
  '/auth/register',
];

/**
 * 配置请求拦截器
 */
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      if (config.url && shouldAddToken(config.url, EXCLUDE_TOKEN_PATHS)) {
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
  const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl, EXCLUDE_TOKEN_PATHS);
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
          // 检查是否为租户暂停
          const tenantReason = parseTenantError(error);
          if (tenantReason) {
            markTenantSuspended(tenantReason);
            window.location.href = '/tenant-suspended';
            return Promise.reject(error);
          }
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
          // 检查是否为租户暂停
          const tenantReason = parseTenantError(data);
          if (tenantReason) {
            markTenantSuspended(tenantReason);
            window.location.href = '/tenant-suspended';
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
          }
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
        handleNetworkError(error, (msg) => message.error(msg));
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
