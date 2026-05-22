/**
 * API 请求配置
 * 配置 @hospital/api 包的请求和响应拦截器
 *
 * Structured error codes from the server are handled here:
 *   SCHEDULE_CONFLICT  → show conflict details in notification
 *   PERMISSION_DENIED  → redirect to unauthorized page
 *   RATE_LIMITED       → show rate-limit warning
 *   VALIDATION_ERROR   → show field-level errors
 */
import { setRequestInterceptor, setResponseInterceptor, ApiError } from '@hospital/api';
import { getToken, getStorage, STORAGE_KEYS, handleTokenExpired, markAuthExpired, shouldSilenceAuthExpiredFeedback, parseTenantError, markTenantSuspended } from '@hospital/shared';
import { message, Modal, notification } from 'antd';
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
 * Handle structured error codes from the server's ErrorResponse envelope.
 *
 * Returns `true` if the error was fully handled (caller should return), or
 * `false` if the caller should continue with generic error handling.
 */
const handleStructuredErrorCode = (error: ApiError): boolean => {
  const { errorCode, errorDetails, message: errorMessage } = error;

  if (!errorCode) return false;

  switch (errorCode) {
    // ── Schedule conflict: show details in a notification ──
    case 'SCHEDULE_CONFLICT': {
      const conflicts = errorDetails?.conflicts as Array<{ message?: string }> | undefined;
      const conflictMessages = conflicts?.map(c => c.message).filter(Boolean);
      notification.warning({
        message: '排班冲突',
        description: conflictMessages?.length
          ? conflictMessages.join('\n')
          : errorMessage || '存在排班冲突，请调整后重试',
        duration: 6,
      });
      return true;
    }

    // ── Permission denied: redirect to unauthorized ──
    case 'PERMISSION_DENIED': {
      message.error(errorMessage || '权限不足，请联系管理员');
      // Optionally redirect: window.location.href = '/unauthorized';
      return true;
    }

    // ── Rate limited: show warning ──
    case 'RATE_LIMITED': {
      notification.warning({
        message: '请求过于频繁',
        description: errorMessage || '请稍后再试',
        duration: 4,
      });
      return true;
    }

    // ── Validation error: show field-level errors ──
    case 'VALIDATION_ERROR': {
      const fields = errorDetails?.fields as Array<{ field?: string; message?: string }> | undefined;
      if (fields?.length) {
        const fieldMsgs = fields.map(f => `${f.field}: ${f.message}`).join('\n');
        notification.error({
          message: '参数校验失败',
          description: fieldMsgs,
          duration: 6,
        });
      } else {
        message.error(errorMessage || '请求参数错误');
      }
      return true;
    }

    // ── Tenant status errors ──
    case 'TENANT_SUSPENDED':
    case 'TENANT_OVERDUE': {
      // Already handled by parseTenantError in the 403 branch; skip generic toast.
      return true;
    }

    default:
      // Not a recognized structured code — fall through to generic handling.
      return false;
  }
};

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

const getRequestPath = (url: string): string => {
  try {
    return new URL(url, window.location.origin).pathname;
  } catch {
    return url.split('?')[0];
  }
};

/**
 * 检查是否需要添加 token
 * 使用精确路径匹配，避免 /admin/login 错误匹配 /admin/login-history
 */
const shouldAddToken = (url: string): boolean => {
  const requestPath = getRequestPath(url);
  return !EXCLUDE_TOKEN_PATHS.some(path => {
    // 精确匹配：路径完全相等，或者路径以 path/ 开头（带参数的情况）
    // 例如：/admin/login 匹配 /admin/login 或 /admin/login?xxx
    // 但不匹配 /admin/login-history
    return requestPath === path || requestPath.startsWith(path + '/');
  });
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
      if (config.url && shouldAddToken(config.url)) {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }

      // 添加租户上下文 Header：从 localStorage 读取当前租户 ID
      // 如果不存在，则不添加，后端可通过子域名/路径前缀等其他方式识别租户
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

        // Structured error codes: handle specific codes before generic HTTP status handling
        if (handleStructuredErrorCode(error)) {
          return Promise.reject(error);
        }

        // 401 未授权 - 弹框确认后跳转登录页
        if (error.isUnauthorized()) {
          const requestUrl = error.url || '';
          const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl);

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
        if (code === 400 && errorMessage && (
          errorMessage.includes('解密失败') ||
          errorMessage.includes('密码解密失败') ||
          errorMessage.includes('RSA密钥不匹配') ||
          errorMessage.includes('Base64解码失败') ||
          errorMessage.includes('无法解码为UTF-8字符串')
        )) {
          // 如果是登录接口，静默处理，让登录函数自动重试
          const requestUrl = error.url || '';
          if (requestUrl.includes('/admin/login') || requestUrl.includes('/admin/phone-login')) {
            // 不显示错误消息，直接返回错误让登录函数处理重试
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
        // 获取请求 URL（可能是相对路径或完整路径）
        const requestUrl = error?.config?.url || error?.request?.responseURL || '';
        // Extract structured error envelope
        const structuredError = data?.error;
        const errorCode = structuredError?.code || data?.error_code;
        const errorDetails = structuredError?.details;

        // Structured error codes: handle specific codes before generic HTTP status handling
        const apiError = new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails);
        if (handleStructuredErrorCode(apiError)) {
          return Promise.reject(apiError);
        }

        // 401 未授权
        if (status === 401) {
          const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl);

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

        // 密码解密错误（400状态码 + 解密失败消息）- 登录接口会自动重试，不显示错误
        if (status === 400 && errorMsg && (
          errorMsg.includes('解密失败') ||
          errorMsg.includes('密码解密失败') ||
          errorMsg.includes('RSA密钥不匹配') ||
          errorMsg.includes('Base64解码失败') ||
          errorMsg.includes('无法解码为UTF-8字符串')
        )) {
          // 如果是登录接口，静默处理，让登录函数自动重试
          if (requestUrl.includes('/admin/login') || requestUrl.includes('/admin/phone-login')) {
            // 不显示错误消息，直接返回错误让登录函数处理重试
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails));
          }
        }

        // 显示错误消息
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
