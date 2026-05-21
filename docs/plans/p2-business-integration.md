# P2 业务接入实施计划：leave_request + extra_quota 对接审批引擎

## 1. 背景

审批引擎（Phase 1 + P0/P1）已完成核心基础设施：

- `approval_flow_definitions` / `approval_flow_nodes` / `approval_flow_conditions` — 流程定义
- `approval_instances` / `approval_tasks` / `approval_records` — 运行时
- `engine.py` — 流程引擎（启动、审批、拒绝、转交、撤回、条件路由、自动审批）
- `condition_evaluator.py` — 结构化条件求值（eq/neq/gt/gte/lt/lte/in/not_in/contains/exists）
- Celery 通知任务 + 超时检查
- 管理端审批中心页面（待办、已办、我发起的、流程定义管理）

当前 `leave_request` 和 `extra_quota` 两个业务模块仍使用硬编码审批逻辑，需要通过适配器模式接入统一审批引擎。

## 2. 现有审批逻辑分析

### 2.1 leave_request（停诊/调班申请）

**文件:** `apps/server/app/modules/leave_requests/service.py`

**当前流程:**
1. `create_stop_clinic()` / `create_schedule_change()` — 创建申请，状态直接为 `pending`
2. `review()` — 审核人直接调用，硬编码单级审批
   - 设置 `request.status = APPROVED / REJECTED`
   - 通过时调用 `_handle_approved_request()` 执行业务副作用
3. `cancel()` — 申请人取消

**通过后的业务副作用:**
- **停诊** (`_handle_stop_clinic`):
  - 更新排班状态 `schedule.status = 0`
  - 取消该医生该日期时段的所有待确认/已确认预约 (`apt.status = 6`)
- **调班** (`_handle_schedule_change`):
  - 交换原时段和目标时段的排班日期/时段/时间

**关键字段:**
- `LeaveRequest.tenant_id`, `doctor_id`, `request_type` (stop_clinic/schedule_change)
- `schedule_id`, `stop_date`, `stop_period`
- `original_date`, `original_period`, `target_date`, `target_period`
- `affected_appointments` — 受影响预约数

### 2.2 extra_quota（加号申请）

**文件:** `apps/server/app/modules/schedules/service_extra_quota.py`

**当前流程:**
1. `create_request()` — 创建申请
   - `quantity <= 5` 时自动批准，直接更新号源
   - `quantity > 5` 时状态为 `pending`，等待人工审批
2. `approve()` — 审批通过，使用 Redis 分布式锁保护号源更新
3. `reject()` — 拒绝

**通过后的业务副作用:**
- 更新 `schedule.extra_quota += quantity`
- 调用 `schedule.sync_total_slots()` 同步总号源

**自动审批规则:**
- `AUTO_APPROVE_THRESHOLD = 5`，`quantity <= 5` 自动通过
- 使用 Redis 分布式锁 `extra_quota:approve:{schedule_id}` 防并发

**关键字段:**
- `ExtraQuotaRequest.tenant_id`, `store_id`, `schedule_id`, `doctor_id`
- `quantity`, `quota_type`, `open_to_public`, `patient_id`
- `schedule_date`, `time_slot`

## 3. 适配器协议设计

### 3.1 协议定义

```python
# apps/server/app/modules/approval_flows/adapters.py

from typing import Protocol, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession


class ApprovalCallbackContext:
    """审批回调上下文"""
    def __init__(
        self,
        db: AsyncSession,
        instance: "ApprovalInstance",
        business_id: str,
        business_type: str,
        tenant_id: str,
        store_id: Optional[str],
        approver_id: str,
        comment: Optional[str] = None,
    ):
        self.db = db
        self.instance = instance
        self.business_id = business_id
        self.business_type = business_type
        self.tenant_id = tenant_id
        self.store_id = store_id
        self.approver_id = approver_id
        self.comment = comment


class BusinessAdapter(Protocol):
    """业务适配器协议"""

    business_type: str

    async def get_payload(self, business_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取业务数据 payload（用于条件路由求值）"""
        ...

    async def on_approved(self, context: ApprovalCallbackContext) -> None:
        """审批通过回调"""
        ...

    async def on_rejected(self, context: ApprovalCallbackContext) -> None:
        """审批拒绝回调"""
        ...

    async def on_cancelled(self, context: ApprovalCallbackContext) -> None:
        """撤回回调"""
        ...
```

