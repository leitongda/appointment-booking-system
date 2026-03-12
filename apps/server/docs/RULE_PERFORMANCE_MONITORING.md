# 规则引擎性能监控文档

## 概述

规则引擎性能监控功能用于收集和分析规则引擎的性能数据，帮助评估是否需要添加缓存层。

## 功能特性

### 1. 调用频率统计
- 记录每次规则引擎方法调用
- 按操作类型分组统计
- 计算平均调用速率

### 2. 数据库查询延迟监控
- 记录每次查询的耗时
- 计算 P50、P95、P99 延迟
- 按操作类型分组统计

### 3. 慢查询日志
- 记录超过阈值的查询
- 包含查询类型、参数、耗时
- 自动保存到 Redis 列表

### 4. 性能报告 API
- 提供性能统计查询接口
- 支持按操作类型和时间范围过滤
- 需要超级管理员权限

## 配置项

在 `.env` 文件中添加以下配置：

```bash
# 规则引擎性能监控配置
RULE_PERFORMANCE_MONITORING_ENABLED=true    # 是否启用性能监控
RULE_SLOW_QUERY_THRESHOLD=100               # 慢查询阈值（毫秒）
RULE_METRICS_TTL=604800                     # 指标保留时间（秒，默认7天）
RULE_SLOW_QUERY_TTL=2592000                 # 慢查询保留时间（秒，默认30天）
```

## 监控的操作类型

| 操作类型 | 说明 |
|---------|------|
| `get_applicable_rule_set` | 获取适用的规则组 |
| `check_action_window` | 检查动作时间窗 |
| `get_booking_policy` | 获取预约策略 |
| `get_checkin_policy` | 获取签到策略 |
| `get_capacity_policy` | 获取容量策略 |
| `check_booking_conflicts` | 检查预约冲突 |
| `check_capacity_limits` | 检查容量限制 |

## API 接口

### 1. 获取性能统计

**端点**: `GET /api/v1/admin/rule-sets/performance`

**权限**: 超级管理员

**查询参数**:
- `operation` (可选): 操作类型
- `hours` (可选): 统计时间范围（小时），默认 24，范围 1-168

**响应示例**:
```json
{
  "enabled": true,
  "stats": {
    "get_applicable_rule_set": {
      "count": 1523,
      "latency_ms": {
        "p50": 12.5,
        "p95": 45.2,
        "p99": 89.3,
        "avg": 18.7,
        "max": 125.4,
        "min": 5.2
      },
      "slow_query_count": 12,
      "avg_rate": 63.46
    }
  },
  "summary": {
    "total_calls": 1523,
    "total_slow_queries": 12,
    "slowest_operation": "get_applicable_rule_set",
    "slowest_p99": 89.3
  }
}
```

### 2. 获取慢查询列表

**端点**: `GET /api/v1/admin/rule-sets/slow-queries`

**权限**: 超级管理员

**查询参数**:
- `operation` (可选): 操作类型
- `limit` (可选): 返回数量限制，默认 100，范围 1-1000

**响应示例**:
```json
{
  "total": 12,
  "data": [
    {
      "operation": "get_applicable_rule_set",
      "duration_ms": 125.4,
      "shift_type_id": "shift_123",
      "timestamp": "2026-03-05T10:30:45.123456",
      "metadata": {
        "args": "('shift_123',)",
        "kwargs": "{'enabled': True}"
      }
    }
  ]
}
```

### 3. 清除性能指标

**端点**: `DELETE /api/v1/admin/rule-sets/performance/metrics`

**权限**: 超级管理员

**查询参数**:
- `operation` (可选): 操作类型

**响应示例**:
```json
{
  "success": true,
  "deleted": 7,
  "message": "已清除 7 个操作的指标数据"
}
```

## 使用示例

### 1. 启用性能监控

在 `.env` 文件中设置：
```bash
RULE_PERFORMANCE_MONITORING_ENABLED=true
```

### 2. 查看性能统计

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/performance?hours=24" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 3. 查看慢查询

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/slow-queries?limit=50" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 4. 清除指标数据

```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/rule-sets/performance/metrics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 性能评估建议

### 1. 评估缓存需求

根据性能统计数据分析是否需要添加缓存：

**需要添加缓存的指标**:
- P99 延迟超过 100ms
- 慢查询数量超过总调用的 5%
- 平均调用速率 > 100 次/分钟
- 同一规则组被频繁访问

**缓存策略建议**:
- 热点规则组缓存：缓存经常访问的规则组数据
- 班次类型映射缓存：缓存班次类型到规则组的映射关系
- 策略结果缓存：缓存策略查询结果
- 过期时间：5-15 分钟

### 2. 监控指标解读

**延迟指标**:
- **P50**: 中位数延迟，反映典型性能
- **P95**: 95% 分位延迟，反映大部分用户性能
- **P99**: 99% 分位延迟，反映最差情况性能
- **平均值**: 平均延迟，可能被异常值影响

**调用频率**:
- **高频率**: > 1000 次/小时，建议缓存
- **中频率**: 100-1000 次/小时，可选缓存
- **低频率**: < 100 次/小时，无需缓存

**慢查询分析**:
- 查看慢查询的 `operation` 和 `metadata`
- 分析 `shift_type_id` 是否集中
- 检查数据库查询是否可以优化

## 注意事项

1. **性能影响**
   - 监控功能本身使用异步记录，对性能影响极小
   - Redis 操作耗时 < 1ms，不影响主流程
   - 可以通过环境变量禁用监控

2. **数据保留**
   - 指标数据默认保留 7 天
   - 慢查询日志默认保留 30 天
   - 可通过配置调整保留时间

3. **权限控制**
   - 性能报告 API 需要超级管理员权限
   - 避免在日志中记录敏感信息
   - 元数据长度限制为 200 字符

4. **故障处理**
   - Redis 连接失败不影响规则引擎正常工作
   - 监控异常会被记录到日志
   - 支持手动清除指标数据

## 故障排查

### 1. 监控数据未记录

**可能原因**:
- `RULE_PERFORMANCE_MONITORING_ENABLED=false`
- Redis 连接失败
- 异步任务执行异常

**解决方法**:
- 检查环境变量配置
- 查看日志中的错误信息
- 测试 Redis 连接

### 2. API 返回空数据

**可能原因**:
- 监控刚启用，尚未积累数据
- 查询时间范围内无数据
- 操作类型参数错误

**解决方法**:
- 延长查询时间范围
- 不指定 `operation` 参数
- 等待数据积累

### 3. 慢查询过多

**可能原因**:
- 阈值设置过低
- 数据库查询未优化
- 缺少必要的索引

**解决方法**:
- 调整 `RULE_SLOW_QUERY_THRESHOLD`
- 优化数据库查询
- 添加索引或使用缓存

## 后续优化方向

1. **添加缓存层**
   - 根据监控数据确定缓存策略
   - 使用 Redis 缓存热点数据
   - 设置合理的过期时间

2. **数据库优化**
   - 添加必要的索引
   - 优化慢查询语句
   - 考虑读写分离

3. **监控增强**
   - 添加实时性能图表
   - 支持性能告警
   - 自动生成优化建议

4. **数据分析**
   - 识别性能瓶颈
   - 分析访问模式
   - 预测性能趋势
