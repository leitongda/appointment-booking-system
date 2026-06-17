# Server 端结构优化计划

## Context

当前 server 端 (`apps/server/app/`) 有 477+ Python 文件、56 个业务模块。架构核心 `modules/` 目录已成型，但存在以下问题：

- `to_camel()` 函数在 45 个文件中重复定义
- 8 组 enum 在 `models/` 和 `schemas/` 中各定义一次（如 `MessageType`, `FeedbackType` 等）
- 业务常量散落在各模块的 `common.py` 中，无统一位置
- 模块内文件命名风格不完全统一（后缀不规律）
- 7 个遗留文件仍留在 `services/` 目录
- 无 `enums/`、`constants/`、`repositories/` 等推荐目录

**目标**：在保持 `modules/` 域聚合架构不变的前提下，引入推荐的分层补充（`enums/`, `constants/`, `repositories/`），统一命名规范，消除重复代码。

---

## 一、目标目录结构

```
apps/server/app/
├── main.py                    # 应用入口 (不变)
├── celery_app.py              # Celery (不变)
│
├── core/                      # 核心配置 (不变)
│   ├── config.py, security.py, logging.py
│   ├── redis.py, websocket.py, events.py
│   └── error_codes.py
│
├── api/                       # 路由注册层 (不变)
│   └── v1/__init__.py         # RouterRegistration 集中注册
│
├── db/                        # 数据库 (不变)
├── middleware/                 # 中间件 (不变)
├── common/                    # 跨模块共享工具 (不变)
├── utils/                     # 通用工具 (不变)
├── infrastructure/            # 外部集成 (不变)
├── tasks/                     # Celery 任务 (不变)
├── seed/                      # 种子数据 (不变)
│
├── models/                    # ORM 模型 (不变)
├── schemas/                   # 共享 Pydantic Schema (精简)
│   ├── response.py            # to_camel (唯一权威定义) + Response/PageResponse
│   └── ...                    # 跨模块复用的 schema
│
├── enums/                     # [新增] 枚举统一
│   ├── __init__.py            # re-export all
│   ├── appointment.py         # AppointmentStatus, CheckinMethod
│   ├── schedule.py            # ScheduleStatus, PublishStatus, AppointmentType, ScheduleMode
│   ├── message.py             # MessageType
│   ├── feedback.py            # FeedbackType, FeedbackStatus
│   ├── notification.py        # NotificationChannel, NotificationStatus, NotificationPriority
│   ├── support_ticket.py      # SupportTicketType/Status/Priority
│   ├── payment.py             # PaymentStatus, RefundStatus
│   ├── user.py                # RoleType (从 common/auth_types.py 迁入)
│   └── common.py              # TimeUnit, VisitScope, Period, Platform 等通用枚举
│
├── constants/                 # [新增] 业务常量统一
│   ├── __init__.py
│   ├── appointment.py         # ACTIVE_APPOINTMENT_STATUSES, APPOINTMENT_QUERY_OPTIONS
│   ├── schedule.py            # TIME_SLOT_MAP, BOOKABLE_STATUSES
│   └── tenant.py              # MAX_STORES_DEFAULT, MAX_DOCTORS_DEFAULT 等
│
└── modules/                   # 业务模块 (保持域聚合，统一内部规范)
    ├── appointments/          # 复杂模块范例
    │   ├── __init__.py
    │   ├── router.py          # 聚合路由 + 根级端点
    │   ├── router_query.py    # 查询端点
    │   ├── router_booking.py  # 预约端点
    │   ├── router_flow.py     # 流程端点
    │   ├── service.py         # 组合服务入口
    │   ├── service_booking.py # 预约逻辑 (Mixin)
    │   ├── service_flow.py    # 流程逻辑 (Mixin)
    │   ├── common.py          # 模块内共享
    │   └── schemas.py         # 仅本模块使用的 schema
    │
    ├── doctors/               # 读写分离模块范例
    │   ├── router.py
    │   ├── service.py         # DoctorService(QueryMixin, MutationMixin)
    │   ├── service_query.py
    │   ├── service_mutation.py
    │   └── schemas.py
    │
    ├── blacklists/            # 简单模块范例
    │   ├── router.py
    │   └── service.py
    │
    └── ... (其余 53 个模块)
```

---

## 二、模块命名规范

### 2.1 目录命名

| 类型 | 规则 | 示例 |
|------|------|------|
| REST 资源集合 | 复数名词 | `appointments/`, `doctors/`, `patients/`, `stores/` |
| 功能域 | 单数或复合 | `auth/`, `export/`, `revenue/`, `upload/` |
| 多词概念 | snake_case | `doctor_booking_settings/`, `schedule_templates/`, `leave_requests/` |
| 路由前缀 | `_` 替换为 `-` | `medical_records/` → `/medical-records` |

**结论**：当前命名已经规范，不需要改动。

### 2.2 模块内部文件后缀规范

| 文件模式 | 用途 | 必须? |
|----------|------|-------|
| `router.py` | API 端点（或聚合路由） | 是 |
| `router_{子域}.py` | 复杂模块的子域端点 | 复杂模块 |
| `service.py` | 主服务入口（组合类或单类） | 是 |
| `service_{子域}.py` | 子域业务逻辑（Mixin 类） | 拆分模块 |
| `schemas.py` | 仅本模块使用的 Pydantic schema | 按需 |
| `common.py` | 模块内共享常量/基类/工具 | 按需 |
| `repository.py` | 数据访问抽象（可选） | 按需 |
| `engine.py` | 引擎核心逻辑 | 引擎类模块 |

