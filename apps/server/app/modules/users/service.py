from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from datetime import datetime
import uuid
import random
import string

from app.models.user import User, Patient
from app.schemas.user import UserCreate, UserUpdate, PatientCreate, PatientUpdate
from app.core.security import get_password_hash, verify_password
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.audit import set_create_audit, set_update_audit
from app.common.account_sync import AccountSyncService

class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[User]:
        # 空值直接返回 None，避免查询 phone=NULL 的记录
        if not phone or not phone.strip():
            return None
        result = await self.db.execute(select(User).where(User.phone == phone))
        return result.scalar_one_or_none()

    async def get_by_openid(self, openid: str) -> Optional[User]:
        result = await self.db.execute(select(User).where(User.openid == openid))
        return result.scalar_one_or_none()

    async def get_by_unionid(self, unionid: str) -> Optional[User]:
        """通过 unionid 获取用户（跨应用关联）"""
        result = await self.db.execute(select(User).where(User.unionid == unionid))
        return result.scalar_one_or_none()

    async def update_wechat_info(self, user_id: str, data: dict, operator_id: Optional[str] = None) -> bool:
        """更新用户的微信信息

        Args:
            user_id: 用户ID
            data: 微信信息字典，可包含 unionid, nickname, avatar
            operator_id: 操作者ID
        """
        result = await self.db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return False

        # 更新 unionid
        if data.get("unionid") and not user.unionid:
            user.unionid = data["unionid"]

        # 更新微信昵称
        if data.get("nickname"):
            user.wechat_nickname = data["nickname"]
            # 如果用户没有设置昵称，使用微信昵称
            if not user.nickname or user.nickname == "微信用户":
                user.nickname = data["nickname"]

        # 更新微信头像
        if data.get("avatar"):
            user.wechat_avatar = data["avatar"]
            # 如果用户没有设置头像，使用微信头像
            if not user.avatar:
                user.avatar = data["avatar"]

        # 更新同步时间
        user.wechat_synced_at = datetime.now()

        set_update_audit(user, operator_id)
        await self.db.flush()

        # 双写同步: User -> accounts + account_users
        await AccountSyncService.sync_user_to_account(
            self.db, user_id, operator_id=operator_id
        )

        await self.db.commit()
        return True

    async def create(self, data: UserCreate) -> User:
        # 空字符串 phone 转为 None，避免唯一约束冲突
        phone = data.phone.strip() if data.phone else None
        phone = phone if phone else None  # 空字符串也转为 None

        from app.middleware.tenant_context import get_current_tenant_id
        tenant_id = get_current_tenant_id()

        user = User(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            phone=phone,
            password_hash=get_password_hash(data.password) if data.password else "",
            openid=data.openid,
            unionid=data.unionid,
            nickname=data.nickname or "微信用户",
            avatar=data.avatar or "",
            wechat_nickname=data.nickname if data.openid else None,
            wechat_avatar=data.avatar if data.openid else None,
            wechat_synced_at=datetime.now() if data.openid else None,
            status=1
        )
        set_create_audit(user, None)
        self.db.add(user)
        await self.db.flush()

        # 双写同步: User -> accounts + account_users
        await AccountSyncService.sync_user_to_account(
            self.db, user.id, operator_id=None
        )

        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def update(self, user_id: str, data: UserUpdate, operator_id: Optional[str] = None) -> Optional[User]:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(user, field, value)

        set_update_audit(user, operator_id)
        await self.db.flush()

        # 双写同步: User -> accounts + account_users
        await AccountSyncService.sync_user_to_account(
            self.db, user_id, operator_id=operator_id
        )

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

    async def change_password(self, user_id: str, old_password: str, new_password: str) -> tuple[bool, str]:
        """修改密码"""
        user = await self.get_by_id(user_id)
        if not user:
            return False, "用户不存在"

        # 验证旧密码（如果有密码）
        if user.password_hash and not verify_password(old_password, user.password_hash):
            return False, "原密码错误"

        # 设置新密码
        user.password_hash = get_password_hash(new_password)
        set_update_audit(user, user_id)
        await self.db.flush()

        # 双写同步: 密码变更同步到 accounts
        await AccountSyncService.sync_user_to_account(
            self.db, user_id, operator_id=user_id
        )

        await self.db.commit()
        return True, "密码修改成功"

    async def bind_phone(self, user_id: str, phone: str) -> tuple[bool, str]:
        """绑定/更换手机号"""
        user = await self.get_by_id(user_id)
        if not user:
            return False, "用户不存在"

        # 检查手机号是否已被使用
        existing = await self.get_by_phone(phone)
        if existing and existing.id != user_id:
            return False, "该手机号已被其他用户绑定"

        user.phone = phone
        set_update_audit(user, user_id)
        await self.db.flush()

        # 双写同步: 手机号变更同步到 accounts
        await AccountSyncService.sync_user_to_account(
            self.db, user_id, operator_id=user_id
        )

        await self.db.commit()
        return True, "手机号绑定成功"


class PatientService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _generate_card_no(self) -> str:
        """生成就诊卡编号"""
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        random_str = ''.join(random.choices(string.digits, k=4))
        return f"JZK{timestamp}{random_str}"

    async def get_by_id(self, patient_id: str) -> Optional[Patient]:
        result = await self.db.execute(select(Patient).where(Patient.id == patient_id))
        return result.scalar_one_or_none()

    async def get_by_id_and_user(self, patient_id: str, user_id: str) -> Optional[Patient]:
        """获取指定用户的就诊人详情"""
        result = await self.db.execute(
            select(Patient).where(Patient.id == patient_id, Patient.user_id == user_id)
        )
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
            tenant_id=get_current_tenant_id(),
            user_id=user_id,
            name=data.name,
            phone=data.phone,
            id_card=data.id_card,
            gender=data.gender,
            relationship=data.relationship,
            is_default=is_default,
            card_no=self._generate_card_no(),
        )
        set_create_audit(patient, user_id)
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

        set_update_audit(patient, user_id)
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
