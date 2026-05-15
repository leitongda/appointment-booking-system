# Phase 0: unified_message 模块创建 + 数据迁移

## Context

统一消息中心重构的 P0 实施。基于 `.claude/plans/iridescent-crunching-seahorse.md` 迁移策略和 `reviews/unified-message-migration-review.md` 审查结论，创建新模块基础设施。

**已完成的 P0 项：**
- `beta_unified_message` 字段已添加到 `TenantFeatures`（tenants/schemas.py）
- `env.py` 已添加 `notification_log`, `notification_preference` 导入

**本次实施范围：**
- 创建 `unified_message` 模块（6 个新表 + 服务层 + 兼容层）
- Alembic migration 084
- 数据迁移脚本
- 模型注册

---

## 步骤

### Step 1: 创建 unified_message 模块目录和 models.py

创建 `apps/server/app/modules/unified_message/__init__.py` 和 `models.py`。

6 个新表定义（使用 SQLAlchemy 2.0 `mapped_column` 风格，与项目现有 `Column` 风格保持一致）：

| 表名 | 关键约束 | 说明 |
|------|---------|------|
| `notification_groups` | `dedup_key` unique, `(tenant_id)` indexed | 一次业务事件 = 一个通知组 |
| `notification_recipients` | FK → groups, `(tenant_id, user_id)` indexed | 每个接收人 |
| `notification_deliveries` | FK → groups + recipients, `(tenant_id, channel)` indexed | 每个接收人 x 每个渠道 |
| `unified_templates` | `UniqueConstraint("tenant_id", "code")` | 统一模板（多租户联合唯一） |
| `channel_strategies` | `UniqueConstraint("tenant_id", "event_type")` | 渠道策略 |
| `recipient_rules` | `(tenant_id)` indexed | 接收人规则 |

**关键设计决策（来自审查共识）：**
- `NotificationRecipient` 存储真实联系方式（phone/email/openid），不脱敏（重试发送依赖真实地址）
- `UnifiedTemplate.code` 使用 `(tenant_id, code)` 联合唯一约束（非全局唯一）
- 所有表使用 `String(36)` PK（UUID），与现有模型一致
- 继承 `Base`，不继承 `AuditMixin`（与 `NotificationLog` 一致，由应用层管理时间）

**复用：**
- `app/db/base.py` — `Base`, `TimestampMixin`
- UUID 生成: `lambda: str(uuid.uuid4())`（与现有模型一致）

### Step 2: 创建 schemas.py

请求/响应 Pydantic 模式，与现有 API 契约兼容：

- `NotificationEvent` — 发送事件入参（参考 `app/schemas/notification.py` 中现有定义）
- `SendResult` / `BatchSendResult` — 发送结果
- `UnreadCountResponse` — 未读计数（兼容旧 API 响应格式）
- `MessageQuery` — 消息列表查询参数
- 保持与旧 API 响应 JSON 结构 100% 一致（字段名、null vs 缺失、时间格式）

### Step 3: 创建 service.py — UnifiedMessageService

核心服务层，替代 `MessageService` + `NotificationDispatcher`：

```python
class UnifiedMessageService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send(self, event: NotificationEvent) -> SendResult:
        """统一发送入口"""
        # 1. 去重检查（Redis SET NX EX 第一层 + DB dedup_key 第二层）
        # 2. 解析接收人（RecipientRule 引擎）
        # 3. 渲染模板（UnifiedTemplate + Jinja2）
        # 4. 获取渠道策略（ChannelStrategy）
        # 5. 偏好过滤 + 静默时段检查
        # 6. 按策略发送（fallback / parallel / all）
        # 7. 记录投递结果（NotificationDelivery）
        # 8. 配额检查

    def send_sync(self, event: NotificationEvent) -> SendResult:
        """同步版本，供 Celery 任务使用（get_sync_db session）"""

    # 查询方法（兼容旧 API）
    async def get_user_messages(self, user_id, user_type, query) -> tuple[list, int]
    async def get_unread_count(self, user_id, user_type) -> UnreadCountResponse
    async def mark_as_read(self, message_id, user_id) -> bool
    async def mark_all_as_read(self, user_id, user_type, message_type=None) -> int
```

