"""认证服务单元测试

测试用户登录、注册、修改密码、微信登录等功能。
"""

import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from fastapi import HTTPException

from app.modules.users.service import UserService
from app.schemas.user import UserCreate
from app.models.user import User
from app.core.security import verify_password


@pytest.mark.unit
class TestUserServiceQuery:
    """用户查询服务测试"""

    async def test_get_by_id(self, db_session, test_user):
        """测试通过ID获取用户"""
        service = UserService(db_session)
        user = await service.get_by_id(test_user.id)

        assert user is not None
        assert user.id == test_user.id
        assert user.phone == "13800138001"

    async def test_get_by_id_not_found(self, db_session):
        """测试获取不存在的用户"""
        service = UserService(db_session)
        user = await service.get_by_id(str(uuid4()))
        assert user is None

    async def test_get_by_phone(self, db_session, test_user):
        """测试通过手机号获取用户"""
        service = UserService(db_session)
        user = await service.get_by_phone("13800138001")

        assert user is not None
        assert user.phone == "13800138001"

    async def test_get_by_phone_not_found(self, db_session):
        """测试获取不存在的手机号"""
        service = UserService(db_session)
        user = await service.get_by_phone("19999999999")
        assert user is None

    async def test_get_by_phone_empty(self, db_session):
        """测试空手机号查询"""
        service = UserService(db_session)
        user = await service.get_by_phone("")
        assert user is None

        user = await service.get_by_phone("   ")
        assert user is None

    async def test_get_by_openid(self, db_session, test_user):
        """测试通过openid获取用户"""
        test_user.openid = "wx_openid_123"
        await db_session.commit()

        service = UserService(db_session)
        user = await service.get_by_openid("wx_openid_123")

        assert user is not None
        assert user.openid == "wx_openid_123"

    async def test_get_by_openid_not_found(self, db_session):
        """测试获取不存在的openid"""
        service = UserService(db_session)
        user = await service.get_by_openid("not_exist_openid")
        assert user is None

    async def test_get_by_unionid(self, db_session, test_user):
        """测试通过unionid获取用户"""
        test_user.unionid = "wx_unionid_123"
        await db_session.commit()

        service = UserService(db_session)
        user = await service.get_by_unionid("wx_unionid_123")

        assert user is not None
        assert user.unionid == "wx_unionid_123"

    async def test_get_by_unionid_not_found(self, db_session):
        """测试获取不存在的unionid"""
        service = UserService(db_session)
        user = await service.get_by_unionid("not_exist_unionid")
        assert user is None


@pytest.mark.unit
class TestUserServiceMutation:
    """用户变更服务测试"""

    async def test_create_user(self, db_session, test_tenant):
        """测试创建用户"""
        from app.middleware.tenant_context import set_tenant_context
        service = UserService(db_session)
        data = UserCreate(
            phone="13900139000",
            password="password123",
            nickname="新用户",
        )

        # 设置租户上下文
        token = set_tenant_context(test_tenant.id)
        user = await service.create(data)
        set_tenant_context(None)  # 清理上下文

        assert user.phone == "13900139000"
        assert user.nickname == "新用户"
        # UserCreate不包含gender字段，所以默认是0
        assert user.gender == 0
        assert user.password_hash is not None
        assert user.status == 1

    async def test_create_user_with_empty_phone(self, db_session):
        """测试创建空手机号用户（微信用户）"""
        service = UserService(db_session)
        data = UserCreate(
            phone="",
            password="",
            openid="wx_openid_456",
            nickname="微信用户",
        )

        user = await service.create(data)

        assert user.phone is None
        assert user.openid == "wx_openid_456"
        assert user.nickname == "微信用户"

    async def test_create_user_with_wechat(self, db_session):
        """测试创建微信用户"""
        service = UserService(db_session)
        data = UserCreate(
            phone="",
            password="",
            openid="wx_openid_789",
            unionid="wx_unionid_789",
            nickname="微信用户",
            avatar="https://example.com/avatar.jpg",
        )

        user = await service.create(data)

        assert user.openid == "wx_openid_789"
        assert user.unionid == "wx_unionid_789"
        assert user.wechat_nickname == "微信用户"
        assert user.wechat_avatar == "https://example.com/avatar.jpg"
        assert user.wechat_synced_at is not None

    async def test_update_user(self, db_session, test_user):
        """测试更新用户"""
        from app.schemas.user import UserUpdate

        service = UserService(db_session)
        data = UserUpdate(nickname="更新后的昵称")

        user = await service.update(test_user.id, data)

        assert user is not None
        assert user.nickname == "更新后的昵称"

    async def test_update_user_not_found(self, db_session):
        """测试更新不存在的用户"""
        from app.schemas.user import UserUpdate

        service = UserService(db_session)
        data = UserUpdate(nickname="新昵称")

        user = await service.update(str(uuid4()), data)

        assert user is None

    async def test_update_wechat_info(self, db_session, test_user):
        """测试更新微信信息"""
        service = UserService(db_session)
        data = {
            "unionid": "wx_unionid_new",
            "nickname": "微信昵称",
            "avatar": "https://example.com/new_avatar.jpg",
        }

        result = await service.update_wechat_info(test_user.id, data)

        assert result is True

        await db_session.refresh(test_user)
        assert test_user.unionid == "wx_unionid_new"
        assert test_user.wechat_nickname == "微信昵称"
        assert test_user.wechat_avatar == "https://example.com/new_avatar.jpg"
        assert test_user.wechat_synced_at is not None

    async def test_update_wechat_info_not_found(self, db_session):
        """测试更新不存在的用户微信信息"""
        service = UserService(db_session)
        data = {"nickname": "微信昵称"}

        result = await service.update_wechat_info(str(uuid4()), data)

        assert result is False

    async def test_update_wechat_info_update_nickname(self, db_session, test_user):
        """测试更新微信信息时同步昵称"""
        service = UserService(db_session)
        data = {"nickname": "新微信昵称"}

        await service.update_wechat_info(test_user.id, data)
        await db_session.refresh(test_user)

        # 如果用户昵称为空或默认值，应该同步更新
        assert test_user.wechat_nickname == "新微信昵称"

    async def test_update_wechat_info_update_avatar(self, db_session, test_user):
        """测试更新微信信息时同步头像"""
        service = UserService(db_session)
        data = {"avatar": "https://example.com/avatar.jpg"}

        await service.update_wechat_info(test_user.id, data)
        await db_session.refresh(test_user)

        assert test_user.wechat_avatar == "https://example.com/avatar.jpg"


