# 审批流引擎 P0 强化实施计划

## Context

自适应多智能体研究评审发现：现有 Phase 1 审批引擎是骨架代码，从未集成业务模块。新企业级设计规格（workflow_* 表、outbox、乐观锁等）与现有实现存在系统性差异。经 Critic 质询和 Team Lead 裁决，决定：

- **保留 `approval_*` 表命名**（避免无收益的全链路变更）
- **保留 `approval:*` 权限码**（"审批"比"工作流"更直观）
- **用 Celery 替代 outbox 模式**（复用已有基础设施）
- **用 Redis 分布式锁替代数据库乐观锁**（更简单）
- **条件路由一期仅支持 AND**（无 OR 场景需求）

本计划覆盖 5 个 P0 行动项。

---

## 1. 新增 `approval_tasks` 表 + 模型

**文件:** `apps/server/app/models/approval_flow.py`

新增 `ApprovalTask` 模型，分离"谁应该审批"（任务）和"谁审批了"（记录）两种语义：

```python
class ApprovalTask(Base):
    """审批任务表 - 每个审批节点每个审批人一条待办"""
    __tablename__ = "approval_tasks"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    store_id = Column(String(36), ForeignKey("stores.id"), nullable=True)
    instance_id = Column(String(36), ForeignKey("approval_instances.id", ondelete="CASCADE"), nullable=False, index=True)
    node_key = Column(String(100), nullable=False)
    node_name = Column(String(200))
    task_type = Column(String(30), nullable=False, default="approval", comment="approval/cc")
    status = Column(String(20), nullable=False, default="pending", comment="pending/completed/cancelled/transferred/expired")
    assignee_id = Column(String(36), nullable=False, comment="审批人 ID")
    assignee_name = Column(String(100))
    candidate_user_ids = Column(JSON, comment="候选人 ID 列表（或签/会签时）")
    assignee_snapshot = Column(JSON, comment="审批人解析快照")
    completed_at = Column(DateTime)
    completed_by = Column(String(36))
    timeout_at = Column(DateTime, comment="超时时间")
    created_at = Column(DateTime, default=lambda: __import__('datetime').datetime.utcnow)

    instance = relationship("ApprovalInstance", back_populates="tasks")
```

在 `ApprovalInstance` 上增加 `tasks` relationship：
```python
tasks = relationship("ApprovalTask", back_populates="instance", cascade="all, delete-orphan",
                     order_by="ApprovalTask.created_at", lazy="selectin")
```

**索引:**
- `(tenant_id, status)` — 待办查询
- `(assignee_id, status)` — 我的待办
- `(instance_id, node_key)` — 实例节点任务

**在 `__init__.py` 中导出:** `apps/server/app/models/__init__.py` 已导入 approval_flow 模块，自动覆盖。

**Alembic 迁移:** 生成 `109_add_approval_tasks.py`（需数据库可用时执行）。

---

## 2. 增加 `snapshot_json` 到流程定义表

**文件:** `apps/server/app/models/approval_flow.py`

在 `ApprovalFlowDefinition` 增加字段：
```python
snapshot_json = Column(JSON, comment="发布时的流程快照（节点+条件的完整 JSON）")
```

**文件:** `apps/server/app/modules/approval_flows/service_definitions.py`

在 `activate()` 方法中，生成快照：
```python
# 生成流程快照
snapshot = {
    "nodes": [
        {
            "node_key": n.node_key, "node_name": n.node_name, "node_type": n.node_type,
            "approval_mode": n.approval_mode, "assignee_type": n.assignee_type,
            "assignee_config": n.assignee_config, "timeout_hours": n.timeout_hours,
            "timeout_action": n.timeout_action, "sort_order": n.sort_order,
            "conditions": [
                {"target_node_key": c.target_node_key, "field_name": c.field_name,
                 "operator": c.operator, "value": c.value, "priority": c.priority}
                for c in n.conditions
            ]
        }
        for n in nodes
    ]
}
flow_def.snapshot_json = snapshot
```

**文件:** `apps/server/app/modules/approval_flows/schemas.py`

在 `FlowDefinitionResponse` 增加 `snapshot_json` 字段。

---

## 3. 增加 `not_in` / `exists` 运算符

**文件:** `apps/server/app/modules/approval_flows/condition_evaluator.py`

在 `OPERATORS` 字典增加：
```python
"not_in": lambda a, b: a not in (b if isinstance(b, list) else json.loads(b)),
"exists": lambda a, b: (a is not None) == bool(b),
```

**文件:** `apps/server/app/modules/approval_flows/schemas.py`

更新 `FlowConditionCreate.operator` 的正则：
```python
operator: str = Field(pattern="^(eq|neq|gt|gte|lt|lte|in|not_in|contains|exists)$")
```

---