### 3.2 适配器注册

```python
# apps/server/app/modules/approval_flows/adapters.py (续)

_ADAPTERS: Dict[str, BusinessAdapter] = {}

def register_adapter(adapter: BusinessAdapter):
    _ADAPTERS[adapter.business_type] = adapter

def get_adapter(business_type: str) -> Optional[BusinessAdapter]:
    return _ADAPTERS.get(business_type)
```

## 4. leave_request 适配器实现

### 4.1 适配器代码

```python
# apps/server/app/modules/approval_flows/adapters_leave_request.py

from typing import Dict, Any
from sqlalchemy import select, and_
from app.models.leave_request import LeaveRequest, RequestType
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.modules.approval_flows.adapters import (
    BusinessAdapter, ApprovalCallbackContext, register_adapter
)


class LeaveRequestAdapter:
    """停诊/调班申请审批适配器"""

    business_type = "leave_request"

    async def get_payload(self, business_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取停诊/调班申请数据，供条件路由使用"""
        result = await self.db.execute(
            select(LeaveRequest).where(
                and_(LeaveRequest.id == business_id, LeaveRequest.tenant_id == tenant_id)
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            return {}

        # 获取医生信息
        doctor = (await self.db.execute(
            select(Doctor).where(Doctor.id == request.doctor_id)
        )).scalar_one_or_none()

        return {
            "request_type": request.request_type,
            "doctor_id": request.doctor_id,
            "store_id": doctor.store_id if doctor else None,
            "affected_appointments": request.affected_appointments or 0,
            "stop_period": request.stop_period,
            "original_period": request.original_period,
            "target_period": request.target_period,
        }

    async def on_approved(self, context: ApprovalCallbackContext) -> None:
        """审批通过：执行停诊/调班业务逻辑"""
        request = (await context.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == context.business_id)
        )).scalar_one_or_none()

        if not request:
            return

        # 更新申请状态
        request.status = "approved"
        request.reviewer_id = context.approver_id
        request.review_comment = context.comment
        from datetime import datetime
        request.reviewed_at = datetime.utcnow()

        # 复用现有业务逻辑
        if request.request_type == RequestType.STOP_CLINIC.value:
            await self._handle_stop_clinic(context.db, request)
        elif request.request_type == RequestType.SCHEDULE_CHANGE.value:
            await self._handle_schedule_change(context.db, request)

    async def on_rejected(self, context: ApprovalCallbackContext) -> None:
        """审批拒绝"""
        request = (await context.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == context.business_id)
        )).scalar_one_or_none()

        if request:
            request.status = "rejected"
            request.reviewer_id = context.approver_id
            request.review_comment = context.comment
            from datetime import datetime
            request.reviewed_at = datetime.utcnow()

    async def on_cancelled(self, context: ApprovalCallbackContext) -> None:
        """撤回"""
        request = (await context.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == context.business_id)
        )).scalar_one_or_none()

        if request:
            request.status = "cancelled"

    # --- 以下复用 service.py 中的业务逻辑 ---

    async def _handle_stop_clinic(self, db, request):
        """处理停诊（与 LeaveRequestService._handle_stop_clinic 相同逻辑）"""
        if request.schedule_id:
            schedule = (await db.execute(
                select(Schedule).where(Schedule.id == request.schedule_id)
            )).scalar_one_or_none()
            if schedule:
                schedule.status = 0

        if request.stop_date:
            appointments = (await db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == request.doctor_id,
                        Appointment.schedule_id.isnot(None),
                        Appointment.status.in_([0, 1]),
                    )
                )
            )).scalars().all()
            for apt in appointments:
                if apt.schedule_id:
                    sched = (await db.execute(
                        select(Schedule).where(Schedule.id == apt.schedule_id)
                    )).scalar_one_or_none()
                    if sched and sched.schedule_date == request.stop_date:
                        if request.stop_period == 'all' or sched.time_slot == request.stop_period:
                            apt.status = 6
                            apt.cancel_reason = f"医生停诊（审批单 {request.id}）"

    async def _handle_schedule_change(self, db, request):
        """处理调班（与 LeaveRequestService._handle_schedule_change 相同逻辑）"""
        if not request.original_date or not request.target_date:
            return

        orig_schedules = (await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.doctor_id == request.doctor_id,
                    Schedule.schedule_date == request.original_date,
                    Schedule.time_slot == request.original_period,
                    Schedule.status == 1,
                )
            )
        )).scalars().all()

        target_schedules = (await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.doctor_id == request.doctor_id,
                    Schedule.schedule_date == request.target_date,
                    Schedule.time_slot == request.target_period,
                    Schedule.status == 1,
                )
            )
        )).scalars().all()

        if orig_schedules and target_schedules:
            orig = orig_schedules[0]
            target = target_schedules[0]
            orig.schedule_date, target.schedule_date = target.schedule_date, orig.schedule_date
            orig.time_slot, target.time_slot = target.time_slot, orig.time_slot
            orig.start_time, target.start_time = target.start_time, orig.start_time
            orig.end_time, target.end_time = target.end_time, orig.end_time
        elif orig_schedules:
            orig = orig_schedules[0]
            orig.schedule_date = request.target_date
            orig.time_slot = request.target_period
        elif target_schedules:
            target = target_schedules[0]
            target.schedule_date = request.original_date
            target.time_slot = request.original_period
```

