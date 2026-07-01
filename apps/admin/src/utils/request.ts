/**
 * API 请求配置（机构端）
 *
 * 本文件仅保留「机构端专有差异」：EXCLUDE_TOKEN_PATHS、UI 反馈依赖（antd
 * message/notification/Modal）、401 登录过期流程（Modal + window.location.href 跳转 +
 * isPublicEntryRoute/shouldSilenceAuthExpiredFeedback 静默判定 + rememberReturnPath 记忆回跳）、
 * 403 租户暂停跳 /tenant-suspended。其余共享骨架（token/X-Tenant-ID 注入、错误状态码分类分发、
 * ApiError vs 原始 Axios 双路径、结构化错误码、RSA 静默重试、网络错误兜底）由
 * @hospital/api 的 createWebInterceptors() 工厂提供。
 *
 * 对外导出 setupRequestInterceptor / setupResponseInterceptor / initApiConfig 签名不变，
 * 调用点（initApp.ts）零改动。
 */
import { createWebInterceptors, type RawAxiosErrorRenderer } from '@hospital/api';
import {
  ApiError,
  ERROR_MESSAGES,
  isRsaDecryptError,
} from '@hospital/api';
import {
  handleTokenExpired,
  markAuthExpired,
  shouldSilenceAuthExpiredFeedback,
  isPublicEntryRoute,
  parseTenantError,
  markTenantSuspended,
  rememberReturnPath,
} from '@hospital/shared';
import { message, Modal, notification } from 'antd';

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
 * 结构化错误码处理的 UI 依赖（message.error / notification.warning）
 */
const errorDeps = {
  showError: (msg: string) => message.error(msg),
  showWarning: (opts: { message: string; description?: string; duration?: number }) =>
    notification.warning(opts),
};

/**
 * 401 登录过期 Modal（机构端专用：window.location.href 跳 /login）
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
      window.location.href = '/login';
    },
  });
};

/**
 * 401 认证失效流程（机构端）：
 * markAuthExpired → 静默判定（登录页/根路径/无 token 仅清理不弹框）→
 * rememberReturnPath → handleTokenExpired(Modal 跳 /login)
 *
 * 注意：工厂已在外层完成 isProtectedRequest（登录接口不触发）过滤，此处无需再判。
 */
const onUnauthorized = ({ message: errorMessage }: { requestUrl: string; message: string }) => {
  markAuthExpired();

  // 登录页/根路径下绝不弹认证失效 Modal，仅静默清理 token。
  // shouldSilenceAuthExpiredFeedback 覆盖"公共入口页"与"已无 token"两种场景。
  if (shouldSilenceAuthExpiredFeedback() || isPublicEntryRoute()) {
    handleTokenExpired();
    return;
  }

  // 在清理 token / 弹框跳转前记忆当前业务页，供重新登录后回跳。
  // 必须在 handleTokenExpired（内部 removeToken）之前调用，否则 onPageChange
  // 短路分支不会写入 LAST_PATH。
  rememberReturnPath();

  handleTokenExpired(() => showLoginExpiredModal(errorMessage));
};

/**
 * 403 租户暂停（机构端）：markTenantSuspended + window.location.href 跳 /tenant-suspended
 */
const onTenantSuspended = ({ reason }: { reason: ReturnType<typeof parseTenantError>; message: string }) => {
  if (reason) {
    markTenantSuspended(reason);
    window.location.href = '/tenant-suspended';
  }
};

/**
 * 原始 Axios 路径下 RSA 解密失败需要静默重试的登录接口片段
 */
const RSA_LOGIN_PATH_GLOBS = ['/admin/login', '/admin/phone-login'];

/**
 * 原始 Axios 路径的端点级渲染：机构端与默认分发一致，但需保证返回的 ApiError
 * 携带结构化错误信封字段（errorCode/errorDetails），与瘦身高前逐字等价。
 * 这里返回 undefined 交回工厂默认分发（工厂已正确构造 ApiError 含结构化字段）。
 *
 * 注：admin 瘦身前的原始 Axios 路径用 errorMsg 链路 = detail || message || statusFallback，
 * 与工厂默认 axiosErrorMessageChain 一致，故无需覆盖。
 */
const rawAxiosErrorRenderer: RawAxiosErrorRenderer = () => undefined;

// 创建拦截器（工厂内部注册到全局 axios 实例）
const interceptors = createWebInterceptors({
  excludeTokenPaths: EXCLUDE_TOKEN_PATHS,
  deps: errorDeps,
  injectTenantHeader: true,
  onUnauthorized,
  onTenantSuspended,
  useStructuredErrorCode: true,
  useRsaRetry: true,
  rsaLoginPathGlobs: RSA_LOGIN_PATH_GLOBS,
  serverErrorMessageMode: 'fallback',
  axiosErrorMessageChain: ['detail', 'message', 'statusFallback'],
  rawAxiosErrorRenderer,
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
 * 自动在请求头中添加 Authorization token 与 X-Tenant-ID（登录相关接口不添加 token）
 *
 * 注意：工厂 apply() 同时注册请求与响应拦截器，此处通过 applyOnce 幂等保护。
 */
export const setupRequestInterceptor = () => {
  applyOnce();
};

/**
 * 配置响应拦截器
 * 处理 API 业务错误和 HTTP 错误，提供用户友好的错误提示
 *
 * 工厂 apply() 已一并注册响应拦截器；保留本导出仅为维持对外签名不变
 * （initApp.ts 仅调用 initApiConfig，历史调用点可能单独调用本函数）。
 */
export const setupResponseInterceptor = () => {
  applyOnce();
};

/**
 * 初始化所有请求配置
 */
export const initApiConfig = () => {
  applyOnce();
  console.log('✓ API 请求配置已初始化');
};

// 保持对 ApiError / ERROR_MESSAGES / isRsaDecryptError 的 re-export，
// 供 admin 内其他模块（如有）按原路径导入。这些符号原本即来自 @hospital/api，
// 此处显式 re-export 维持瘦身高前的导入兼容性。
export { ApiError, ERROR_MESSAGES, isRsaDecryptError };
