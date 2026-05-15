# Phase 0：迁移策略详细设计

## Context

统一消息中心重构的第一步：设计迁移策略和 API 兼容层。

**核心发现（决定迁移策略）：**
1. MessageService 是业务模块调用通知系统的**主要入口** — 4 个业务模块目录调用 MessageService 的 3 种 send_* 方法（send_appointment_notification、send_schedule_notification、send_stop_clinic_notification），不直接调用 NotificationDispatcher。send_system_notification 无外部调用者，仅在 service_messages.py 内部降级路径中使用
2. Celery 任务（预约提醒/重试/邮件钩子）**完全独立实现**，既不导入也不使用 NotificationDispatcher 或 MessageService，直接操作数据库（同步 session）和渠道服务
3. 前端通过 14 个 API 端点访问消息功能（messageApi 14 个方法，与后端 14 个路由完全对齐），其中前端实际只调用 7 个（getList, getUnreadCount, markAsRead, markAllAsRead, delete, send, getAllList），另外 7 个为死代码
4. 现有 API 端点结构合理，重构后可保持相同的 API surface
5. 现有 FeatureFlagService 基于租户 features JSON 实现三级优先级灰度（系统默认→计划默认→租户覆盖），迁移应复用而非重建

**迁移策略选择：分层模块替换（Option C）**
- 保持 API 路由和业务调用接口不变
- 从内到外逐层替换：数据模型 → 服务层 → 路由层
- 每层独立测试，Feature flag 切换

---

## 迁移架构

```
Phase 0: 新模块创建 + 兼容层
Phase 1: 新数据模型 + 新服务层（旧路由转发到新服务）
Phase 2: 新路由层（替换旧路由）
Phase 3: 清理旧代码
```

## 步骤

### Step 0.1: 创建新模块目录结构

创建 `apps/server/app/modules/unified_message/` 目录：

```
modules/unified_message/
├── __init__.py
├── models.py           # 新数据模型（Step 0.2）
├── schemas.py          # 新请求/响应模式
├── service.py          # 新服务层（Step 0.3）
├── router.py           # 新路由（Phase 2）
├── compat.py           # 兼容层（Step 0.4）
└── migrations/
    └── 001_initial.py  # 新表 Migration
```

保留旧模块不动，新旧并存。

**Alembic 模型注册（必须）：**
- 在 `apps/server/app/models/__init__.py` 中导入新模型，确保 `alembic revision --autogenerate` 能检测到新表
- 在 `apps/server/migrations/env.py` 的显式导入列表中添加新模型（当前未导入 notification_log 和 notification_preference）

### Step 0.2: 新数据模型设计

**关键决策：保持 Message + NotificationLog 双表，不合并。**

新建表（不删除旧表）：