### 4.2 流程定义配置

```json
{
  "name": "停诊/调班审批",
  "business_type": "leave_request",
  "nodes": [
    { "node_key": "start", "node_name": "开始", "node_type": "start" },
    {
      "node_key": "store_admin_approve",
      "node_name": "门店管理员审批",
      "node_type": "approval",
      "approval_mode": "or",
      "assignee_type": "role",
      "assignee_config": {
        "role_codes": ["STORE_ADMIN"]
      },
      "timeout_hours": 48,
      "timeout_action": "remind"
    },
    { "node_key": "end", "node_name": "结束", "node_type": "end" }
  ],
  "conditions": []
}
```

### 4.3 条件路由示例（可选扩展）

如果需要按受影响预约数分流：

```json
{
  "conditions": [
    {
      "source_node_key": "start",
      "target_node_key": "store_admin_approve",
      "field_name": "affected_appointments",
      "operator": "lte",
      "value": "10",
      "priority": 0
    },
    {
      "source_node_key": "start",
      "target_node_key": "dept_admin_approve",
      "field_name": "affected_appointments",
      "operator": "gt",
      "value": "10",
      "priority": 1
    }
  ]
}
```

## 5. extra_quota 适配器实现

### 5.1 适配器代码

```python
# apps/server/app/modules/approval_flows/adapters_extra_quota.py

from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy import select, and_

from app.core.redis import RedisCache
from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.schedule import Schedule
from app.modules.approval_flows.adapters import (
    BusinessAdapter, ApprovalCallbackContext, register_adapter
)


class ExtraQuotaAdapter:
    """加号申请审批适配器"""

    business_type = "extra_quota"

    async def get_payload(self, business_id: str, tenant_id: str) -> Dict[str, Any]:
        """获取加号申请数据，供条件路由使用"""
        result = await self.db.execute(
            select(ExtraQuotaRequest).where(
                and_(
                    ExtraQuotaRequest.id == business_id,
                    ExtraQuotaRequest.tenant_id == tenant_id,
                )
            )
        )
        request = result.scalar_one_or_none()
        if not request:
            return {}

        return {
            "quantity": request.quantity,
            "quota_type": request.quota_type,
            "store_id": request.store_id,
            "doctor_id": request.doctor_id,
            "schedule_id": request.schedule_id,
            "open_to_public": request.open_to_public,
        }

    async def on_approved(self, context: ApprovalCallbackContext) -> None:
        """审批通过：更新排班号源"""
        request = (await context.db.execute(
            select(ExtraQuotaRequest).where(
                ExtraQuotaRequest.id == context.business_id
            )
        )).scalar_one_or_none()

        if not request:
            return

        # 更新申请状态
        request.approval_status = "approved"
        request.approver_id = context.approver_id
        request.approval_remark = context.comment
        request.approved_at = datetime.utcnow()

        # 使用分布式锁保护号源更新（复用现有锁逻辑）
        lock_name = f"extra_quota:approve:{request.schedule_id}"
        async with RedisCache.tenant_distributed_lock(
            lock_name, tenant_id=context.tenant_id, timeout=10, retry_times=5
        ):
            schedule = (await context.db.execute(
                select(Schedule).where(
                    and_(
                        Schedule.id == request.schedule_id,
                        Schedule.tenant_id == context.tenant_id,
                    )
                )
            )).scalar_one_or_none()

            if schedule:
                schedule.extra_quota = (schedule.extra_quota or 0) + request.quantity
                schedule.sync_total_slots()

    async def on_rejected(self, context: ApprovalCallbackContext) -> None:
        """审批拒绝"""
        request = (await context.db.execute(
            select(ExtraQuotaRequest).where(
                ExtraQuotaRequest.id == context.business_id
            )
        )).scalar_one_or_none()

        if request:
            request.approval_status = "rejected"
            request.approver_id = context.approver_id
            request.approval_remark = context.comment
            request.approved_at = datetime.utcnow()

    async def on_cancelled(self, context: ApprovalCallbackContext) -> None:
        """撤回"""
        request = (await context.db.execute(
            select(ExtraQuotaRequest).where(
                ExtraQuotaRequest.id == context.business_id
            )
        )).scalar_one_or_none()

        if request:
            request.approval_status = "cancelled"
```

