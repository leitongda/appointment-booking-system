"""加号申请/审批服务。"""
import logging
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import RedisCache
from app.models.extra_quota_request import ExtraQuotaRequest
from app.models.schedule import Schedule
from app.utils.audit import set_create_audit, set_update_audit
from app.utils.datetime import utc_now

logger = logging.getLogger(__name__)

# 自动批准阈值：数量 <= 此值时自动批准，否则需要人工审批
AUTO_APPROVE_THRESHOLD = 5


class ExtraQuotaService:
    """加号申请/审批服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 创建申请 ====================

    async def create_request(
        self,
        tenant_id: str,
        store_id: str,
        applicant_id: str,
        schedule_id: str,
        quantity: int,
        quota_type: str = "normal",
        open_to_public: bool = True,
        patient_id: str | None = None,
        reason: str | None = None,
    ) -> ExtraQuotaRequest:
        """创建加号申请。

        当 quantity <= AUTO_APPROVE_THRESHOLD 时自动批准并更新排班号源。
        超过阈值则创建待审批记录，等待人工审批。
        """
        # 1. 验证排班存在且属于该租户
        schedule = await self._get_schedule(schedule_id, tenant_id)
        if not schedule:
            raise ValueError("排班不存在或不属于当前租户")

        # 2. 验证门店一致性
        if schedule.store_id != store_id:
            raise ValueError("排班不属于指定门店")

        # 3. 使用分布式锁防止并发操作同一排班
        lock_name = f"extra_quota:create:{schedule_id}"

        async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=10, retry_times=5):
            # 4. 判断是否自动批准
            auto_approved = quantity <= AUTO_APPROVE_THRESHOLD
            approval_status = "approved" if auto_approved else "pending"

            # 5. 创建申请记录
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
                approval_status=approval_status,
                applicant_id=applicant_id,
                approver_id=applicant_id if auto_approved else None,
                approval_remark="自动批准（数量未超过阈值）" if auto_approved else None,
                approved_at=utc_now() if auto_approved else None,
            )
            set_create_audit(request, applicant_id)
            self.db.add(request)

            # 6. 自动批准时更新排班号源
            if auto_approved:
                schedule.extra_quota = (schedule.extra_quota or 0) + quantity
                schedule.sync_total_slots()
                set_update_audit(schedule, applicant_id)
            else:
                await self.db.flush()
                await self._start_approval_if_configured(request)

            await self.db.commit()
            await self.db.refresh(request)

        logger.info(
            "加号申请创建: request_id=%s, schedule_id=%s, quantity=%d, auto_approved=%s",
            request.id, schedule_id, quantity, auto_approved,
        )
        return request

    async def _start_approval_if_configured(self, request: ExtraQuotaRequest):
        """有激活通用审批流程时创建审批实例；未配置时保留旧审核入口。"""
        from app.modules.approval_flows.engine import ApprovalEngine, FlowNotFoundError

        form_data = {
            "schedule_id": request.schedule_id,
            "doctor_id": request.doctor_id,
            "schedule_date": request.schedule_date,
            "time_slot": request.time_slot,
            "quantity": request.quantity,
            "quota_type": request.quota_type,
            "open_to_public": bool(request.open_to_public),
            "patient_id": request.patient_id,
            "reason": request.reason,
        }

        try:
            await ApprovalEngine(self.db).start_instance(
                business_type="extra_quota",
                business_id=request.id,
                form_data=form_data,
                applicant_id=request.applicant_id,
                title=f"加号申请 - {request.quantity} 个号源",
                store_id=request.store_id,
            )
        except FlowNotFoundError:
            return

    # ==================== 审批操作 ====================

    async def approve(
        self,
        tenant_id: str,
        request_id: str,
        approver_id: str,
        remark: str | None = None,
    ) -> ExtraQuotaRequest:
        """审批通过加号申请（旧审核入口，作为无通用审批流程定义时的 fallback）。

        通用引擎已完整接入：发起端通过 _start_approval_if_configured() 调用
        ApprovalEngine.start_instance()，回调端通过 business_callbacks.py 的
        handle_extra_quota_approval() 处理审批结果。本方法仅在未配置流程定义时使用。
        """
        request = await self._get_request(request_id, tenant_id)
        if not request:
            raise ValueError("加号申请不存在")
        if request.approval_status != "pending":
            raise ValueError(f"当前状态为 [{request.approval_status}]，只有待审批状态可以操作")

        # 使用分布式锁保护号源更新
        lock_name = f"extra_quota:approve:{request.schedule_id}"

        async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=10, retry_times=5):
            # 更新申请状态
            request.approval_status = "approved"
            request.approver_id = approver_id
            request.approval_remark = remark
            request.approved_at = utc_now()
            set_update_audit(request, approver_id)

            # 更新排班号源
            schedule = await self._get_schedule(request.schedule_id, tenant_id)
            if schedule:
                schedule.extra_quota = (schedule.extra_quota or 0) + request.quantity
                schedule.sync_total_slots()
                set_update_audit(schedule, approver_id)

            await self.db.commit()
            await self.db.refresh(request)

        logger.info(
            "加号申请批准: request_id=%s, approver_id=%s, quantity=%d",
            request_id, approver_id, request.quantity,
        )
        return request

    async def reject(
        self,
        tenant_id: str,
        request_id: str,
        approver_id: str,
        remark: str | None = None,
    ) -> ExtraQuotaRequest:
        """拒绝加号申请。"""
        request = await self._get_request(request_id, tenant_id)
        if not request:
            raise ValueError("加号申请不存在")
        if request.approval_status != "pending":
            raise ValueError(f"当前状态为 [{request.approval_status}]，只有待审批状态可以操作")

        request.approval_status = "rejected"
        request.approver_id = approver_id
        request.approval_remark = remark
        request.approved_at = utc_now()
        set_update_audit(request, approver_id)

        await self.db.commit()
        await self.db.refresh(request)

        logger.info("加号申请拒绝: request_id=%s, approver_id=%s", request_id, approver_id)
        return request

    # ==================== 查询 ====================

    async def get_list(
        self,
        tenant_id: str,
        store_id: str | None = None,
        schedule_id: str | None = None,
        doctor_id: str | None = None,
        approval_status: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list, int]:
        """查询加号申请列表。返回 (items, total)。"""
        conditions = [ExtraQuotaRequest.tenant_id == tenant_id]

        if store_id:
            conditions.append(ExtraQuotaRequest.store_id == store_id)
        if schedule_id:
            conditions.append(ExtraQuotaRequest.schedule_id == schedule_id)
        if doctor_id:
            conditions.append(ExtraQuotaRequest.doctor_id == doctor_id)
        if approval_status:
            conditions.append(ExtraQuotaRequest.approval_status == approval_status)
        if start_date:
            conditions.append(ExtraQuotaRequest.schedule_date >= start_date)
        if end_date:
            conditions.append(ExtraQuotaRequest.schedule_date <= end_date)

        where_clause = and_(*conditions)

        # 总数
        count_result = await self.db.execute(
            select(func.count(ExtraQuotaRequest.id)).where(where_clause)
        )
        total = count_result.scalar() or 0

        # 分页查询
        query = (
            select(ExtraQuotaRequest)
            .where(where_clause)
            .order_by(ExtraQuotaRequest.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        result = await self.db.execute(query)
        items = list(result.scalars().all())

        return items, total

    async def get_by_id(self, tenant_id: str, request_id: str) -> ExtraQuotaRequest | None:
        """查询单个加号申请。"""
        return await self._get_request(request_id, tenant_id)

    # ==================== 内部方法 ====================

    async def _get_schedule(self, schedule_id: str, tenant_id: str) -> Schedule | None:
        """获取排班（带租户隔离）。"""
        result = await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.id == schedule_id,
                    Schedule.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()

    async def _get_request(self, request_id: str, tenant_id: str) -> ExtraQuotaRequest | None:
        """获取加号申请（带租户隔离）。"""
        result = await self.db.execute(
            select(ExtraQuotaRequest).where(
                and_(
                    ExtraQuotaRequest.id == request_id,
                    ExtraQuotaRequest.tenant_id == tenant_id,
                )
            )
        )
        return result.scalar_one_or_none()
