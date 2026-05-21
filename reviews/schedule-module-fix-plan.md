# 排班模块修复计划

> 基于 2026-05-21 多智能体批判性评估 + 假设验证，P0/P1 分级修复方案。

---

## P0 — 本周必修（数据安全 / 正确性）

### P0-1: `booked_slots` 原子更新

**问题**：`service_booking.py:264` 使用 Python 端 `schedule.booked_slots += 1`，是 read-modify-write 模式。Redis 锁失效时可并发丢号。

**方案**：改为 SQL 原子更新 + 行锁。

**涉及文件**：
- `apps/server/app/modules/appointments/service_booking.py`
  - L264: `schedule.booked_slots += 1` → 原子 UPDATE
  - L504: `schedule.booked_slots = max(0, schedule.booked_slots - 1)` → 原子 UPDATE
  - L624: 同上

**具体改动**：

```python
# L264 改为:
from sqlalchemy import update as sa_update
result = await self.db.execute(
    sa_update(Schedule)
    .where(Schedule.id == schedule.id, Schedule.booked_slots < Schedule.total_slots)
    .values(booked_slots=Schedule.booked_slots + 1)
    .returning(Schedule.booked_slots)
)
new_count = result.scalar()
if new_count is None:
    raise ValueError("号源已满")
# 刷新 ORM 对象状态
schedule.booked_slots = new_count

# L504 / L624 改为:
await self.db.execute(
    sa_update(Schedule)
    .where(Schedule.id == schedule.id, Schedule.booked_slots > 0)
    .values(booked_slots=Schedule.booked_slots - 1)
)
await self.db.refresh(schedule, ["booked_slots"])
```

**前置检查**：L209-214 的 "号源已满" 校验仍保留作为快速失败，原子 UPDATE 作为最终防线。

**迁移**：无。

**测试**：补一个并发预约测试（2 个协程同时抢最后一个号，断言只有一个成功）。

**成本**：2h。

**负责**：Engineer。

---

### P0-2: 复合索引

**问题**：`service_query.py` 和 `service_conflict.py` 的查询热点是 `(store_id, schedule_date)` 和 `(doctor_id, schedule_date)`，但无复合索引。

**方案**：Alembic 迁移新增索引。

**涉及文件**：
- 新增迁移: `alembic revision --autogenerate -m "add_schedule_composite_indexes"`

**索引定义**：

```python
# schedules 表
Index('ix_schedules_store_date', 'store_id', 'schedule_date')
Index('ix_schedules_doctor_date', 'doctor_id', 'schedule_date')
Index('ix_schedules_tenant_store_date', 'tenant_id', 'store_id', 'schedule_date')
```

**迁移**：是，新增 Alembic 迁移。

**成本**：30min（含迁移生成 + 验证）。

**负责**：Engineer。

---

### P0-3: `_invalidate_rest_days_cache` 补调用

**问题**：`service_query.py:29` 定义了缓存失效函数，但全代码库 0 处调用。写入 RestDay 后 5 分钟内同进程查询仍用旧数据。

**方案**：在 `RestService` 的 `create`/`delete`/`cancel` 三个写方法末尾调用。

**涉及文件**：
- `apps/server/app/modules/rest_days/service.py`
  - L106 后（create commit 后）: 调用 `_invalidate_rest_days_cache(tenant_id)`
  - L116 后（delete commit 后）: 调用 `_invalidate_rest_days_cache(tenant_id)`
  - L127 后（cancel commit 后）: 调用 `_invalidate_rest_days_cache(tenant_id)`

**具体改动**：

```python
# 在 service.py 顶部添加 import
from app.modules.schedules.service_query import _invalidate_rest_days_cache

# create 方法 L106 后:
await self.db.commit()
_invalidate_rest_days_cache(tenant_id)  # 新增
await self.db.refresh(rest_day)

# delete 方法 L116 后:
await self.db.commit()
_invalidate_rest_days_cache(get_current_tenant_id())  # 新增

# cancel 方法 L127 后:
await self.db.commit()
_invalidate_rest_days_cache(get_current_tenant_id())  # 新增
```

**迁移**：无。

**成本**：15min。

**负责**：Engineer。

