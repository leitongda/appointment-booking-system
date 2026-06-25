/**
 * API 重试机制
 * 为幂等操作（GET 请求）提供自动重试、指数退避、抖动和端点级熔断策略
 */

import type { AxiosInstance, AxiosRequestConfig } from 'axios';

type AxiosError = any;

// ─── 端点熔断器 ─────────────────────────────────────────────

/** 端点熔断器配置 */
interface CircuitBreakerOptions {
  /** 同一端点连续失败多少次后触发熔断，默认 5 */
  failureThreshold: number;
  /** 熔断持续时间（毫秒），默认 30000（30 秒） */
  resetDuration: number;
  /** 最多存储多少个端点的熔断状态，默认 100 */
  maxEntries: number;
}

class EndpointCircuitBreaker {
  private failures = new Map<string, { count: number; openUntil: number }>();
  private options: Required<CircuitBreakerOptions>;

  constructor(options: Partial<CircuitBreakerOptions> = {}) {
    const defaults: Required<CircuitBreakerOptions> = {
      failureThreshold: 5,
      resetDuration: 30000,
      maxEntries: 100,
    };
    this.options = { ...defaults, ...options };
  }

  /** 记录一次失败，返回该端点的连续失败次数 */
  recordFailure(endpoint: string): number {
    const entry = this.failures.get(endpoint) ?? { count: 0, openUntil: 0 };
    entry.count += 1;

    if (entry.count >= this.options.failureThreshold) {
      entry.openUntil = Date.now() + this.options.resetDuration;
    }

    this.failures.set(endpoint, entry);

    // LRU 淘汰，防止内存泄漏
    if (this.failures.size > this.options.maxEntries) {
      const oldestKey = this.failures.keys().next().value;
      if (oldestKey !== undefined) this.failures.delete(oldestKey);
    }

    return entry.count;
  }

  /** 记录成功，重置该端点的连续失败计数 */
  recordSuccess(endpoint: string): void {
    this.failures.delete(endpoint);
  }

  /** 该端点当前是否处于熔断状态 */
  isOpen(endpoint: string): boolean {
    const entry = this.failures.get(endpoint);
    if (!entry) return false;
    // openUntil > 0 表示已触发熔断，检查是否已过期
    if (entry.openUntil > 0 && Date.now() >= entry.openUntil) {
      this.failures.delete(endpoint);
      return false;
    }
    // openUntil > 0 且未过期 → 熔断中；openUntil === 0 → 尚未触发，不熔断
    return entry.openUntil > 0;
  }
}

// ─── 公共类型 ───────────────────────────────────────────────

/**
 * 重试配置选项
 */
export interface RetryOptions {
  /** 最大重试次数（默认 3） */
  maxRetries?: number;
  /** 初始重试延迟（毫秒，默认 1000ms） */
  retryDelay?: number;
  /** 延迟倍增因子（默认 2，实现指数退避：1s, 2s, 4s） */
  retryDelayFactor?: number;
  /** 是否记录重试日志（默认 true） */
  logRetry?: boolean;
  /** 自定义判断函数：决定是否重试（默认重试网络错误、5xx、408、429） */
  shouldRetry?: (error: AxiosError) => boolean;
  /** 重试延迟上限（毫秒，默认 30000） */
  maxDelay?: number;
  /** 是否在延迟中添加随机抖动（默认 true，防止 thundering herd） */
  enableJitter?: boolean;
  /** 是否启用端点级熔断（默认 true） */
  enableCircuitBreaker?: boolean;
  /** 熔断器配置（仅在 enableCircuitBreaker=true 时生效） */
  circuitBreaker?: Partial<CircuitBreakerOptions>;
}

const RETRY_OPTION_KEYS: Array<keyof RetryOptions> = [
  'maxRetries',
  'retryDelay',
  'retryDelayFactor',
  'logRetry',
  'shouldRetry',
  'maxDelay',
  'enableJitter',
  'enableCircuitBreaker',
  'circuitBreaker',
];

