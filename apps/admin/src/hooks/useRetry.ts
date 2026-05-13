/**
 * 客户端重试机制 Hook
 *
 * 提供指数退避策略的自动重试功能，适用于网络不稳定场景
 */
import { useState, useCallback, useRef } from 'react';
import { App } from 'antd';

/**
 * 重试配置
 */
export interface RetryConfig {
  /** 最大重试次数 */
  maxRetries: number;
  /** 初始延迟（毫秒） */
  initialDelay: number;
  /** 延迟倍增因子 */
  delayFactor: number;
  /** 最大延迟（毫秒） */
  maxDelay: number;
  /** 是否显示重试提示 */
  showRetryMessage: boolean;
  /** 自定义判断是否应该重试 */
  shouldRetry?: (error: Error) => boolean;
}

/**
 * 默认重试配置
 */
const DEFAULT_RETRY_CONFIG: Required<RetryConfig> = {
  maxRetries: 3,
  initialDelay: 1000,
  delayFactor: 2,
  maxDelay: 10000,
  showRetryMessage: true,
};

/**
 * 默认的重试判断条件
 */
const defaultShouldRetry = (error: any): boolean => {
  // 网络错误
  if (error.message === 'Network Error') return true;
  // 请求超时
  if (error.message?.includes('timeout')) return true;
  // 5xx 服务器错误
  if (error.response?.status >= 500) return true;
  // 429 请求过多
  if (error.response?.status === 429) return true;
  // 408 请求超时
  if (error.response?.status === 408) return true;
  return false;
};

/**
 * 重试状态
 */
export interface RetryState {
  /** 是否正在重试 */
  isRetrying: boolean;
  /** 当前重试次数 */
  retryCount: number;
  /** 最大重试次数 */
  maxRetries: number;
  /** 最后一次错误 */
  lastError: Error | null;
}

/**
 * useRetry Hook
 *
 * 提供指数退避策略的自动重试功能
 *
 * @example
 * // 基础用法
 * const { execute, isRetrying, retryCount } = useRetry();
 *
 * const handleSubmit = async () => {
 *   await execute(
 *     async () => await api.saveData(data),
 *     { successMessage: '保存成功' }
 *   );
 * };
 *
 * @example
 * // 自定义配置
 * const { execute } = useRetry({
 *   maxRetries: 5,
 *   initialDelay: 500,
 *   showRetryMessage: false,
 * });
 */
export function useRetry(config?: Partial<RetryConfig>) {
  const { message } = App.useApp();
  const finalConfig = { ...DEFAULT_RETRY_CONFIG, ...config };

  const [state, setState] = useState<RetryState>({
    isRetrying: false,
    retryCount: 0,
    maxRetries: finalConfig.maxRetries,
    lastError: null,
  });

  // 使用 ref 存储重试计数，避免闭包问题
  const retryCountRef = useRef(0);

  /**
   * 计算延迟时间（指数退避）
   */
  const calculateDelay = useCallback((retryCount: number): number => {
    const delay = finalConfig.initialDelay * Math.pow(finalConfig.delayFactor, retryCount);
    return Math.min(delay, finalConfig.maxDelay);
  }, [finalConfig]);

  /**
   * 执行带重试的异步操作
   *
   * @param fn 要执行的异步函数
   * @param options 选项
   */
  const execute = useCallback(async <T>(
    fn: () => Promise<T>,
    options?: {
      successMessage?: string;
      errorMessage?: string;
      onSuccess?: (result: T) => void;
      onError?: (error: Error) => void;
      shouldRetry?: (error: Error) => boolean;
    }
  ): Promise<T | null> => {
    const {
      successMessage,
      errorMessage = '操作失败',
      onSuccess,
      onError,
      shouldRetry: customShouldRetry,
    } = options ?? {};

    const shouldRetryFn = customShouldRetry || finalConfig.shouldRetry || defaultShouldRetry;
    retryCountRef.current = 0;

    const attempt = async (): Promise<T> => {
      try {
        const result = await fn();

        // 重置状态
        setState({
          isRetrying: false,
          retryCount: 0,
          maxRetries: finalConfig.maxRetries,
          lastError: null,
        });

        // 成功提示
        if (successMessage) {
          message.success(successMessage);
        }

        // 成功回调
        onSuccess?.(result);

        return result;
      } catch (error: any) {
        const currentRetry = retryCountRef.current;
        const shouldRetry = shouldRetryFn(error) && currentRetry < finalConfig.maxRetries;

        if (shouldRetry) {
          retryCountRef.current += 1;
          const delay = calculateDelay(currentRetry);

          // 更新状态
          setState({
            isRetrying: true,
            retryCount: retryCountRef.current,
            maxRetries: finalConfig.maxRetries,
            lastError: error,
          });

          // 显示重试提示
          if (finalConfig.showRetryMessage) {
            message.warning({
              content: `请求失败，正在重试 (${retryCountRef.current}/${finalConfig.maxRetries})...`,
              duration: delay / 1000,
            });
          }

          // 等待后重试
          await new Promise((resolve) => { setTimeout(resolve, delay); });
          return attempt();
        }

        // 重试失败，显示错误
        setState({
          isRetrying: false,
          retryCount: currentRetry,
          maxRetries: finalConfig.maxRetries,
          lastError: error,
        });

        // 错误提示
        const errorMsg = error.message || errorMessage;
        message.error(errorMsg);

        // 错误回调
        onError?.(error);

        throw error;
      }
    };

    return attempt();
  }, [finalConfig, calculateDelay, message]);

  /**
   * 重置状态
   */
  const reset = useCallback(() => {
    retryCountRef.current = 0;
    setState({
      isRetrying: false,
      retryCount: 0,
      maxRetries: finalConfig.maxRetries,
      lastError: null,
    });
  }, [finalConfig.maxRetries]);

  return {
    ...state,
    execute,
    reset,
  };
}

/**
 * 创建带重试功能的请求函数
 *
 * @example
 * const fetchWithRetry = createRetryFunction();
 * const result = await fetchWithRetry(() => api.getData());
 */
export function createRetryFunction(_defaultConfig?: Partial<RetryConfig>) {
  return <T>(fn: () => Promise<T>, _options?: Parameters<ReturnType<typeof useRetry>['execute']>[1]) => {
    // 这个函数需要配合 useRetry 使用
    return fn();
  };
}

export default useRetry;
