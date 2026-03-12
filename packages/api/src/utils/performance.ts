/**
 * API 性能监控工具
 * 记录 API 调用耗时、超时次数、重试次数等性能指标
 */

/**
 * 性能指标数据
 */
export interface PerformanceMetrics {
  /** API 端点 */
  url: string;
  /** HTTP 方法 */
  method: string;
  /** 请求耗时（毫秒） */
  duration: number;
  /** 是否超时 */
  isTimeout: boolean;
  /** 是否重试过 */
  isRetried: boolean;
  /** 重试次数 */
  retryCount?: number;
  /** 成功或失败 */
  success: boolean;
  /** 错误信息 */
  error?: string;
  /** 时间戳 */
  timestamp: number;
}

/**
 * 性能统计摘要
 */
export interface PerformanceSummary {
  /** 总请求数 */
  totalRequests: number;
  /** 成功请求数 */
  successfulRequests: number;
  /** 失败请求数 */
  failedRequests: number;
  /** 超时请求数 */
  timeoutRequests: number;
  /** 重试请求数 */
  retriedRequests: number;
  /** 平均耗时（毫秒） */
  averageDuration: number;
  /** P95 耗时（毫秒） */
  p95Duration: number;
  /** P99 耗时（毫秒） */
  p99Duration: number;
}

/**
 * 性能监控类
 */
class PerformanceMonitor {
  private metrics: PerformanceMetrics[] = [];
  private maxMetricsCount = 1000; // 最多存储 1000 条记录
  private flushInterval = 60000; // 60 秒刷新一次
  private flushTimer: ReturnType<typeof setInterval> | null = null;

  constructor() {
    // 定期刷新数据到存储或后端
    this.startFlushTimer();
  }

  /**
   * 记录性能指标
   */
  record(metric: PerformanceMetrics): void {
    this.metrics.push(metric);

    // 限制存储数量
    if (this.metrics.length > this.maxMetricsCount) {
      this.metrics.shift();
    }

    // 发送到分析平台（如果可用）
    this.sendToAnalytics(metric);
  }

  /**
   * 记录成功请求
   */
  recordSuccess(
    url: string,
    method: string,
    duration: number,
    isTimeout: boolean = false,
    isRetried: boolean = false,
    retryCount: number = 0
  ): void {
    this.record({
      url,
      method,
      duration,
      isTimeout,
      isRetried,
      retryCount: isRetried ? retryCount : undefined,
      success: true,
      timestamp: Date.now(),
    });
  }

  /**
   * 记录失败请求
   */
  recordFailure(
    url: string,
    method: string,
    duration: number,
    error: string,
    isTimeout: boolean = false,
    isRetried: boolean = false,
    retryCount: number = 0
  ): void {
    this.record({
      url,
      method,
      duration,
      isTimeout,
      isRetried,
      retryCount: isRetried ? retryCount : undefined,
      success: false,
      error,
      timestamp: Date.now(),
    });
  }

  /**
   * 获取性能统计摘要
   */
  getSummary(urlPattern?: string): PerformanceSummary {
    let filteredMetrics = this.metrics;

    // 如果指定了 URL 模式，只统计匹配的请求
    if (urlPattern) {
      const regex = new RegExp(urlPattern);
      filteredMetrics = this.metrics.filter((m) => regex.test(m.url));
    }

    const totalRequests = filteredMetrics.length;
    if (totalRequests === 0) {
      return {
        totalRequests: 0,
        successfulRequests: 0,
        failedRequests: 0,
        timeoutRequests: 0,
        retriedRequests: 0,
        averageDuration: 0,
        p95Duration: 0,
        p99Duration: 0,
      };
    }

    const successfulRequests = filteredMetrics.filter((m) => m.success).length;
    const failedRequests = totalRequests - successfulRequests;
    const timeoutRequests = filteredMetrics.filter((m) => m.isTimeout).length;
    const retriedRequests = filteredMetrics.filter((m) => m.isRetried).length;

    const durations = filteredMetrics.map((m) => m.duration).sort((a, b) => a - b);
    const averageDuration = durations.reduce((sum, d) => sum + d, 0) / totalRequests;

    // 计算 P95 和 P99
    const p95Index = Math.floor(totalRequests * 0.95);
    const p99Index = Math.floor(totalRequests * 0.99);
    const p95Duration = durations[p95Index] || 0;
    const p99Duration = durations[p99Index] || 0;

    return {
      totalRequests,
      successfulRequests,
      failedRequests,
      timeoutRequests,
      retriedRequests,
      averageDuration,
      p95Duration,
      p99Duration,
    };
  }