// ─── 不可重试的 HTTP 状态码 ────────────────────────────────────

/** 认证/授权类错误，永远不应被重试 */
const NOT_RETRYABLE_STATUSES = new Set([401, 403]);

// ─── 全局重试预算（滑动窗口限流） ────────────────────────────

const RETRY_BUDGET_WINDOW_MS = 30_000; // 30 秒滑动窗口
const MAX_GLOBAL_RETRIES_PER_WINDOW = 50;
const globalRetryTimestamps: number[] = [];

function hasRetryBudget(): boolean {
  const now = Date.now();
  while (globalRetryTimestamps.length > 0) {
    const firstTimestamp = globalRetryTimestamps[0];
    if (firstTimestamp !== undefined && firstTimestamp < now - RETRY_BUDGET_WINDOW_MS) {
      globalRetryTimestamps.shift();
    } else {
      break;
    }
  }
  return globalRetryTimestamps.length < MAX_GLOBAL_RETRIES_PER_WINDOW;
}

function consumeRetryBudget(): void {
  globalRetryTimestamps.push(Date.now());
}

// ─── 默认配置 ───────────────────────────────────────────────

const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  retryDelay: 1000,
  retryDelayFactor: 2,
  logRetry: true,
  maxDelay: 30000,
  enableJitter: true,
  enableCircuitBreaker: true,
  circuitBreaker: {
    failureThreshold: 5,
    resetDuration: 30000,
    maxEntries: 100,
  },
  shouldRetry: (error: AxiosError) => {
    const isNetworkError = !error.response;
    const isServerError = error.response?.status ? error.response.status >= 500 : false;
    const isTimeout = error.response?.status === 408;
    const isRateLimited = error.response?.status === 429;
    return isNetworkError || isServerError || isTimeout || isRateLimited;
  },
};

// ─── 辅助函数 ───────────────────────────────────────────────

/** 从请求配置中提取端点标识 (METHOD + path) */
function getEndpointKey(requestConfig: any): string {
  const method = (requestConfig.method || 'GET').toUpperCase();
  const url = (requestConfig.url || '').split('?')[0];
  return `${method} ${url}`;
}

/** 计算 429 响应中 Retry-After 的毫秒值，无则返回 0 */
function parseRetryAfterMs(error: AxiosError): number {
  // 优先从 header 读取
  const headerValue = error.response?.headers?.['retry-after'];
  if (headerValue != null) {
    const parsed = Number(headerValue);
    if (!isNaN(parsed) && parsed > 0) return parsed * 1000;
  }
  // 回退到响应体
  const data = error.response?.data as any;
  if (data?.data?.retry_after) {
    const parsed = Number(data.data.retry_after);
    if (!isNaN(parsed) && parsed > 0) return parsed * 1000;
  }
  return 0;
}

/** 带取消支持的延迟等待，响应 AbortController 的 abort 信号 */
function delayWithAbort(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      return reject(new DOMException('Aborted', 'AbortError'));
    }

    const timer = setTimeout(() => {
      if (signal) signal.removeEventListener('abort', onAbort);
      resolve();
    }, ms);

    const onAbort = () => {
      clearTimeout(timer);
      reject(new DOMException('Aborted', 'AbortError'));
    };

    if (signal) {
      signal.addEventListener('abort', onAbort, { once: true });
    }
  });
}

/** 计算最终延迟（含 jitter + maxDelay + Retry-After） */
function computeDelay(
  retryCount: number,
  retryDelay: number,
  retryDelayFactor: number,
  maxDelay: number,
  enableJitter: boolean,
  is429: boolean,
  retryAfterMs: number,
): number {
  let delay = retryDelay * Math.pow(retryDelayFactor, retryCount);
  delay = Math.min(delay, maxDelay);
  if (enableJitter) {
    delay += delay * 0.2 * Math.random(); // +0~20% 随机抖动
  }
  if (is429 && retryAfterMs > 0) {
    delay = Math.max(delay, retryAfterMs);
  }
  return delay;
}

