/**
 * 性能数据上报器
 * 负责将采集的性能数据上报到服务端
 */

import type { PerformanceMetric, RouteMetric } from './metrics';

/**
 * 上报配置
 */
export interface ReportConfig {
  /** 上报地址 */
  endpoint?: string;
  /** 批量上报间隔（毫秒） */
  flushInterval?: number;
  /** 批量上报数量阈值 */
  batchSize?: number;
  /** 是否启用上报 */
  enabled?: boolean;
  /** 获取当前会话 ID 的回调（注入 Tracker session_id） */
  getSessionId?: () => string;
}

/**
 * 性能数据上报包
 */
export interface PerformanceReport {
  /** 页面 URL */
  pageUrl: string;
  /** 用户代理 */
  userAgent: string;
  /** 屏幕信息 */
  screen: {
    width: number;
    height: number;
    dpr: number;
  };
  /** 时间戳 */
  timestamp: number;
  /** 会话 ID（与行为追踪共享） */
  sessionId?: string;
  /** Core Web Vitals 指标 */
  metrics: PerformanceMetric[];
  /** 路由指标 */
  routeMetrics: RouteMetric[];
}

/**
 * 上报器类
 */
class PerformanceReporter {
  private config: Required<ReportConfig>;
  private pendingMetrics: PerformanceMetric[] = [];
  private pendingRouteMetrics: RouteMetric[] = [];
  private flushTimer: ReturnType<typeof setInterval> | null = null;
  private isFlushScheduled = false;

  constructor(config: ReportConfig = {}) {
    this.config = {
      endpoint: config.endpoint || '/api/v1/performance/report',
      flushInterval: config.flushInterval || 30000, // 30 秒
      batchSize: config.batchSize || 20,
      enabled: config.enabled !== false,
      getSessionId: config.getSessionId ?? (() => ''),
    };
  }

  /**
   * 添加指标到待上报队列
   */
  addMetric(metric: PerformanceMetric): void {
    if (!this.config.enabled) return;

    this.pendingMetrics.push(metric);

    // 达到批量阈值时立即上报
    if (this.pendingMetrics.length >= this.config.batchSize) {
      this.scheduleFlush();
    }
  }

  /**
   * 添加路由指标到待上报队列
   */
  addRouteMetric(metric: RouteMetric): void {
    if (!this.config.enabled) return;

    this.pendingRouteMetrics.push(metric);

    // 达到批量阈值时立即上报
    if (this.pendingRouteMetrics.length >= this.config.batchSize) {
      this.scheduleFlush();
    }
  }

  /**
   * 批量添加指标
   */
  addMetrics(metrics: PerformanceMetric[]): void {
    if (!this.config.enabled) return;

    this.pendingMetrics.push(...metrics);

    if (this.pendingMetrics.length >= this.config.batchSize) {
      this.scheduleFlush();
    }
  }

  /**
   * 批量添加路由指标
   */
  addRouteMetrics(metrics: RouteMetric[]): void {
    if (!this.config.enabled) return;

    this.pendingRouteMetrics.push(...metrics);

    if (this.pendingRouteMetrics.length >= this.config.batchSize) {
      this.scheduleFlush();
    }
  }

  /**
   * 启动定时上报
   */
  start(): void {
    if (!this.config.enabled || this.flushTimer) return;

    this.flushTimer = setInterval(() => {
      this.flush();
    }, this.config.flushInterval);

    // 页面隐藏/卸载时使用 sendBeacon 上报剩余数据
    // 统一使用 pagehide + sendBeacon，避免与 Tracker 的 beforeunload 产生冗余请求
    if (typeof window !== 'undefined') {
      window.addEventListener('pagehide', () => {
        this.flushBeacon();
      });
    }
  }

  /**
   * 停止定时上报
   */
  stop(): void {
    if (this.flushTimer) {
      clearInterval(this.flushTimer);
      this.flushTimer = null;
    }
  }

  /**
   * 调度上报（使用 requestIdleCallback 或 setTimeout）
   */
  private scheduleFlush(): void {
    if (this.isFlushScheduled) return;
    this.isFlushScheduled = true;

    if (typeof requestIdleCallback !== 'undefined') {
      requestIdleCallback(() => this.flush());
    } else {
      // 使用 requestAnimationFrame 确保在渲染完成后执行
      if (typeof requestAnimationFrame !== 'undefined') {
        requestAnimationFrame(() => {
          setTimeout(() => this.flush(), 0);
        });
      } else {
        setTimeout(() => this.flush(), 0);
      }
    }
  }

