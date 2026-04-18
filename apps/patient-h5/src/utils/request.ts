/**
 * API 请求配置 - 患者端 H5
 * 配置 @hospital/api 包的请求和响应拦截器
 * 
 * 功能：
 * 1. 自动添加 Authorization token
 * 2. 自动添加 store_id 参数（多门店隔离）
 * 3. 统一错误处理
 */
import { setRequestInterceptor, setResponseInterceptor } from '@hospital/api';
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
  return !EXCLUDE_STORE_ID_PATHS.some(path => url.includes(path));
};

/**
 * 检查是否需要添加 token
 */
const shouldAddToken = (url: string): boolean => {
  return !EXCLUDE_TOKEN_PATHS.some(path => url.includes(path));
};

/**
 * 配置请求拦截器
 * 自动在请求头中添加 Authorization token
 * 自动在请求参数中添加 store_id（多门店隔离）
 * 注意：登录相关接口不添加 token，避免携带过期 token 导致的问题
 */
export const setupRequestInterceptor = () => {
  setRequestInterceptor(
    (config: InternalAxiosRequestConfig) => {
      // 1. 添加 Authorization token（登录相关接口除外）
      if (config.url && shouldAddToken(config.url)) {
        const token = getToken();
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
      }
      
      // 2. 自动添加 store_id 参数（多门店隔离）
      const storeId = getStoreId();
      if (storeId && config.url && shouldAddStoreId(config.url)) {
        // 对于 GET 请求，添加到 params
        if (config.method?.toLowerCase() === 'get') {
          config.params = {
            ...config.params,
            store_id: storeId,
          };
        }
        // 对于其他请求（POST/PUT等），如果是需要门店过滤的列表查询，也添加到 params
        // 注意：创建/更新操作的 store_id 应该在业务代码中显式传递
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
      // 正常响应直接返回
      return response;
    },
    (error) => {
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
          return Promise.reject(new Error('登录已过期，请重新登录'));
        }
        
        // 403 禁止访问 — 检查是否为租户暂停
        if (status === 403) {
          const tenantReason = parseTenantError(data);
          if (tenantReason) {
            Dialog.alert({
              content: data?.message || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
              confirmText: '我知道了',
            });
            return Promise.reject(new Error(data?.message || '机构暂停服务'));
          }
          console.warn('没有权限访问该资源');
          return Promise.reject(new Error(data?.data?.detail || '没有权限访问'));
        }
        
        // 404 未找到
        if (status === 404) {
          console.warn('请求的资源不存在');
          return Promise.reject(new Error('请求的资源不存在'));
        }
        
        // 500 服务器错误
        if (status >= 500) {
          console.error('服务器错误:', data);
          return Promise.reject(new Error(data?.message || '服务器错误，请稍后重试'));
        }
      }
      
      // 网络错误
      if (!response) {
        console.error('网络错误，请检查网络连接');
        return Promise.reject(new Error('网络错误，请检查网络连接'));
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

