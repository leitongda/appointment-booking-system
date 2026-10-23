/**
 * 性能监控单元测试
 */

import { getPerformanceMonitor, createApiTimer, getPerformanceSummary, clearPerformanceData } from '../performance';

describe('Performance Monitor', () => {
  beforeEach(() => {
    clearPerformanceData();
  });

  test('should record successful API call', () => {
    const monitor = getPerformanceMonitor();
    const timer = createApiTimer('/test', 'GET');
    // 回拨 startTime 固定已耗时：立即 recordSuccess 时 Date.now 差值可能为 0
    (timer as any).startTime = Date.now() - 10;

    timer.recordSuccess();

    const summary = monitor.getSummary();
    expect(summary.totalRequests).toBe(1);
    expect(summary.successfulRequests).toBe(1);
    expect(summary.failedRequests).toBe(0);
    expect(summary.averageDuration).toBeGreaterThan(0);
  });

  test('should record failed API call', () => {
    const monitor = getPerformanceMonitor();
    const timer = createApiTimer('/test', 'POST');

    timer.recordFailure('Network error');

    const summary = monitor.getSummary();
    expect(summary.totalRequests).toBe(1);
    expect(summary.successfulRequests).toBe(0);
    expect(summary.failedRequests).toBe(1);
  });

  test('should track timeout events', () => {
    const monitor = getPerformanceMonitor();
    const timer = createApiTimer('/test', 'GET');

    timer.markAsTimeout();
    timer.recordFailure('Timeout');

    const summary = monitor.getSummary();
    expect(summary.timeoutRequests).toBe(1);
  });

  test('should track retry events', () => {
    const monitor = getPerformanceMonitor();
    const timer = createApiTimer('/test', 'GET');

    timer.markAsRetried(2);
    timer.recordSuccess();

    const summary = monitor.getSummary();
    expect(summary.retriedRequests).toBe(1);
  });

  test('should calculate percentiles correctly', () => {
    const monitor = getPerformanceMonitor();

    // 创建 100 个请求，耗时从 100ms 到 1000ms
    for (let i = 1; i <= 100; i++) {
      const timer = createApiTimer('/test', 'GET');
      // 模拟不同的耗时
      (timer as any).startTime = Date.now() - i * 10;
      timer.recordSuccess();
    }

    const summary = monitor.getSummary();
    expect(summary.totalRequests).toBe(100);
    expect(summary.p95Duration).toBeGreaterThan(0);
    expect(summary.p99Duration).toBeGreaterThan(0);
    expect(summary.p99Duration).toBeGreaterThanOrEqual(summary.p95Duration);
  });

  test('should filter by URL pattern', () => {
    const monitor = getPerformanceMonitor();

    const timer1 = createApiTimer('/api/v1/rule-sets', 'GET');
    timer1.recordSuccess();

    const timer2 = createApiTimer('/api/v1/appointments', 'GET');
    timer2.recordSuccess();

    const ruleSetsSummary = monitor.getSummary('/api/v1/rule-sets');
    expect(ruleSetsSummary.totalRequests).toBe(1);

    const allSummary = monitor.getSummary();
    expect(allSummary.totalRequests).toBe(2);
  });
});
