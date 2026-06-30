import { request, setResponseInterceptor, getHttpClient } from '@hospital/api';
import {
  setToken,
  getStorage,
  setStorage,
  STORAGE_KEYS,
  markAuthExpired,
  resetTokenExpiredState,
} from '@hospital/shared';

interface HttpResponse<T = any> {
  data: T;
}

interface HttpRequestConfig {
  url?: string;
  headers?: Record<string, string>;
  _retry?: boolean;
}

interface HttpError {
  config?: HttpRequestConfig;
  response?: {
    status?: number;
    data?: any;
  };
  message?: string;
}

/** 是否正在刷新 token */
let isRefreshing = false;
/** 等待刷新完成的请求队列 */
let pendingRequests: Array<{
  resolve: (token: string) => void;
  reject: (error: any) => void;
}> = [];

/** 处理等待队列 */
function processPendingRequests(error: any, token?: string) {
  pendingRequests.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token!);
    }
  });
  pendingRequests = [];
}

/** 刷新 token */
async function refreshToken(): Promise<{ accessToken: string; refreshToken: string }> {
  const refreshTokenValue = getStorage(STORAGE_KEYS.REFRESH_TOKEN);
  if (!refreshTokenValue) {
    throw new Error('No refresh token available');
  }

  const response: any = await request.post('/admin/refresh', {
    refresh_token: refreshTokenValue,
  });

  return {
    accessToken: response.accessToken,
    refreshToken: response.refreshToken,
  };
}

/** 判断是否是需要跳过刷新的请求 */
function shouldSkipRefresh(url: string): boolean {
  return (
    url.includes('/login') ||
    url.includes('/refresh') ||
    url.includes('/public-key') ||
    url.includes('/public')
  );
}

/** 重试原始请求 */
function retryOriginalRequest(
  config: HttpRequestConfig,
  newToken: string,
) {
  config.headers = {
    ...config.headers,
    Authorization: `Bearer ${newToken}`,
  };
  config._retry = true;
  const request = getHttpClient().request;
  if (!request) {
    return Promise.reject(new Error('HTTP client does not support request retry'));
  }
  return request(config);
}

/**
 * 设置 token 刷新拦截器
 * 在 401 响应时自动尝试刷新 token，刷新成功后重试原请求
 */
export function setupAuthInterceptor() {
  setResponseInterceptor(
    (response: HttpResponse) => response,
    async (error: HttpError) => {
      const originalRequest = error.config;

      // 非 401 错误直接抛出
      if (error.response?.status !== 401 || !originalRequest) {
        return Promise.reject(error);
      }

      const url = originalRequest.url || '';

      // 登录/刷新/公钥接口不处理
      if (shouldSkipRefresh(url)) {
        return Promise.reject(error);
      }

      // 已经重试过一次，不再重试
      if (originalRequest._retry) {
        markAuthExpired();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      // 没有 refresh token，直接跳转登录
      const refreshTokenValue = getStorage(STORAGE_KEYS.REFRESH_TOKEN);
      if (!refreshTokenValue) {
        markAuthExpired();
        window.location.href = '/login';
        return Promise.reject(error);
      }

      // 如果正在刷新，排队等待
      if (isRefreshing) {
        return new Promise<string>((resolve, reject) => {
          pendingRequests.push({ resolve, reject });
        }).then((newToken) => retryOriginalRequest(originalRequest, newToken));
      }

      // 开始刷新
      isRefreshing = true;
      originalRequest._retry = true;

      try {
        const { accessToken, refreshToken: newRefreshToken } = await refreshToken();

        // 存储新 token
        setToken(accessToken);
        setStorage(STORAGE_KEYS.REFRESH_TOKEN, newRefreshToken);
        resetTokenExpiredState();

        // 处理等待队列
        processPendingRequests(null, accessToken);

        // 重试原请求
        return retryOriginalRequest(originalRequest, accessToken);
      } catch (refreshError) {
        // 刷新失败，清除 token 跳转登录
        processPendingRequests(refreshError);
        markAuthExpired();
        localStorage.removeItem(STORAGE_KEYS.TOKEN);
        localStorage.removeItem(STORAGE_KEYS.REFRESH_TOKEN);
        window.location.href = '/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    },
  );
}
