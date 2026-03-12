# 性能监控

## 范围

当前服务端已具备规则引擎性能监控能力，主要用于：

- 观察规则引擎热点调用
- 跟踪慢查询
- 评估是否需要进一步引入缓存层

## 当前实现位置

- 监控服务：
  [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/services/rule_performance_service.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/services/rule_performance_service.py)
- 规则引擎入口：
  [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/services/rule_engine_service.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/services/rule_engine_service.py)
- 管理接口：
  [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/modules/rule_sets/router.py](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/app/modules/rule_sets/router.py)

## 配置

```env
RULE_PERFORMANCE_MONITORING_ENABLED=true
RULE_SLOW_QUERY_THRESHOLD=100
RULE_METRICS_TTL=604800
RULE_SLOW_QUERY_TTL=2592000
```

## 当前接口

- `GET /api/v1/rule-sets/performance`
- `GET /api/v1/rule-sets/slow-queries`
- `DELETE /api/v1/rule-sets/performance/metrics`

说明：

- 以上接口需要超级管理员权限
- 当前权威路径是 `/api/v1/rule-sets/*`
- 旧文档里如果出现 `/api/v1/admin/rule-sets/*`，应以当前代码为准

## 建议使用方式

1. 先看最近 `24h` 的统计
2. 再看特定操作的 `P95/P99`
3. 最后结合慢查询列表判断是否值得上缓存

## 历史文档

以下文件仍保留，作为实现背景和详细记录：

- [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/docs/PERFORMANCE_MONITORING_README.md](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/docs/PERFORMANCE_MONITORING_README.md)
- [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/docs/PERFORMANCE_MONITORING_QUICKSTART.md](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/docs/PERFORMANCE_MONITORING_QUICKSTART.md)
- [/Users/leijiadashao/leitond/appointment-booking-system/apps/server/docs/RULE_PERFORMANCE_MONITORING.md](/Users/leijiadashao/leitond/appointment-booking-system/apps/server/docs/RULE_PERFORMANCE_MONITORING.md)

如果后续继续整理，建议把这三份合并或归档，而不是继续新增第四份平行文档。
