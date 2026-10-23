/**
 * Web 拦截器工厂 —— admin / doctor / patient-h5 三端 request.ts 的共享骨架。
 *
 * 设计目标：
 * 1. 收敛三端 ~90% 相同的拦截器骨架（token 注入、错误状态码分类分发、
 *    ApiError vs 原始 Axios 双路径、网络错误兜底、ApiError 构造）。
 * 2. 各端差异通过 options / deps 注入，**绝不抹平**。
 * 3. packages/api 保持零 UI 依赖：禁止 import 'antd' / 'antd-mobile' / 'umi'。
 *    所有 UI 反馈（showError/showWarning）与导航（onUnauthorized/onTenantSuspended）
 *    由调用端通过 deps / options 注入。
 *
 * 行为契约：工厂内部各分支必须与瘦身前三端逐字等价，差异点全部参数化。
 *
 * 注意：本文件依赖 @hospital/shared（packages/api 本就依赖 shared），复用其
 * getToken / parseTenantError / handleTokenExpired 等工具，绝不复制粘贴。
 */

import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios';
import {
  getToken,
  getStorage,
  STORAGE_KEYS,
  parseTenantError,
} from '@hospital/shared';
import { ApiError, setRequestInterceptor, setResponseInterceptor } from './request';
import {
  ERROR_MESSAGES,
  getRequestPath,
  shouldAddToken,
  handleStructuredErrorCode,
  isRsaDecryptError,
  handleNetworkError,
  type ErrorHandlingDeps,
} from './utils/error-handling';

// ─── UI / 导航依赖（由调用端注入） ────────────────────────────────

/**
 * 各端注入的 UI 反馈方法。
 * showError：显示一条错误消息（admin/doctor 用 message.error，patient-h5 用 Toast.show）。
 * showWarning：显示一条带描述的警告通知（admin 用 notification.warning；未提供时退化为 showError）。
 */
export type WebInterceptorDeps = ErrorHandlingDeps;

// ─── 工厂配置 ─────────────────────────────────────────────────────

/**
 * 401（认证失效）处理上下文 —— 传给 onUnauthorized 回调，由各端决定
 * 是否过滤登录接口、是否静默、是否记忆回跳路径、用何种 UI / 导航方式。
 */
export interface UnauthorizedContext {
  /** 该次请求的 URL（已尽力从 error.url / config.url 提取），可能为空串 */
  requestUrl: string;
  /** 用户可见的错误消息（后端 message 或默认 401 文案） */
  message: string;
}

/**
 * 403（租户暂停）处理上下文 —— 传给 onTenantSuspended 回调，由各端决定
 * 跳转 /tenant-suspended（admin/doctor）还是弹 Dialog 停留（patient-h5）。
 */
export interface TenantSuspendedContext {
  /** parseTenantError 解析出的暂停原因 */
  reason: ReturnType<typeof parseTenantError>;
  /** 用户可见消息（ApiError 路径用 errorMessage，原始 Axios 路径用 data.message 或默认文案） */
  message: string;
}

/**
 * 原始 Axios 错误的端点级渲染覆盖（patient-h5 使用）。
 *
 * patient-h5 的各状态码文案高度定制（401→'登录已过期，请重新登录'、403→门店暂停特定文案、
 * 404/5xx 优先用后端 message、其他状态码仅当 data.message 存在时提示，且其他状态码 reject
 * 的是原始 axios error 而非 ApiError），无法用统一的「消息提取链」表达，故提供此钩子让
 * patient-h5 完整接管原始 Axios 路径的状态码分发。
 *
 * 返回值语义：
 * - 返回非 undefined（可为 ApiError 或原始 error）：工厂直接 `Promise.reject(返回值)`，
 *   即「用该值 reject」。patient-h5 对「其他状态码」返回原始 error 以保持瘦身高前行为。
 * - 返回 undefined：交回工厂默认分发（admin/doctor 走此路径）。
 */
export type RawAxiosErrorRenderer = (
  status: number,
  data: any,
  requestUrl: string,
  error: any,
) => any | undefined;

/**
 * createWebInterceptors 配置项。
 */
export interface WebInterceptorOptions {
  /** 不自动注入 Bearer token 的路径（登录/注册/公钥等）。各端不同。 */
  excludeTokenPaths: string[];

  /** UI 反馈依赖（showError / showWarning）。 */
  deps: WebInterceptorDeps;

  // ── 请求拦截器：token 之外的注入（各端差异） ──

  /**
   * 是否注入 X-Tenant-ID Header（从 localStorage 读取 CURRENT_TENANT_ID）。
   * 仅 admin 开启。默认 false。
   */
  injectTenantHeader?: boolean;

  /**
   * 是否注入 store_id 到 GET 请求参数（多门店隔离）。
   * 仅 patient-h5 开启。开启时需提供 excludeStoreIdPaths 与 getStoreId。
   * 默认 false。
   */
  injectStoreId?: boolean;