**复用现有组件：**
- `ChannelRegistry` — `app/infrastructure/notifications/registry.py`
- `BaseNotificationChannel` — `app/infrastructure/notifications/channels/base.py`
- 各渠道实现 — `app/infrastructure/notifications/channels/`
- 去重逻辑 — 保留 Redis（`dispatcher.py:242-272`）+ 新增 DB `dedup_key`
- 偏好过滤 — `dispatcher.py:274-343`
- 静默时段 — `dispatcher.py:345-370`

### Step 4: 创建 compat.py — 兼容层

```python
class MessageServiceCompat:
    """让业务模块无感知切换到新服务"""

    async def _should_use_new(self, tenant_id: str) -> bool:
        from app.common.feature_flags import FeatureFlagService
        return await FeatureFlagService.is_beta_enabled(self.db, tenant_id, "beta_unified_message")

    async def send_appointment_notification(self, ...):
        if await self._should_use_new(tenant_id):
            return await self.new_service.send(event)
        else:
            return await self.old_service.send_appointment_notification(...)
```

包装 3 个活跃 `send_*` 方法（`send_appointment_notification`, `send_schedule_notification`, `send_stop_clinic_notification`）+ `send_system_notification` 最小实现。

### Step 5: 注册模型

修改 `apps/server/app/models/__init__.py`，添加：
```python
from app.modules.unified_message.models import (
    NotificationGroup,
    NotificationRecipient,
    NotificationDelivery,
    UnifiedTemplate,
    ChannelStrategy,
    RecipientRule,
)
```

### Step 6: Alembic Migration 084

创建 `apps/server/migrations/versions/084_create_unified_message_tables.py`：
- 6 个 `CREATE TABLE` 语句
- 索引和唯一约束
- `upgrade()` / `downgrade()`
- 确认 `alembic revision --autogenerate` 能检测到新表

### Step 7: 数据迁移脚本

创建 `apps/server/scripts/migrate_unified_message.py`：

**映射关系：**
| 旧表 | 新表 | 映射 |
|------|------|------|
| `messages` | `notification_groups` | 按 `(tenant_id, related_id, message_type)` 分组 |
| `messages` | `notification_recipients` | 每条 message → 一条 recipient |
| `notification_logs` | `notification_deliveries` | 每条 log → 一条 delivery |
| `message_templates` + `email_templates` | `unified_templates` | 合并映射 |

**特性：**
- 增量迁移（记录已迁移 ID 范围，支持断点续传）
- 迁移前后行数统计对比
- `notification_groups` 新增 `legacy_message_id` 字段（回溯用）
- `notification_deliveries` 新增 `legacy_log_id` 字段（回溯用）
- 使用独立 Python 脚本（非 Alembic migration），因为涉及复杂数据转换

---

## 关键文件清单

### 需要创建的文件
- `apps/server/app/modules/unified_message/__init__.py`
- `apps/server/app/modules/unified_message/models.py`
- `apps/server/app/modules/unified_message/schemas.py`
- `apps/server/app/modules/unified_message/service.py`
- `apps/server/app/modules/unified_message/compat.py`
- `apps/server/migrations/versions/084_create_unified_message_tables.py`
- `apps/server/scripts/migrate_unified_message.py`

### 需要修改的文件
- `apps/server/app/models/__init__.py` — 注册 6 个新模型

### 已完成的修改
- `apps/server/app/modules/tenants/schemas.py` — `beta_unified_message` 字段
- `apps/server/migrations/env.py` — 导入 notification_log, notification_preference

---

## 验证计划

1. `alembic revision --autogenerate` 确认检测到 6 个新表
2. `alembic upgrade head` 创建表成功
3. `pytest tests/unit/ -k "unified_message" -v` 单元测试通过
4. `pytest tests/unit/test_message_service.py -v` 旧测试不受影响
5. 兼容层在 `beta_unified_message=False` 时正确转发到旧服务
6. 兼容层在 `beta_unified_message=True` 时调用新服务
7. 数据迁移脚本：迁移前后行数统计对比

---

## 实施顺序

```
Step 1 (models.py) → Step 2 (schemas.py) → Step 3 (service.py) → Step 4 (compat.py)
     ↓
Step 5 (注册模型) → Step 6 (Alembic migration) → Step 7 (数据迁移脚本)
```

Step 1-4 可以一起创建（无外部依赖），Step 5-7 依赖 Step 1 的模型定义。
