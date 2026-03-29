# P1 多租户改造完善计划

## 探索结论

| STATUS.md 中的待做项 | 实际状态 | 行动 |
|---------------------|---------|------|
| 配额实时检查集成到各资源创建 API | **已完成** | 门店/管理员/医生/预约四大核心资源创建均已集成 `check_quota()`，无需额外工作 |
| 导入服务租户隔离 | **有缺口** | 规则组导入完全无隔离，规则组导出缺少 tenant_id 过滤，旧导出模块无隔离 |
| 缓存隔离测试补充 | **有缺口** | 分布式锁使用不一致，规则引擎性能监控未隔离，缺少隔离测试 |

## 实际工作量评估

需要做的工作分为 3 个独立任务，可并行执行：

---

### Team A: 导入服务租户隔离修复（高优先级 - 安全漏洞）

**涉及文件：**
- `app/modules/import_export/service_rule_set_import.py` — 规则组导入服务（无任何 tenant_id）
- `app/modules/import_export/router_export.py:561-703` — 规则组导出（缺 tenant_id 过滤）
- `app/modules/export/service.py` — 旧导出服务（无 tenant_id 过滤）
- `app/modules/export/router.py` — 旧导出路由（无 tenant_id 获取）
- `tests/tenants/test_import_tenant_isolation.py` — 补充导出隔离测试

**具体修改：**

1. **`service_rule_set_import.py`**:
   - `import_rule_sets()` 方法添加 `tenant_id` 参数
   - `_import_rule_set()` 中创建 `RuleSet` 时设置 `tenant_id`
   - 查询已存在规则组时添加 `tenant_id` 过滤（防跨租户名称冲突）
   - 关联的 `RuleWindow/RuleBookingPolicy/RuleCheckinPolicy/RuleCapacityPolicy` 查询也需加 tenant_id

2. **`router_export.py` 的 `export_rule_sets` 端点** (行 561-703):
   - 添加 `get_tenant_filter(current_admin)` 获取 tenant_id
   - 查询 `RuleSet` 时添加 `.where(RuleSet.tenant_id == tenant_id)`

3. **旧导出模块 `export/service.py` + `router.py`**:
   - `ExportService` 方法添加 `tenant_id` 参数
   - `export_appointments`: 添加 `Appointment.tenant_id == tenant_id` 过滤
   - `export_patients`: 添加 `Patient.tenant_id == tenant_id` 过滤
   - `export_schedules`: 添加 `Schedule.tenant_id == tenant_id` 过滤
   - 路由层使用 `get_current_tenant_id()` 获取并传入

4. **补充测试**:
   - 规则组导入租户隔离测试
   - 规则组导出租户隔离测试
   - 旧导出模块租户隔离测试

---

### Team B: 缓存隔离修复与测试补充（中优先级）

**涉及文件：**
- `app/modules/appointments/service_booking.py:119,276` — 分布式锁改用租户隔离版本
- `app/services/rule_performance_service.py` — 规则引擎性能监控 key 添加 tenant_id
- `tests/tenants/test_cache_isolation.py` — 补充 API 限流隔离测试
- `tests/tenants/test_distributed_lock_isolation.py` — 补充预约锁隔离测试

**具体修改：**

1. **`service_booking.py` 分布式锁** (行 119, 276):
   - `redis_cache.distributed_lock(...)` 改为 `redis_cache.tenant_distributed_lock(..., tenant_id=...)`
   - 需要确认上下文中已有 tenant_id 可用

2. **`rule_performance_service.py`**:
   - 所有 Redis key 前缀从 `rule_engine:counter:{operation}` 改为 `rule_engine:{tenant_id}:counter:{operation}`
   - 类似地修改 latency、slow_query、stats 前缀
   - 方法添加 `tenant_id` 参数，默认从上下文获取
   - 更新 `tests/unit/test_rule_performance_monitoring.py` 中的 mock patch 路径

3. **补充测试**:
   - API 限流租户隔离测试（验证不同租户的限流计数器独立）
   - 预约分布式锁租户隔离测试
   - 规则引擎性能监控租户隔离测试

---

### Team C: 清理冗余 + 微信 Token 隔离（低优先级）

**涉及文件：**
- `app/core/redis_admin_session_tenant.py` — 重复文件，应删除
- `app/core/redis.py` — 微信 Token 缓存添加 tenant_id
- `app/infrastructure/wechat/token_manager.py` — 传递 tenant_id 到缓存层

**具体修改：**

1. **删除 `redis_admin_session_tenant.py`**:
   - 确认无引用后删除
   - 功能已合并到 `redis.py` 中

2. **微信 Token 缓存隔离**:
   - `get_wechat_token` / `set_wechat_token` 方法添加可选 `tenant_id` 参数
   - key 格式改为 `wechat:token:{tenant_id}:{app_id}`
   - token_manager 调用时传入 tenant_id

---

## 执行策略

3 个 Team 并行执行，各自独立，互不影响：
- Team A: 4 个文件修改 + 测试
- Team B: 3 个文件修改 + 测试
- Team C: 3 个文件修改

## 验证

```bash
cd apps/server && python3 -m pytest tests/ --tb=short -q
```

全量测试通过（当前基线 487 passed, 20 skipped）。

## 风险

- **Team A 风险**: 规则组导入是复杂的多表事务，添加 tenant_id 需仔细处理所有关联表
- **Team B 风险**: 性能监控的 Redis key 格式变更会影响现有数据（旧 key 会自然过期）
- **Team C 风险**: 微信 Token 隔离需要确认 token_manager 的调用链
