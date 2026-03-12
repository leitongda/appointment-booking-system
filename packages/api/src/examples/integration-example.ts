/**
 * API 超时和重试机制集成示例
 *
 * 本示例展示如何在应用中使用自动重试和性能监控功能
 */

import { ruleSetApi } from '@hospital/api';
import { getPerformanceSummary, clearPerformanceData } from '@hospital/api';

/**
 * 示例 1: 基础使用 - 自动重试
 *
 * GET 请求会在遇到网络错误或 5xx 错误时自动重试（最多 3 次）
 */
export async function basicExample() {
  try {
    // 这个请求会自动重试（如果失败）
    const ruleSets = await ruleSetApi.getList({ enabled: true });
    console.log(`成功获取 ${ruleSets.data.length} 个规则组`);
    return ruleSets;
  } catch (error) {
    console.error('获取规则组失败（已重试 3 次）:', error);
    throw error;
  }
}

/**
 * 示例 2: 查看性能统计
 */
export async function performanceExample() {
  // 执行一些 API 请求
  await ruleSetApi.getList();
  await ruleSetApi.getById('rule-set-123');

  // 获取性能统计
  const summary = getPerformanceSummary();

  console.log('=== API 性能统计 ===');
  console.log(`总请求数: ${summary.totalRequests}`);
  console.log(`成功请求数: ${summary.successfulRequests}`);
  console.log(`失败请求数: ${summary.failedRequests}`);
  console.log(`超时请求数: ${summary.timeoutRequests}`);
  console.log(`重试请求数: ${summary.retriedRequests}`);
  console.log(`平均耗时: ${summary.averageDuration.toFixed(2)}ms`);
  console.log(`P95 耗时: ${summary.p95Duration}ms`);
  console.log(`P99 耗时: ${summary.p99Duration}ms`);

  // 获取特定 API 的统计
  const ruleSetSummary = getPerformanceSummary('/rule-sets');
  console.log('\n=== 规则组 API 统计 ===');
  console.log(`总请求数: ${ruleSetSummary.totalRequests}`);
  console.log(`平均耗时: ${ruleSetSummary.averageDuration.toFixed(2)}ms`);

  return summary;
}

/**
 * 示例 3: 定期性能监控
 */
export class PerformanceMonitor {
  private intervalId: ReturnType<typeof setInterval> | null = null;

  start(intervalMs: number = 60000) {
    console.log('性能监控已启动');

    this.intervalId = setInterval(() => {
      const summary = getPerformanceSummary();

      // 检查是否有性能问题
      const successRate = (summary.successfulRequests / summary.totalRequests) * 100;
      const timeoutRate = (summary.timeoutRequests / summary.totalRequests) * 100;

      console.log('\n=== 性能监控报告 ===');
      console.log(`成功率: ${successRate.toFixed(2)}%`);
      console.log(`超时率: ${timeoutRate.toFixed(2)}%`);
      console.log(`平均耗时: ${summary.averageDuration.toFixed(2)}ms`);

      // 发送告警（如果需要）
      if (successRate < 95) {
        console.warn('警告：成功率低于 95%');
      }

      if (timeoutRate > 5) {
        console.warn('警告：超时率超过 5%');
      }

      // 定期清空数据，避免内存占用过多
      clearPerformanceData();

    }, intervalMs);
  }

  stop() {
    if (this.intervalId) {
      clearInterval(this.intervalId);
      this.intervalId = null;
      console.log('性能监控已停止');
    }
  }
}

/**
 * 示例 4: 错误处理和用户提示
 */
export async function errorHandlingExample() {
  try {
    const ruleSets = await ruleSetApi.getList({ enabled: true });
    return ruleSets;
  } catch (error: any) {
    // 检查错误类型并给出相应的用户提示
    if (error.code === 408) {
      console.error('请求超时，请稍后重试');
      // 显示用户友好的错误消息
      alert('请求超时，请检查网络连接后重试');
    } else if (error.code >= 500) {
      console.error('服务器错误，请稍后重试');
      alert('服务器暂时不可用，请稍后重试');
    } else if (error.code === 404) {
      console.error('资源不存在');
      alert('请求的资源不存在');
    } else {
      console.error('未知错误:', error.message);
      alert('发生未知错误，请稍后重试');
    }

    // 可以选择上报错误到监控系统
    // reportError(error);

    throw error;
  }
}

/**
 * 示例 5: 预览规则效果（带超时）
 */
export async function previewRuleExample(ruleSetId: string) {
  const startTime = Date.now();

  try {
    // 预览规则效果可能会有较长的计算时间
    const result = await ruleSetApi.preview({
      schedule_date: '2026-03-06',
      start_time: '09:00',
      end_time: '17:00',
      shift_type_id: 'shift-123',
      current_time: new Date().toISOString(),
    });

    const duration = Date.now() - startTime;
    console.log(`预览成功，耗时 ${duration}ms`);
    return result;

  } catch (error: any) {
    const duration = Date.now() - startTime;

    if (duration > 30000) {
      console.error('预览超时（超过 30 秒）');
      alert('规则预览超时，请简化规则后重试');
    } else {
      console.error('预览失败:', error.message);
      alert('规则预览失败，请检查输入后重试');
    }

    throw error;
  }
}

// 使用示例
if (typeof window !== 'undefined') {
  // 在浏览器环境中，可以导出一个全局对象用于调试
  (window as any).apiDebug = {
    basicExample,
    performanceExample,
    PerformanceMonitor,
    errorHandlingExample,
    previewRuleExample,
  };

  console.log('API 调试工具已加载到 window.apiDebug');
}
