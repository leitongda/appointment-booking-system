from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from datetime import datetime
import uuid
import random
import string

from pypinyin import lazy_pinyin

from app.models.doctor import Doctor
from app.models.department import Department
from app.models.store import Store
from app.models.user import User
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.core.security import get_password_hash, verify_password

class DoctorService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_phone(self, phone: str) -> Optional[Doctor]:
        """根据手机号获取医生"""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.phone == phone)
        )
        return result.scalar_one_or_none()
    
    async def get_by_username(self, username: str) -> Optional[Doctor]:
        """根据账号获取医生"""
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.username == username)
        )
        return result.scalar_one_or_none()
    
    async def authenticate(self, phone: str, password: str) -> Optional[Doctor]:
        """医生认证（支持手机号或账号登录）"""
        # 先尝试手机号登录
        doctor = await self.get_by_phone(phone)
        if not doctor:
            # 再尝试账号登录
            doctor = await self.get_by_username(phone)
        
        if not doctor or not doctor.password_hash:
            return None
        if not verify_password(password, doctor.password_hash):
            return None
        return doctor
    
    async def update_login_info(self, doctor_id: str, ip: str) -> None:
        """更新登录信息"""
        result = await self.db.execute(select(Doctor).where(Doctor.id == doctor_id))
        doctor = result.scalar_one_or_none()
        if doctor:
            doctor.last_login_at = datetime.now()
            doctor.last_login_ip = ip
            await self.db.commit()
    
    async def get_by_id(self, doctor_id: str) -> Optional[Doctor]:
        result = await self.db.execute(
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.id == doctor_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        name: Optional[str] = None,
        store_id: Optional[str] = None,
        department_id: Optional[str] = None,
        status: Optional[int] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Doctor], int]:
        query = select(Doctor).options(selectinload(Doctor.department), selectinload(Doctor.store))
        count_query = select(func.count(Doctor.id))
        
        if name:
            query = query.where(Doctor.name.contains(name))
            count_query = count_query.where(Doctor.name.contains(name))
        if store_id:
            query = query.where(Doctor.store_id == store_id)
            count_query = count_query.where(Doctor.store_id == store_id)
        if department_id:
            query = query.where(Doctor.department_id == department_id)
            count_query = count_query.where(Doctor.department_id == department_id)
        if status is not None:
            query = query.where(Doctor.status == status)
            count_query = count_query.where(Doctor.status == status)
        
        query = query.order_by(Doctor.sort_order.desc()).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_recommended(self, limit: int = 6, store_id: Optional[str] = None) -> List[Doctor]:
        """获取推荐医生
        
        Args:
            limit: 返回数量
            store_id: 门店ID，如提供则只返回该门店的推荐医生
        """
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.is_recommended == 1, Doctor.status == 1)
        )
        
        if store_id:
            query = query.where(Doctor.store_id == store_id)
        
        query = query.order_by(Doctor.sort_order.desc()).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_by_department(self, department_id: str, store_id: Optional[str] = None) -> List[Doctor]:
        """获取科室下的医生
        
        Args:
            department_id: 科室ID
            store_id: 门店ID，如提供则只返回该门店的医生
        """
        query = (
            select(Doctor)
            .options(selectinload(Doctor.department), selectinload(Doctor.store))
            .where(Doctor.department_id == department_id, Doctor.status == 1)
        )
        
        if store_id:
            query = query.where(Doctor.store_id == store_id)
        
        query = query.order_by(Doctor.sort_order.desc())
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, data: DoctorCreate) -> Doctor:
        user_id = None
        
        # 如果未提供密码，使用默认密码
        password = data.password or "123456"
        password_hash = get_password_hash(password)
        
        # 如果提供手机号，创建用户账号
        if data.phone:
            user = User(
                id=str(uuid.uuid4()),
                phone=data.phone,
                password_hash=password_hash,
                nickname=data.name,
                status=1
            )
            self.db.add(user)
            await self.db.flush()
            user_id = user.id
        
        doctor = Doctor(
            id=str(uuid.uuid4()),
            user_id=user_id,
            store_id=data.store_id,
            department_id=data.department_id,
            name=data.name,
            username=data.username,
            phone=data.phone,
            password_hash=password_hash,
            gender=data.gender,
            avatar=data.avatar,
            banner=data.banner,
            title=data.title,
            years_of_experience=data.years_of_experience,
            education=data.education,
            graduate_school=data.graduate_school,
            license_number=data.license_number,
            license_image=data.license_image,
            honors=data.honors,
            schedule_desc=data.schedule_desc,
            max_daily_appointments=data.max_daily_appointments,
            online_consult_enabled=data.online_consult_enabled,
            online_consult_fee=data.online_consult_fee,
            registration_fee=data.registration_fee,
            page_style=data.page_style,
            promo_video=data.promo_video,
            tags=data.tags,
            specialty=data.specialty,
            introduction=data.introduction,
            is_recommended=data.is_recommended,
            sort_order=data.sort_order,
            status=data.status,
            use_fee_template=data.use_fee_template
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
        
        # 如果更新密码，需要加密
        if 'password' in update_data and update_data['password']:
            update_data['password_hash'] = get_password_hash(update_data['password'])
            del update_data['password']
        
        for field, value in update_data.items():
            if hasattr(doctor, field):
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
    
    async def check_username_exists(self, username: str, exclude_id: Optional[str] = None) -> bool:
        """检查用户名是否已存在"""
        query = select(Doctor).where(Doctor.username == username)
        if exclude_id:
            query = query.where(Doctor.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is not None
    
    def name_to_pinyin(self, name: str) -> str:
        """将中文姓名转换为拼音"""
        return ''.join(lazy_pinyin(name))
    
    async def generate_username(self, name: str) -> str:
        """根据姓名生成唯一用户名"""
        base_username = self.name_to_pinyin(name)
        username = base_username
        
        # 检查是否存在，如果存在则添加随机数字后缀
        if await self.check_username_exists(username):
            for _ in range(10):  # 最多尝试10次
                suffix = '_' + ''.join(random.choices(string.digits, k=3))
                username = base_username + suffix
                if not await self.check_username_exists(username):
                    break
        
        return username
    
    async def suggest_usernames(self, base_username: str, count: int = 3) -> List[str]:
        """生成推荐用户名列表"""
        suggestions = []
        attempts = 0
        max_attempts = count * 5
        
        while len(suggestions) < count and attempts < max_attempts:
            suffix = '_' + ''.join(random.choices(string.digits, k=3))
            candidate = base_username + suffix
            if not await self.check_username_exists(candidate) and candidate not in suggestions:
                suggestions.append(candidate)
            attempts += 1
        
        return suggestions
