/**
 * API 请求配置
 * 配置 @hospital/api 包的请求和响应拦截器
 */
import {
  setRequestInterceptor,
  setResponseInterceptor,
  ApiError,
  ERROR_MESSAGES,
  getRequestPath,
  shouldAddToken,
  handleStructuredErrorCode,
  isRsaDecryptError,
  handleNetworkError,
} from '@hospital/api';
import { getToken, getStorage, STORAGE_KEYS, handleTokenExpired, markAuthExpired, shouldSilenceAuthExpiredFeedback, parseTenantError, markTenantSuspended } from '@hospital/shared';
import { message, Modal, notification } from 'antd';
import type { InternalAxiosRequestConfig } from 'axios';

/**
 * 不需要自动添加 token 的接口路径
 * 登录、注册等认证相关接口不应该携带旧的 token
 */
const EXCLUDE_TOKEN_PATHS = [
  '/admin/login',
  '/admin/phone-login',
  '/admin/sms/send',
  '/admin/sms/login',
  '/admin/wechat/qrcode',
  '/admin/wechat/check',
  '/admin/public-key',
  '/auth/login',
  '/auth/register',
  '/doctors/login',
];

/**
 * 结构化错误码处理的 UI 依赖
 */
const errorDeps = {
  showError: (msg: string) => message.error(msg),
  showWarning: (opts: { message: string; description?: string; duration?: number }) =>
    notification.warning(opts),
};

/**
 * 配置请求拦截器
 * 自动在请求头中添加 Authorization token
 * 注意：登录相关接口不添加 token，避免携带过期 token 导致的问题
 */
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      // 登录相关接口不添加 token
      if (config.url && shouldAddToken(config.url, EXCLUDE_TOKEN_PATHS)) {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }

      // 添加租户上下文 Header：从 localStorage 读取当前租户 ID
      const currentTenantId = getStorage<string>(STORAGE_KEYS.CURRENT_TENANT_ID);
      if (currentTenantId) {
        config.headers['X-Tenant-ID'] = currentTenantId;
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

        // 结构化错误码处理
        if (handleStructuredErrorCode(error, errorDeps)) {
          return Promise.reject(error);
        }

        // 401 未授权 - 弹框确认后跳转登录页
        if (error.isUnauthorized()) {
          const requestUrl = error.url || '';
          const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl, EXCLUDE_TOKEN_PATHS);

          if (!isProtectedRequest) {
            return Promise.reject(error);
          }

          if (shouldSilenceAuthExpiredFeedback()) {
            markAuthExpired();
            handleTokenExpired();
            return Promise.reject(error);
          }

          markAuthExpired();
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
                window.location.href = '/login';
              },
            });
          });
          return Promise.reject(error);
        }

        // 403 禁止访问
        if (error.isForbidden()) {
          const tenantReason = parseTenantError(error);
          if (tenantReason) {
            markTenantSuspended(tenantReason);
            window.location.href = '/tenant-suspended';
            return Promise.reject(error);
          }
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

        // 密码解密错误（400状态码 + 解密失败消息）- 登录接口会自动重试，不显示错误
        if (code === 400 && errorMessage && isRsaDecryptError(errorMessage)) {
          const requestUrl = error.url || '';
          if (requestUrl.includes('/admin/login') || requestUrl.includes('/admin/phone-login')) {
            return Promise.reject(error);
          }
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
        const requestUrl = error?.config?.url || error?.request?.responseURL || '';
        // 提取结构化错误信息
        const structuredError = data?.error;
        const errorCode = structuredError?.code || data?.error_code;
        const errorDetails = structuredError?.details;

        // 构建 ApiError 以复用结构化错误处理
        const apiError = new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails);
        if (handleStructuredErrorCode(apiError, errorDeps)) {
          return Promise.reject(apiError);
        }

        // 401 未授权
        if (status === 401) {
          const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl, EXCLUDE_TOKEN_PATHS);

          if (!isProtectedRequest) {
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
          }

          if (shouldSilenceAuthExpiredFeedback()) {
            markAuthExpired();
            handleTokenExpired();
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
          }
          markAuthExpired();
          handleTokenExpired(() => {
            Modal.confirm({
              title: '登录已过期',
              content: errorMsg || '您的登录已失效，请重新登录。',
              okText: '重新登录',
              cancelButtonProps: { style: { display: 'none' } },
              closable: false,
              maskClosable: false,
              onOk: () => {
                Modal.destroyAll();
                window.location.href = '/login';
              },
            });
          });
          return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
        }

        // 密码解密错误 - 登录接口自动重试
        if (status === 400 && errorMsg && isRsaDecryptError(errorMsg)) {
          if (requestUrl.includes('/admin/login') || requestUrl.includes('/admin/phone-login')) {
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
          }
        }

        // 403 — 检查是否为租户暂停
        if (status === 403) {
          const tenantReason = parseTenantError(data);
          if (tenantReason) {
            markTenantSuspended(tenantReason);
            window.location.href = '/tenant-suspended';
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
          }
        }
        message.error(errorMsg);
        return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
      }

      // 网络错误或其他错误
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
  console.log('✓ API 请求配置已初始化');
};