## 4. 重写 engine.py（核心变更）

**文件:** `apps/server/app/modules/approval_flows/engine.py`

### 4.1 新增导入

```python
from app.core.redis import RedisCache
from app.models.approval_flow import ApprovalTask  # 新增
import structlog
logger = structlog.get_logger(__name__)
```

### 4.2 Redis 锁保护审批操作

在 `approve()` 和 `reject()` 方法开头加锁：
```python
async def approve(self, instance_id, approver_id, approver_name, comment=None):
    lock_name = f"approval:instance:{instance_id}"
    async with RedisCache.distributed_lock(lock_name, timeout=10, retry_times=3):
        return await self._do_approve(instance_id, approver_id, approver_name, comment)
```

原有 `approve` 逻辑移到 `_do_approve`。

### 4.3 任务管理

**start_instance 改造:**
- 解析审批人后，为每个审批人创建 `ApprovalTask` 记录
- `assignee_snapshot` 存储：`{"id": ..., "name": ..., "resolved_by": node.assignee_type, "config": node.assignee_config}`
- 计算 `timeout_at`（如果节点配置了 timeout_hours）

**approve 改造:**
- 查找并更新 `ApprovalTask`（assignee_id=approver_id, status=pending -> completed）
- `_check_approval_complete` 改为基于 `ApprovalTask` 查询（而非 ApprovalRecord）
- 推进到下一节点时，取消当前节点所有 pending 任务（status=cancelled）

**reject 改造:**
- 取消当前节点所有 pending 任务

**delegate 改造:**
- 原任务 status=transferred
- 创建新任务（assignee_id=target_user_id）

**withdraw 改造:**
- 取消所有 pending 任务

### 4.4 Celery 通知替代 WebSocket 直调

将 `_notify_approver` / `_notify_applicant` / `_notify_cc` 改为触发 Celery 任务：

```python
async def _notify_approver(self, approver_id, instance, node_name):
    from app.tasks.approval_task import send_approval_notification
    send_approval_notification.delay(
        user_id=approver_id,
        message_type="approval_pending",
        data={"instance_id": instance.id, "title": instance.title, "node_name": node_name}
    )
```

### 4.5 structlog 日志

在关键节点替换 `logging.getLogger` 为 `structlog.get_logger`，增加结构化字段：
```python
logger.info("approval_started", business_type=business_type, business_id=business_id, flow_def_id=flow_def.id)
logger.info("approval_completed", instance_id=instance.id, status="approved")
logger.info("approval_rejected", instance_id=instance.id, approver_id=approver_id)
```

### 4.6 _check_approval_complete 改造

改为基于 `ApprovalTask` 查询：
```python
async def _check_approval_complete(self, node, instance_id, node_key):
    mode = node.approval_mode or "or"
    # 查询已完成的任务
    stmt = select(func.count(ApprovalTask.id)).where(
        and_(ApprovalTask.instance_id == instance_id,
             ApprovalTask.node_key == node_key,
             ApprovalTask.status == "completed")
    )
    completed_count = (await self.db.execute(stmt)).scalar() or 0

    if mode == "or":
        return completed_count > 0
    elif mode == "and":
        # 查询总任务数
        total_stmt = select(func.count(ApprovalTask.id)).where(
            and_(ApprovalTask.instance_id == instance_id,
                 ApprovalTask.node_key == node_key,
                 ApprovalTask.task_type == "approval")
        )
        total_count = (await self.db.execute(total_stmt)).scalar() or 0
        return completed_count >= total_count
    elif mode == "sequential":
        return completed_count > 0
    return False
```

---

## 5. 创建 Celery 审批任务

**新建文件:** `apps/server/app/tasks/approval_task.py`

