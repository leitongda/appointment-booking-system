# API 工具函数

本目录包含 API 请求相关的工具函数和监控机制。

## 文件说明

### retry.ts
提供自动重试机制，为幂等操作（GET、HEAD 请求）在遇到网络错误或服务器错误时自动重试。

**主要功能**:
- 自动重试失败的 GET 请求（最多 3 次）
- 指数退避策略（1s, 2s, 4s）
- 只重试网络错误和 5xx 服务器错误
- 自动集成到 axios 实例

**使用示例**:
```typescript
import { setupRetryInterceptor } from '@hospital/api';

// 为 axios 实例设置重试拦截器
setupRetryInterceptor(axiosInstance, {
  maxRetries: 3,
  retryDelay: 1000,
  retryDelayFactor: 2,
});
```

### performance.ts
提供 API 性能监控功能，自动记录请求耗时、超时次数、重试次数等指标。

**主要功能**:
- 自动记录每个 API 请求的耗时
- 跟踪超时和重试事件
- 计算性能统计（平均耗时、P95、P99）
- 支持按 URL 模式过滤统计

**使用示例**:
```typescript
import { getPerformanceSummary } from '@hospital/api';

// 获取所有 API 的性能统计
const summary = getPerformanceSummary();

console.log(`
  总请求数: ${summary.totalRequests}
  成功率: ${(summary.successfulRequests / summary.totalRequests * 100).toFixed(2)}%
  平均耗时: ${summary.averageDuration}ms
  P95 耗时: ${summary.p95Duration}ms
  P99 耗时: ${summary.p99Duration}ms
`);

// 获取特定 API 的性能统计
const ruleSetSummary = getPerformanceSummary('/rule-sets');
```

## 测试

运行单元测试：

```bash
# 在 packages/api 目录下
npm test -- retry.test.ts
npm test -- performance.test.ts
```

## 配置

### 重试配置

默认配置（可在 `retry.ts` 中修改）：

```typescript
{
  maxRetries: 3,           // 最大重试次数
  retryDelay: 1000,        // 初始重试延迟（毫秒）
  retryDelayFactor: 2,     // 延迟倍增因子
  logRetry: true,          // 是否记录重试日志
}
```

### 性能监控配置

默认配置（可在 `performance.ts` 中修改）：

```typescript
{
  maxMetricsCount: 1000,   // 最多存储的记录数
  flushInterval: 60000,    // 刷新间隔（毫秒）
}
```

## 注意事项

1. **重试机制**: 只对幂等操作（GET、HEAD）启用重试，POST/PUT/DELETE 不会重试
2. **性能监控**: 所有请求都会被监控，包括成功和失败的请求
3. **存储限制**: 性能数据最多存储 1000 条，超出后会自动删除旧数据
4. **隐私**: 性能数据不会包含敏感信息，只记录 URL、方法、耗时等指标