  /** 不自动注入 store_id 的路径（门店验证/认证/分析等）。仅 injectStoreId 时生效。 */
  excludeStoreIdPaths?: string[];

  /** store_id 取值函数（patient-h5 提供其原有 getStoreId 实现）。 */
  getStoreId?: () => string | null;

  /**
   * 请求拦截器的 error 回调是否打印 console.error('请求错误:', error)。
   * admin / patient-h5 瘦身前为 true；doctor 瘦身前为 false（仅 reject）。
   * 默认 true（与多数端一致）。
   */
  logRequestError?: boolean;

  /**
   * 401 处理前是否按 shouldAddToken(requestUrl, excludeTokenPaths) 过滤「受保护请求」。
   * admin / doctor 瘦身前为 true（登录接口不触发认证失效流程）；
   * patient-h5 瘦身前为 false（无论请求 URL 一律触发 markAuthExpired + 跳登录）。
   * 默认 true。
   */
  filterUnauthorizedByProtectedRequest?: boolean;

  /**
   * 响应成功拦截器（对应 setResponseInterceptor 的 onFulfilled）。
   * admin / doctor 瘦身前传 undefined（不处理成功响应）；
   * patient-h5 瘦身前传 (response) => response。默认 undefined。
   */
  onResponseSuccess?: (response: AxiosResponse) => any;

  // ── 响应拦截器：401 / 403 的副作用回调（各端差异显著，不抹平） ──

  /**
   * 401 认证失效回调。工厂已判定该请求「应触发认证失效流程」
   * （即 isProtectedRequest 为 true，登录接口等被排除的请求不会触发本回调）。
   *
   * 各端在此完成自己的副作用：
   * - admin：markAuthExpired → 静默判定(isPublicEntryRoute/shouldSilenceAuthExpiredFeedback)
   *          → rememberReturnPath → handleTokenExpired(Modal + window.location.href)
   * - doctor：markAuthExpired → shouldSilenceAuthExpiredFeedback →
   *          handleTokenExpired(Modal + history.push)
   * - patient-h5：markAuthExpired → handleTokenExpired(Toast + history.push)，不过滤不静默
   */
  onUnauthorized?: (ctx: UnauthorizedContext) => void;

  /**
   * 403 租户暂停回调（已通过 parseTenantError 判定为租户暂停时触发）。
   * 各端在此完成自己的副作用：
   * - admin/doctor：markTenantSuspended(reason) + 跳转 /tenant-suspended
   * - patient-h5：Dialog.alert 停留，不跳页（不调用 markTenantSuspended）
   */
  onTenantSuspended?: (ctx: TenantSuspendedContext) => void;

  // ── 响应拦截器：可选的额外错误处理分支（admin 专有） ──

  /**
   * 是否在两条路径上都先调用 handleStructuredErrorCode 处理结构化错误码。
   * 仅 admin 开启。默认 false（doctor / patient-h5 瘦身前不调用）。
   */
  useStructuredErrorCode?: boolean;

  /**
   * 是否处理 RSA 解密失败的静默重试分支（400 + isRsaDecryptError + 登录接口）。
   * 仅 admin 开启。开启时需提供 rsaLoginPathGlobs。默认 false。
   */
  useRsaRetry?: boolean;

  /** RSA 重试分支判定登录接口时使用的路径片段（如 ['/admin/login', '/admin/phone-login']）。 */
  rsaLoginPathGlobs?: string[];

  /**
   * 5xx 服务器错误的用户可见消息来源。
   * - 'fallback'（默认，admin/doctor）：ERROR_MESSAGES[code] || serverErrorFallbackMessage
   * - 'preferBackend'（patient-h5）：errorMessage || serverErrorFallbackMessage
   */
  serverErrorMessageMode?: 'fallback' | 'preferBackend';

  /**
   * 5xx 服务器错误的兜底文案。
   * admin / doctor / patient-h5(原始 Axios) 为 ERROR_MESSAGES[500] = '服务器错误，请稍后重试'；
   * patient-h5(ApiError 路径) 瘦身前为 '服务器开小差了，请稍后重试'。
   * 默认 ERROR_MESSAGES[500]。
   */
  serverErrorFallbackMessage?: string;

  /**
   * 原始 Axios 路径下提取用户消息的链路。
   * - admin（默认）：['detail', 'message', 'statusFallback']（最终兜底 '请求失败'）
   * - doctor：['detail', 'data.detail', 'message', 'statusFallback']
   */
  axiosErrorMessageChain?: ('detail' | 'data.detail' | 'message' | 'statusFallback')[];

  /**
   * 原始 Axios 错误的端点级渲染覆盖（patient-h5 使用）。
   * 提供时优先于 axiosErrorMessageChain 与工厂默认的状态码分发。
   */
  rawAxiosErrorRenderer?: RawAxiosErrorRenderer;