```python
"""审批流 Celery 任务"""
from app.celery_app import celery_app
from app.db.session import get_sync_db
from app.middleware.tenant_context import set_tenant_context, clear_tenant_context


@celery_app.task(
    name="app.tasks.approval_task.send_approval_notification",
    queue="notification",
    autoretry_for=(Exception,),
    max_retries=3,
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    time_limit=30,
    soft_time_limit=25,
)
def send_approval_notification(user_id: str, message_type: str, data: dict):
    """发送审批通知（WebSocket + 可扩展站内信）"""
    import asyncio
    from app.core.websocket import notify_doctor, WSMessageType

    ws_type = {
        "approval_pending": WSMessageType.APPROVAL_PENDING,
        "approval_approved": WSMessageType.APPROVAL_APPROVED,
        "approval_rejected": WSMessageType.APPROVAL_REJECTED,
        "approval_delegated": WSMessageType.APPROVAL_DELEGATED,
        "approval_withdrawn": WSMessageType.APPROVAL_WITHDRAWN,
    }.get(message_type)

    if ws_type:
        asyncio.get_event_loop().run_until_complete(
            notify_doctor(user_id, ws_type, data=data)
        )


@celery_app.task(
    name="app.tasks.approval_task.check_approval_timeouts",
    queue="scheduled",
    autoretry_for=(Exception,),
    max_retries=2,
    time_limit=120,
    soft_time_limit=100,
)
def check_approval_timeouts():
    """检查审批超时任务（定时执行）"""
    from sqlalchemy import select, and_
    from datetime import datetime
    from app.models.approval_flow import ApprovalTask, ApprovalInstance

    with get_sync_db() as db:
        # 查找超时的 pending 任务
        stmt = select(ApprovalTask).join(ApprovalInstance).where(
            and_(
                ApprovalTask.status == "pending",
                ApprovalTask.timeout_at.isnot(None),
                ApprovalTask.timeout_at < datetime.utcnow(),
                ApprovalInstance.status == "pending",
            )
        )
        tasks = db.execute(stmt).scalars().all()

        for task in tasks:
            instance = db.get(ApprovalInstance, task.instance_id)
            if not instance or instance.status != "pending":
                continue

            # 获取节点的超时动作
            from app.models.approval_flow import ApprovalFlowNode
            node_stmt = select(ApprovalFlowNode).where(
                and_(
                    ApprovalFlowNode.flow_def_id == instance.flow_def_id,
                    ApprovalFlowNode.node_key == task.node_key,
                )
            )
            node = db.execute(node_stmt).scalar_one_or_none()
            if not node:
                continue

            if node.timeout_action == "remind":
                # 发送提醒通知
                send_approval_notification.delay(
                    user_id=task.assignee_id,
                    message_type="approval_pending",
                    data={"instance_id": instance.id, "title": instance.title, "is_remind": True}
                )
            elif node.timeout_action == "auto_approve":
                # 自动通过（标记任务完成，引擎推进）
                task.status = "completed"
                task.completed_at = datetime.utcnow()
                task.completed_by = "system"
                # 注意：引擎推进需要异步，这里仅标记任务
                # 实际推进由另一个异步任务或 API 触发

        db.commit()
```

**注册到 celery_app.py:**
- `task_routes` 增加: `"app.tasks.approval_task.*": {"queue": "notification"}`
- `beat_schedule` 增加: `"approval-timeout-check": {"task": "app.tasks.approval_task.check_approval_timeouts", "schedule": crontab(minute="*/10"), "options": {"queue": "scheduled"}}`
- `autodiscover_tasks` 增加: `"app.tasks.approval_task"`

---

## 6. service_instances.py 待办查询改造

**文件:** `apps/server/app/modules/approval_flows/service_instances.py`

`get_list` 中的"我的待办"查询改为基于 `ApprovalTask`：

```python
elif user_id:
    # 我待办的: ApprovalTask 中 assignee_id = user_id 且 status = pending
    stmt = stmt.where(
        ApprovalInstance.status == "pending",
        ApprovalInstance.id.in_(
            select(ApprovalTask.instance_id).where(
                and_(
                    ApprovalTask.assignee_id == user_id,
                    ApprovalTask.status == "pending",
                )
            )
        ),
    )
```

`get_pending_count` 同理改造。

---

## 7. 文件变更清单

| 文件 | 操作 | 变更内容 |
|------|------|---------|
| `models/approval_flow.py` | 修改 | 新增 ApprovalTask 模型 + snapshot_json 字段 + tasks relationship |
| `models/__init__.py` | 无需改 | 已导入 approval_flow 模块 |
| `modules/approval_flows/engine.py` | 重写 | Redis 锁 + 任务管理 + Celery 通知 + structlog |
| `modules/approval_flows/condition_evaluator.py` | 修改 | 增加 not_in/exists 运算符 |
| `modules/approval_flows/schemas.py` | 修改 | 增加 not_in/exists 到 operator regex + snapshot_json 响应字段 |
| `modules/approval_flows/service_instances.py` | 修改 | 待办查询改为基于 ApprovalTask |
| `modules/approval_flows/service_definitions.py` | 修改 | activate() 增加快照生成 |
| `tasks/approval_task.py` | 新建 | Celery 通知任务 + 超时检查任务 |
| `celery_app.py` | 修改 | 注册 approval_task 路由和定时任务 |
| `migrations/env.py` | 无需改 | 已导入 approval_flow 模块 |

---

## 8. 验证方式

1. **Python 导入检查:** `python -c "from app.models.approval_flow import ApprovalTask; print('OK')"`
2. **Celery 任务注册检查:** `celery -A app.celery_app inspect registered | grep approval`
3. **Alembic 迁移生成:** `alembic revision --autogenerate -m "add_approval_tasks"`（需数据库）
4. **单元测试:** 后续补充（Critic 质询 7 指出测试覆盖为零）