### 5.2 流程定义配置

```json
{
  "name": "加号审批",
  "business_type": "extra_quota",
  "nodes": [
    { "node_key": "start", "node_name": "开始", "node_type": "start" },
    {
      "node_key": "auto_approve_check",
      "node_name": "自动审批检查",
      "node_type": "approval",
      "approval_mode": "or",
      "assignee_type": "role",
      "assignee_config": {
        "role_codes": ["STORE_ADMIN"],
        "auto_approve_rules": {
          "all": [
            { "field": "quantity", "operator": "lte", "value": "5" }
          ]
        }
      },
      "timeout_hours": 24,
      "timeout_action": "remind"
    },
    { "node_key": "end", "node_name": "结束", "node_type": "end" }
  ],
  "conditions": []
}
```

### 5.3 自动审批说明

`auto_approve_rules` 复用 `condition_evaluator.OPERATORS`，支持：
- `quantity lte 5` — 小额加号自动通过
- `quantity gt 5` 且 `store_id in [...]` — 特定门店小额自动通过

引擎在 `start_instance` 和 `_advance` 时自动检查规则，命中则标记任务完成、写入 `ApprovalRecord(approver_id="system")` 并推进流程。

## 6. 业务模块改造

### 6.1 leave_request 改造

**文件:** `apps/server/app/modules/leave_requests/service.py`

改造 `create_stop_clinic` 和 `create_schedule_change`：

