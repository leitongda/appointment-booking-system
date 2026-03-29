# P2 + 测试修复 + 迁移策略 -- 实施方案

> 基于 reviews/saas-tenant-refit-review.md 画布，P0/P1 完成后的后续工作计划
> 用户确认：无生产数据、全局过滤暂缓先补漏、PG 集成测试本轮实施

---

## Phase 1: 修复 37 个既有测试失败 (P2-3)

### 目标
将 467 passed / 37 failed 提升到 504 passed / 0 failed。

### 1.1 conftest.py 添加租户 fixture (分类 E 的根因)

**文件**: `apps/server/tests/conftest.py`

- 新增 `test_tenant` fixture，创建测试用 Tenant + SubscriptionPlan
- 更新所有依赖 tenant_id 的 fixture（`test_store`, `test_doctor`, `test_department`, `test_admin`, `test_super_admin`, `test_store_admin`, `test_user`, `test_patient` 等），关联 `test_tenant.id`
- 确保集成测试中创建的请求正确设置租户上下文（`X-Tenant-ID` header 或 `set_tenant_context`）

### 1.2 分类 A: 响应格式断言修复 (13个)

**模式替换**:
- `response.json()["detail"]` -> `response.json()["message"]`
- `response.json()["access_token"]` -> `response.json()["data"]["accessToken"]`
- 确认统一响应格式 `{code, message, data}`

**涉及文件**:
- `tests/integration/test_auth_login.py` (6个)
- `tests/integration/test_auth_protection.py` (3个)
- `tests/integration/test_permissions_403.py` (3个)
- `tests/tenants/test_import_tenant_isolation.py` (1个: `BusinessError.detail` -> `BusinessError.message`)

### 1.3 分类 B: 路由 404 修复 (5个)

**策略**: 对比 `app/api/v1/__init__.py` 路由注册表
- 路由已移动 -> 更新测试 URL
- 路由已废弃 -> 标记 `@pytest.mark.skip` 或删除

**涉及文件**:
- `tests/integration/test_admin_and_doctor_endpoints.py` (1个: `/api/v1/doctor-portal/me`)
- `tests/integration/test_appointments_router_endpoints.py` (2个: `/statistics`, `/queue/info`)
- `tests/tenants/test_tenant_data_isolation.py` (2个: `/export/doctors`)

### 1.4 分类 C: Mock 配置修复 (3个)

**涉及文件**: `tests/tenants/test_import_tenant_isolation.py`
- `MagicMock` 替代为真实 ORM 模型类
- 使用 conftest 中的 fixture 创建测试数据

### 1.5 分类 D: 缺少 import (2个)

**涉及文件**:
- `tests/tenants/test_tenant_data_isolation.py` (1个: 添加 `from sqlalchemy import select`)
- `tests/tenants/test_tenant_isolation_enhanced.py` (1个: 同上)

### 1.6 分类 E: 业务逻辑变更 (10个)

**根因**: P0/P1 改造后需要租户上下文，但测试未设置。
- 导入/导出测试: 请求中添加 `X-Tenant-ID` header
- 公开端点测试: 确保测试数据有 `tenant_id`
- 由 conftest fixture 统一解决大部分问题

### 1.7 验证

```bash
cd apps/server && python3 -m pytest tests/ -v --tb=short
# 目标: 504 passed, 0 failed
```

### 1.8 并行分组

- **Agent A**: conftest.py fixture 更新 + 分类 E 修复 (集成测试租户上下文)
- **Agent B**: 分类 A (格式断言) + 分类 B (路由 404) + 分类 C/D (mock/import)

---

## Phase 2: 数据库复合索引策略 (P2-2)

### 目标
为高频多租户查询添加复合索引，避免全表扫描。

### 2.1 推荐复合索引

| 表 | 索引列 | 场景 |
|---|---|---|
| appointments | (tenant_id, status) | 按状态查预约 |
| appointments | (tenant_id, user_id) | 按用户查预约 |
| appointments | (tenant_id, doctor_id, schedule_date) | 医生日历 |
| appointments | (tenant_id, schedule_id) | 排班关联 |
| schedules | (tenant_id, doctor_id, schedule_date) | 按医生+日期 |
| schedules | (tenant_id, store_id, schedule_date) | 按门店+日期 |
| schedules | (tenant_id, status) | 按状态查排班 |
| doctors | (tenant_id, department_id) | 按科室查医生 |
| doctors | (tenant_id, store_id) | 按门店查医生 |
| doctors | (tenant_id, status) | 按状态 |
| departments | (tenant_id, store_id) | 按门店查科室 |
| stores | (tenant_id, status) | 按状态 |
| admins | (tenant_id, role_id) | 按角色 |
| admins | (tenant_id, status) | 按状态 |
| users | (tenant_id, phone) | 按手机号 |
| users | (tenant_id, status) | 按状态 |
| patients | (tenant_id, user_id) | 按用户查就诊人 |
| schedule_templates | (tenant_id, store_id) | 按门店查模板 |

### 2.2 实施

**文件**: `apps/server/migrations/versions/042_add_composite_indexes.py`

