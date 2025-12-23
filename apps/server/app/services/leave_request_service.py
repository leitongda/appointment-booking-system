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


class LeaveRequestService:
    """停诊/调班申请服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, request_id: str) -> Optional[LeaveRequest]:
        """根据ID获取申请"""
        result = await self.db.execute(
            select(LeaveRequest).where(LeaveRequest.id == request_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(self, query: LeaveRequestQuery) -> tuple[List[LeaveRequest], int]:
        """获取申请列表"""
        stmt = select(LeaveRequest)
        count_stmt = select(func.count(LeaveRequest.id))
        
        # 门店过滤：通过医生关联门店
        if query.store_id:
            stmt = stmt.join(Doctor, LeaveRequest.doctor_id == Doctor.id)
            stmt = stmt.where(Doctor.store_id == query.store_id)
            count_stmt = count_stmt.join(Doctor, LeaveRequest.doctor_id == Doctor.id)
            count_stmt = count_stmt.where(Doctor.store_id == query.store_id)
        
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
        # 计算受影响的预约数
        affected = await self._count_affected_appointments(
            data.doctor_id, 
            data.stop_date, 
            data.stop_period
        )
        
        request = LeaveRequest(
            id=str(uuid.uuid4()),
            doctor_id=data.doctor_id,
            request_type=RequestType.STOP_CLINIC.value,
            schedule_id=data.schedule_id,
            stop_date=data.stop_date,
            stop_period=data.stop_period,
            reason=data.reason,
            affected_appointments=affected
        )
        
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request
    
    async def create_schedule_change(self, data: ScheduleChangeCreate) -> LeaveRequest:
        """创建调班申请"""
        # 计算受影响的预约数
        affected = await self._count_affected_appointments(
            data.doctor_id,
            data.original_date,
            data.original_period
        )
        
        request = LeaveRequest(
            id=str(uuid.uuid4()),
            doctor_id=data.doctor_id,
            request_type=RequestType.SCHEDULE_CHANGE.value,
            original_date=data.original_date,
            original_period=data.original_period,
            target_date=data.target_date,
            target_period=data.target_period,
            reason=data.reason,
            affected_appointments=affected
        )
        
        self.db.add(request)
        await self.db.commit()
        await self.db.refresh(request)
        return request
    
    async def review(
        self, 
        request_id: str, 
        reviewer_id: str, 
        data: ReviewRequest
    ) -> Optional[LeaveRequest]:
        """审核申请"""
        request = await self.get_by_id(request_id)
        if not request:
            return None
        
        if request.status != RequestStatus.PENDING.value:
            raise ValueError("该申请已处理，无法重复审核")
        
        request.status = data.status.value
        request.reviewer_id = reviewer_id
        request.review_comment = data.review_comment
        request.reviewed_at = datetime.utcnow()
        
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
        await self.db.commit()
        return True
    
    async def _count_affected_appointments(
        self, 
        doctor_id: str, 
        date: any, 
        period: str
    ) -> int:
        """计算受影响的预约数"""
        stmt = select(func.count(Appointment.id)).where(
            and_(
                Appointment.doctor_id == doctor_id,
                Appointment.appointment_date == date,
                Appointment.status.in_(['pending', 'confirmed'])
            )
        )
        
        if period != 'all':
            stmt = stmt.where(Appointment.time_period == period)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def _handle_approved_request(self, request: LeaveRequest):
        """处理通过的申请"""
        if request.request_type == RequestType.STOP_CLINIC.value:
            # 停诊：更新排班状态
            if request.schedule_id:
                schedule_result = await self.db.execute(
                    select(Schedule).where(Schedule.id == request.schedule_id)
                )
                schedule = schedule_result.scalar_one_or_none()
                if schedule:
                    schedule.status = 0  # 停诊
            
            # 取消相关预约（实际应发送通知给患者）
            # 这里简化处理，只更新状态
            await self.db.execute(
                select(Appointment).where(
                    and_(
                        Appointment.doctor_id == request.doctor_id,
                        Appointment.appointment_date == request.stop_date,
                        Appointment.status.in_(['pending', 'confirmed'])
                    )
                )
            )
        
        elif request.request_type == RequestType.SCHEDULE_CHANGE.value:
            # 调班：交换排班
            # 实际实现需要更复杂的逻辑
            pass
    
    async def get_pending_count(self, store_id: Optional[str] = None) -> int:
        """获取待审核数量"""
        stmt = select(func.count(LeaveRequest.id)).where(
            LeaveRequest.status == RequestStatus.PENDING.value
        )
        
        # 门店过滤
        if store_id:
            stmt = stmt.join(Doctor, LeaveRequest.doctor_id == Doctor.id)
            stmt = stmt.where(Doctor.store_id == store_id)
        
        result = await self.db.execute(stmt)
        return result.scalar() or 0
    
    async def get_doctor_requests(
        self, 
        doctor_id: str, 
        status: Optional[str] = None
    ) -> List[LeaveRequest]:
        """获取医生的申请列表"""
        stmt = select(LeaveRequest).where(LeaveRequest.doctor_id == doctor_id)
        
        if status:
            stmt = stmt.where(LeaveRequest.status == status)
        
        stmt = stmt.order_by(LeaveRequest.created_at.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
