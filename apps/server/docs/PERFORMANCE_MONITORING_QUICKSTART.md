# 规则引擎性能监控 - 快速开始指南

## 1. 启用性能监控

在 `.env` 文件中设置：

```bash
RULE_PERFORMANCE_MONITORING_ENABLED=true
```

## 2. 验证监控是否工作

### 方法 1: 查看日志

```bash
tail -f logs/app.log | grep "慢查询"
```

### 方法 2: 调用 API

```bash
# 获取性能统计（需要超级管理员 Token）
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/performance?hours=1" \
  -H "Authorization: Bearer YOUR_SUPER_ADMIN_TOKEN"
```

## 3. 查看性能报告

### 查看最近 24 小时的性能统计

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/performance" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查看特定操作的统计

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/performance?operation=get_applicable_rule_set" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查看最近 7 天的统计

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/performance?hours=168" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 4. 分析慢查询

### 查看最近的慢查询

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/slow-queries" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查看特定操作的慢查询

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/slow-queries?operation=check_action_window" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 查看更多慢查询

```bash
curl -X GET "http://localhost:8000/api/v1/admin/rule-sets/slow-queries?limit=500" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 5. 评估是否需要缓存

根据以下指标判断：

### 需要添加缓存的情况

- **P99 延迟** > 100ms
- **慢查询比例** > 5%（慢查询数 / 总调用数）
- **平均调用速率** > 100 次/分钟
- **同一规则组** 被频繁访问

### 示例分析

```json
{
  "stats": {
    "get_applicable_rule_set": {
      "count": 1523,
      "latency_ms": {
        "p99": 89.3,    // 接近 100ms，建议关注
        "avg": 18.7
      },
      "slow_query_count": 12,  // 12/1523 = 0.8%，可接受
      "avg_rate": 63.46  // 每分钟 63 次，中等频率
    }
  }
}
```

**结论**: P99 延迟接近阈值，建议添加缓存。

## 6. 清除监控数据

### 清除所有操作的指标

```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/rule-sets/performance/metrics" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 清除特定操作的指标

```bash
curl -X DELETE "http://localhost:8000/api/v1/admin/rule-sets/performance/metrics?operation=get_applicable_rule_set" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 7. 配置调整

### 调整慢查询阈值

```bash
# .env 文件
RULE_SLOW_QUERY_THRESHOLD=200  # 改为 200ms
```

### 调整数据保留时间

```bash
# .env 文件
RULE_METRICS_TTL=1209600        # 保留 14 天
RULE_SLOW_QUERY_TTL=5184000     # 保留 60 天
```

### 禁用监控

```bash
# .env 文件
RULE_PERFORMANCE_MONITORING_ENABLED=false
```

## 8. 常见问题

### Q: 监控会影响性能吗？
A: 不会。监控使用异步记录，开销 < 1ms。

### Q: Redis 连接失败会影响业务吗？
A: 不会。监控异常会被捕获并记录，不影响规则引擎正常工作。

### Q: 如何判断是否需要添加缓存？
A: 参考 "评估是否需要缓存" 部分，重点关注 P99 延迟和调用频率。

### Q: 监控数据会占用多少存储？
A: 约 10-20MB/周，可根据需要调整保留时间。

### Q: 能否自定义监控的操作？
A: 可以。在 `rule_engine_service.py` 中为需要监控的方法添加 `@monitor_performance` 装饰器。

## 9. 下一步

1. **收集数据**: 运行系统 1-2 周，收集足够的性能数据
2. **分析数据**: 使用 API 和慢查询日志分析性能瓶颈
3. **优化决策**: 根据数据决定是否添加缓存
4. **验证效果**: 添加缓存后继续监控，验证优化效果

## 10. 相关文档

- 完整文档: `/docs/RULE_PERFORMANCE_MONITORING.md`
- 实现总结: `/docs/PERFORMANCE_MONITORING_README.md`