---

## P1 — 本月内（正确性 + 架构债务）

### P1-1: `batch_resume` for-else 修复

**问题**：`service_mutation.py:1094` 的 `else` 绑在 `for`（L1007）而非 `if`。内层循环无 `break`，`else` 每次都执行，`affected_count` 被多加。

**方案**：改为显式 `if not suspensions:` 判断。

**涉及文件**：
- `apps/server/app/modules/schedules/service_mutation.py` L1007-1098

**具体改动**：

```python
# 将 L1007-1098 的 for-else 结构改为:
for suspension in suspensions:
    # ... 原有逻辑不变 (L1008-1088) ...
    processed_suspension_ids.add(suspension.id)

# 删除 L1089-1093 的 else 分支（已由 should_cancel 处理）
# 将 L1094-1098 的 for-else else 改为:
if not suspensions:
    # 如果没有找到停诊记录，直接恢复排班状态
    schedule.status = 1
    schedule.schedule_status = ScheduleStatus.PUBLISHED
    affected_count += 1
```

**测试**：`test_schedule_service.py:404` 改为 `assert count == 1`（精确断言而非 `>= 0`）。

**迁移**：无。

**成本**：30min。

**负责**：Engineer。

---

### P1-2: 唯一索引 NULL 安全

**问题**：`uix_schedule_doctor_date_time` 包含 `start_time`/`end_time`，PG 下 NULL != NULL，纯 `time_slot` 排班无去重保护。

**方案**：新增一个不依赖 start_time/end_time 的唯一约束，覆盖 time_slot 模式。

**涉及文件**：
- 新增迁移

**约束定义**：

```python
# 新增部分唯一索引（仅对 time_slot 排班生效）
Index(
    'uix_schedule_doctor_date_slot',
    'doctor_id', 'schedule_date', 'time_slot',
    unique=True,
    postgresql_where=text("time_slot IS NOT NULL AND start_time IS NULL")
)
# 同理保留原索引但加条件
Index(
    'uix_schedule_doctor_date_time_partial',
    'doctor_id', 'schedule_date', 'start_time', 'end_time',
    unique=True,
    postgresql_where=text("start_time IS NOT NULL")
)
```

**迁移**：是，需先删除原 `uix_schedule_doctor_date_time`，再创建两个条件索引。

**成本**：1h（含数据检查 + 迁移）。

**负责**：Engineer。

---

### P1-3: 状态字段收敛（评估阶段）

**问题**：`status (int 0/1)` + `schedule_status (7态)` + `publish_status (3态)` 三套并存，手动同步易出错。

**方案分两步**：

**Step 1 — 评估**（本周）：
- 梳理所有读写 `status` 字段的代码路径
- 确认 `publish_status` 是否可合并到 `schedule_status`
- 产出合并方案文档

**Step 2 — 执行**（下周）：
- 新增 DB CHECK 约束
- 逐步迁移读写路径到 `schedule_status`
- `status` 字段保留但标记 deprecated，读路径 fallback 到 `schedule_status`

**涉及文件**：
- `apps/server/app/models/schedule.py`
- `apps/server/app/modules/schedules/service_mutation.py`
- `apps/server/app/modules/schedules/service_query.py`
- 新增迁移

**成本**：评估 2h + 执行 4h。

**负责**：Engineer。

---

### P1-3 评估结论（2026-05-21 完成）

**三字段职责分析：**

| 字段 | 类型 | 用途 | 写入路径 |
|------|------|------|---------|
| `status` (int 0/1) | 布尔标记 | 快速判断"是否停诊" | service_mutation.py（批量停诊/恢复，~6 处） |
| `schedule_status` (7 态) | 完整状态机 | 排班生命周期管理 | service_mutation.py（~15 处）、service_generation.py、router_import.py |
| `publish_status` (3 态) | 发布工作流 | 发布/撤回过滤 | service_mutation.py（~5 处）、router_import.py |

**关键发现：`publish_status` 可从 `schedule_status` 推导：**

| schedule_status | 对应 publish_status |
|----------------|-------------------|
| draft | draft |
| published / booking / full | published |
| withdrawn | withdrawn |
| suspended / finished | 继承先前状态（无需独立字段） |