  /**
   * ApiError 路径下的额外副作用钩子（patient-h5 的 console.warn/console.error）。
   * 默认 undefined（admin/doctor 无此行为）。
   */
  onApiErrorSideEffect?: (
    kind: 'notFound' | 'serverError' | 'forbidden',
    error: ApiError,
  ) => void;

  /**
   * 网络错误的额外副作用钩子（patient-h5 在 handleNetworkError 回调内 console.error）。
   * 默认 undefined。
   */
  onNetworkErrorSideEffect?: (msg: string) => void;
}

// ─── 工厂内部工具 ─────────────────────────────────────────────────

/** patient-h5 的 store_id 注入判定（startsWith 匹配排除路径）。 */
const shouldAddStoreId = (url: string, excludePaths: string[]): boolean => {
  const requestPath = getRequestPath(url);
  return !excludePaths.some((path) => requestPath.startsWith(path));
};

/** 原始 Axios 路径下，按链路提取用户消息。 */
const extractAxiosMessage = (
  data: any,
  status: number,
  chain: ('detail' | 'data.detail' | 'message' | 'statusFallback')[],
): string => {
  for (const step of chain) {
    if (step === 'detail' && data?.detail) return data.detail;
    if (step === 'data.detail' && data?.data?.detail) return data.data.detail;
    if (step === 'message' && data?.message) return data.message;
    if (step === 'statusFallback') {
      const m = ERROR_MESSAGES[status];
      if (m) return m;
    }
  }
  return '请求失败';
};

// ─── 工厂返回 ─────────────────────────────────────────────────────

export interface WebInterceptors {
  /** 注册请求 + 响应拦截器到全局 axios 实例。 */
  apply: () => void;
}

// ─── 工厂主入口 ───────────────────────────────────────────────────