```python
# unified_message/models.py

class NotificationGroup(Base):
    """通知组：一次业务事件生成一个通知组，关联多个渠道的发送记录"""
    __tablename__ = "notification_groups"
    id = String(36), PK
    tenant_id = String(36), indexed
    store_id = String(36), indexed
    event_type = String(50)          # appointment.success / appointment.reminder.24h
    template_code = String(50)       # 关联 UnifiedTemplate
    message_type = String(30)        # appointment / system / stop_clinic
    priority = String(10)            # critical / high / medium / low
    variables = JSON                 # 模板变量
    related_id = String(36)          # 关联业务 ID
    dedup_key = String(200), unique  # 去重键
    status = String(20)              # pending / partial / sent / failed
    created_at = DateTime
    updated_at = DateTime

class NotificationRecipient(Base):
    """接收人记录：通知组下的每个接收人"""
    __tablename__ = "notification_recipients"
    id = String(36), PK
    group_id = String(36), FK → notification_groups.id
    tenant_id = String(36), indexed
    user_id = String(36), indexed
    user_type = String(20)
    # 站内信数据（复用 Message 语义）
    title = String(200)
    content = Text
    is_read = Integer, default 0
    read_at = DateTime
    # 联系方式（真实地址，与现有 NotificationLog.recipient 一致）
    # 注：不存储脱敏数据，原因：1) 现有代码无脱敏 2) 脱敏后重试发送无法获取真实地址
    # 查询 API 层面做返回脱敏，存储时保留真实地址
    phone = String(20)
    email = String(100)
    openid = String(100)
    status = String(20)              # pending / sent / failed
    created_at = DateTime
    updated_at = DateTime

class NotificationDelivery(Base):
    """投递记录：每个接收人 × 每个渠道 = 一条记录（替代 NotificationLog）"""
    __tablename__ = "notification_deliveries"
    id = String(36), PK
    group_id = String(36), FK → notification_groups.id
    recipient_id = String(36), FK → notification_recipients.id
    tenant_id = String(36), indexed
    channel = String(20), indexed     # in_app / sms / email / wechat / websocket
    status = String(20), indexed      # pending / sent / failed / permanently_failed
    recipient_address = String(200)   # 接收地址（真实地址，查询 API 层面做返回脱敏）
    error_message = Text
    retry_count = Integer, default 0
    max_retries = Integer, default 3
    next_retry_at = DateTime
    sent_at = DateTime
    extra_data = JSON
    created_at = DateTime

class UnifiedTemplate(Base):
    """统一模板：所有渠道共享"""
    __tablename__ = "unified_templates"
    id = String(36), PK
    tenant_id = String(36), indexed
    code = String(50)                # appointment_success
    # 唯一约束: UniqueConstraint("tenant_id", "code") — 多租户下各租户可使用相同模板代码
    name = String(100)
    message_type = String(30)
    event_type = String(50)          # appointment.success
    # 各渠道模板内容
    subject_template = String(200)   # 邮件主题
    html_template = Text             # 邮件 HTML
    text_template = Text             # 短信/站内信纯文本
    wechat_template_id = String(50)  # 微信模板 ID
    wechat_template_mapping = JSON   # 微信字段映射
    # 通用
    variables_schema = JSON          # 变量定义和默认值
    status = Integer, default 1
    created_at = DateTime
    updated_at = DateTime

class ChannelStrategy(Base):
    """渠道策略：按事件类型配置"""
    __tablename__ = "channel_strategies"
    id = String(36), PK
    tenant_id = String(36), indexed
    event_type = String(50), unique_per_tenant
    channels = JSON                   # ["email", "sms", "in_app"]
    strategy = String(20)            # fallback / parallel / all
    dedup_window_seconds = Integer   # 0 = 不去重, 86400 = 24h
    priority = String(10)            # critical / high / medium / low
    quiet_hours_exempt = Boolean     # 是否豁免静默时段
    status = Integer, default 1
    created_at = DateTime
    updated_at = DateTime

class RecipientRule(Base):
    """接收人规则"""
    __tablename__ = "recipient_rules"
    id = String(36), PK
    tenant_id = String(36), indexed
    name = String(100)
    rule_type = String(30)           # role / department / user_list / dynamic / event_driven
    rule_config = JSON               # 规则配置
    event_type = String(50)          # 绑定的事件类型（可选）
    status = Integer, default 1
    created_at = DateTime
    updated_at = DateTime
```

**旧表保留策略：**
- `messages` 表 → 保留，Phase 2 完成后废弃
- `notification_logs` 表 → 保留，Phase 2 完成后废弃
- `message_templates` 表 → 数据迁移到 `unified_templates`，然后废弃
- `email_templates` 表 → 数据迁移到 `unified_templates`，然后废弃
- `notification_preferences` 表 → Phase 1 迁移到新偏好模型

### Step 0.3: 新服务层设计

```python
# unified_message/service.py

class UnifiedMessageService:
    """新统一消息服务 — 替代 MessageService + NotificationDispatcher"""

    async def send(self, event: NotificationEvent) -> SendResult:
        """统一发送入口"""
        # 1. 去重检查（NotificationGroup.dedup_key）
        # 2. 解析接收人（RecipientRule 引擎）
        # 3. 渲染模板（UnifiedTemplate + Jinja2）
        # 4. 获取渠道策略（ChannelStrategy）
        # 5. 偏好过滤 + 静默时段检查
        # 6. 按策略发送（fallback / parallel / all）
        # 7. 记录投递结果（NotificationDelivery）
        # 8. 配额检查
        pass

    async def send_batch(self, events: list[NotificationEvent]) -> BatchSendResult:
        """批量发送"""
        pass

    async def schedule_send(self, event: NotificationEvent, send_at: datetime) -> str:
        """定时发送"""
        pass

    # 查询方法（与旧 API 兼容）
    async def get_user_messages(self, user_id, user_type, query) -> tuple[list, int]:
        """兼容旧 MessageService.get_user_messages"""
        pass

    async def get_unread_count(self, user_id, user_type) -> UnreadCountResponse:
        """兼容旧 MessageService.get_unread_count"""
        pass

    async def mark_as_read(self, message_id, user_id) -> bool:
        pass

    async def mark_all_as_read(self, user_id, user_type, message_type=None) -> int:
        pass

    # Celery 任务同步接口（供同步 session 环境调用）
    def send_sync(self, event: NotificationEvent) -> SendResult:
        """同步版本发送入口，供 Celery 任务使用"""
        # 使用同步 session，直接调用渠道服务
        # 与现有 notification_task.py 的发送模式一致
        pass
```