// ─── 重试状态外部跟踪 ─────────────────────────────────────────

/** 自增请求 ID，用于跨 mergeConfig 追踪重试状态 */
let nextRetryId = 0;

/**
 * 外部重试状态表。
 * key = _retryId（数字，会被 mergeConfig 原样复制），
 * value = { count, retryConfig, createdAt }。
 * 彻底摆脱对 config 上自定义属性持久化的依赖。
 */
const retryStateMap = new Map<number, {
  count: number;
  retryConfig: Required<RetryOptions>;
  createdAt: number;
}>();

// ── 孤立状态清理（防止 abort 导致的内存泄漏）──
const STATE_TTL_MS = 60_000; // 60 秒后视为孤立状态
const STATE_CLEANUP_INTERVAL = 30_000; // 每 30 秒清理一次

const _cleanupTimer = setInterval(() => {
  const now = Date.now();
  for (const [id, state] of retryStateMap) {
    if (now - state.createdAt > STATE_TTL_MS) {
      retryStateMap.delete(id);
    }
  }
}, STATE_CLEANUP_INTERVAL);
// Node.js 环境下不阻塞进程退出
if (typeof (_cleanupTimer as any)?.unref === 'function') {
  (_cleanupTimer as any).unref();
}

// ─── 核心：拦截器注册 ───────────────────────────────────────

/**
 * 为 axios 实例添加重试拦截器
 *
 * @param instance axios 实例
 * @param options 重试配置
 */
