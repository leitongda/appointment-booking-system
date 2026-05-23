from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import uuid

from app.models.leave_request import LeaveRequest, RequestType, RequestStatus
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.schemas.leave_request import (
    StopClinicCreate, ScheduleChangeCreate, ReviewRequest, LeaveRequestQuery
)
from app.utils.audit import set_create_audit, set_update_audit
from app.middleware.tenant_context import get_current_tenant_id


class LeaveRequestService:
    """停诊/调班申请服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, request_id: str) -> Optional[LeaveRequest]:
        """根据ID获取申请"""
        stmt = select(LeaveRequest).where(LeaveRequest.id == request_id)
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(LeaveRequest.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_list(self, query: LeaveRequestQuery) -> tuple[List[LeaveRequest], int]:
        """获取申请列表"""
        stmt = select(LeaveRequest)
        count_stmt = select(func.count(LeaveRequest.id))

        # 租户过滤
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(LeaveRequest.tenant_id == tenant_id)
            count_stmt = count_stmt.where(LeaveRequest.tenant_id == tenant_id)

        # 门店过滤：通过医生关联门店
        if query.store_id:
            stmt = stmt.join(Doctor, LeaveRequest.doctor_id == Doctor.id)
            stmt = stmt.where(Doctor.store_id == query.store_id, Doctor.deleted_at.is_(None))
            count_stmt = count_stmt.join(Doctor, LeaveRequest.doctor_id == Doctor.id)
            count_stmt = count_stmt.where(Doctor.store_id == query.store_id, Doctor.deleted_at.is_(None))

        if query.doctor_id:
            stmt = stmt.where(LeaveRequest.doctor_id == query.doctor_id)
            count_stmt = count_stmt.where(LeaveRequest.doctor_id == query.doctor_id)

        if query.request_type:
            stmt = stmt.where(LeaveRequest.request_type == query.request_type.value)
            count_stmt = count_stmt.where(LeaveRequest.request_type == query.request_type.value)

        if query.status:
            stmt = stmt.where(LeaveRequest.status == query.status.value)
            count_stmt = count_stmt.where(LeaveRequest.status == query.status.value)

        if query.start_date:
            stmt = stmt.where(LeaveRequest.created_at >= query.start_date)
            count_stmt = count_stmt.where(LeaveRequest.created_at >= query.start_date)

        if query.end_date:
            stmt = stmt.where(LeaveRequest.created_at <= query.end_date)
            count_stmt = count_stmt.where(LeaveRequest.created_at <= query.end_date)

        stmt = stmt.order_by(LeaveRequest.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)

        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)

        return list(result.scalars().all()), count_result.scalar() or 0

    async def create_stop_clinic(self, data: StopClinicCreate) -> LeaveRequest:
        """创建停诊申请"""
        tenant_id = get_current_tenant_id()

        # 计算受影响的预约数
        affected = await self._count_affected_appointments(
            data.doctor_id,
            data.stop_date,
            data.stop_period
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
            affected_appointments=affected
        )
        set_create_audit(request, data.doctor_id)

        self.db.add(request)
        await self.db.flush()
        await self._start_approval_if_configured(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def create_schedule_change(self, data: ScheduleChangeCreate) -> LeaveRequest:
        """创建调班申请"""
        tenant_id = get_current_tenant_id()

        # 计算受影响的预约数
        affected = await self._count_affected_appointments(
            data.doctor_id,
            data.original_date,
            data.original_period
        )

        request = LeaveRequest(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            doctor_id=data.doctor_id,
            request_type=RequestType.SCHEDULE_CHANGE.value,
            original_date=data.original_date,
            original_period=data.original_period,
            target_date=data.target_date,
            target_period=data.target_period,
            reason=data.reason,
            affected_appointments=affected
        )
        set_create_audit(request, data.doctor_id)

        self.db.add(request)
        await self.db.flush()
        await self._start_approval_if_configured(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def _start_approval_if_configured(self, request: LeaveRequest):
        """有激活通用审批流程时创建审批实例；未配置时保留旧审核入口。"""
        from app.modules.approval_flows.engine import ApprovalEngine, FlowNotFoundError

        form_data = {
            "request_type": request.request_type,
            "doctor_id": request.doctor_id,
            "schedule_id": request.schedule_id,
            "stop_date": request.stop_date.isoformat() if request.stop_date else None,
            "stop_period": request.stop_period,
            "original_date": request.original_date.isoformat() if request.original_date else None,
            "original_period": request.original_period,
            "target_date": request.target_date.isoformat() if request.target_date else None,
            "target_period": request.target_period,
            "reason": request.reason,
            "affected_appointments": request.affected_appointments,
        }
        title = "停诊申请" if request.request_type == RequestType.STOP_CLINIC.value else "调班申请"

        try:
            await ApprovalEngine(self.db).start_instance(
                business_type="leave_request",
                business_id=request.id,
                form_data=form_data,
                applicant_id=request.doctor_id,
                title=f"{title} - {request.reason[:40]}",
                store_id=None,
            )
        except FlowNotFoundError:
            return

    async def review(
        self,
        request_id: str,
        reviewer_id: str,
        data: ReviewRequest
    ) -> Optional[LeaveRequest]:
        """审核申请（旧审核入口，作为无通用审批流程定义时的 fallback）。

        通用引擎已完整接入：发起端通过 _start_approval_if_configured() 调用
        ApprovalEngine.start_instance()，回调端通过 business_callbacks.py 的
        handle_leave_request_approval() 处理审批结果。本方法仅在未配置流程定义时使用。
        """
        request = await self.get_by_id(request_id)
        if not request:
            return None

        if request.status != RequestStatus.PENDING.value:
            raise ValueError("该申请已处理，无法重复审核")

        request.status = data.status.value
        request.reviewer_id = reviewer_id
        request.review_comment = data.review_comment
        request.reviewed_at = datetime.utcnow()
        set_update_audit(request, reviewer_id)

        # 如果通过，处理排班和预约
        if data.status == RequestStatus.APPROVED:
            await self._handle_approved_request(request)

        await self.db.commit()
        await self.db.refresh(request)
        return request

    async def cancel(self, request_id: str, doctor_id: str) -> bool:
        """取消申请"""
        request = await self.get_by_id(request_id)
        if not request:
            return False

        if request.doctor_id != doctor_id:
            raise ValueError("无权取消此申请")

        if request.status != RequestStatus.PENDING.value:
            raise ValueError("该申请已处理，无法取消")

        request.status = RequestStatus.CANCELLED.value
        set_update_audit(request, doctor_id)
        await self.db.commit()
        return True

    async def _count_affected_appointments(
        self,
        doctor_id: str,
        date: any,
        period: str
    ) -> int:
        """计算受影响的预约数"""
        stmt = (
            select(func.count(Appointment.id))
            .join(Schedule, Appointment.schedule_id == Schedule.id)
            .where(
                and_(
                    Appointment.doctor_id == doctor_id,
                    Schedule.schedule_date == date,
                    Appointment.status.in_([0, 1])  # 待支付/已预约
                )
            )
        )

        if period != 'all':
            stmt = stmt.where(Schedule.time_slot == period)

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def _handle_approved_request(self, request: LeaveRequest):
        """处理通过的申请"""
        if request.request_type == RequestType.STOP_CLINIC.value:
            await self._handle_stop_clinic(request)
        elif request.request_type == RequestType.SCHEDULE_CHANGE.value:
            await self._handle_schedule_change(request)

    async def _handle_stop_clinic(self, request: LeaveRequest):
        """处理停诊申请通过"""
        # 停诊：更新排班状态
        if request.schedule_id:
            schedule_result = await self.db.execute(
                select(Schedule).where(Schedule.id == request.schedule_id)
            )
            schedule = schedule_result.scalar_one_or_none()
            if schedule:
                schedule.status = 0

        # 取消受影响的预约
        if request.stop_date:
            cancel_stmt = (
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == request.doctor_id,
                        Appointment.schedule_id.isnot(None),
                        Appointment.status.in_([0, 1]),
                    )
                )
            )
            appointments = (await self.db.execute(cancel_stmt)).scalars().all()
            for apt in appointments:
                # 通过 schedule 关联判断日期和时段
                if apt.schedule_id:
                    sched = (await self.db.execute(
                        select(Schedule).where(Schedule.id == apt.schedule_id)
                    )).scalar_one_or_none()
                    if sched and sched.schedule_date == request.stop_date:
                        if request.stop_period == 'all' or sched.time_slot == request.stop_period:
                            apt.status = 6  # 已取消
                            apt.cancel_reason = f"医生停诊（审批单 {request.id}）"

    async def _handle_schedule_change(self, request: LeaveRequest):
        """处理调班申请通过：交换原时段和目标时段的排班"""
        if not request.original_date or not request.target_date:
            return

        # 查找原时段的排班
        orig_schedules = (await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.doctor_id == request.doctor_id,
                    Schedule.schedule_date == request.original_date,
                    Schedule.time_slot == request.original_period,
                    Schedule.status == 1,
                )
            )
        )).scalars().all()

        # 查找目标时段的排班
        target_schedules = (await self.db.execute(
            select(Schedule).where(
                and_(
                    Schedule.doctor_id == request.doctor_id,
                    Schedule.schedule_date == request.target_date,
                    Schedule.time_slot == request.target_period,
                    Schedule.status == 1,
                )
            )
        )).scalars().all()

        # 交换排班的日期和时段
        if orig_schedules and target_schedules:
            orig = orig_schedules[0]
            target = target_schedules[0]
            orig.schedule_date, target.schedule_date = target.schedule_date, orig.schedule_date
            orig.time_slot, target.time_slot = target.time_slot, orig.time_slot
            orig.start_time, target.start_time = target.start_time, orig.start_time
            orig.end_time, target.end_time = target.end_time, orig.end_time
        elif orig_schedules:
            # 目标时段无排班，仅移动原排班到目标日期时段
            orig = orig_schedules[0]
            orig.schedule_date = request.target_date
            orig.time_slot = request.target_period
        elif target_schedules:
            # 原时段无排班（可能已被删除），仅移动目标排班到原日期时段
            target = target_schedules[0]
            target.schedule_date = request.original_date
            target.time_slot = request.original_period

    async def get_pending_count(self, store_id: Optional[str] = None) -> int:
        """获取待审核数量"""
        stmt = select(func.count(LeaveRequest.id)).where(
            LeaveRequest.status == RequestStatus.PENDING.value
        )

        # 租户过滤
        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(LeaveRequest.tenant_id == tenant_id)

        # 门店过滤
        if store_id:
            stmt = stmt.join(Doctor, LeaveRequest.doctor_id == Doctor.id)
            stmt = stmt.where(Doctor.store_id == store_id, Doctor.deleted_at.is_(None))

        result = await self.db.execute(stmt)
        return result.scalar() or 0

    async def get_doctor_requests(
        self,
        doctor_id: str,
        status: Optional[str] = None
    ) -> List[LeaveRequest]:
        """获取医生的申请列表"""
        stmt = select(LeaveRequest).where(LeaveRequest.doctor_id == doctor_id)

        tenant_id = get_current_tenant_id()
        if tenant_id:
            stmt = stmt.where(LeaveRequest.tenant_id == tenant_id)

        if status:
            stmt = stmt.where(LeaveRequest.status == status)

        stmt = stmt.order_by(LeaveRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
