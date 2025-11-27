from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.doctor import Doctor
from app.models.department import Department
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.core.security import get_password_hash

class DoctorService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, doctor_id: str) -> Optional[Doctor]:
        result = await self.db.execute(
            select(Doctor).options(selectinload(Doctor.department)).where(Doctor.id == doctor_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        name: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Doctor], int]:
        query = select(Doctor).options(selectinload(Doctor.department))
        count_query = select(func.count(Doctor.id))
        
        if name:
            query = query.where(Doctor.name.contains(name))
            count_query = count_query.where(Doctor.name.contains(name))
        if department_id:
            query = query.where(Doctor.department_id == department_id)
            count_query = count_query.where(Doctor.department_id == department_id)
        if status is not None:
            query = query.where(Doctor.status == status)
            count_query = count_query.where(Doctor.status == status)
        
        query = query.order_by(Doctor.sort_order).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_recommended(self, limit: int = 6) -> List[Doctor]:
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.department))
            .where(Doctor.is_recommended == 1, Doctor.status == 1)
            .order_by(Doctor.sort_order)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_department(self, department_id: str) -> List[Doctor]:
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.department))
            .where(Doctor.department_id == department_id, Doctor.status == 1)
            .order_by(Doctor.sort_order)
        )
        return list(result.scalars().all())
    
    async def create(self, data: DoctorCreate) -> Doctor:
        user_id = None
        
        # 如果提供密码，创建用户账号
        if data.password and data.phone:
            user = User(
                id=str(uuid.uuid4()),
                phone=data.phone,
                password_hash=get_password_hash(data.password),
                nickname=data.name,
                status=1
            )
            self.db.add(user)
            await self.db.flush()
            user_id = user.id
        
        doctor = Doctor(
            id=str(uuid.uuid4()),
            user_id=user_id,
            department_id=data.department_id,
            name=data.name,
            phone=data.phone,
            avatar=data.avatar,
            title=data.title,
            specialty=data.specialty,
            introduction=data.introduction,
            registration_fee=data.registration_fee,
            is_recommended=data.is_recommended,
            sort_order=data.sort_order,
            status=data.status
        )
        self.db.add(doctor)
        await self.db.commit()
        await self.db.refresh(doctor)
        return doctor
    
    async def update(self, doctor_id: str, data: DoctorUpdate) -> Optional[Doctor]:
        doctor = await self.get_by_id(doctor_id)
        if not doctor:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(doctor, field, value)
        
        await self.db.commit()
        await self.db.refresh(doctor)
        return doctor
    
    async def delete(self, doctor_id: str) -> bool:
        doctor = await self.get_by_id(doctor_id)
        if not doctor:
            return False
        
        await self.db.delete(doctor)
        await self.db.commit()
        return True