### Step 0.4: 兼容层设计

```python
# unified_message/compat.py

class MessageServiceCompat:
    """兼容层：让业务模块无感知地切换到新服务"""

    def __init__(self, new_service: UnifiedMessageService, old_service: MessageService, db: AsyncSession):
        self.new_service = new_service
        self.old_service = old_service
        self.db = db
        # 不在 __init__ 中缓存 flag，每次调用时运行时检查

    async def _should_use_new(self, tenant_id: str) -> bool:
        """运行时检查 feature flag，支持动态切换"""
        from app.common.feature_flags import FeatureFlagService
        return await FeatureFlagService.is_beta_enabled(self.db, tenant_id, "beta_unified_message")

    async def send_appointment_notification(self, tenant_id, user_id, user_type, title, content,
                                            appointment_id, template_code=None,
                                            template_variables=None):
        if await self._should_use_new(tenant_id):
            event = NotificationEvent(
                event_type="appointment.success",
                recipient_id=user_id,
                recipient_type=user_type,
                template_code=template_code or "appointment_success",
                variables=template_variables or {},
                title=title,
                content=content,
                related_id=appointment_id,
            )
            return await self.new_service.send(event)
        else:
            return await self.old_service.send_appointment_notification(...)

    # 同理包装其他 3 个 send_* 方法
    async def send_schedule_notification(self, ...): ...
    async def send_system_notification(self, ...): ...
    async def send_stop_clinic_notification(self, ...): ...
```

**切换方式：**
- 复用现有 FeatureFlagService（`apps/server/app/common/feature_flags.py`）
- 在 TenantFeatures schema 中添加 `beta_unified_message: bool = Field(default=False, description="统一消息中心（灰度）")`
- 兼容层每次调用时运行时检查 `await FeatureFlagService.is_beta_enabled(db, tenant_id, "beta_unified_message")`
- 不在 `__init__` 中缓存 flag 值，确保动态切换生效
- 逐租户灰度：通过管理后台 TenantFeatures JSON 字段控制，无需重启服务
- 默认 False（使用旧服务）

### Step 0.5: 迁移顺序规划

**业务调用点的迁移顺序（由低风险到高风险）：**

1. **send_schedule_notification**（仅通知医生，2 处直接调用 + 2 处间接调用）
   - 调用者：schedules/service_generation.py:282, schedules/service_mutation.py:350（直接）
   - 间接调用：schedules/service_mutation.py:108,164 通过 `_send_schedule_notification_to_doctor`
   - 风险：低

2. **send_stop_clinic_notification**（通知受影响患者，2 处调用，有动态查询逻辑）
   - 调用者：schedule_suspensions/service.py:232, schedules/service_mutation.py:384
   - 风险：中（需要验证接收人规则引擎的正确性）

3. **send_appointment_notification**（最复杂，5 处调用，多渠道 + 多场景）
   - 调用者：appointments/service_booking.py:305,516,654, appointments/service_flow.py:190,256
   - 风险：高

4. **send_system_notification**（保留接口定义和最小实现，无外部调用者）
   - 当前 0 处外部调用，仅在 service_messages.py 内部降级路径中使用
   - 迁移策略：在 UnifiedMessageService 中保留接口签名和最小实现（in_app 渠道），不列为迁移优先级
   - 目的：保证兼容层完整性，为产品扩展预留通道
   - 风险：极低（无外部调用者）

5. **Celery 任务迁移**（最后，因为涉及同步/异步会话差异）
   - notification_task.py — 预约提醒（923 行，4 个任务，全部同步 session）
   - notification_retry_task.py — 重试（同步 session，退避策略 1min→5min→30min）
   - email_hook_task.py — 邮件钩子（同步 session，smtplib 同步发送）
   - **关键约束**：Celery 任务层保持同步实现，新服务提供 `send_sync` 同步接口
   - **关键约束**：必须有独立集成测试覆盖"预约创建→等待提醒→验证通知发送"完整链路
   - 风险：高（定时任务，出错影响范围大）

