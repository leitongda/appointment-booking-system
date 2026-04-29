# P0 行动计划：预约规则三项紧急改进

## Context

多维度审查发现预约规则系统存在三个紧急问题：
1. 患者端固定文案与可配置规则脱节（H5 提示"提前2小时取消"，小程序提示"提前24小时"，而实际值可配置）
2. 预约创建时分布式锁粒度过粗，只读检查在锁内执行，影响并发
3. RuleSet 可被硬删除，历史预约的 rule_set_id 悬空（虽有快照兜底，但不够健壮）

---

## P0-1：患者端规则动态展示（12-16h）

### 方案：复用现有 API + 扩展预约响应

**核心思路**：不新增接口，利用已有的 `GET /settings/booking/rules` 和排班接口中的规则引擎计算结果，在预约响应中附带规则摘要。

### 步骤

#### 1. 后端：扩展 AppointmentResponse 添加规则摘要字段

**文件**: `apps/server/app/schemas/appointment.py`

在 `AppointmentResponse` 中新增可选字段：
```python
# 规则摘要（患者端展示用）
cancel_deadline: Optional[datetime] = None       # 取消截止时间
checkin_advance_minutes: Optional[int] = None     # 建议提前签到分钟数
checkin_deadline: Optional[datetime] = None       # 签到截止时间
no_show_limit: Optional[int] = None               # 爽约次数限制
blacklist_days: Optional[int] = None              # 黑名单天数
```

**文件**: `apps/server/app/modules/appointments/service_booking.py` (create 方法，约第 270 行)

创建预约成功后，从快照字段和 SystemSettings 中提取规则摘要，填充到响应中。

#### 2. 前端 H5：替换硬编码温馨提示为动态内容

**文件**: `apps/patient-h5/src/pages/booking/confirm.tsx` (第 67-93 行)

替换当前硬编码的 4 条温馨提示，改为从预约创建 API 响应中获取规则数据动态渲染：
- 取消截止时间 → `cancel_deadline` 渲染为"请至少在 {deadline} 前取消"
- 签到要求 → `checkin_advance_minutes` 渲染为"请提前 {N} 分钟到达签到"
- 爽约规则 → `no_show_limit` + `blacklist_days` 渲染为"无故爽约 {N} 次将被限制预约 {M} 天"

保留第 1 条固定文案（"携带身份证件"），后 3 条改为动态。

#### 3. 前端小程序：同步替换硬编码文案

**文件**: `apps/patient-miniapp/src/packageBooking/pages/booking/result.tsx` (第 81-94 行)

与 H5 同步，替换硬编码温馨提示。小程序预约结果页需从预约创建 API 或页面参数中获取规则数据。

#### 4. 前端 H5：取消预约时展示规则影响

**文件**: `apps/patient-h5/src/pages/appointment/detail.tsx` (第 36-50 行)

取消确认 Dialog 中增加取消后果说明（基于预约响应中的规则数据）。

### 关键复用

- `GET /settings/booking/rules` 端点已返回 `cancelHours`、`signInAdvanceMinutes`、`signInLateMinutes` 等（`modules/settings/router.py:332-358`）
- 预约创建 API 响应中已有快照时间（`cancel_close_at`），仅需暴露到前端 schema
- 排班接口 `GET /schedules/available/{doctor_id}` 已返回 `booking_open_at`/`booking_close_at`（`modules/schedules/router.py:390-503`）

---

## P0-2：分布式锁粒度优化（4-8h）

### 方案：将只读预检查移到锁外

### 步骤

#### 1. 重构 create 方法的检查顺序

**文件**: `apps/server/app/modules/appointments/service_booking.py` (第 147-268 行)

**当前锁结构**：
```
外层用户锁 (timeout=10s, retry=5)
  ├── 日限额检查 (DB查询)
  ├── 同日同时段重复检查 (DB查询)
  ├── 同医生限额检查 (DB查询)
  └── 内层排班锁 (timeout=10s, retry=5)
        ├── 容量检查
        ├── 重复预约检查
        ├── 号源余量确认
        └── 创建预约 + 更新排班
```

**优化后**：
```
锁外预检查（第 147 行之前）
  ├── 日限额检查 (DB查询)        ← 从用户锁内移出
  ├── 同日同时段重复检查 (DB查询) ← 从用户锁内移出
  ├── 同医生限额检查 (DB查询)    ← 从用户锁内移出

排班锁 (timeout=5s, retry=3)    ← 移除用户锁，仅保留排班锁
  ├── 最终重复预约确认（防止竞态）
  ├── 容量检查
  ├── 号源余量确认
  └── 创建预约 + 更新排班
```

