from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
import uuid

from app.models.user import User, Patient
from app.schemas.user import UserCreate, UserUpdate, PatientCreate, PatientUpdate
from app.core.security import get_password_hash, verify_password

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, phone: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()
    
    async def get_by_openid(self, openid: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.openid == openid))
        return result.scalar_one_or_none()
    
    async def create(self, data: UserCreate) -> User:
        user = User(
            id=str(uuid.uuid4()),
            phone=data.phone,
            password_hash=get_password_hash(data.password) if data.password else "",
            openid=data.openid,
            status=1
        )
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def update(self, user_id: str, data: UserUpdate) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)
        
        await self.db.commit()
        await self.db.refresh(user)
        return user
    
    async def authenticate(self, phone: str, password: str) -> Optional[User]:
        user = await self.get_by_phone(phone)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, patient_id: str) -> Optional[Patient]:
        result = await self.db.execute(select(Patient).where(Patient.id == patient_id))
        return result.scalar_one_or_none()
    
    async def get_by_user_id(self, user_id: str) -> list[Patient]:
        result = await self.db.execute(
            select(Patient).where(Patient.user_id == user_id).order_by(Patient.is_default.desc())
        )
        return list(result.scalars().all())
    
    async def create(self, user_id: str, data: PatientCreate) -> Patient:
        # 如果是第一个就诊人，设为默认
        existing = await self.get_by_user_id(user_id)
        is_default = len(existing) == 0 or data.is_default
        
        # 如果新增为默认，取消其他默认
        if is_default and existing:
            for p in existing:
                if p.is_default:
                    p.is_default = False
        
        patient = Patient(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=data.name,
            phone=data.phone,
            id_card=data.id_card,
            gender=data.gender,
            relationship=data.relationship,
            is_default=is_default
        )
        self.db.add(patient)
        await self.db.commit()
        await self.db.refresh(patient)
        return patient
    
    async def update(self, patient_id: str, user_id: str, data: PatientUpdate) -> Optional[Patient]:
        patient = await self.get_by_id(patient_id)
        if not patient or patient.user_id != user_id:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 处理默认设置
        if update_data.get('is_default'):
            existing = await self.get_by_user_id(user_id)
            for p in existing:
                if p.is_default and p.id != patient_id:
                    p.is_default = False
        
        for field, value in update_data.items():
            setattr(patient, field, value)
        
        await self.db.commit()
        await self.db.refresh(patient)
        return patient
    
    async def delete(self, patient_id: str, user_id: str) -> bool:
        patient = await self.get_by_id(patient_id)
        if not patient or patient.user_id != user_id:
            return False
        
        await self.db.delete(patient)
        await self.db.commit()
        return True