@pytest.mark.unit
class TestUserServiceAuth:
    """用户认证相关测试"""

    async def test_authenticate_success(self, db_session, test_user):
        """测试认证成功"""
        from app.core.security import get_password_hash

        # 设置密码
        test_user.password_hash = get_password_hash("password123")
        await db_session.commit()

        service = UserService(db_session)
        user = await service.authenticate("13800138001", "password123")

        assert user is not None
        assert user.phone == "13800138001"

    async def test_authenticate_wrong_password(self, db_session, test_user):
        """测试认证失败（错误密码）"""
        from app.core.security import get_password_hash

        test_user.password_hash = get_password_hash("password123")
        await db_session.commit()

        service = UserService(db_session)
        user = await service.authenticate("13800138001", "wrong_password")

        assert user is None

    async def test_authenticate_not_found(self, db_session):
        """测试认证失败（用户不存在）"""
        service = UserService(db_session)
        user = await service.authenticate("19999999999", "password")
        assert user is None

    async def test_authenticate_user_without_password(self, db_session, test_user):
        """测试无密码账号不会触发密码校验异常"""
        test_user.password_hash = ""
        await db_session.commit()

        service = UserService(db_session)
        user = await service.authenticate("13800138001", "any_password")

        assert user is None

    async def test_change_password_success(self, db_session, test_user):
        """测试修改密码成功"""
        from app.core.security import get_password_hash

        test_user.password_hash = get_password_hash("old_password")
        await db_session.commit()

        service = UserService(db_session)
        success, message = await service.change_password(
            test_user.id, "old_password", "new_password123"
        )

        assert success is True
        assert "成功" in message

        # 验证新密码
        await db_session.refresh(test_user)
        assert verify_password("new_password123", test_user.password_hash)

    async def test_change_password_user_not_found(self, db_session):
        """测试修改密码（用户不存在）"""
        service = UserService(db_session)
        success, message = await service.change_password(
            str(uuid4()), "old_password", "new_password"
        )

        assert success is False
        assert "不存在" in message

    async def test_change_password_wrong_old_password(self, db_session, test_user):
        """测试修改密码（旧密码错误）"""
        from app.core.security import get_password_hash

        test_user.password_hash = get_password_hash("correct_password")
        await db_session.commit()

        service = UserService(db_session)
        success, message = await service.change_password(
            test_user.id, "wrong_password", "new_password"
        )

        # 当用户有密码哈希时，验证旧密码会失败
        assert success is False
        # 错误消息可能是"原密码错误"或"旧密码错误"
        assert "密码错误" in message or "错误" in message

    async def test_change_password_no_old_password(self, db_session, test_user):
        """测试修改密码（没有旧密码）"""
        # 用户没有设置密码
        test_user.password_hash = ""
        await db_session.commit()

        service = UserService(db_session)
        success, message = await service.change_password(
            test_user.id, "", "new_password"
        )

        assert success is True
        assert "成功" in message

    async def test_bind_phone_success(self, db_session, test_user):
        """测试绑定手机号成功"""
        service = UserService(db_session)
        success, message = await service.bind_phone(test_user.id, "13900139000")

        assert success is True
        assert "成功" in message

        await db_session.refresh(test_user)
        assert test_user.phone == "13900139000"

    async def test_bind_phone_user_not_found(self, db_session):
        """测试绑定手机号（用户不存在）"""
        service = UserService(db_session)
        success, message = await service.bind_phone(str(uuid4()), "13900139000")

        assert success is False
        assert "不存在" in message

    async def test_bind_phone_already_used(self, db_session, test_tenant, test_user):
        """测试绑定已被使用的手机号"""
        # 创建另一个用户
        other_user = User(
            id=str(uuid4()),
            phone="13900139000",
            password_hash="hash",
            nickname="其他用户",
            tenant_id=test_tenant.id,
            status=1,
            created_at=test_user.created_at,
        )
        db_session.add(other_user)
        await db_session.commit()

        service = UserService(db_session)
        success, message = await service.bind_phone(test_user.id, "13900139000")

        assert success is False
        assert "已被其他用户绑定" in message

    async def test_bind_phone_update_own(self, db_session, test_user):
        """测试更新自己的手机号"""
        service = UserService(db_session)
        success, message = await service.bind_phone(test_user.id, "13900139000")

        assert success is True

        # 再次绑定同一手机号应该成功（自己的手机号）
        success, message = await service.bind_phone(test_user.id, "13900139001")
        assert success is True


