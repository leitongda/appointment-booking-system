"""患者管理服务（管理后台使用）"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import datetime, timedelta
import uuid

from app.models.user import User, Patient
from app.models.appointment import Appointment


class PatientManageService:
    """患者管理服务（管理后台）"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        keyword: Optional[str] = None,
        is_blacklist: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        """获取患者列表"""
        # 查询所有就诊人
        query = select(Patient).options(selectinload(Patient.user))
        conditions = []
        
        if keyword:
            conditions.append(
                or_(
                    Patient.name.ilike(f"%{keyword}%"),
                    Patient.phone.ilike(f"%{keyword}%"),
                    Patient.id_card.ilike(f"%{keyword}%")
                )
            )
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 统计总数
        count_query = select(func.count(Patient.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        # 分页查询
        query = query.order_by(Patient.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        patients = result.unique().scalars().all()
        
        # 获取每个患者的预约统计
        patient_data = []
        for patient in patients:
            # 查询预约次数
            appointment_count = await self.db.scalar(
                select(func.count(Appointment.id)).where(Appointment.patient_id == patient.id)
            )
            
            # 查询爽约次数
            no_show_count = await self.db.scalar(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.patient_id == patient.id,
                        Appointment.status == 7  # 爽约状态
                    )
                )
            )
            
            # 检查是否在黑名单中（通过用户状态判断）
            user = patient.user
            is_in_blacklist = user.status == 0 if user else False
            
            # 如果筛选黑名单
            if is_blacklist is not None:
                if is_blacklist and not is_in_blacklist:
                    continue
                if not is_blacklist and is_in_blacklist:
                    continue
            
            patient_data.append({
                'id': patient.id,
                'userId': patient.user_id,
                'name': patient.name,
                'phone': patient.phone,
                'idCard': patient.id_card,
                'gender': patient.gender,
                'birthday': patient.birthday.isoformat() if patient.birthday else None,
                'relationship': patient.relationship,
                'isDefault': patient.is_default,
                'appointmentCount': appointment_count or 0,
                'noShowCount': no_show_count or 0,
                'isBlacklist': is_in_blacklist,
                'createdAt': patient.created_at.isoformat() if patient.created_at else None,
            })
        
        return patient_data, total or 0

    async def get_detail(self, patient_id: str) -> Optional[dict]:
        """获取患者详情"""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.id == patient_id)
        )
        patient = result.unique().scalar_one_or_none()
        
        if not patient:
            return None
        
        # 查询最近预约记录
        appointments_result = await self.db.execute(
            select(Appointment)
            .where(Appointment.patient_id == patient_id)
            .order_by(Appointment.created_at.desc())
            .limit(10)
        )
        appointments = appointments_result.scalars().all()
        
        # 查询预约统计
        appointment_count = await self.db.scalar(
            select(func.count(Appointment.id)).where(Appointment.patient_id == patient_id)
        )
        no_show_count = await self.db.scalar(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.status == 7
                )
            )
        )
        completed_count = await self.db.scalar(
            select(func.count(Appointment.id)).where(
                and_(
                    Appointment.patient_id == patient_id,
                    Appointment.status == 5
                )
            )
        )
        
        user = patient.user
        
        return {
            'id': patient.id,
            'userId': patient.user_id,
            'name': patient.name,
            'phone': patient.phone,
            'idCard': patient.id_card,
            'gender': patient.gender,
            'birthday': patient.birthday.isoformat() if patient.birthday else None,
            'relationship': patient.relationship,
            'isDefault': patient.is_default,
            'isBlacklist': user.status == 0 if user else False,
            'statistics': {
                'appointmentCount': appointment_count or 0,
                'completedCount': completed_count or 0,
                'noShowCount': no_show_count or 0,
            },
            'recentAppointments': [
                {
                    'id': a.id,
                    'appointmentNo': a.appointment_no,
                    'status': a.status,
                    'createdAt': a.created_at.isoformat() if a.created_at else None,
                }
                for a in appointments
            ],
            'createdAt': patient.created_at.isoformat() if patient.created_at else None,
        }

    async def add_to_blacklist(self, patient_id: str, reason: str = None) -> bool:
        """加入黑名单"""
        result = await self.db.execute(
            select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        )
        patient = result.unique().scalar_one_or_none()
        
        if not patient or not patient.user:
            return False
        
        patient.user.status = 0  # 禁用用户
        await self.db.commit()
        return True

    async def remove_from_blacklist(self, patient_id: str) -> bool:
        """移出黑名单"""
        result = await self.db.execute(
            select(Patient).options(selectinload(Patient.user)).where(Patient.id == patient_id)
        )
        patient = result.unique().scalar_one_or_none()
        
        if not patient or not patient.user:
            return False
        
        patient.user.status = 1  # 启用用户
        await self.db.commit()
        return True

    async def get_blacklist(
        self,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        """获取黑名单列表"""
        # 查询被禁用用户的就诊人
        query = select(Patient).join(User).where(User.status == 0)
        
        count_query = select(func.count(Patient.id)).join(User).where(User.status == 0)
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Patient.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        patients = result.scalars().all()
        
        patient_data = []
        for patient in patients:
            no_show_count = await self.db.scalar(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.patient_id == patient.id,
                        Appointment.status == 7
                    )
                )
            )
            
            patient_data.append({
                'id': patient.id,
                'name': patient.name,
                'phone': patient.phone,
                'idCard': patient.id_card,
                'noShowCount': no_show_count or 0,
                'createdAt': patient.created_at.isoformat() if patient.created_at else None,
            })
        
        return patient_data, total or 0