**`publish_status` 的唯一独立读路径**：`service_query.py:332`（患者端可预约查询）+ `service_query.py:97-99`（列表过滤）。但这两处同时还有 `Schedule.status == 1` 和 `schedule_status in BOOKABLE` 条件，`publish_status` 是冗余守卫。

**结论：**

1. **`publish_status` 可安全移除** — 语义完全包含在 `schedule_status` 中。5 处写入 + 3 处读取可替换。
2. **`status` (int) 保留不改** — 与 `schedule_status` 始终同步，改动收益低（15+ 处读路径），风险高。建议在 `schedule_status` 上加 DB CHECK 约束后标记 deprecated。
3. **推荐方案**：仅移除 `publish_status`，`status` 标记 deprecated。不做三合一。

**执行范围缩减**：原计划 6h → 实际 2h（只移除 `publish_status`）。

---

### P1-4: 进程内缓存改 Redis（或移除）

**问题**：`_rest_days_cache` 是进程内 dict，多 worker 间不共享，且 P0-3 补了失效调用后仍只对单进程有效。

**方案**：评估两个选项：

**选项 A — 改 Redis**：
- 将 `_rest_days_cache` 的 key/value 存入 Redis，TTL 5 分钟
- `_invalidate_rest_days_cache` 改为 `redis.delete(key)`
- 所有 worker 共享同一份缓存

**选项 B — 移除进程内缓存**：
- 删掉 `_rest_days_cache`，每次查 DB
- RestDay 表数据量小（每个租户几十条），查询成本低
- 简单可靠，无一致性问题

**推荐**：选项 B。复杂度低，RestDay 查询频率不高（排班生成时一次），不值得引入 Redis 缓存管理。

**成本**：30min。

**负责**：Engineer。

---

### P1-5: `router.py` 拆分（规划阶段）

**问题**：`router.py` 1992 行，27 个端点 + 内嵌 Pydantic + 工具函数。

**方案**：按职能拆为 5 个文件：

| 文件 | 职责 | 预估行数 |
|------|------|---------|
| `router_schedules.py` | CRUD + 列表 + 详情 | ~400 |
| `router_statistics.py` | 统计端点 | ~200 |
| `router_extra_quota.py` | 加号管理 | ~200 |
| `router_custom.py` | 自定义排班 | ~200 |
| `router_state_machine.py` | 发布/撤回/停诊/恢复/拖拽 | ~400 |
| `router.py` | 保留为入口，re-export + 注册 | ~50 |

**前置**：统计端点（`get_schedule_statistics` L206-364）下沉到 `service_statistics.py`。

**迁移**：无（纯重构，URL 不变）。

**成本**：4h。

**负责**：Engineer。

---

## 优先级总览

| ID | 项目 | 优先级 | 成本 | 风险 | 依赖 |
|----|------|--------|------|------|------|
| P0-1 | booked_slots 原子更新 | P0 | 2h | 中（改抢号核心路径） | 无 |
| P0-2 | 复合索引 | P0 | 30min | 低 | 无 |
| P0-3 | cache invalidation 补调用 | P0 | 15min | 极低 | 无 |
| P1-1 | batch_resume for-else | P1 | 30min | 极低 | 无 |
| P1-2 | 唯一索引 NULL 安全 | P1 | 1h | 低 | 无 |
| P1-3 | 状态字段收敛 | P1 | 6h | 中 | 无 |
| P1-4 | 进程内缓存移除 | P1 | 30min | 极低 | P0-3 |
| P1-5 | router.py 拆分 | P1 | 4h | 低 | 无 |

**总工时**：~14.5h（P0 约 3h，P1 约 11.5h）

---

## 执行顺序建议

```
P0-3 (15min) → P0-2 (30min) → P1-1 (30min) → P1-4 (30min)
    ↓
P0-1 (2h) — 需要仔细测试
    ↓
P1-2 (1h) → P1-3 (6h) → P1-5 (4h)
```

P0-3/P0-2/P1-1/P1-4 互不依赖，可并行。P0-1 改抢号路径需要最充分的测试。P1-3/P1-5 是架构性重构，排在最后。
