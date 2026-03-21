/**
 * API 重试机制
 * 为幂等操作（GET 请求）提供自动重试和指数退避策略
 */

import { AxiosInstance, AxiosRequestConfig, AxiosError } from 'axios';

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
  /** 自定义判断函数：决定是否重试（默认只重试网络错误和 5xx） */
  shouldRetry?: (error: AxiosError) => boolean;
}

/**
 * 默认重试配置
 */
const DEFAULT_RETRY_OPTIONS: Required<RetryOptions> = {
  maxRetries: 3,
  retryDelay: 1000, // 1s
  retryDelayFactor: 2, // 指数退避：1s, 2s, 4s
  logRetry: true,
  shouldRetry: (error: AxiosError) => {
    // 默认重试条件：
    // 1. 网络错误（无响应）
    // 2. 5xx 服务器错误
    // 3. 408 请求超时
    const isNetworkError = !error.response;
    const isServerError = error.response?.status ? error.response.status >= 500 : false;
    const isTimeout = error.response?.status === 408;

    return isNetworkError || isServerError || isTimeout;
  },
};

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

  // 请求拦截器：初始化重试计数
  instance.interceptors.request.use((requestConfig) => {
    // 只为幂等操作（GET、HEAD）添加重试支持
    const isIdempotent = ['GET', 'HEAD'].includes((requestConfig.method || '').toUpperCase());

    if (isIdempotent) {
      (requestConfig as any)._retry = 0;
      (requestConfig as any)._retryConfig = config;
      (requestConfig as any)._isIdempotent = true;
    }

    return requestConfig;
  }, undefined);

  // 响应拦截器：处理重试逻辑
  instance.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const requestConfig = error.config as any;

      // 检查是否应该重试
      if (!requestConfig?._isIdempotent) {
        return Promise.reject(error);
      }

      const retryConfig = requestConfig._retryConfig as Required<RetryOptions>;
      const currentRetry = requestConfig._retry || 0;

      // 判断是否应该重试
      if (currentRetry < retryConfig.maxRetries && retryConfig.shouldRetry(error)) {
        requestConfig._retry = currentRetry + 1;

        // 计算延迟时间（指数退避）
        const delay = retryConfig.retryDelay * Math.pow(retryConfig.retryDelayFactor, currentRetry);

        // 记录重试日志
        if (retryConfig.logRetry) {
          console.warn(
            `[API Retry] 请求重试 (${currentRetry + 1}/${retryConfig.maxRetries}): ` +
            `${requestConfig.method?.toUpperCase()} ${requestConfig.url} - ` +
            `延迟 ${delay}ms`
          );
        }

        // 发送监控埋点（重试事件）
        trackRetryEvent({
          url: requestConfig.url,
          method: requestConfig.method,
          retryCount: currentRetry + 1,
          maxRetries: retryConfig.maxRetries,
          delay,
          error: error.message,
        });

        // 标记计时器为已重试
        if ((requestConfig as any)._timer) {
          (requestConfig as any)._timer.markAsRetried(currentRetry + 1);
        }

        // 等待后重试
        await new Promise((resolve) => setTimeout(resolve, delay));

        return instance(requestConfig);
      }

      // 达到最大重试次数，发送失败埋点
      if (currentRetry >= retryConfig.maxRetries && retryConfig.logRetry) {
        console.error(
          `[API Retry] 重试失败: ${requestConfig.method?.toUpperCase()} ${requestConfig.url} - ` +
          `已重试 ${currentRetry} 次`
        );

        trackRetryFailedEvent({
          url: requestConfig.url,
          method: requestConfig.method,
          retryCount: currentRetry,
          error: error.message,
        });
      }

      return Promise.reject(error);
    }
  );
}

/**
 * 重试事件数据
 */
interface RetryEventData {
  url?: string;
  method?: string;
  retryCount: number;
  maxRetries: number;
  delay: number;
  error?: string;
}

/**
 * 重试失败事件数据
 */
interface RetryFailedEventData {
  url?: string;
  method?: string;
  retryCount: number;
  error?: string;
}

/**
 * 发送重试事件埋点
 * 集成到现有 analytics 系统（如果可用）
 */
function trackRetryEvent(data: RetryEventData): void {
  // 这里可以集成到现有的 analytics 系统
  // 如果有全局埋点工具，可以在这里调用
  try {
    // 示例：发送到分析平台
    if (typeof window !== 'undefined' && (window as any).analytics) {
      (window as any).analytics.track('api_retry', {
        url: data.url,
        method: data.method,
        retry_count: data.retryCount,
        max_retries: data.maxRetries,
        delay: data.delay,
        error: data.error,
        timestamp: Date.now(),
      });
    }
  } catch (error) {
    // 静默失败，不影响业务
    console.debug('Failed to track retry event:', error);
  }
}

/**
 * 发送重试失败埋点
 */
function trackRetryFailedEvent(data: RetryFailedEventData): void {
  try {
    if (typeof window !== 'undefined' && (window as any).analytics) {
      (window as any).analytics.track('api_retry_failed', {
        url: data.url,
        method: data.method,
        retry_count: data.retryCount,
        error: data.error,
        timestamp: Date.now(),
      });
    }
  } catch (error) {
    console.debug('Failed to track retry failed event:', error);
  }
}

/**
 * 为特定请求设置自定义重试配置
 *
 * @param config axios 请求配置
 * @param options 重试配置
 */
export function withRetry(
  config: AxiosRequestConfig,
  options: RetryOptions = {}
): AxiosRequestConfig {
  const isIdempotent = ['GET', 'HEAD'].includes((config.method || '').toUpperCase());

  if (!isIdempotent) {
    console.warn('[API Retry] 警告：仅为幂等操作（GET、HEAD）启用重试，当前方法不会重试');
  }

  return {
    ...config,
    // @ts-ignore - 添加自定义属性
    _isIdempotent: isIdempotent,
    // @ts-ignore
    _retry: 0,
    // @ts-ignore
    _retryConfig: { ...DEFAULT_RETRY_OPTIONS, ...options },
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
 * 实际应用中可以配合后端上报或本地存储
 */
export function getRetryStats(): RetryStats {
  // 这里可以从本地存储或内存中获取统计信息
  // 简单实现，返回默认值
  return {
    totalRetries: 0,
    totalFailures: 0,
    averageRetryCount: 0,
  };
}
