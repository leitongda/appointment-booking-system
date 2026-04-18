import { setRequestInterceptor, setResponseInterceptor, ApiError } from '@hospital/api';
import { getToken, handleTokenExpired, markAuthExpired, STORAGE_KEYS, getStorage, shouldSilenceAuthExpiredFeedback, parseTenantError, markTenantSuspended } from '@hospital/shared';
import { toast } from 'sonner';

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

const shouldAddToken = (url: string): boolean => {
  const requestPath = getRequestPath(url);
  return !EXCLUDE_TOKEN_PATHS.some(path => {
    return requestPath === path || requestPath.startsWith(path + '/');
  });
};

export function setupRequestInterceptor() {
  setRequestInterceptor(
    (config: any) => {
      if (config.url && shouldAddToken(config.url)) {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }

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
}

export function setupResponseInterceptor() {
  setResponseInterceptor(
    undefined,
    (error) => {
      if (error instanceof ApiError) {
        const { code, message: errorMessage } = error;

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
            toast.error('登录已过期', {
              description: errorMessage || '您的登录已失效，请重新登录。',
              action: {
                label: '重新登录',
                onClick: () => {
                  window.location.href = '/login';
                },
              },
              duration: Infinity,
            });
          });
          return Promise.reject(error);
        }

        if (error.isForbidden()) {
          const tenantReason = parseTenantError(error);
          if (tenantReason) {
            markTenantSuspended(tenantReason);
            window.location.href = '/tenant-suspended';
            return Promise.reject(error);
          }
          toast.error(errorMessage || ERROR_MESSAGES[403]);
          return Promise.reject(error);
        }

        if (error.isNotFound()) {
          toast.error(errorMessage || ERROR_MESSAGES[404]);
          return Promise.reject(error);
        }

        if (error.isServerError()) {
          toast.error(ERROR_MESSAGES[code] || ERROR_MESSAGES[500]);
          return Promise.reject(error);
        }

        // RSA 解密错误 - 登录接口自动重试，静默处理
        if (code === 400 && errorMessage) {
          const isDecryptError =
            errorMessage.includes('解密失败') ||
            errorMessage.includes('RSA密钥不匹配') ||
            errorMessage.includes('Base64解码失败');

          if (isDecryptError) {
            const requestUrl = error.url || '';
            if (requestUrl.includes('/admin/login') || requestUrl.includes('/admin/phone-login')) {
              return Promise.reject(error);
            }
          }
        }

        if (errorMessage) {
          toast.error(errorMessage);
        }

        return Promise.reject(error);
      }

      const response = error?.response;
      if (response) {
        const { status, data } = response;
        const errorMsg = data?.detail || data?.message || ERROR_MESSAGES[status] || '请求失败';

        if (status === 401) {
          const requestUrl = error?.config?.url || '';
          const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl);

          if (!isProtectedRequest) {
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
          }

          if (shouldSilenceAuthExpiredFeedback()) {
            markAuthExpired();
            handleTokenExpired();
            return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
          }
          markAuthExpired();
          handleTokenExpired(() => {
            toast.error('登录已过期', {
              description: errorMsg || '您的登录已失效，请重新登录。',
              action: {
                label: '重新登录',
                onClick: () => {
                  window.location.href = '/login';
                },
              },
              duration: Infinity,
            });
          });
          return Promise.reject(new ApiError(status, errorMsg, data, requestUrl));
        }

        toast.error(errorMsg);
        // 403 — 检查是否为租户暂停
        if (status === 403) {
          const tenantReason = parseTenantError(data);
          if (tenantReason) {
            markTenantSuspended(tenantReason);
            window.location.href = '/tenant-suspended';
            return Promise.reject(new ApiError(status, errorMsg, data, error?.config?.url));
          }
        }
        return Promise.reject(new ApiError(status, errorMsg, data, error?.config?.url));
      }

      if (error instanceof Error) {
        if (error.message === 'Network Error') {
          toast.error('网络连接失败，请检查网络设置');
        } else if (error.message.includes('timeout')) {
          toast.error('请求超时，请稍后重试');
        }
        return Promise.reject(error);
      }

      return Promise.reject(error);
    }
  );
}