### Step 0.6: 数据迁移方案

**旧表 → 新表映射关系：**

| 旧表 | 新表 | 映射逻辑 |
|------|------|---------|
| `messages` | `notification_recipients` | 每条 message → 一条 recipient（user_id, user_type, title, content, is_read, read_at） |
| `messages` | `notification_groups` | 按 (tenant_id, related_id, message_type) 分组，每组一条 group |
| `notification_logs` | `notification_deliveries` | 每条 log → 一条 delivery（channel, status, recipient_address, error_message, retry_count, sent_at） |
| `notification_logs` | `notification_groups` | 通过 related_id + tenant_id 关联到已创建的 group |
| `message_templates` | `unified_templates` | 直接映射（code, name, message_type, title_template→text_template, content_template→text_template） |
| `email_templates` | `unified_templates` | 合并到 unified_templates（code, name, subject_template, html_template, content_template→text_template） |
| `notification_preferences` | 保留原表 | Phase 1 再迁移，当前不动 |

**迁移脚本设计：**
- 使用独立的数据迁移脚本（非 Alembic migration），因为涉及复杂的数据转换逻辑
- 脚本支持增量迁移（记录已迁移的 ID 范围，支持断点续传）
- 迁移前后统计行数对比，确保数据完整
- 迁移脚本放在 `apps/server/scripts/migrate_unified_message.py`

**新旧表 ID 关联：**
- `notification_groups` 新增 `legacy_message_id` 字段（可选），存储第一条关联的 messages.id，便于回溯
- `notification_deliveries` 新增 `legacy_log_id` 字段（可选），存储关联的 notification_logs.id

### Step 0.7: 双写策略

**阶段 1 — 数据迁移 + 新系统只读验证：**
- 运行数据迁移脚本：旧表存量数据 → 新表
- 新服务读取新表，验证数据正确性
- 旧服务继续写入旧表
- **产品级验收指标**：
  - 消息发送成功率一致（用户实际收到通知的比例）
  - 消息送达时间无退化（新服务响应时间 ≤ 旧服务）
  - 用户已读状态正确同步

**阶段 2 — 双写：**
- 旧服务写入旧表
- 新服务同时写入新表
- 定时任务对比新旧表数据一致性
- **数据一致性检查**：消息发送成功率、已读状态同步率、投递记录完整性

**阶段 3 — 切换写入：**
- 兼容层切换到新服务
- 只写新表
- 旧表停止写入

**阶段 4 — 清理：**
- 确认新系统稳定（至少运行 2 周）
- 删除旧表和旧代码

### Step 0.8: 回滚方案

1. **Feature flag 立即回滚**：通过管理后台将租户的 `beta_unified_message` 设为 False，所有请求回到旧服务（无需重启）
2. **数据库回滚**：新表独立于旧表，不影响旧系统
3. **Celery 任务回滚**：保留旧任务代码，通过配置切换
4. **前端回滚条件**：前端无需回滚的前提条件：
   - API 响应 JSON 结构 100% 不变（字段名、字段顺序、null vs 缺失、时间格式）
   - 错误码/错误消息格式不变
   - WebSocket 推送格式不变
   - admin 端 NotificationButton.tsx 的 snake_case 类型兼容（需在 Phase 1 修正为 camelCase）
   - **必须编写 API 契约测试**验证以上条件

## 关键文件清单

### 需要创建的文件
- `apps/server/app/modules/unified_message/__init__.py`
- `apps/server/app/modules/unified_message/models.py`
- `apps/server/app/modules/unified_message/schemas.py`
- `apps/server/app/modules/unified_message/service.py`
- `apps/server/app/modules/unified_message/compat.py`
- `apps/server/app/modules/unified_message/router.py`
- `apps/server/alembic/versions/XXX_create_unified_message_tables.py`

### 需要修改的文件（Phase 0 最小改动）
- `apps/server/app/models/__init__.py` — 注册新模型
- `apps/server/app/api/v1/__init__.py` — 注册新路由（Phase 2）
- `apps/server/app/modules/tenants/schemas.py` — TenantFeatures 添加 `beta_unified_message` 字段

