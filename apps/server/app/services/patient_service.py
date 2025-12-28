"""患者管理服务（管理后台使用）"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple
from datetime import datetime, date
import uuid

from app.models.user import User, Patient
from app.models.appointment import Appointment
from app.models.schedule import Schedule
from app.models.doctor import Doctor
from app.models.department import Department
from app.models.store import Store
from app.schemas.user import PatientUpdate, PatientCreateByAdmin, FamilyMemberCreate
from app.core.security import get_password_hash
from app.utils.audit import set_create_audit, set_update_audit


class PatientManageService:
    """患者管理服务（管理后台）"""
    
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        keyword: Optional[str] = None,
        is_blacklist: Optional[bool] = None,
        store_id: Optional[str] = None,
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
                    Patient.id_card.ilike(f"%{keyword}%"),
                    Patient.card_no.ilike(f"%{keyword}%")
                )
            )
        
        # 门店过滤
        if store_id:
            conditions.append(
                or_(Patient.store_id == store_id, Patient.store_id.is_(None))
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
                'cardNo': patient.card_no,
                'name': patient.name,
                'phone': patient.phone,
                'idCard': patient.id_card,
                'gender': patient.gender,
                'birthday': patient.birthday.isoformat() if patient.birthday else None,
                'relationship': patient.relationship,
                'isDefault': patient.is_default,
                'source': patient.source or 1,
                'appointmentCount': appointment_count or 0,
                'noShowCount': no_show_count or 0,
                'isBlacklist': is_in_blacklist,
                'createdAt': patient.created_at.isoformat() if patient.created_at else None,
            })
        
        return patient_data, total or 0

    def _calculate_age(self, birthday: datetime) -> Optional[int]:
        """计算年龄"""
        if not birthday:
            return None
        today = date.today()
        age = today.year - birthday.year
        if (today.month, today.day) < (birthday.month, birthday.day):
            age -= 1
        return age

    async def get_detail(self, patient_id: str) -> Optional[dict]:
        """获取患者详情（扩展版）"""
        result = await self.db.execute(
            select(Patient)
            .options(selectinload(Patient.user))
            .where(Patient.id == patient_id)
        )
        patient = result.unique().scalar_one_or_none()
        
        if not patient:
            return None
        
        user = patient.user
        
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
        
        # 查询最近就诊日期
        last_appointment = await self.db.execute(
            select(Appointment)
            .where(and_(
                Appointment.patient_id == patient_id,
                Appointment.status == 5
            ))
            .order_by(Appointment.complete_time.desc())
            .limit(1)
        )
        last_appt = last_appointment.scalar_one_or_none()
        last_visit_date = None
        if last_appt and last_appt.complete_time:
            last_visit_date = last_appt.complete_time.isoformat()
        
        # 查询家庭成员（同一用户下的所有就诊人）
        family_result = await self.db.execute(
            select(Patient)
            .where(Patient.user_id == patient.user_id)
            .order_by(Patient.is_default.desc(), Patient.created_at.asc())
        )
        family_members = family_result.scalars().all()
        
        family_data = []
        for member in family_members:
            member_appt_count = await self.db.scalar(
                select(func.count(Appointment.id)).where(Appointment.patient_id == member.id)
            )
            member_no_show = await self.db.scalar(
                select(func.count(Appointment.id)).where(
                    and_(
                        Appointment.patient_id == member.id,
                        Appointment.status == 7
                    )
                )
            )
            family_data.append({
                'id': member.id,
                'userId': member.user_id,
                'cardNo': member.card_no,
                'name': member.name,
                'phone': member.phone,
                'idCard': member.id_card,
                'gender': member.gender,
                'birthday': member.birthday.isoformat() if member.birthday else None,
                'relationship': member.relationship,
                'isDefault': member.is_default,
                'appointmentCount': member_appt_count or 0,
                'noShowCount': member_no_show or 0,
                'isBlacklist': user.status == 0 if user else False,
                'createdAt': member.created_at.isoformat() if member.created_at else None,
            })
        
        return {
            # 基本信息
            'id': patient.id,
            'userId': patient.user_id,
            'cardNo': patient.card_no,
            'name': patient.name,
            'phone': patient.phone,
            'gender': patient.gender,
            'province': patient.province,
            'city': patient.city,
            'district': patient.district,
            'street': patient.street,
            'idCardType': patient.id_card_type or 1,
            'idCard': patient.id_card,
            'ethnicity': patient.ethnicity or '汉族',
            'birthday': patient.birthday.isoformat() if patient.birthday else None,
            'age': self._calculate_age(patient.birthday),
            'relationship': patient.relationship,
            'address': patient.address,
            'source': patient.source or 1,
            'totalConsumption': float(patient.total_consumption or 0),
            'lastVisitDate': last_visit_date,
            'isBlacklist': user.status == 0 if user else False,
            'createdAt': patient.created_at.isoformat() if patient.created_at else None,
            
            # 用户信息
            'nickname': user.nickname if user else None,
            'points': user.points if user else 0,
            
            # 统计信息
            'statistics': {
                'appointmentCount': appointment_count or 0,
                'completedCount': completed_count or 0,
                'noShowCount': no_show_count or 0,
            },
            
            # 家庭成员
            'familyMembers': family_data,
        }

    async def update_patient(self, patient_id: str, data: PatientUpdate, operator_id: Optional[str] = None) -> Optional[dict]:
        """更新患者信息"""
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            return None
        
        # 更新非空字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(patient, key):
                setattr(patient, key, value)
        
        set_update_audit(patient, operator_id)
        await self.db.commit()
        await self.db.refresh(patient)
        
        return await self.get_detail(patient_id)

    async def get_appointments(
        self,
        patient_id: str,
        doctor_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[int] = None,
        is_admin_booked: Optional[bool] = None,
        is_follow_up: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        """获取患者预约记录"""
        query = select(Appointment).where(Appointment.patient_id == patient_id)
        conditions = [Appointment.patient_id == patient_id]
        
        if doctor_id:
            conditions.append(Appointment.doctor_id == doctor_id)
        
        if status is not None:
            conditions.append(Appointment.status == status)
        
        # 日期筛选需要关联 schedule 表
        if start_date or end_date:
            query = query.join(Schedule, Appointment.schedule_id == Schedule.id)
            if start_date:
                conditions.append(Schedule.schedule_date >= start_date)
            if end_date:
                conditions.append(Schedule.schedule_date <= end_date)
        
        query = query.where(and_(*conditions))
        
        # 统计总数
        count_conditions = conditions.copy()
        if start_date or end_date:
            count_query = select(func.count(Appointment.id)).join(Schedule, Appointment.schedule_id == Schedule.id)
        else:
            count_query = select(func.count(Appointment.id))
        count_query = count_query.where(and_(*count_conditions))
        total = await self.db.scalar(count_query)
        
        # 分页查询
        query = query.order_by(Appointment.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        appointments = result.scalars().all()
        
        appointment_data = []
        for appt in appointments:
            # 获取排班信息
            schedule = await self.db.get(Schedule, appt.schedule_id) if appt.schedule_id else None
            doctor = await self.db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
            department = await self.db.get(Department, doctor.department_id) if doctor and doctor.department_id else None
            store = await self.db.get(Store, doctor.store_id) if doctor and doctor.store_id else None
            
            appointment_data.append({
                'id': appt.id,
                'appointmentNo': appt.appointment_no,
                'storeName': store.name if store else None,
                'departmentName': department.name if department else None,
                'doctorId': appt.doctor_id,
                'doctorName': doctor.name if doctor else None,
                'scheduleDate': schedule.schedule_date.isoformat() if schedule and schedule.schedule_date else None,
                'startTime': str(schedule.start_time) if schedule and schedule.start_time else None,
                'endTime': str(schedule.end_time) if schedule and schedule.end_time else None,
                'queueNumber': appt.queue_number,
                'status': appt.status,
                'isAdminBooked': False,  # TODO: 需要添加字段支持
                'isFollowUp': False,  # TODO: 需要添加字段支持
                'createdAt': appt.created_at.isoformat() if appt.created_at else None,
            })
        
        return appointment_data, total or 0

    async def get_consumption_records(
        self,
        patient_id: str,
        item_name: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        """获取患者消费/项目记录"""
        # 目前消费记录关联预约，后续可扩展
        # 查询已完成的预约作为消费记录
        query = select(Appointment).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status == 5  # 已完成
            )
        )
        
        count_query = select(func.count(Appointment.id)).where(
            and_(
                Appointment.patient_id == patient_id,
                Appointment.status == 5
            )
        )
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Appointment.complete_time.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        appointments = result.scalars().all()
        
        records = []
        for appt in appointments:
            schedule = await self.db.get(Schedule, appt.schedule_id) if appt.schedule_id else None
            doctor = await self.db.get(Doctor, appt.doctor_id) if appt.doctor_id else None
            store = await self.db.get(Store, doctor.store_id) if doctor and doctor.store_id else None
            
            records.append({
                'id': appt.id,
                'orderNo': appt.appointment_no,
                'storeName': store.name if store else None,
                'itemName': f"{doctor.name if doctor else ''}诊疗" if doctor else '诊疗服务',
                'scheduleDate': schedule.schedule_date.isoformat() if schedule and schedule.schedule_date else None,
                'startTime': str(schedule.start_time) if schedule and schedule.start_time else None,
                'endTime': str(schedule.end_time) if schedule and schedule.end_time else None,
                'status': appt.status,
                'createdAt': appt.created_at.isoformat() if appt.created_at else None,
            })
        
        return records, total or 0

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
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[dict], int]:
        """获取黑名单列表"""
        # 查询被禁用用户的就诊人
        conditions = [User.status == 0]
        
        # 门店过滤
        if store_id:
            conditions.append(
                or_(Patient.store_id == store_id, Patient.store_id.is_(None))
            )
        
        query = select(Patient).join(User).where(and_(*conditions))
        count_query = select(func.count(Patient.id)).join(User).where(and_(*conditions))
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

    def _generate_card_no(self) -> str:
        """生成就诊卡编号"""
        import random
        import string
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"JZK{timestamp}{random_str}"

    async def create_patient(self, data: PatientCreateByAdmin, store_id: Optional[str] = None, operator_id: Optional[str] = None) -> dict:
        """创建患者（管理员手动添加）"""
        # 检查手机号是否已存在用户
        result = await self.db.execute(
            select(User).where(User.phone == data.phone)
        )
        user = result.scalar_one_or_none()
        
        if user:
            # 用户已存在，检查是否已有同名就诊人
            existing_patient = await self.db.execute(
                select(Patient).where(
                    and_(
                        Patient.user_id == user.id,
                        Patient.name == data.name
                    )
                )
            )
            if existing_patient.scalar_one_or_none():
                raise ValueError(f"该用户下已存在名为 {data.name} 的就诊人")
        else:
            # 创建新用户
            user = User(
                id=str(uuid.uuid4()),
                phone=data.phone,
                password_hash=get_password_hash("123456"),  # 默认密码
                nickname=data.name,
                status=1,
            )
            set_create_audit(user, operator_id)
            self.db.add(user)
            await self.db.flush()
        
        # 解析生日
        birthday = None
        if data.birthday:
            try:
                birthday = datetime.strptime(data.birthday, '%Y-%m-%d')
            except ValueError:
                pass
        
        # 创建就诊人
        patient = Patient(
            id=str(uuid.uuid4()),
            user_id=user.id,
            store_id=store_id,  # 关联门店
            name=data.name,
            phone=data.phone,
            id_card=data.id_card,
            gender=data.gender,
            birthday=birthday,
            relationship=data.relationship or "本人",
            is_default=data.is_default,
            card_no=self._generate_card_no(),
            province=data.province,
            city=data.city,
            district=data.district,
            street=data.street,
            id_card_type=data.id_card_type,
            ethnicity=data.ethnicity,
            address=data.address,
            source=2,  # 管理员添加
        )
        set_create_audit(patient, operator_id)
        self.db.add(patient)
        await self.db.commit()
        
        return await self.get_detail(patient.id)

    async def add_family_member(self, patient_id: str, data: FamilyMemberCreate, operator_id: Optional[str] = None) -> Optional[dict]:
        """为患者添加家庭成员（亲友）"""
        # 获取患者
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            return None
        
        # 检查是否已存在同名亲友
        existing = await self.db.execute(
            select(Patient).where(
                and_(
                    Patient.user_id == patient.user_id,
                    Patient.name == data.name
                )
            )
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"该用户下已存在名为 {data.name} 的就诊人")
        
        # 解析生日
        birthday = None
        if data.birthday:
            try:
                birthday = datetime.strptime(data.birthday, '%Y-%m-%d')
            except ValueError:
                pass
        
        # 创建亲友
        member = Patient(
            id=str(uuid.uuid4()),
            user_id=patient.user_id,
            name=data.name,
            phone=data.phone,
            id_card=data.id_card,
            gender=data.gender,
            birthday=birthday,
            relationship=data.relationship,
            is_default=data.is_default,
            card_no=self._generate_card_no(),
            province=data.province,
            city=data.city,
            district=data.district,
            street=data.street,
            id_card_type=data.id_card_type,
            ethnicity=data.ethnicity,
            address=data.address,
            source=2,  # 管理员添加
        )
        set_create_audit(member, operator_id)
        
        # 如果设为默认，取消其他默认
        if data.is_default:
            await self.db.execute(
                select(Patient).where(
                    and_(
                        Patient.user_id == patient.user_id,
                        Patient.is_default == True
                    )
                )
            )
            # 更新所有同用户的就诊人为非默认
            from sqlalchemy import update
            await self.db.execute(
                update(Patient).where(Patient.user_id == patient.user_id).values(is_default=False)
            )
        
        self.db.add(member)
        await self.db.commit()
        
        # 返回新增的成员信息
        return {
            'id': member.id,
            'userId': member.user_id,
            'cardNo': member.card_no,
            'name': member.name,
            'phone': member.phone,
            'idCard': member.id_card,
            'gender': member.gender,
            'birthday': member.birthday.isoformat() if member.birthday else None,
            'relationship': member.relationship,
            'isDefault': member.is_default,
            'appointmentCount': 0,
            'noShowCount': 0,
            'isBlacklist': False,
            'createdAt': member.created_at.isoformat() if member.created_at else None,
        }

    async def update_family_member(self, patient_id: str, member_id: str, data: PatientUpdate, operator_id: Optional[str] = None) -> Optional[dict]:
        """编辑家庭成员信息"""
        # 获取原患者确认用户
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            return None
        
        # 获取要编辑的成员
        result = await self.db.execute(
            select(Patient).where(
                and_(
                    Patient.id == member_id,
                    Patient.user_id == patient.user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            return None
        
        # 更新字段
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if hasattr(member, key):
                setattr(member, key, value)
        
        set_update_audit(member, operator_id)
        await self.db.commit()
        await self.db.refresh(member)
        
        # 返回更新后的信息
        return {
            'id': member.id,
            'userId': member.user_id,
            'cardNo': member.card_no,
            'name': member.name,
            'phone': member.phone,
            'idCard': member.id_card,
            'gender': member.gender,
            'birthday': member.birthday.isoformat() if member.birthday else None,
            'relationship': member.relationship,
            'isDefault': member.is_default,
            'createdAt': member.created_at.isoformat() if member.created_at else None,
        }

    async def delete_family_member(self, patient_id: str, member_id: str) -> bool:
        """删除家庭成员"""
        # 获取原患者确认用户
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id)
        )
        patient = result.scalar_one_or_none()
        
        if not patient:
            return False
        
        # 不能删除自己
        if patient_id == member_id:
            return False
        
        # 获取要删除的成员
        result = await self.db.execute(
            select(Patient).where(
                and_(
                    Patient.id == member_id,
                    Patient.user_id == patient.user_id
                )
            )
        )
        member = result.scalar_one_or_none()
        
        if not member:
            return False
        
        # 检查是否有预约记录
        appt_count = await self.db.scalar(
            select(func.count(Appointment.id)).where(Appointment.patient_id == member_id)
        )
        
        if appt_count and appt_count > 0:
            # 有预约记录，不能删除，只能软删除（这里选择直接返回失败，让前端提示）
            raise ValueError("该就诊人有预约记录，无法删除")
        
        # 删除成员
        await self.db.delete(member)
        await self.db.commit()
        
        return True
