/**
 * 页面性能指标采集
 * 使用 PerformanceObserver API 采集 Core Web Vitals
 */

import { reportMetric } from './reporter';

/**
 * 性能指标类型
 */
export type MetricType = 'FCP' | 'LCP' | 'CLS' | 'FID' | 'INP' | 'TTFB' | 'ROUTE_CHANGE';

/**
 * 单个性能指标数据
 */
export interface PerformanceMetric {
  /** 指标类型 */
  type: MetricType;
  /** 指标值 */
  value: number;
  /** 指标值（单位：毫秒，CLS 除外） */
  rating: 'good' | 'needs-improvement' | 'poor';
  /** 时间戳 */
  timestamp: number;
  /** 额外信息（路由路径等） */
  metadata?: Record<string, unknown>;
}

/**
 * 路由切换性能指标
 */
export interface RouteMetric {
  /** 路由路径 */
  path: string;
  /** 路由切换耗时（毫秒） */
  duration: number;
  /** 时间戳 */
  timestamp: number;
}

/**
 * Core Web Vitals 阈值配置
 */
const VITAL_THRESHOLDS = {
  FCP: { good: 1800, poor: 3000 },
  LCP: { good: 2500, poor: 4000 },
  CLS: { good: 0.1, poor: 0.25 },
  FID: { good: 100, poor: 300 },
  INP: { good: 200, poor: 500 },
  TTFB: { good: 800, poor: 1800 },
  ROUTE_CHANGE: { good: 500, poor: 1000 },
} as const;

/**
 * 评估指标等级
 */
function getRating(type: MetricType, value: number): 'good' | 'needs-improvement' | 'poor' {
  const thresholds = VITAL_THRESHOLDS[type];
  if (!thresholds) return 'good';

  if (value <= thresholds.good) return 'good';
  if (value <= thresholds.poor) return 'needs-improvement';
  return 'poor';
}

/**
 * 指标采集器类
 */
class MetricsCollector {
  private metrics: PerformanceMetric[] = [];
  private routeMetrics: RouteMetric[] = [];
  private observers: PerformanceObserver[] = [];
  private isSupported = typeof PerformanceObserver !== 'undefined';

  /**
   * 初始化性能观察器
   */
  init(): void {
    if (!this.isSupported) {
      console.debug('[Perf] PerformanceObserver not supported');
      return;
    }

    // FCP (First Contentful Paint)
    this.observe('paint', (entry) => {
      if (entry.name === 'first-contentful-paint') {
        this.recordMetric({
          type: 'FCP',
          value: entry.startTime,
          rating: getRating('FCP', entry.startTime),
          timestamp: Date.now(),
        });
      }
    });

    // LCP (Largest Contentful Paint)
    this.observeLCP();

    // CLS (Cumulative Layout Shift)
    this.observeCLS();

    // FID (First Input Delay) - 仅在支持时采集
    if (this.supportsEntryType('first-input')) {
      this.observeFID();
    }

    // INP (Interaction to Next Paint) - 仅在支持时采集
    if (this.supportsEntryType('event')) {
      this.observeINP();
    }

    // TTFB (Time to First Byte)
    this.observeTTFB();
  }

  /**
   * 通用观察方法
   */
  private observe(
    type: string,
    callback: (entry: PerformanceEntry) => void
  ): void {
    if (!this.isSupported) return;

    try {
      const observer = new PerformanceObserver((entries) => {
        for (const entry of entries.getEntries()) {
          callback(entry);
        }
      });
      observer.observe({ type, buffered: true });
      this.observers.push(observer);
    } catch (e) {
      console.debug(`[Perf] Failed to observe ${type}:`, e);
    }
  }

  /**
   * 观察 LCP（需要特殊处理，取最大值）
   */
  private observeLCP(): void {
    if (!this.supportsEntryType('largest-contentful-paint')) return;

    let lastLCP = 0;

    const observer = new PerformanceObserver((entries) => {
      const lastEntry = entries.getEntries().at(-1) as any;
      if (!lastEntry) return;

      const value = lastEntry.startTime || lastEntry.renderTime || lastEntry.loadTime;
      if (value > lastLCP) {
        lastLCP = value;
        this.recordMetric({
          type: 'LCP',
          value: lastLCP,
          rating: getRating('LCP', lastLCP),
          timestamp: Date.now(),
          metadata: {
            element: lastEntry.element?.tagName || 'unknown',
            url: lastEntry.url,
          },
        });
      }
    });

    try {
      observer.observe({ type: 'largest-contentful-paint', buffered: true });
      this.observers.push(observer);
    } catch (e) {
      console.debug('[Perf] Failed to observe LCP:', e);
    }
  }

  /**
   * 观察 CLS（需要累积计算）
   */
  private observeCLS(): void {
    if (!this.supportsEntryType('layout-shift')) return;

    let clsValue = 0;
    let sessionValue = 0;
    let sessionEntries: PerformanceEntry[] = [];

    const observer = new PerformanceObserver((entries) => {
      for (const entry of entries.getEntries()) {
        // 忽略没有最近用户输入的布局偏移
        if (!(entry as any).hadRecentInput) {
          sessionValue += (entry as any).value;
          sessionEntries.push(entry);
        }
      }

      // 如果会话值超过 1 秒没有新条目，则记录
      if (sessionValue > clsValue) {
        clsValue = sessionValue;
        this.recordMetric({
          type: 'CLS',
          value: clsValue,
          rating: getRating('CLS', clsValue),
          timestamp: Date.now(),
        });
      }
    });

    try {
      observer.observe({ type: 'layout-shift', buffered: true });
      this.observers.push(observer);
    } catch (e) {
      console.debug('[Perf] Failed to observe CLS:', e);
    }
  }

