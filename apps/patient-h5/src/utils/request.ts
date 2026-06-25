/**
 * API 请求配置 - 患者端 H5
 * 配置 @hospital/api 包的请求和响应拦截器
 *
 * 功能：
 * 1. 自动添加 Authorization token
 * 2. 自动添加 store_id 参数（多门店隔离）
 * 3. 统一错误处理
 */
import {
  setRequestInterceptor,
  setResponseInterceptor,
  ApiError,
  ERROR_MESSAGES,
  getRequestPath,
  handleNetworkError,
} from '@hospital/api';
import { getToken, handleTokenExpired, markAuthExpired, STORE_CONTEXT_KEY, type StoreContext, parseTenantError } from '@hospital/shared';
import { history } from 'umi';
import { Toast, Dialog } from 'antd-mobile';
import type { InternalAxiosRequestConfig } from 'axios';
import type { AxiosResponse } from 'axios';

/**
 * 获取当前门店ID（从 localStorage）
 */
const getStoreId = (): string | null => {
  try {
    const stored = localStorage.getItem(STORE_CONTEXT_KEY);
    if (stored) {
      const context = JSON.parse(stored) as StoreContext;
      return context.storeId;
    }
  } catch {
    // ignore
  }
  return null;
};

/**
 * 不需要自动添加 store_id 的接口路径
 */
const EXCLUDE_STORE_ID_PATHS = [
  '/stores/by-code/',  // 门店验证接口本身不需要 store_id
  '/auth/',            // 认证相关接口
  '/analytics/',       // 分析接口
];

/**
 * 不需要自动添加 token 的接口路径
 * 登录、注册等认证相关接口不应该携带旧的 token
 */
const EXCLUDE_TOKEN_PATHS = [
  '/auth/login',
  '/auth/register',
  '/auth/wechat/login',
  '/auth/wechat/bind-phone',
];

/**
 * 检查是否需要添加 store_id
 */
const shouldAddStoreId = (url: string): boolean => {
  const requestPath = getRequestPath(url);
  return !EXCLUDE_STORE_ID_PATHS.some(path => requestPath.startsWith(path));
};

/**
 * 检查是否需要添加 token（使用精确路径匹配）
 */
const shouldAddTokenLocal = (url: string): boolean => {
  const requestPath = getRequestPath(url);
  return !EXCLUDE_TOKEN_PATHS.some(
    path => requestPath === path || requestPath.startsWith(path + '/')
  );
};

/**
 * 配置请求拦截器
 * 自动在请求头中添加 Authorization token
 * 自动在请求参数中添加 store_id（多门店隔离）
 */
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      // 1. 添加 Authorization token（登录相关接口除外）
      if (config.url && shouldAddTokenLocal(config.url)) {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }

      // 2. 自动添加 store_id 参数（多门店隔离）
      const storeId = getStoreId();
      if (storeId && config.url && shouldAddStoreId(config.url)) {
        if (config.method?.toLowerCase() === 'get') {
          config.params = {
            ...config.params,
            store_id: storeId,
          };
        }
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
 * 处理统一的错误响应，如 401 未授权
 */
export const setupResponseInterceptor = () => {
  setResponseInterceptor(
    (response: AxiosResponse) => {
      return response;
    },
    (error) => {
      // 处理 ApiError（@hospital/api 响应拦截器已解析的业务错误）
      if (error instanceof ApiError) {
        const { code: _code, message: errorMessage, url: requestUrl } = error;

        if (error.isUnauthorized()) {
          markAuthExpired();
          handleTokenExpired(() => {
            Toast.show({ icon: 'fail', content: '登录已过期，请重新登录' });
            history.push('/login');
          });
          return Promise.reject(error);
        }

        if (error.isForbidden()) {
          // 检查是否为租户暂停
          const tenantReason = parseTenantError(error);
          if (tenantReason) {
            Dialog.alert({
              content: errorMessage || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
              confirmText: '我知道了',
            });
            return Promise.reject(error);
          }
          console.warn('没有权限访问该资源');
          return Promise.reject(error);
        }

        if (error.isNotFound()) {
          console.warn('请求的资源不存在');
          return Promise.reject(error);
        }

        if (error.isServerError()) {
          console.error('服务器错误:', error.data);
          return Promise.reject(error);
        }

        return Promise.reject(error);
      }

      // 处理原始 Axios HTTP 错误
      const { response } = error;

      if (response) {
        const { status, data } = response;

        // 401 未授权 - 清除 token 并跳转到登录页
        if (status === 401) {
          markAuthExpired();
          handleTokenExpired(() => {
            Toast.show({ icon: 'fail', content: '登录已过期，请重新登录' });
            history.push('/login');
          });
          return Promise.reject(new ApiError(status, '登录已过期，请重新登录', data, error?.config?.url));
        }

        // 403 禁止访问 — 检查是否为租户暂停
        if (status === 403) {
          const tenantReason = parseTenantError(data);
          if (tenantReason) {
            Dialog.alert({
              content: data?.message || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
              confirmText: '我知道了',
            });
            return Promise.reject(new ApiError(status, data?.message || '机构暂停服务', data, error?.config?.url));
          }
          console.warn('没有权限访问该资源');
          return Promise.reject(new ApiError(status, data?.data?.detail || '没有权限访问', data, error?.config?.url));
        }

        // 404 未找到
        if (status === 404) {
          console.warn('请求的资源不存在');
          return Promise.reject(new ApiError(status, ERROR_MESSAGES[404], data, error?.config?.url));
        }

        // 500 服务器错误
        if (status >= 500) {
          console.error('服务器错误:', data);
          return Promise.reject(new ApiError(status, data?.message || ERROR_MESSAGES[500], data, error?.config?.url));
        }
      }

      // 网络错误
      if (!response && error instanceof Error) {
        handleNetworkError(error, (msg) => console.error(msg));
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
  console.log('✓ API 请求配置已初始化（患者端）');
};
