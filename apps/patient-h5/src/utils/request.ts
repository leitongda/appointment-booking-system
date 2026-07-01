/**
 * API 请求配置（患者端 H5）
 *
 * 本文件仅保留「患者端专有差异」：
 * - EXCLUDE_TOKEN_PATHS / EXCLUDE_STORE_ID_PATHS、store_id 注入（多门店隔离）；
 * - UI 反馈依赖（antd-mobile Toast / Dialog）；
 * - 401 登录过期流程（Toast + history.push，无 isProtectedRequest 过滤、无静默判定）；
 * - 403 租户暂停弹 Dialog.alert 停留（不跳页、不 markTenantSuspended）；
 * - 原始 Axios 路径各状态码文案高度定制 + 其他状态码 reject 原始 error（非 ApiError）。
 *
 * 其余共享骨架（token/store_id 注入、错误状态码分类分发、ApiError vs 原始 Axios 双路径、
 * 网络错误兜底）由 @hospital/api 的 createWebInterceptors() 工厂提供。
 *
 * 对外导出 setupRequestInterceptor / setupResponseInterceptor / initApiConfig 签名不变，
 * 调用点（MainLayout/index.tsx）零改动。
 */
import { createWebInterceptors, type RawAxiosErrorRenderer } from '@hospital/api';
import { ApiError, ERROR_MESSAGES } from '@hospital/api';
import {
  getToken,
  handleTokenExpired,
  markAuthExpired,
  STORE_CONTEXT_KEY,
  type StoreContext,
  parseTenantError,
} from '@hospital/shared';
import { history } from 'umi';
import { Toast, Dialog } from 'antd-mobile';
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
 * UI 反馈依赖（患者端用 antd-mobile Toast.show）
 * showError 包装为 Toast.show({icon:'fail', content: msg})，与瘦身高前一致。
 */
const errorDeps = {
  showError: (msg: string) => Toast.show({ icon: 'fail', content: msg }),
  showWarning: (opts: { message: string; description?: string; duration?: number }) =>
    Toast.show({ icon: 'fail', content: `${opts.message}${opts.description ? '：' + opts.description : ''}` }),
};

/**
 * 401 认证失效流程（患者端）：
 * markAuthExpired → handleTokenExpired(Toast + history.push)。
 * 不过滤 isProtectedRequest、不静默、无 rememberReturnPath（瘦身高前行为）。
 */
const triggerUnauthorized = (_message: string) => {
  markAuthExpired();
  handleTokenExpired(() => {
    Toast.show({ icon: 'fail', content: '登录已过期，请重新登录' });
    history.push('/login');
  });
};

const onUnauthorized = ({ message: _msg }: { requestUrl: string; message: string }) => {
  triggerUnauthorized(_msg);
};

/**
 * 403 租户暂停弹窗（患者端）：Dialog.alert 停留，不跳页、不 markTenantSuspended。
 */
const showTenantSuspendedDialog = (content: string) => {
  Dialog.alert({
    content,
    confirmText: '我知道了',
  });
};

const onTenantSuspended = ({ message }: { reason: ReturnType<typeof parseTenantError>; message: string }) => {
  showTenantSuspendedDialog(message);
};

/**
 * 原始 Axios 路径的端点级渲染（患者端）：完整接管各状态码分发，与瘦身高前逐字等价。
 *
 * 关键行为（不得抹平）：
 * - 401：固定文案 '登录已过期，请重新登录'，reject 对应 ApiError；
 * - 403 租户：Dialog.alert 用 data.message 兜底文案，reject ApiError(data.message || '机构暂停服务')；
 * - 403 非租户：console.warn + Toast(data.data.detail || data.message || '没有权限访问')；
 * - 404：console.warn + Toast(data.message || ERROR_MESSAGES[404])；
 * - 5xx：console.error + Toast(data.message || ERROR_MESSAGES[500])；
 * - 其他（400/409 等）：仅当 data.message 存在时 Toast，且 reject **原始 error**（非 ApiError）。
 */