  /**
   * 清空性能数据
   */
  clear(): void {
    this.metrics = [];
  }

  /**
   * 发送到分析平台
   */
  private sendToAnalytics(metric: PerformanceMetrics): void {
    try {
      if (typeof window !== 'undefined' && (window as any).analytics) {
        (window as any).analytics.track('api_performance', {
          url: metric.url,
          method: metric.method,
          duration: metric.duration,
          is_timeout: metric.isTimeout,
          is_retried: metric.isRetried,
          retry_count: metric.retryCount,
          success: metric.success,
          error: metric.error,
          timestamp: metric.timestamp,
        });
      }
    } catch (error) {
      // 静默失败
      console.debug('Failed to send to analytics:', error);
    }
  }

  /**
   * 启动定时刷新
   */
  private startFlushTimer(): void {
    if (this.flushTimer) return;

    this.flushTimer = setInterval(() => {
      // 定期刷新数据到本地存储或后端
      this.flushToStorage();
    }, this.flushInterval);
  }

  /**
   * 刷新数据到本地存储
   */
  private flushToStorage(): void {
    try {
      if (typeof window !== 'undefined' && window.localStorage) {
        const summary = this.getSummary();
        window.localStorage.setItem('api_performance_summary', JSON.stringify(summary));
      }
    } catch (error) {
      console.debug('Failed to flush to storage:', error);
    }
  }

  /**
   * 销毁监控实例
   */
  destroy(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
    this.clear();
  }
}

// 创建全局单例
const performanceMonitor = new PerformanceMonitor();

/**
 * 获取性能监控实例
 */
export function getPerformanceMonitor(): PerformanceMonitor {
  return performanceMonitor;
}

/**
 * API 请求计时器
 * 用于自动记录请求耗时
 */
export class ApiTimer {
  private startTime: number;
  private url: string;
  private method: string;
  private isTimeout: boolean = false;
  private isRetried: boolean = false;
  private retryCount: number = 0;

  constructor(url: string, method: string) {
    this.url = url;
    this.method = method;
    this.startTime = Date.now();
  }

  /**
   * 标记为超时
   */
  markAsTimeout(): void {
    this.isTimeout = true;
  }

  /**
   * 标记为已重试
   */
  markAsRetried(retryCount: number = 1): void {
    this.isRetried = true;
    this.retryCount = retryCount;
  }

  /**
   * 记录成功
   */
  recordSuccess(): void {
    const duration = Date.now() - this.startTime;
    performanceMonitor.recordSuccess(
      this.url,
      this.method,
      duration,
      this.isTimeout,
      this.isRetried,
      this.retryCount
    );
  }

  /**
   * 记录失败
   */
  recordFailure(error: string): void {
    const duration = Date.now() - this.startTime;
    performanceMonitor.recordFailure(
      this.url,
      this.method,
      duration,
      error,
      this.isTimeout,
      this.isRetried,
      this.retryCount
    );
  }

  /**
   * 获取当前耗时
   */
  getDuration(): number {
    return Date.now() - this.startTime;
  }
}

/**
 * 创建 API 计时器
 */
export function createApiTimer(url: string, method: string): ApiTimer {
  return new ApiTimer(url, method);
}

/**
 * 获取性能统计摘要
 */
export function getPerformanceSummary(urlPattern?: string): PerformanceSummary {
  return performanceMonitor.getSummary(urlPattern);
}

/**
 * 清空性能数据
 */
export function clearPerformanceData(): void {
  performanceMonitor.clear();
}