### 2.3 子域拆分策略

根据模块特性选择拆分方式：

| 策略 | 适用场景 | 示例 |
|------|----------|------|
| **读写分离** | 单实体多操作 | `service_query.py` + `service_mutation.py` |
| **领域分离** | 多业务流程 | `service_booking.py` + `service_flow.py` |
| **功能分离** | 多技术关注点 | `service_generation.py` + `service_conflict.py` |

### 2.4 Service 组合模式（强制标准）

每个模块的 `service.py` 必须导出一个组合服务类：

```python
# 简单模块
class BlacklistService:
    def __init__(self, db: AsyncSession):
        self.db = db

# 读写分离
class DoctorService(DoctorQueryMixin, DoctorMutationMixin):
    def __init__(self, db: AsyncSession):
        self.db = db

# 领域分离
class AppointmentService(AppointmentBookingService, AppointmentFlowService):
    pass
```

路由只从这个 `service.py` 导入服务类。

---

## 三、是否按业务模块聚合

**是，保持当前 `modules/` 域聚合架构，不要拆散为层聚合。**

理由：
- 当前 56 个模块已经按业务域聚合在 `modules/` 下
- 每个模块内聚了 router + service + schema，修改一个业务域只需关注一个目录
- 推荐的 `services/` + `repositories/` 平铺结构在 56 个模块的规模下会导致文件爆炸（56 个 service + 56 个 repository = 112 个文件平铺在一个目录）

**补充**：对跨模块复用的数据访问逻辑，在对应模块内创建 `repository.py`（可选），而非统一建 `repositories/` 目录。

---

## 四、实施步骤

### Phase 1: 基础设施 — enums/ + constants/ + to_camel 统一

**风险：低 | 不改变任何外部行为**

1. **创建 `app/enums/`**：将 45 个分散的 enum 定义统一
   - `models/` 中的 11 个 enum → `enums/` 单一定义，原位置改为 re-export
   - `schemas/` 中的 22 个 enum → 同上
   - `modules/appointments/common.py` 的 `APPOINTMENT_STATUS` / `CHECKIN_METHOD` → `enums/appointment.py`

2. **创建 `app/constants/`**：
   - `modules/appointments/common.py` → `ACTIVE_APPOINTMENT_STATUSES`, `APPOINTMENT_QUERY_OPTIONS` → `constants/appointment.py`

3. **统一 `to_camel()`**：
   - 权威定义：`schemas/response.py:7`
   - 删除其余 44 处重复定义，全部改为 `from app.schemas.response import to_camel`

### Phase 2: 模块标准化（逐模块推进）

按风险从低到高的顺序：

1. **Tier 1 简单模块**（12 个，仅 router）：确认无需改动
2. **Tier 2 标准模块**（22 个，router + service）：确认 service.py 导出规范
3. **Tier 3 拆分模块**（9 个，读写/领域分离）：统一 service.py 组合入口
4. **Tier 4 复杂模块**（13 个，多路由/多服务）：标准化子域命名

每个模块处理流程：检查 → 调整 → 更新测试 import → 提交

### Phase 3: 遗留清理

- 迁移 `services/email_template_service.py` → `modules/email_templates/service.py`
- 迁移 `services/rule_performance_service.py` → `modules/rule_engine/` 或 `modules/statistics/`
- 清空 `services/` 目录

### Phase 4: Repository 模式（可选，按需）

仅在以下场景引入 `repository.py`：
- 某模块内多处重复的复杂查询模式
- 跨模块需要共享的数据访问逻辑（如排班可用性查询被 appointments/schedules/doctors 共用）

---

## 五、涉及的关键文件

| 文件 | 变更类型 |
|------|----------|
| `app/schemas/response.py` | to_camel 唯一权威定义 |
| `app/enums/*.py` | 新建 8-10 个 enum 文件 |
| `app/constants/*.py` | 新建 2-3 个常量文件 |
| `app/modules/appointments/common.py` | 提取 enum/constant 后精简 |
| `app/models/feedback.py`, `support_ticket.py`, `message.py`, `email_template.py`, `leave_request.py` | enum 改为从 `app.enums` re-export |
| `app/schemas/feedback.py`, `support_ticket.py`, `message.py`, `notification_log.py` 等 | enum 改为从 `app.enums` re-export |
| 44 个含 `to_camel` 定义的文件 | 删除本地定义，改为 import |
| `app/services/` 下 2 个遗留文件 | 迁移到对应模块 |

---

## 六、验证方式

1. **Phase 1 完成后**：
   - `cd apps/server && pytest tests/unit/ -x` — 所有单元测试通过
   - `grep -r "def to_camel" app/ --include="*.py" | grep -v response.py` — 应为空（0 处重复）
   - `grep -r "class.*Enum" app/ --include="*.py" | grep -v enums/ | grep -v __pycache__` — 原位置的 enum 应只剩 re-export

2. **Phase 2 完成后**：
   - `cd apps/server && pytest tests/ -x` — 全量测试通过
   - 对每个处理过的模块运行其对应测试文件

3. **Phase 3 完成后**：
   - `grep -r "from app.services\." app/ --include="*.py" | grep -v __pycache__` — 应无直接 import
   - `ls app/services/` — 应只剩 `__init__.py`