const rawAxiosErrorRenderer: RawAxiosErrorRenderer = (status, data, requestUrl, error) => {
  // 401 未授权 - 清除 token 并跳转到登录页
  if (status === 401) {
    triggerUnauthorized('登录已过期，请重新登录');
    return new ApiError(status, '登录已过期，请重新登录', data, requestUrl);
  }

  // 403 禁止访问 — 检查是否为租户暂停
  if (status === 403) {
    const tenantReason = parseTenantError(data);
    if (tenantReason) {
      showTenantSuspendedDialog(
        data?.message || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
      );
      return new ApiError(status, data?.message || '机构暂停服务', data, requestUrl);
    }
    // 403 非租户场景：对齐 admin，给患者明确提示
    console.warn('没有权限访问该资源');
    const _403msg = data?.data?.detail || data?.message || '没有权限访问';
    Toast.show({ icon: 'fail', content: _403msg });
    return new ApiError(status, _403msg, data, requestUrl);
  }

  // 404 未找到 — 对齐 admin 提示用户
  if (status === 404) {
    console.warn('请求的资源不存在');
    const _404msg = data?.message || ERROR_MESSAGES[404];
    Toast.show({ icon: 'fail', content: _404msg });
    return new ApiError(status, _404msg, data, requestUrl);
  }

  // 500 服务器错误 — 必须告知用户
  if (status >= 500) {
    console.error('服务器错误:', data);
    const _500msg = data?.message || ERROR_MESSAGES[500];
    Toast.show({ icon: 'fail', content: _500msg });
    return new ApiError(status, _500msg, data, requestUrl);
  }

  // 其他 HTTP 错误状态码（如 400/409）：也提示用户，但 reject 原始 error（瘦身高前行为）
  if (data?.message) {
    Toast.show({ icon: 'fail', content: data.message });
  }
  return error; // 返回原始 error，工厂据此 Promise.reject(error)
};

/**
 * ApiError 路径下的额外副作用（患者端的 console.warn/console.error）。
 * 与瘦身高前顺序一致：先副作用后 Toast。
 */
const onApiErrorSideEffect = (
  kind: 'notFound' | 'serverError' | 'forbidden',
  apiError: ApiError,
) => {
  if (kind === 'forbidden') {
    console.warn('没有权限访问该资源');
  } else if (kind === 'notFound') {
    console.warn('请求的资源不存在');
  } else if (kind === 'serverError') {
    console.error('服务器错误:', apiError.data);
  }
};

// 创建拦截器（工厂内部注册到全局 axios 实例）
const interceptors = createWebInterceptors({
  excludeTokenPaths: EXCLUDE_TOKEN_PATHS,
  deps: errorDeps,
  // store_id 注入（患者端多门店隔离）
  injectStoreId: true,
  excludeStoreIdPaths: EXCLUDE_STORE_ID_PATHS,
  getStoreId,
  logRequestError: true, // 患者端瘦身前请求错误回调打印 console.error
  // 患者端 401 不过滤 isProtectedRequest（一律触发认证失效流程）
  filterUnauthorizedByProtectedRequest: false,
  // 患者端瘦身前注册了 (response) => response 成功处理器
  onResponseSuccess: (response: AxiosResponse) => response,
  onUnauthorized,
  onTenantSuspended,
  rawAxiosErrorRenderer,
  onApiErrorSideEffect,
  onNetworkErrorSideEffect: (msg) => console.error(msg), // 患者端网络错误回调内 console.error
  // 患者端不使用结构化错误码 / RSA 静默重试
  serverErrorMessageMode: 'preferBackend',
  serverErrorFallbackMessage: '服务器开小差了，请稍后重试', // 患者端 ApiError 路径 5xx 兜底文案
});

/**
 * 拦截器是否已注册（幂等保护，避免重复 apply 导致拦截器链重复）。
 */
let interceptorsApplied = false;

const applyOnce = () => {
  if (interceptorsApplied) return;
  interceptorsApplied = true;
  interceptors.apply();
};

/**
 * 配置请求拦截器
 * 自动在请求头中添加 Authorization token
 * 自动在请求参数中添加 store_id（多门店隔离）
 */
export const setupRequestInterceptor = () => {
  applyOnce();
};

/**
 * 配置响应拦截器
 * 处理统一的错误响应，如 401 未授权
 */
export const setupResponseInterceptor = () => {
  applyOnce();
};

/**
 * 初始化所有请求配置
 */
export const initApiConfig = () => {
  applyOnce();
  console.log('✓ API 请求配置已初始化（患者端）');
};

// 维持瘦身高前的 re-export 兼容性
export { ApiError, ERROR_MESSAGES, getToken };