- 使用 `op.create_index()` 添加复合索引
- 保留已有单列 `tenant_id` 索引
- 提供 downgrade 删除所有新增索引

### 2.3 验证

```bash
# 应用迁移
alembic upgrade head
# 检查索引
psql -c "\di" | grep idx_
# EXPLAIN 验证
EXPLAIN ANALYZE SELECT * FROM appointments WHERE tenant_id = 'xxx' AND status = 1;
```

---

## Phase 3: 高风险 service 租户过滤补漏 (P2-1 替代)

### 目标
审计无租户过滤的 service 文件，为高风险模块补充手动过滤。

### 3.1 审计范围

需检查的模块（无或不确定有租户过滤）:
- `feedback`, `medical_record`, `content`, `settings`, `rule_set`
- `schedule_template`, `shift_type`, `schedule_suspension`, `custom_schedule`
- `email_template`, `point_log`, `behavior_log`, `schedule_generation_log`
- `messages`, `blacklist`, `consultation_fee`, `doctor_booking_setting`
- `leave_request`, `booking_notice`, `user_favorite`, `waitlist`

### 3.2 风险分级

| 级别 | 判定标准 | 处理方式 |
|---|---|---|
| **高** | 直接操作用户数据，无间接隔离 | 必须补充 tenant_id 过滤 |
| **中** | 通过 store_id 间接隔离 | 评估是否需要补充 |
| **低** | 平台级数据或只读配置 | 记录，暂不处理 |

### 3.3 实施

- 逐模块读取 service 文件
- 按风险分级决定是否添加过滤
- 使用 `get_current_tenant_id()` + 条件过滤模式（与 P0 一致）

---

## Phase 4: Alembic 迁移策略 (无生产数据简化版)

### 目标
由于无生产数据，策略大幅简化。

### 4.1 当前状态
- 迁移 039/040 已添加 tenant_id 字段（nullable=True）
- 无历史数据需要回填

### 4.2 实施内容

**文件**: `apps/server/migrations/versions/043_tenant_id_not_null.py`

1. 将核心业务表的 `tenant_id` 从 `nullable=True` 改为 `nullable=False`
2. 对外键引用的表，确保外键约束 `NOT NULL`
3. 提供 downgrade 回退到 nullable

**注意**: 只对核心业务表操作，不涉及 `Company`, `MiniappInstance` 等已有 NOT NULL 的新表。

**涉及表**: stores, admins, roles, users, patients, doctors, departments, schedules, schedule_templates, appointments

### 4.3 验证

```bash
alembic upgrade head
# 检查列定义
psql -c "\d stores" | grep tenant_id
```

---

## Phase 5: PostgreSQL 集成测试 (P2-4)

### 目标
添加 PG 测试环境，验证迁移和复合索引。

### 5.1 实施内容

**新建文件**: `apps/server/tests/conftest_pg.py`
- 提供 `pg_session` fixture（使用环境变量 `TEST_DATABASE_URL`）
- 使用 `@pytest.mark.integration` 标记

**新建文件**: `apps/server/docker-compose.test.yml`
- PostgreSQL 16 测试实例

**新建文件**: `apps/server/tests/integration/test_alembic_migration.py`
- 验证迁移可正常执行和回滚
- 验证复合索引已创建

**修改文件**: `.github/workflows/test.yml`
- 添加 PostgreSQL service
- 添加 integration test 步骤

### 5.2 验证

```bash
docker-compose -f docker-compose.test.yml up -d postgres
TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:5433/test_db" \
  python3 -m pytest tests/integration/ -m integration -v
```

---

## 执行顺序和并行策略

```
Phase 1 (测试修复) ──────────────────────> Phase 2 (复合索引)
     │                                              │
     │                                              v
     ├────────────────────────────────────> Phase 4 (tenant_id NOT NULL)
     │
     v
Phase 3 (service 补漏) ───────────────> Phase 5 (PG 集成测试)
```

- **第一批并行**: Phase 1 + Phase 3
- **第二批**: Phase 2 + Phase 4（依赖 Phase 1 的测试基线）
- **第三批**: Phase 5（依赖 Phase 2 的复合索引）

### 并行 Agent 分组

| 批次 | Agent | 任务 |
|------|-------|------|
| 1 | A | Phase 1: conftest fixture + 分类 E 修复 |
| 1 | B | Phase 1: 分类 A/B/C/D 修复 |
| 1 | C | Phase 3: service 租户过滤审计与补漏 |
| 2 | D | Phase 2: 复合索引迁移脚本 |
| 2 | E | Phase 4: tenant_id NOT NULL 迁移 |
| 3 | F | Phase 5: PG 集成测试基础设施 |

---

## 预估工作量

| Phase | 内容 | 预估 |
|-------|------|------|
| Phase 1 | 37 个测试修复 | 12-16h |
| Phase 2 | 复合索引 | 6-8h |
| Phase 3 | service 补漏 | 8-12h |
| Phase 4 | NOT NULL 迁移 | 4-6h |
| Phase 5 | PG 集成测试 | 8-10h |
| **合计** | | **38-52h** |