export function setupRetryInterceptor(
  instance: AxiosInstance,
  options: RetryOptions = {}
): void {
  const config = { ...DEFAULT_RETRY_OPTIONS, ...options };
  // 合并嵌套的 circuitBreaker 配置
  if (config.enableCircuitBreaker) {
    config.circuitBreaker = {
      ...DEFAULT_RETRY_OPTIONS.circuitBreaker,
      ...options.circuitBreaker,
    };
  }

  // 创建熔断器实例（闭包内共享）
  const circuitBreaker = config.enableCircuitBreaker
    ? new EndpointCircuitBreaker(config.circuitBreaker)
    : null;

  // ── 请求拦截器：为幂等请求分配唯一 retryId ──
  instance.interceptors.request.use((requestConfig: any) => {
    const isIdempotent = ['GET', 'HEAD'].includes((requestConfig.method || '').toUpperCase());

    if (isIdempotent) {
      // 从 config 属性和 params 备份读取（params 经 mergeConfig 深合并，不会丢失）
      const existingRetryId = (requestConfig as any)._retryId ?? requestConfig.params?.__retry_rid;

      if (!existingRetryId) {
        const id = ++nextRetryId;
        // 合并自定义选项（来自 withRetry）和全局默认
        const customOptions = (requestConfig as any)._retryOptions as RetryOptions | undefined;
        const finalRetryConfig = customOptions
          ? {
            ...config,
            ...customOptions,
            ...(customOptions.circuitBreaker && {
              circuitBreaker: { ...config.circuitBreaker, ...customOptions.circuitBreaker },
            }),
          }
          : config;
        retryStateMap.set(id, { count: 0, retryConfig: finalRetryConfig, createdAt: Date.now() });
        // 双写到 config 属性 + params 备份
        (requestConfig as any)._retryId = id;
        requestConfig.params = { ...requestConfig.params, __retry_rid: id };
      } else {
        // 恢复可能被 mergeConfig 吞掉的 config 属性
        if (!(requestConfig as any)._retryId) {
          (requestConfig as any)._retryId = existingRetryId;
        }
      }

      // _isIdempotent 也写到 params 备份（错误拦截器依赖它判断是否重试）
      requestConfig.params = {
        ...requestConfig.params,
        __retry_idem: 1,
      };
      (requestConfig as any)._isIdempotent = true;
    }

    return requestConfig;
  }, undefined);

  // ── 响应拦截器：成功时通知熔断器并清理状态 ──
  instance.interceptors.response.use(
    (response: any) => {
      if (circuitBreaker) {
        const endpoint = getEndpointKey(response.config);
        circuitBreaker.recordSuccess(endpoint);
      }
      // 成功 → 清理重试状态
      const retryId = (response.config as any)?._retryId ?? (response.config as any)?.params?.__retry_rid;
      if (retryId) retryStateMap.delete(retryId);
      return response;
    },
    async (error: AxiosError) => {
      const requestConfig = error.config as any;

      // 非幂等操作不重试（从 config 属性和 params 备份中读取）
      const isIdempotent = requestConfig?._isIdempotent || requestConfig?.params?.__retry_idem;
      if (!isIdempotent) {
        return Promise.reject(error);
      }

      // 从 config 属性和 params 备份中读取 retryId
      const retryId = (requestConfig._retryId ?? requestConfig.params?.__retry_rid) as number | undefined;
      const state = retryId ? retryStateMap.get(retryId) : undefined;

      // 没有重试状态或 retryId 丢失（不应该发生），直接拒绝
      if (!retryId || !state) {
        return Promise.reject(error);
      }

      const { retryConfig } = state;
      const currentRetry = state.count;
      const endpoint = getEndpointKey(requestConfig);

      // ── 硬性保护：认证/授权错误永远不重试 ──
      const errorStatus = error.response?.status;
      if (errorStatus && NOT_RETRYABLE_STATUSES.has(errorStatus)) {
        if (retryConfig.logRetry) {
          console.warn(
            `[API Retry] 认证/授权错误 (${errorStatus})，跳过重试: ${endpoint}`
          );
        }
        retryStateMap.delete(retryId);
        return Promise.reject(error);
      }

      // ── 全局重试预算检查 ──
      if (!hasRetryBudget()) {
        if (retryConfig.logRetry) {
          console.warn(
            `[API Retry] 全局重试预算耗尽 (${MAX_GLOBAL_RETRIES_PER_WINDOW}/${RETRY_BUDGET_WINDOW_MS / 1000}s)，跳过重试: ${endpoint}`
          );
        }
        retryStateMap.delete(retryId);
        return Promise.reject(error);
      }

      // 端点熔断检查
      if (circuitBreaker && circuitBreaker.isOpen(endpoint)) {
        if (retryConfig.logRetry) {
          console.warn(`[API Retry] 端点已熔断，跳过重试: ${endpoint}`);
        }
        retryStateMap.delete(retryId);
        return Promise.reject(error);
      }

      // 判断是否应该重试
      if (currentRetry < retryConfig.maxRetries && retryConfig.shouldRetry(error)) {
        state.count = currentRetry + 1;
        consumeRetryBudget();

        const is429 = error.response?.status === 429;
        const retryAfterMs = is429 ? parseRetryAfterMs(error) : 0;

        const delay = computeDelay(
          currentRetry,
          retryConfig.retryDelay,
          retryConfig.retryDelayFactor,
          retryConfig.maxDelay,
          retryConfig.enableJitter,
          is429,
          retryAfterMs,
        );

        // 记录重试日志
        if (retryConfig.logRetry) {
          console.warn(
            `[API Retry] 请求重试 (${state.count}/${retryConfig.maxRetries}): ` +
            `${endpoint} - 延迟 ${Math.round(delay)}ms` +
            (is429 ? ' (429 限流)' : '')
          );
        }

        // 发送监控埋点
        trackRetryEvent({
          url: requestConfig.url,
          method: requestConfig.method,
          retryCount: state.count,
          maxRetries: retryConfig.maxRetries,
          delay,
          error: error.message,
        });

        // 标记计时器为已重试并记录当前尝试的失败
        if (requestConfig._timer) {
          requestConfig._timer.markAsRetried(state.count);
          requestConfig._timer.recordFailure(error.message);
        }

        // 等待后重试（支持 AbortController 取消）
        try {
          await delayWithAbort(delay, requestConfig?.signal as AbortSignal | undefined);
        } catch {
          // 请求被取消，清理状态，不再重试
          retryStateMap.delete(retryId);
          return Promise.reject(error);
        }

        return instance(requestConfig);
      }

      // 达到最大重试次数或不应重试，记录失败到熔断器
      if (retryConfig.shouldRetry(error)) {
        circuitBreaker?.recordFailure(endpoint);
      }

      // 达到最大重试次数，发送失败埋点
      if (currentRetry >= retryConfig.maxRetries && retryConfig.logRetry) {
        console.error(
          `[API Retry] 重试失败: ${endpoint} - 已重试 ${currentRetry} 次`
        );

        trackRetryFailedEvent({
          url: requestConfig.url,
          method: requestConfig.method,
          retryCount: currentRetry,
          error: error.message,
        });
      }

      // 清理状态
      retryStateMap.delete(retryId);
      return Promise.reject(error);
    }
  );
}