export function createWebInterceptors(options: WebInterceptorOptions): WebInterceptors {
  const {
    excludeTokenPaths,
    deps,
    injectTenantHeader = false,
    injectStoreId = false,
    excludeStoreIdPaths = [],
    getStoreId,
    logRequestError = true,
    filterUnauthorizedByProtectedRequest = true,
    onResponseSuccess,
    onUnauthorized,
    onTenantSuspended,
    useStructuredErrorCode = false,
    useRsaRetry = false,
    rsaLoginPathGlobs = [],
    serverErrorMessageMode = 'fallback',
    serverErrorFallbackMessage = ERROR_MESSAGES[500],
    axiosErrorMessageChain = ['detail', 'message', 'statusFallback'],
    rawAxiosErrorRenderer,
    onApiErrorSideEffect,
    onNetworkErrorSideEffect,
  } = options;

  // ── 请求拦截器 ──
  const applyRequestInterceptor = () => {
    setRequestInterceptor(
      (config: InternalAxiosRequestConfig) => {
        // 1. token 注入（三端共有；登录相关接口除外）
        if (config.url && shouldAddToken(config.url, excludeTokenPaths)) {
          const token = getToken();
          if (token) {
            config.headers.Authorization = `Bearer ${token}`;
          }
        }

        // 2. X-Tenant-ID 注入（仅 admin）
        if (injectTenantHeader) {
          const currentTenantId = getStorage<string>(STORAGE_KEYS.CURRENT_TENANT_ID);
          if (currentTenantId) {
            config.headers['X-Tenant-ID'] = currentTenantId;
          }
        }

        // 3. store_id 注入（仅 patient-h5，仅 GET，且不在排除路径）
        if (injectStoreId && getStoreId) {
          const storeId = getStoreId();
          if (storeId && config.url && shouldAddStoreId(config.url, excludeStoreIdPaths)) {
            if (config.method?.toLowerCase() === 'get') {
              config.params = {
                ...config.params,
                store_id: storeId,
              };
            }
          }
        }

        return config;
      },
      (error) => {
        if (logRequestError) {
          console.error('请求错误:', error);
        }
        return Promise.reject(error);
      },
    );
  };

  // ── 401 统一入口：可选做 isProtectedRequest 过滤，副作用交回调 ──
  const handleUnauthorized = (requestUrl: string, message: string) => {
    if (filterUnauthorizedByProtectedRequest) {
      const isProtectedRequest = !requestUrl || shouldAddToken(requestUrl, excludeTokenPaths);
      if (!isProtectedRequest) {
        // 登录接口等被排除的请求：不触发认证失效流程（admin/doctor 行为）。
        return;
      }
    }
    // patient-h5 瘦身前无此过滤，一律触发认证失效流程。
    onUnauthorized?.({ requestUrl, message });
  };

  // ── 响应拦截器：ApiError 路径 ──
  const handleApiError = (error: ApiError): ApiError => {
    const { code, message: errorMessage } = error;

    // 403 + 租户暂停：必须先于结构化错误码分支判定（R4-9）。
    // handleStructuredErrorCode 会把 TENANT_* 视为「已处理」，若放在前面，
    // onTenantSuspended 永远不会触发，admin 也就不会跳 /tenant-suspended。
    if (error.isForbidden()) {
      const tenantReason = parseTenantError(error);
      if (tenantReason) {
        onTenantSuspended?.({
          reason: tenantReason,
          message: errorMessage || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
        });
        return error;
      }
    }

    // 结构化错误码（仅 admin）
    if (useStructuredErrorCode && handleStructuredErrorCode(error, deps)) {
      return error;
    }

    // 401
    if (error.isUnauthorized()) {
      const requestUrl = error.url || '';
      handleUnauthorized(requestUrl, errorMessage);
      return error;
    }

    // 403（非租户暂停）
    if (error.isForbidden()) {
      onApiErrorSideEffect?.('forbidden', error);
      deps.showError(errorMessage || ERROR_MESSAGES[403]);
      return error;
    }

    // 404
    if (error.isNotFound()) {
      onApiErrorSideEffect?.('notFound', error);
      deps.showError(errorMessage || ERROR_MESSAGES[404]);
      return error;
    }

    // 5xx
    if (error.isServerError()) {
      onApiErrorSideEffect?.('serverError', error);
      const msg =
        serverErrorMessageMode === 'preferBackend'
          ? errorMessage || serverErrorFallbackMessage
          : ERROR_MESSAGES[code] || serverErrorFallbackMessage;
      deps.showError(msg);
      return error;
    }

    // RSA 解密失败静默重试（仅 admin）
    if (useRsaRetry && code === 400 && errorMessage && isRsaDecryptError(errorMessage)) {
      const requestUrl = error.url || '';
      if (rsaLoginPathGlobs.some((g) => requestUrl.includes(g))) {
        return error;
      }
    }

    // 其他业务错误
    if (errorMessage) {
      deps.showError(errorMessage);
    }
    return error;
  };

  // ── 响应拦截器：原始 Axios 路径 ──
  const handleRawAxiosError = (error: any): any => {
    const response = error?.response;
    if (response) {
      const { status, data } = response;
      const requestUrl = error?.config?.url || error?.request?.responseURL || '';

      // 端点级渲染覆盖（patient-h5：各状态码文案高度定制，完整接管）
      if (rawAxiosErrorRenderer) {
        const rendered = rawAxiosErrorRenderer(status, data, requestUrl, error);
        if (rendered) {
          return Promise.reject(rendered);
        }
      }

      const structuredError = data?.error;
      const errorCode = structuredError?.code || data?.error_code;
      const errorDetails = structuredError?.details;
      const errorMsg = extractAxiosMessage(data, status, axiosErrorMessageChain);

      const apiError = new ApiError(status, errorMsg, data, requestUrl, errorCode, errorDetails);

      // 403 + 租户暂停：必须先于结构化错误码分支判定（R4-9）。
      // 否则 TENANT_* 会被 handleStructuredErrorCode 提前吞掉。
      if (status === 403) {
        const tenantReason = parseTenantError(data);
        if (tenantReason) {
          onTenantSuspended?.({
            reason: tenantReason,
            message: data?.message || '该机构订阅已到期，暂不支持新预约，请联系机构续费。',
          });
          return Promise.reject(apiError);
        }
      }

      // 结构化错误码（仅 admin）
      if (useStructuredErrorCode && handleStructuredErrorCode(apiError, deps)) {
        return Promise.reject(apiError);
      }

      // 401
      if (status === 401) {
        handleUnauthorized(requestUrl, errorMsg);
        return Promise.reject(apiError);
      }

      // RSA 解密失败静默重试（仅 admin）
      if (useRsaRetry && status === 400 && errorMsg && isRsaDecryptError(errorMsg)) {
        if (rsaLoginPathGlobs.some((g) => requestUrl.includes(g))) {
          return Promise.reject(apiError);
        }
      }

      // 兜底：显示消息
      deps.showError(errorMsg);
      return Promise.reject(apiError);
    }

    // 网络错误
    if (error instanceof Error) {
      handleNetworkError(error, (msg) => {
        onNetworkErrorSideEffect?.(msg);
        deps.showError(msg);
      });
      return Promise.reject(error);
    }

    return Promise.reject(error);
  };

  const applyResponseInterceptor = () => {
    setResponseInterceptor(
      onResponseSuccess,
      (error: any) => {
        if (error instanceof ApiError) {
          return Promise.reject(handleApiError(error));
        }
        return handleRawAxiosError(error);
      },
    );
  };

  return {
    apply: () => {
      applyRequestInterceptor();
      applyResponseInterceptor();
    },
  };
}