```python
async def create_stop_clinic(self, data: StopClinicCreate) -> LeaveRequest:
    """创建停诊申请"""
    tenant_id = get_current_tenant_id()

    affected = await self._count_affected_appointments(
        data.doctor_id, data.stop_date, data.stop_period
    )

    request = LeaveRequest(
        id=str(uuid.uuid4()),
        tenant_id=tenant_id,
        doctor_id=data.doctor_id,
        request_type=RequestType.STOP_CLINIC.value,
        schedule_id=data.schedule_id,
        stop_date=data.stop_date,
        stop_period=data.stop_period,
        reason=data.reason,
        affected_appointments=affected,
        status="pending",  # 保持 pending，等审批引擎推进
    )
    set_create_audit(request, data.doctor_id)
    self.db.add(request)
    await self.db.flush()  # flush 而非 commit，让审批引擎在同一事务中

    # 尝试启动审批流程
    from app.modules.approval_flows.engine import ApprovalEngine
    from app.modules.approval_flows.adapters import get_adapter

    engine = ApprovalEngine(self.db)
    try:
        await engine.start_instance(
            business_type="leave_request",
            business_id=request.id,
            tenant_id=tenant_id,
            store_id=None,  # leave_request 通过 doctor 关联门店
            applicant_id=data.doctor_id,
            title=f"停诊申请 - {data.stop_date} {data.stop_period}",
            form_data={
                "doctor_id": data.doctor_id,
                "schedule_id": data.schedule_id,
                "stop_date": str(data.stop_date),
                "stop_period": data.stop_period,
                "reason": data.reason,
                "affected_appointments": affected,
            },
        )
    except ValueError as e:
        # 未配置流程定义时，走旧逻辑（渐进式迁移）
        if "未找到已发布" in str(e):
            await self.db.commit()
            await self.db.refresh(request)
            return request
        raise

    await self.db.commit()
    await self.db.refresh(request)
    return request
```

**`review()` 方法改造：**

渐进迁移期间保留 `review()` 作为兼容接口，但标记为 deprecated。当审批引擎接管后，`review()` 仅用于历史数据的直接审核。

### 6.2 extra_quota 改造

**文件:** `apps/server/app/modules/schedules/service_extra_quota.py`

改造 `create_request`：

```python
async def create_request(self, tenant_id, store_id, applicant_id, schedule_id,
                         quantity, quota_type="normal", open_to_public=True,
                         patient_id=None, reason=None) -> ExtraQuotaRequest:
    """创建加号申请。通过审批引擎处理审批流程。"""
    schedule = await self._get_schedule(schedule_id, tenant_id)
    if not schedule:
        raise ValueError("排班不存在或不属于当前租户")
    if schedule.store_id != store_id:
        raise ValueError("排班不属于指定门店")

    lock_name = f"extra_quota:create:{schedule_id}"
    async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=10, retry_times=5):
        request = ExtraQuotaRequest(
            id=str(uuid4()),
            tenant_id=tenant_id,
            store_id=store_id,
            schedule_id=schedule_id,
            doctor_id=schedule.doctor_id,
            schedule_date=str(schedule.schedule_date),
            time_slot=schedule.time_slot or "",
            quantity=quantity,
            quota_type=quota_type,
            open_to_public=1 if open_to_public else 0,
            patient_id=patient_id,
            reason=reason,
            approval_status="pending",
            applicant_id=applicant_id,
        )
        set_create_audit(request, applicant_id)
        self.db.add(request)
        await self.db.flush()

        # 尝试启动审批流程
        from app.modules.approval_flows.engine import ApprovalEngine

        engine = ApprovalEngine(self.db)
        try:
            await engine.start_instance(
                business_type="extra_quota",
                business_id=request.id,
                tenant_id=tenant_id,
                store_id=store_id,
                applicant_id=applicant_id,
                title=f"加号申请 - {schedule.schedule_date} {quantity}个",
                form_data={
                    "schedule_id": schedule_id,
                    "doctor_id": schedule.doctor_id,
                    "quantity": quantity,
                    "quota_type": quota_type,
                    "open_to_public": open_to_public,
                    "patient_id": patient_id,
                    "reason": reason,
                },
            )
        except ValueError as e:
            # 未配置流程定义时，走旧逻辑（渐进式迁移）
            if "未找到已发布" in str(e):
                # 旧逻辑：自动审批
                if quantity <= AUTO_APPROVE_THRESHOLD:
                    request.approval_status = "approved"
                    request.approver_id = applicant_id
                    request.approval_remark = "自动批准（数量未超过阈值）"
                    request.approved_at = datetime.utcnow()
                    schedule.extra_quota = (schedule.extra_quota or 0) + quantity
                    schedule.sync_total_slots()
                await self.db.commit()
                await self.db.refresh(request)
                return request
            raise

        await self.db.commit()
        await self.db.refresh(request)
        return request
```

