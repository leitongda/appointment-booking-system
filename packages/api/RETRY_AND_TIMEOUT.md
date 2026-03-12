# API 超时配置和重试机制使用指南

## 概述

本系统为规则组 API 提供了完善的超时配置和重试机制，以提高 API 的可靠性和用户体验。

## 功能特性

### 1. 后端超时配置

#### API 层超时
- **默认超时时间**: 30 秒
- **配置位置**: `apps/server/app/core/config.py`
- **应用范围**: 所有 API 端点

#### 数据库查询超时
- **默认超时时间**: 10 秒
- **实现方式**: PostgreSQL statement_timeout
- **自动管理**: 请求结束后自动重置

### 2. 前端自动重试机制

#### 重试策略
- **重试对象**: 仅幂等操作（GET、HEAD 请求）
- **最大重试次数**: 3 次
- **退避策略**: 指数退避（1s, 2s, 4s）
- **重试条件**:
  - 网络错误（无响应）
  - 5xx 服务器错误
  - 408 请求超时

#### 不重试的操作
- POST 请求（非幂等）
- PUT 请求（非幂等）
- DELETE 请求（非幂等）
- 4xx 客户端错误（除了 408）

### 3. 性能监控埋点

#### 自动记录指标
- API 调用耗时
- 超时次数
- 重试次数
- 成功/失败率
- P95/P99 耗时

#### 监控事件
- `api_retry`: 请求重试事件
- `api_retry_failed`: 重试失败事件
- `api_performance`: 性能指标事件

## 使用示例

### 前端使用

#### 基础使用（自动重试）

```typescript
import { ruleSetApi } from '@hospital/api';

// GET 请求会自动重试（最多 3 次）
const ruleSets = await ruleSetApi.getList({ enabled: true });
```

#### 自定义重试配置

```typescript
import { request, withRetry } from '@hospital/api';

// 为特定请求设置自定义重试配置
const response = await request.get('/rule-sets', withRetry({
  maxRetries: 5,
  retryDelay: 2000,
  retryDelayFactor: 1.5,
}));
```

#### 查看性能统计

```typescript
import { getPerformanceSummary } from '@hospital/api';

// 获取所有 API 的性能统计
const summary = getPerformanceSummary();

console.log(`
  总请求数: ${summary.totalRequests}
  成功率: ${(summary.successfulRequests / summary.totalRequests * 100).toFixed(2)}%
  平均耗时: ${summary.averageDuration}ms
  超时请求数: ${summary.timeoutRequests}
  重试请求数: ${summary.retriedRequests}
  P95 耗时: ${summary.p95Duration}ms
  P99 耗时: ${summary.p99Duration}ms
`);

// 获取特定 API 的性能统计
const ruleSetSummary = getPerformanceSummary('/rule-sets');
```

### 后端使用

#### API 端点实现

```python
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
import time
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/rule-sets/{rule_set_id}")
async def get_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取规则组详情（带超时监控）"""
    start_time = time.time()

    try:
        # 设置数据库查询超时
        await db.execute(text(f"SET statement_timeout TO {settings.DB_QUERY_TIMEOUT * 1000}"))

        service = RuleSetService(db)
        rule_set = await service.get_by_id(rule_set_id)

        if not rule_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="规则组不存在"
            )

        # 记录成功耗时
        duration = time.time() - start_time
        logger.info(
            f"获取规则组详情成功: admin_id={current_admin['id']}, "
            f"rule_set_id={rule_set_id}, duration={duration:.2f}s"
        )

        return rule_set

    except HTTPException:
        raise
    except Exception as e:
        duration = time.time() - start_time
        is_timeout = duration >= settings.API_TIMEOUT

        logger.error(
            f"获取规则组详情{'超时' if is_timeout else '失败'}: "
            f"admin_id={current_admin['id']}, "
            f"rule_set_id={rule_set_id}, "
            f"duration={duration:.2f}s, error={str(e)}"
        )

        if is_timeout:
            raise HTTPException(
                status_code=status.HTTP_408_REQUEST_TIMEOUT,
                detail="请求超时，请稍后重试"
            )
        else:
            raise
    finally:
        # 重置数据库查询超时
        try:
            await db.execute(text("SET statement_timeout TO 0"))
        except Exception:
            pass
```

## 配置说明

### 后端配置（.env）

```bash
# API 超时配置
API_TIMEOUT=30          # API 调用超时（秒）
DB_QUERY_TIMEOUT=10     # 数据库查询超时（秒）
```

### 前端配置

前端重试机制在 `packages/api/src/utils/retry.ts` 中配置，默认值：

```typescript
{
  maxRetries: 3,           // 最大重试次数
  retryDelay: 1000,        // 初始重试延迟（毫秒）
  retryDelayFactor: 2,     // 延迟倍增因子（指数退避）
  logRetry: true,          // 是否记录重试日志
}
```

## 监控和日志

### 后端日志

后端会记录以下信息：

```
INFO: 获取规则组列表: admin_id=123, total=10, duration=0.15s
INFO: 规则预览成功: admin_id=123, shift_type_id=abc, duration=0.52s
ERROR: 规则预览超时: admin_id=123, shift_type_id=abc, duration=30.15s, error=...
```

### 前端日志

前端会在控制台输出重试日志：

```
[API Retry] 请求重试 (1/3): GET /rule-sets - 延迟 1000ms
[API Retry] 请求重试 (2/3): GET /rule-sets - 延迟 2000ms
[API Retry] 重试失败: GET /rule-sets - 已重试 3 次
```

## 最佳实践

### 1. 为长时间运行的操作设置合理的超时

对于规则预览等可能较慢的操作，建议：
- 设置较长的超时时间（30 秒）
- 使用数据库查询超时（10 秒）防止单个查询过慢
- 提供明确的超时错误提示

### 2. 只对幂等操作启用重试

- **应该重试**: GET、HEAD 请求
- **不应该重试**: POST、PUT、DELETE 请求

### 3. 使用监控数据优化性能

定期检查性能统计：
- 识别慢查询
- 发现频繁超时的 API
- 优化后端查询性能
- 考虑添加缓存

### 4. 合理设置重试次数和延迟

- **重试次数**: 3 次通常足够，过多会延长总等待时间
- **初始延迟**: 1 秒较为合理
- **退避因子**: 2 倍退避（1s, 2s, 4s）可以平衡用户体验和服务器压力

## 故障排查

### 问题：API 请求总是超时

**可能原因**:
1. 数据库查询太慢
2. 网络连接问题
3. 服务器负载过高

**解决方案**:
1. 检查后端日志中的具体耗时
2. 优化慢查询
3. 增加数据库索引
4. 考虑使用缓存

### 问题：前端重试过多

**可能原因**:
1. 服务器不稳定
2. 网络环境差
3. 超时设置过短

**解决方案**:
1. 检查服务器健康状态
2. 增加超时时间
3. 减少最大重试次数

### 问题：性能数据不准确

**可能原因**:
1. 浏览器存储限制
2. 监控器未正确初始化

**解决方案**:
1. 定期清空性能数据
2. 确保在应用启动时初始化监控器

## 未来改进

1. **后端**:
   - 添加断路器模式（Circuit Breaker）
   - 实现请求队列和限流
   - 添加缓存层

2. **前端**:
   - 支持更复杂的重试策略
   - 添加离线队列
   - 实现请求去重

3. **监控**:
   - 集成到现有分析平台
   - 添加性能告警
   - 可视化性能仪表板