**关键改动**：
- 移除用户级锁（外层锁），用户维度的检查移到锁外做预检
- 排班锁内保留一次最终重复确认（防止锁外预检后、获取锁前被其他请求抢占）
- 锁超时从 10s 缩短到 5s（锁内操作减少）
- 重试从 5 次减少到 3 次

#### 2. 调整锁参数

**文件**: `apps/server/app/modules/appointments/service_booking.py`

排班锁参数调整：
- `timeout`: 10 → 5
- `retry_times`: 5 → 3

---

## P0-3：RuleSet 软删除 + 降级（8-12h）

### 方案：添加 deleted_at 字段 + 引用检查 + 查询过滤

### 步骤

#### 1. 模型添加 deleted_at 字段

**文件**: `apps/server/app/models/rule_set.py` (第 37-71 行 RuleSet 类)

在 `description` 字段后添加：
```python
deleted_at = Column(DateTime(timezone=True), nullable=True, comment="软删除时间")
```

更新 `__table_args__` 索引：
```python
Index('idx_rule_sets_enabled_priority', 'enabled', 'priority', 'deleted_at'),
```

#### 2. 创建 Alembic 迁移

**新文件**: `apps/server/migrations/versions/059_add_soft_delete_to_rule_sets.py`

- 添加 `deleted_at` 列（nullable=True）
- 更新索引

#### 3. 修改删除方法为软删除

**文件**: `apps/server/app/modules/rule_sets/service_mutation.py` (第 343-361 行)

改动：
- 添加引用检查：查询 `schedules` 表是否有 `rule_set_id` 指向该规则组
- 如有引用：拒绝删除，返回错误信息
- 无引用：设置 `deleted_at = datetime.now()` + `enabled = False`
- 保留审计日志记录

#### 4. 规则引擎查询添加软删除过滤

**文件**: `apps/server/app/modules/rule_engine/time_windows.py` (第 20-34 行)

在 `get_candidate_rule_sets` 的 where 条件中添加：
```python
RuleSet.deleted_at.is_(None),
```

#### 5. 规则集列表查询添加软删除过滤

**文件**: `apps/server/app/modules/rule_sets/service_query.py`

所有查询 `rule_sets` 表的方法添加默认条件 `RuleSet.deleted_at.is_(None)`。

#### 6. 详情查询处理已删除规则组

**文件**: `apps/server/app/modules/rule_sets/service_query.py`

`get_detail` 方法：已软删除的规则组返回 404（与当前硬删除行为一致）。

#### 7. 更新 DELETE 端点描述

**文件**: `apps/server/app/modules/rule_sets/router.py` (第 444-470 行)

更新描述文案，说明软删除行为和引用检查规则。

---

## 验证计划

### 后端测试

```bash
cd apps/server

# 1. 运行现有测试确保无回归
pytest tests/unit/test_rule_engine.py -v
pytest tests/unit/test_rule_set_service_wrapper.py -v

# 2. 运行预约相关测试
pytest tests/ -k "appointment" -v

# 3. 手动验证软删除
# - 创建规则组，创建使用该规则组的预约，尝试删除规则组（应被拒绝）
# - 创建规则组，无排班引用，删除（应成功软删除）
# - 查询规则列表，确认已删除的不出现
```

### 前端验证

```bash
# 1. 启动患者端 H5
pnpm dev:patient-h5

# 2. 验证预约确认页温馨提示是否动态渲染
# 3. 验证取消预约确认框是否有规则说明

# 4. 启动后端
pnpm dev:server
```

### 集成验证

1. 创建预约 → 确认响应包含 cancel_deadline、checkin_advance_minutes 等字段
2. 患者端预约成功页显示动态规则提示（非固定文案）
3. 取消预约 → 确认框显示取消截止时间
4. 并发预约测试 → 确认锁优化后号源不超卖
5. 删除有排班引用的规则组 → 返回拒绝
6. 删除无引用的规则组 → 软删除成功，历史预约不受影响

---

## 执行顺序

1. **P0-3（RuleSet 软删除）** — 独立性最强，不依赖其他两项
2. **P0-2（分布式锁优化）** — 独立修改 service_booking.py
3. **P0-1（患者端动态展示）** — 需要前后端协调，范围最广

三项可由不同 agent 并行执行（P0-3 和 P0-2 完全独立，P0-1 仅与 P0-2 有少量文件交集）。
