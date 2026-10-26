/**
 * API 请求配置（医生端）
 *
 * 本文件仅保留「医生端专有差异」：EXCLUDE_TOKEN_PATHS、UI 反馈依赖（antd
 * message/Modal）、401 登录过期流程（Modal + history.push 跳转，无 isPublicEntryRoute
 * 判定、无 rememberReturnPath）、403 租户暂停跳 /tenant-suspended、请求错误回调不打印
 * console.error。其余共享骨架（token 注入、错误状态码分类分发、ApiError vs 原始 Axios
 * 双路径、网络错误兜底）由 @hospital/api 的 createWebInterceptors() 工厂提供。
 *
 * 对外导出 setupRequestInterceptor / setupResponseInterceptor / initApiConfig 签名不变，
 * 调用点（app.tsx）零改动。
 */
import { createWebInterceptors, type RawAxiosErrorRenderer } from '@hospital/api';
import { ApiError, ERROR_MESSAGES } from '@hospital/api';
import {
  handleTokenExpired,
  markAuthExpired,
  shouldSilenceAuthExpiredFeedback,
  parseTenantError,
  markTenantSuspended,
} from '@hospital/shared';
import { history } from 'umi';
import { message, Modal } from 'antd';
import { hardNavigate } from './hardNavigate';

/**
 * 不需要自动添加 token 的接口路径
 */
const EXCLUDE_TOKEN_PATHS = [
  '/doctors/login',
  '/auth/login',
  '/auth/register',
];

/**
 * UI 反馈依赖（医生端仅用 message.error，showWarning 退化为 showError）
 */
const errorDeps = {
  showError: (msg: string) => message.error(msg),
  showWarning: (opts: { message: string; description?: string; duration?: number }) =>
    message.error(`${opts.message}${opts.description ? '：' + opts.description : ''}`),
};

/**
 * 401 登录过期 Modal（医生端专用：history.push 跳 /login）
 */
const showLoginExpiredModal = (content: string) => {
  Modal.confirm({
    title: '登录已过期',
    content: content || '您的登录已失效，请重新登录。',
    okText: '重新登录',
    cancelButtonProps: { style: { display: 'none' } },
    closable: false,
    maskClosable: false,
    onOk: () => {
      Modal.destroyAll();
      history.push('/login');
    },
  });
};

/**
 * 401 认证失效流程（医生端）：
 * markAuthExpired → shouldSilenceAuthExpiredFeedback 静默判定（无 isPublicEntryRoute）→
 * handleTokenExpired(Modal 跳 /login)。无 rememberReturnPath。
 *
 * 工厂已在外层完成 isProtectedRequest 过滤，此处无需再判。
 */
const onUnauthorized = ({ message: errorMessage }: { requestUrl: string; message: string }) => {
  markAuthExpired();

  if (shouldSilenceAuthExpiredFeedback()) {
    handleTokenExpired();
    return;
  }

  handleTokenExpired(() => showLoginExpiredModal(errorMessage));
};

/**
 * 403 租户暂停（医生端）：markTenantSuspended + hardNavigate 整页跳 /tenant-suspended
 */
const onTenantSuspended = ({ reason }: { reason: ReturnType<typeof parseTenantError>; message: string }) => {
  if (reason) {
    markTenantSuspended(reason);
    hardNavigate('/tenant-suspended');
  }
};

/**
 * 原始 Axios 路径的端点级渲染（医生端）：
 * 医生端瘦身前的原始 Axios 路径对 403/404/5xx 分别处理，且 5xx 使用
 * ERROR_MESSAGES[status]（而非后端 errorMsg），401 由工厂默认路径处理（onUnauthorized）。
 * 此 renderer 仅接管 403/404/5xx/其他，对 401 返回 undefined 交回工厂。
 */
const rawAxiosErrorRenderer: RawAxiosErrorRenderer = (status, data, requestUrl) => {
  if (status === 401) return undefined; // 交回工厂默认 401 处理

  const errorMsg =
    data?.detail || data?.data?.detail || data?.message || ERROR_MESSAGES[status] || '请求失败';

  if (status === 403) {
    const tenantReason = parseTenantError(data);
    if (tenantReason) {
      onTenantSuspended({
        reason: tenantReason,
        message: data?.message || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
      });
      return new ApiError(status, errorMsg, data, requestUrl);
    }
    message.error(errorMsg);
    return new ApiError(status, errorMsg, data, requestUrl);
  }

  if (status === 404) {
    message.error(errorMsg);
    return new ApiError(status, errorMsg, data, requestUrl);
  }

  if (status >= 500) {
    message.error(ERROR_MESSAGES[status] || ERROR_MESSAGES[500]);
    return new ApiError(status, errorMsg, data, requestUrl);
  }

  message.error(errorMsg);
  return new ApiError(status, errorMsg, data, requestUrl);
};

// 创建拦截器（工厂内部注册到全局 axios 实例）
const interceptors = createWebInterceptors({
  excludeTokenPaths: EXCLUDE_TOKEN_PATHS,
  deps: errorDeps,
  // 医生端不注入 X-Tenant-ID，也不注入 store_id
  logRequestError: false, // 医生端瘦身前请求错误回调仅 reject，不打印 console.error
  onUnauthorized,
  onTenantSuspended,
  rawAxiosErrorRenderer,
  // 医生端不使用结构化错误码 / RSA 静默重试
  serverErrorMessageMode: 'fallback',
  // 医生端原始 Axios 消息链（renderer 内同样使用）：detail || data.detail || message || statusFallback
  axiosErrorMessageChain: ['detail', 'data.detail', 'message', 'statusFallback'],
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
 */
export const setupRequestInterceptor = () => {
  applyOnce();
};

/**
 * 配置响应拦截器
 */
export const setupResponseInterceptor = () => {
  applyOnce();
};

/**
 * 初始化所有请求配置
 */
export const initApiConfig = () => {
  applyOnce();
};

// 维持瘦身高前的 re-export 兼容性（ApiError / ERROR_MESSAGES 原本即来自 @hospital/api）
export { ApiError, ERROR_MESSAGES };