### Phase 1 需要修改的文件（业务调用点）
- `apps/server/app/modules/appointments/service_booking.py` — 3 个调用点（:305, :516, :654）
- `apps/server/app/modules/appointments/service_flow.py` — 2 个调用点（:190, :256）
- `apps/server/app/modules/schedules/service_generation.py` — 1 个调用点（:282）
- `apps/server/app/modules/schedules/service_mutation.py` — 3 个调用点（:350 send_schedule, :384 send_stop_clinic, + 2 处间接调用 :108,:164 通过 `_send_schedule_notification_to_doctor`）
- `apps/server/app/modules/schedule_suspensions/service.py` — 1 个调用点（:232）

### Phase 1 需要修改的文件（Celery 任务）
- `apps/server/app/tasks/notification_task.py`
- `apps/server/app/tasks/notification_retry_task.py`
- `apps/server/app/tasks/email_hook_task.py`

### 前端需要修改的文件（Phase 2）
- `packages/api/src/modules/message.ts` — 类型定义和 API 封装
- `apps/admin/src/components/HeaderActions/NotificationButton.tsx`
- `apps/admin/src/pages/message/index.tsx`
- `apps/admin/src/pages/message/form.tsx`
- `apps/admin/src/pages/system/notification-logs.tsx`
- `apps/doctor/src/pages/message/index.tsx`
- `apps/patient-h5/src/pages/message/index.tsx`
- `apps/patient-h5/src/pages/profile/index.tsx`

## 可复用的现有代码

| 组件 | 文件 | 复用方式 |
|------|------|---------|
| ChannelRegistry | `infrastructure/notifications/registry.py` | 直接复用，注册到新服务 |
| BaseNotificationChannel | `infrastructure/notifications/channels/base.py` | 直接复用 |
| InAppChannel | `infrastructure/notifications/channels/in_app.py` | Phase 1 改造后复用 |
| EmailChannel | `infrastructure/notifications/channels/email.py` | Phase 1 改造后复用 |
| SmsChannel | `infrastructure/notifications/channels/sms.py` | Phase 3 复用 |
| WechatChannel | `infrastructure/notifications/channels/wechat.py` | Phase 3 复用 |
| WebSocketChannel | `infrastructure/notifications/channels/websocket.py` | Phase 3 复用 |
| SmsService | `infrastructure/sms/service.py` | 直接复用 |
| EmailService | `infrastructure/email/service.py` | 直接复用 |
| WechatService | `infrastructure/wechat/service.py` | 直接复用 |
| NotificationQuotaService | `infrastructure/notifications/quota.py` | 改造后复用 |
| ConnectionManager | `core/websocket.py` | 直接复用 |
| 去重逻辑 | `dispatcher.py:242-272` | 保留 Redis 去重作为第一层（热数据），新增数据库 dedup_key 作为第二层（持久化保障） |
| 偏好过滤 | `dispatcher.py:274-343` | 迁移到新服务 |
| 静默时段检查 | `dispatcher.py:345-370` | 迁移到新服务，增加例外规则 |
| 指数退避重试 | `notification_retry_task.py` | 迁移到新重试机制 |
| 微信 Token 管理 | `infrastructure/wechat/token_manager.py` | 直接复用 |

## 验证计划

### Phase 0 验证
1. 新表创建成功，Migration 无报错（确认 Alembic autogenerate 检测到新表）
2. 新服务单元测试通过（使用 SQLite 内存库）
3. 兼容层在 `beta_unified_message=False` 时正确转发到旧服务
4. Feature flag 通过管理后台 TenantFeatures 切换正常工作
5. UnifiedTemplate 的 (tenant_id, code) 联合唯一约束验证

### 集成测试
1. 创建测试租户，通过 TenantFeatures 启用 `beta_unified_message`
2. 发送预约通知 → 验证新表记录正确
3. 对比新旧表数据一致性
4. 回滚 feature flag → 验证回到旧服务
5. **API 契约测试**：对比新旧服务的响应格式（JSON 结构、字段名、时间格式、错误码），确保前端无感知
6. **Celery 链路测试**：预约创建 → 等待提醒 → 验证通知发送（覆盖 notification_task 完整链路）
7. **数据迁移验证**：运行迁移脚本后，统计旧表 vs 新表行数，抽样验证数据正确性

### 测试命令
```bash
cd apps/server
pytest tests/unit/ -k "unified_message" -v
pytest tests/unit/test_message_service.py -v  # 确保旧测试不受影响
```
