/**
 * 前端性能监控
 * 提供页面性能指标采集和上报功能
 */

// 本地导入（供本模块函数使用）
import { initMetrics, destroyMetrics } from './metrics';
import { initReporter, stopReporter } from './reporter';
import type { ReportConfig } from './reporter';

// 重导出指标采集
export {
  getMetricsCollector,
  initMetrics,
  recordRouteChange,
  getMetrics,
  getRouteMetrics,
  clearMetrics,
  destroyMetrics,
} from './metrics';
export type {
  PerformanceMetric,
  RouteMetric,
  MetricType,
} from './metrics';

// 重导出上报器
export {
  getReporter,
  initReporter,
  reportMetric,
  reportMetrics,
  reportRouteMetric,
  stopReporter,
} from './reporter';
export type {
  ReportConfig,
  PerformanceReport,
} from './reporter';

/**
 * 初始化性能监控（包含指标采集和上报）
 */
export function initPerformanceMonitoring(config?: {
  report?: ReportConfig;
}): void {
  // 初始化指标采集
  initMetrics();

  // 初始化上报器
  initReporter(config?.report);
}

/**
 * 销毁性能监控
 */
export function destroyPerformanceMonitoring(): void {
  stopReporter();
  destroyMetrics();
}