@pytest.mark.unit
class TestPatientService:
    """就诊人服务测试"""

    async def test_get_by_id(self, db_session, test_patient):
        """测试通过ID获取就诊人"""
        from app.modules.users.service import PatientService

        service = PatientService(db_session)
        patient = await service.get_by_id(test_patient.id)

        assert patient is not None
        assert patient.id == test_patient.id
        assert patient.name == "测试就诊人"

    async def test_get_by_id_and_user(self, db_session, test_user, test_patient):
        """测试获取指定用户的就诊人详情"""
        from app.modules.users.service import PatientService

        service = PatientService(db_session)
        patient = await service.get_by_id_and_user(test_patient.id, test_user.id)

        assert patient is not None
        assert patient.user_id == test_user.id

    async def test_get_by_id_and_user_wrong_user(self, db_session, test_user, test_patient):
        """测试获取其他用户的就诊人"""
        from app.modules.users.service import PatientService

        service = PatientService(db_session)
        patient = await service.get_by_id_and_user(test_patient.id, str(uuid4()))

        assert patient is None

    async def test_get_by_user_id(self, db_session, test_user, test_patient):
        """测试获取用户的所有就诊人"""
        from app.modules.users.service import PatientService

        service = PatientService(db_session)
        patients = await service.get_by_user_id(test_user.id)

        assert len(patients) >= 1
        assert all(p.user_id == test_user.id for p in patients)

    async def test_create_patient(self, db_session, test_user, test_tenant):
        """测试创建就诊人"""
        from app.middleware.tenant_context import set_tenant_context
        from app.modules.users.service import PatientService
        from app.schemas.user import PatientCreate

        service = PatientService(db_session)
        data = PatientCreate(
            name="新就诊人",
            phone="13900139000",
            id_card="110101199001011234",
            gender=1,
            relationship="本人",  # relationship是字符串类型
        )

        # 设置租户上下文
        token = set_tenant_context(test_tenant.id)
        patient = await service.create(test_user.id, data)
        set_tenant_context(None)  # 清理上下文

        assert patient.name == "新就诊人"
        assert patient.phone == "13900139000"
        assert patient.user_id == test_user.id
        assert patient.is_default is True  # 第一个就诊人自动设为默认
        assert patient.card_no.startswith("JZK")

    async def test_create_patient_not_first_set_default(self, db_session, test_user, test_patient):
        """测试创建就诊人（非第一个，可设置默认）"""
        from app.modules.users.service import PatientService
        from app.schemas.user import PatientCreate

        service = PatientService(db_session)
        data = PatientCreate(
            name="第二个就诊人",
            phone="13900139001",
            is_default=True,
        )

        patient = await service.create(test_user.id, data)

        assert patient.is_default is True

        # 之前的就诊人应该被取消默认
        await db_session.refresh(test_patient)
        assert test_patient.is_default is False

    async def test_update_patient(self, db_session, test_user, test_patient):
        """测试更新就诊人"""
        from app.modules.users.service import PatientService
        from app.schemas.user import PatientUpdate

        service = PatientService(db_session)
        data = PatientUpdate(name="更新后的就诊人")

        patient = await service.update(test_patient.id, test_user.id, data)

        assert patient is not None
        assert patient.name == "更新后的就诊人"

    async def test_update_patient_not_found(self, db_session, test_user):
        """测试更新不存在的就诊人"""
        from app.modules.users.service import PatientService
        from app.schemas.user import PatientUpdate

        service = PatientService(db_session)
        data = PatientUpdate(name="新名称")

        patient = await service.update(str(uuid4()), test_user.id, data)

        assert patient is None

    async def test_delete_patient(self, db_session, test_user, test_patient):
        """测试删除就诊人"""
        from app.modules.users.service import PatientService

        service = PatientService(db_session)
        result = await service.delete(test_patient.id, test_user.id)

        assert result is True

    async def test_delete_patient_wrong_user(self, db_session, test_user, test_patient):
        """测试删除其他用户的就诊人"""
        from app.modules.users.service import PatientService

        service = PatientService(db_session)
        result = await service.delete(test_patient.id, str(uuid4()))

        assert result is False