// ─── 监控埋点（保持原有实现） ────────────────────────────────

interface RetryEventData {
  url?: string;
  method?: string;
  retryCount: number;
  maxRetries: number;
  delay: number;
  error?: string;
}

interface RetryFailedEventData {
  url?: string;
  method?: string;
  retryCount: number;
  error?: string;
}

function trackRetryEvent(data: RetryEventData): void {
  try {
    if (typeof window === 'undefined') return;
    const tracker = window.__hospital_tracker__;
    if (!tracker?.trackEvent) return;
    tracker.trackEvent('api_retry', {
      url: data.url,
      method: data.method,
      retry_count: data.retryCount,
      max_retries: data.maxRetries,
      delay: data.delay,
      error: data.error,
    });
  } catch {
    // 静默失败
  }
}

function trackRetryFailedEvent(data: RetryFailedEventData): void {
  try {
    if (typeof window === 'undefined') return;
    const tracker = window.__hospital_tracker__;
    if (!tracker?.trackEvent) return;
    tracker.trackEvent('api_retry_failed', {
      url: data.url,
      method: data.method,
      retry_count: data.retryCount,
      error: data.error,
    });
  } catch {
    // 静默失败
  }
}

// ─── 公共工具函数 ───────────────────────────────────────────

/**
 * 为特定请求设置自定义重试配置
 *
 * @param axiosConfig axios 请求配置
 * @param options 重试配置
 */
export function withRetry(
  options?: RetryOptions
): AxiosRequestConfig;
export function withRetry(
  axiosConfig: AxiosRequestConfig,
  options?: RetryOptions
): AxiosRequestConfig;
export function withRetry(
  axiosConfigOrOptions: AxiosRequestConfig | RetryOptions = {},
  options: RetryOptions = {}
): AxiosRequestConfig {
  const useOptionsOnly =
    Object.keys(options).length === 0 &&
    RETRY_OPTION_KEYS.some((key) => key in axiosConfigOrOptions);

  const axiosConfig = (useOptionsOnly ? {} : axiosConfigOrOptions) as AxiosRequestConfig;
  const retryOptions = (useOptionsOnly ? axiosConfigOrOptions : options) as RetryOptions;
  const method = (axiosConfig.method || 'GET').toUpperCase();
  const isIdempotent = ['GET', 'HEAD'].includes(method);

  if (!isIdempotent) {
    console.warn('[API Retry] 警告：仅为幂等操作（GET、HEAD）启用重试，当前方法不会重试');
  }

  return {
    ...axiosConfig,
    // @ts-ignore - 添加自定义属性
    _isIdempotent: isIdempotent,
    // @ts-ignore - 自定义重试配置，由 request interceptor 读取
    _retryOptions: retryOptions,
  };
}

/**
 * 监控统计接口
 */
export interface RetryStats {
  totalRetries: number;
  totalFailures: number;
  averageRetryCount: number;
}

/**
 * 获取重试统计信息（简单实现）
 */
export function getRetryStats(): RetryStats {
  return {
    totalRetries: 0,
    totalFailures: 0,
    averageRetryCount: 0,
  };
}