## 7. 渐进式迁移策略

### 7.1 三阶段迁移

| 阶段 | 描述 | 行为 |
|------|------|------|
| 阶段 1 | 适配器就绪，未配置流程定义 | `engine.start_instance()` 抛出 `ValueError("未找到已发布流程定义")`，catch 后走旧逻辑 |
| 阶段 2 | 创建并发布流程定义 | 审批引擎接管，`review()` / `approve()` / `reject()` 由引擎驱动 |
| 阶段 3 | 旧接口废弃 | 移除 `LeaveRequestService.review()` 中的直接审批逻辑，移除 `ExtraQuotaService.approve()` / `reject()` |

### 7.2 兼容性保证

- `leave_request.status` 字段仍由适配器的 `on_approved` / `on_rejected` 回调更新，保持与旧逻辑一致
- `extra_quota.approval_status` 同理
- 列表查询接口不变，前端无需改造
- 审批操作统一走审批中心页面（新增），旧页面的审核按钮渐进隐藏

### 7.3 回滚方案

如果审批引擎出现问题：
1. 删除对应的流程定义（或设为 draft 状态）
2. 业务自动回退到旧逻辑（catch ValueError 分支）
3. 已在引擎中的实例不受影响，继续走引擎流程

## 8. 文件变更清单

| 文件 | 操作 | 变更内容 |
|------|------|---------|
| `modules/approval_flows/adapters.py` | 新建 | 适配器协议 + 注册机制 |
| `modules/approval_flows/adapters_leave_request.py` | 新建 | 停诊/调班适配器 |
| `modules/approval_flows/adapters_extra_quota.py` | 新建 | 加号适配器 |
| `modules/leave_requests/service.py` | 修改 | create_* 方法接入引擎，保留旧逻辑 fallback |
| `modules/schedules/service_extra_quota.py` | 修改 | create_request 接入引擎，保留旧逻辑 fallback |
| `modules/approval_flows/engine.py` | 修改 | 回调时调用适配器（on_approved/on_rejected/on_cancelled） |
| `models/leave_request.py` | 可能修改 | 确保 status 枚举兼容审批引擎状态 |
| `models/extra_quota_request.py` | 可能修改 | 同上 |

## 9. 引擎回调集成

`engine.py` 中 `_on_approved` / `_on_rejected` / `_on_cancelled` 需要调用适配器：

```python
async def _on_approved(self, instance):
    """审批通过回调"""
    from app.modules.approval_flows.adapters import get_adapter
    adapter = get_adapter(instance.business_type)
    if adapter:
        context = ApprovalCallbackContext(
            db=self.db,
            instance=instance,
            business_id=instance.business_id,
            business_type=instance.business_type,
            tenant_id=instance.tenant_id,
            store_id=instance.store_id,
            approver_id=...,  # 从最后一个审批记录获取
        )
        await adapter.on_approved(context)
```

## 10. 预估工作量

| 任务 | 预估 | 负责 |
|------|------|------|
| 适配器协议 + 注册机制 | 2h | Engineer |
| leave_request 适配器实现 | 4h | Engineer |
| extra_quota 适配器实现 | 4h | Engineer |
| engine.py 回调集成 | 2h | Engineer |
| service.py 改造（两个模块） | 4h | Engineer |
| 流程定义配置 + 种子数据 | 2h | Engineer |
| 集成测试 | 4h | Engineer |
| **合计** | **22h** | |

## 11. 测试要点

1. **leave_request 停诊审批通过** → 排班状态变更 + 预约取消
2. **leave_request 调班审批通过** → 排班日期交换
3. **extra_quota 小额自动审批** → 号源自动更新（auto_approve_rules 命中）
4. **extra_quota 大额人工审批** → 号源在通过后更新
5. **未配置流程定义** → fallback 到旧逻辑，行为不变
6. **撤回** → leave_request 状态变 cancelled，extra_quota 状态变 cancelled
7. **拒绝** → 业务状态正确更新，无副作用
8. **并发审批** → Redis 锁保护，号源不重复更新
