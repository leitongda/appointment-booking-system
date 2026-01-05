/**
 * 请求去重工具
 *
 * 用于防止并发相同请求，减少服务器压力
 */

interface PendingRequest {
  promise: Promise<any>;
  timestamp: number;
}

/**
 * 请求去重器类
 */
class RequestDeduplicator {
  /** 待处理请求 Map */
  private pendingRequests = new Map<string, PendingRequest>();

  /** 请求超时时间（毫秒），默认10秒 */
  private readonly timeout: number;

  constructor(timeout = 10000) {
    this.timeout = timeout;
  }

  /**
   * 去重请求
   *
   * 如果有相同的请求正在进行，则返回现有请求的 Promise
   * 否则创建新请求并缓存
   *
   * @param key 请求唯一标识
   * @param requestFn 请求函数
   * @returns 请求结果
   *
   * @example
   * ```ts
   * const data = await requestDeduplicator.dedupe(
   *   `departments-${status}`,
   *   () => departmentApi.getList({ pageSize: 200, status })
   * );
   * ```
   */
  async dedupe<T>(key: string, requestFn: () => Promise<T>): Promise<T> {
    // 检查是否有相同请求正在进行
    const pending = this.pendingRequests.get(key);

    if (pending) {
      const { promise, timestamp } = pending;

      // 检查请求是否超时
      if (Date.now() - timestamp > this.timeout) {
        // 超时则移除旧请求，创建新请求
        this.pendingRequests.delete(key);
      } else {
        // 返回进行中的请求
        return promise;
      }
    }

    // 创建新请求
    const promise = requestFn()
      .finally(() => {
        // 请求完成后清理缓存
        this.pendingRequests.delete(key);
      });

    // 缓存请求
    this.pendingRequests.set(key, {
      promise,
      timestamp: Date.now(),
    });

    return promise;
  }

  /**
   * 取消指定请求
   *
   * @param key 请求唯一标识
   */
  cancel(key: string): void {
    this.pendingRequests.delete(key);
  }

  /**
   * 取消所有请求
   */
  cancelAll(): void {
    this.pendingRequests.clear();
  }

  /**
   * 获取当前待处理的请求数量
   */
  getPendingCount(): number {
    return this.pendingRequests.size;
  }

  /**
   * 获取所有待处理的请求键
   */
  getPendingKeys(): string[] {
    return Array.from(this.pendingRequests.keys());
  }

  /**
   * 清理超时的请求
   */
  cleanup(): void {
    const now = Date.now();
    const keys = Array.from(this.pendingRequests.keys());

    keys.forEach(key => {
      const pending = this.pendingRequests.get(key);
      if (pending && (now - pending.timestamp) > this.timeout) {
        this.pendingRequests.delete(key);
      }
    });
  }
}

/**
 * 全局请求去重器实例
 */
export const requestDeduplicator = new RequestDeduplicator();

/**
 * 定期清理超时请求（每分钟）
 */
if (typeof window !== 'undefined') {
  setInterval(() => {
    requestDeduplicator.cleanup();
  }, 60 * 1000);
}

/**
 * 创建带去重的请求函数
 *
 * @param keyFn 生成请求键的函数
 * @param requestFn 请求函数
 * @returns 带去重的请求函数
 *
 * @example
 * ```ts
 * const getDepartures = createDedupeRequest(
 *   (params) => `departments-${params.status}`,
 *   (params) => departmentApi.getList(params)
 * );
 *
 * // 使用
 * const data = await getDepartures({ pageSize: 200, status: 1 });
 * ```
 */
export function createDedupeRequest<P extends any[], R>(
  keyFn: (...args: P) => string,
  requestFn: (...args: P) => Promise<R>
): (...args: P) => Promise<R> {
  return (...args: P) => {
    const key = keyFn(...args);
    return requestDeduplicator.dedupe(key, () => requestFn(...args));
  };
}