  /**
   * 上报数据
   */
  private async flush(): Promise<void> {
    this.isFlushScheduled = false;

    if (!this.config.enabled) return;
    if (this.pendingMetrics.length === 0 && this.pendingRouteMetrics.length === 0) return;

    const report = this.buildReport();

    // 清空待上报队列
    this.pendingMetrics = [];
    this.pendingRouteMetrics = [];

    try {
      await this.sendReport(report);
    } catch (error) {
      // 上报失败，将数据放回队列
      this.pendingMetrics.unshift(...report.metrics);
      this.pendingRouteMetrics.unshift(...report.routeMetrics);
      console.debug('[Perf] Failed to send report:', error);
    }
  }

  /**
   * 使用 sendBeacon 上报（用于页面隐藏/卸载）
   */
  private flushBeacon(): void {
    if (!this.config.enabled) return;
    if (this.pendingMetrics.length === 0 && this.pendingRouteMetrics.length === 0) return;

    const report = this.buildReport();
    this.pendingMetrics = [];
    this.pendingRouteMetrics = [];

    try {
      if (typeof navigator !== 'undefined' && navigator.sendBeacon) {
        const blob = new Blob([JSON.stringify(report)], {
          type: 'application/json',
        });
        navigator.sendBeacon(this.config.endpoint, blob);
      } else {
        // 降级到同步上报
        this.sendReportSync(report);
      }
    } catch (error) {
      console.debug('[Perf] Failed to send beacon:', error);
    }
  }

  /**
   * 构建上报数据包
   */
  private buildReport(): PerformanceReport {
    return {
      pageUrl: typeof window !== 'undefined' ? window.location.href : '',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
      screen: typeof window !== 'undefined' ? {
        width: window.screen.width,
        height: window.screen.height,
        dpr: window.devicePixelRatio || 1,
      } : { width: 0, height: 0, dpr: 1 },
      timestamp: Date.now(),
      sessionId: this.config.getSessionId?.(),
      metrics: [...this.pendingMetrics],
      routeMetrics: [...this.pendingRouteMetrics],
    };
  }

  /**
   * 发送上报数据
   */
  private async sendReport(report: PerformanceReport): Promise<void> {
    if (typeof fetch === 'undefined') return;

    const response = await fetch(this.config.endpoint, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(report),
      keepalive: true,
    });

    if (!response.ok) {
      throw new Error(`Report failed: ${response.status}`);
    }
  }

  /**
   * 获取待上报数据
   */
  getPendingMetrics(): { metrics: PerformanceMetric[]; routeMetrics: RouteMetric[] } {
    return {
      metrics: [...this.pendingMetrics],
      routeMetrics: [...this.pendingRouteMetrics],
    };
  }

  /**
   * 清空待上报数据
   */
  clear(): void {
    this.pendingMetrics = [];
    this.pendingRouteMetrics = [];
  }
}

// 全局单例
let reporterInstance: PerformanceReporter | null = null;

/**
 * 获取上报器实例
 */
export function getReporter(): PerformanceReporter {
  if (!reporterInstance) {
    reporterInstance = new PerformanceReporter();
  }
  return reporterInstance;
}

/**
 * 初始化上报器
 */
export function initReporter(config?: ReportConfig): PerformanceReporter {
  if (!reporterInstance) {
    reporterInstance = new PerformanceReporter(config);
  } else {
    // 更新配置
    Object.assign(reporterInstance['config'], config);
  }

  reporterInstance.start();
  return reporterInstance;
}

/**
 * 添加指标到上报队列
 */
export function reportMetric(metric: PerformanceMetric): void {
  const reporter = getReporter();
  reporter.addMetric(metric);
}

/**
 * 批量添加指标到上报队列
 */
export function reportMetrics(metrics: PerformanceMetric[]): void {
  const reporter = getReporter();
  reporter.addMetrics(metrics);
}

/**
 * 添加路由指标到上报队列
 */
export function reportRouteMetric(metric: RouteMetric): void {
  const reporter = getReporter();
  reporter.addRouteMetric(metric);
}

/**
 * 停止上报
 */
export function stopReporter(): void {
  if (reporterInstance) {
    reporterInstance.stop();
  }
}