  /**
   * 观察 FID
   */
  private observeFID(): void {
    this.observe('first-input', (entry) => {
      const fidEntry = entry as any;
      this.recordMetric({
        type: 'FID',
        value: fidEntry.processingStart - fidEntry.startTime,
        rating: getRating('FID', fidEntry.processingStart - fidEntry.startTime),
        timestamp: Date.now(),
        metadata: {
          eventType: fidEntry.name,
        },
      });
    });
  }

  /**
   * 观察 INP
   * 仅在最大值变化时记录指标，避免每次交互都上报
   * durationThreshold=40 过滤掉 <40ms 的快速交互，减少回调频率
   */
  private observeINP(): void {
    let inpValue = 0;
    let recordedValue = 0;
    let interactionCount = 0;

    const observer = new PerformanceObserver((list) => {
      for (const entry of list.getEntries() as any[]) {
        interactionCount++;

        // 计算所有交互的延迟
        const interactionDelay = entry.processingStart - entry.startTime;
        if (interactionDelay > inpValue) {
          inpValue = interactionDelay;
        }
      }

      // 仅在最大值变化时记录（避免每次交互都上报）
      if (inpValue > 0 && inpValue > recordedValue) {
        recordedValue = inpValue;
        this.recordMetric({
          type: 'INP',
          value: inpValue,
          rating: getRating('INP', inpValue),
          timestamp: Date.now(),
          metadata: {
            interactionCount,
          },
        });
      }
    });

    try {
      // durationThreshold=40: 浏览器仅在交互延迟 >= 40ms 时才通知 observer，
      // 过滤掉大量快速交互，减少回调频率和处理开销
      observer.observe({ type: 'event', buffered: true, durationThreshold: 40 } as any);
      this.observers.push(observer);
    } catch (e) {
      console.debug('[Perf] Failed to observe INP:', e);
    }
  }

  /**
   * 观察 TTFB
   */
  private observeTTFB(): void {
    if (typeof performance === 'undefined' || !performance.getEntriesByType) return;

    const navigationEntries = performance.getEntriesByType('navigation');
    if (navigationEntries && navigationEntries.length > 0) {
      const navEntry = navigationEntries[0] as any;
      const ttfb = navEntry.responseStart - navEntry.requestStart;

      this.recordMetric({
        type: 'TTFB',
        value: ttfb,
        rating: getRating('TTFB', ttfb),
        timestamp: Date.now(),
      });
    }
  }

  /**
   * 检查是否支持指定的 entryType
   */
  private supportsEntryType(type: string): boolean {
    if (!this.isSupported) return false;

    return (
      PerformanceObserver.supportedEntryTypes &&
      PerformanceObserver.supportedEntryTypes.includes(type)
    );
  }

  /**
   * 记录指标（同时推送到 Reporter 上报队列）
   */
  private recordMetric(metric: PerformanceMetric): void {
    this.metrics.push(metric);

    // 限制存储数量
    if (this.metrics.length > 100) {
      this.metrics.shift();
    }

    // 桥接：将指标推送到 PerformanceReporter 上报队列
    try {
      reportMetric(metric);
    } catch {
      // Reporter 未初始化时静默失败
    }
  }

  /**
   * 记录路由切换耗时
   */
  recordRouteChange(path: string, duration: number): void {
    this.routeMetrics.push({
      path,
      duration,
      timestamp: Date.now(),
    });

    // 也作为普通指标记录
    this.recordMetric({
      type: 'ROUTE_CHANGE',
      value: duration,
      rating: duration > 1000 ? 'poor' : duration > 500 ? 'needs-improvement' : 'good',
      timestamp: Date.now(),
      metadata: { path },
    });
  }

  /**
   * 获取所有指标
   */
  getMetrics(): PerformanceMetric[] {
    return [...this.metrics];
  }

  /**
   * 获取路由指标
   */
  getRouteMetrics(): RouteMetric[] {
    return [...this.routeMetrics];
  }

  /**
   * 按类型获取指标
   */
  getMetricsByType(type: MetricType): PerformanceMetric[] {
    return this.metrics.filter((m) => m.type === type);
  }

  /**
   * 清空所有指标
   */
  clear(): void {
    this.metrics = [];
    this.routeMetrics = [];
  }

  /**
   * 销毁观察器
   */
  destroy(): void {
    for (const observer of this.observers) {
      observer.disconnect();
    }
    this.observers = [];
    this.clear();
  }
}

// 创建全局单例
let collectorInstance: MetricsCollector | null = null;

/**
 * 获取指标采集器实例
 */
export function getMetricsCollector(): MetricsCollector {
  if (!collectorInstance) {
    collectorInstance = new MetricsCollector();
  }
  return collectorInstance;
}

/**
 * 初始化性能指标采集
 */
export function initMetrics(): void {
  const collector = getMetricsCollector();
  collector.init();
}

/**
 * 记录路由切换
 */
export function recordRouteChange(path: string, duration: number): void {
  const collector = getMetricsCollector();
  collector.recordRouteChange(path, duration);
}

/**
 * 获取所有指标
 */
export function getMetrics(): PerformanceMetric[] {
  const collector = getMetricsCollector();
  return collector.getMetrics();
}

/**
 * 获取路由指标
 */
export function getRouteMetrics(): RouteMetric[] {
  const collector = getMetricsCollector();
  return collector.getRouteMetrics();
}

/**
 * 清空指标
 */
export function clearMetrics(): void {
  const collector = getMetricsCollector();
  collector.clear();
}

/**
 * 销毁采集器
 */
export function destroyMetrics(): void {
  if (collectorInstance) {
    collectorInstance.destroy();
    collectorInstance = null;
  }
}
