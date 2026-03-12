"""
Patients 模块黑名单功能单元测试

测试 PatientManageService 的黑名单相关方法：
- add_to_blacklist: 将患者加入黑名单（设置 User.status = 0）
- remove_from_blacklist: 将患者移出黑名单（设置 User.status = 1）
- get_blacklist: 获取黑名单列表（支持门店筛选和分页）
"""

import pytest
from datetime import datetime
from uuid import uuid4
from sqlalchemy import select

from app.models.user import User, Patient
from app.models.store import Store
from app.modules.patients.service_manage import PatientManageService


class TestAddToBlacklist:
    """测试加入黑名单功能"""

    @pytest.mark.asyncio
    async def test_add_to_blacklist_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功加入黑名单"""
        # 确保用户初始状态为正常
        assert test_user.status == 1

        service = PatientManageService(db_session)
        result = await service.add_to_blacklist(test_patient.id, reason="测试加入黑名单")

        assert result is True

        # 验证 User.status 已设置为 0
        refreshed_user = await db_session.scalar(
            select(User).where(User.id == test_user.id)
        )
        assert refreshed_user.status == 0

    @pytest.mark.asyncio
    async def test_add_to_blacklist_patient_not_found(self, db_session):
        """患者不存在时返回 False"""
        service = PatientManageService(db_session)
        non_existent_id = str(uuid4())

        result = await service.add_to_blacklist(non_existent_id, reason="测试")

        assert result is False

    @pytest.mark.asyncio
    async def test_add_to_blacklist_no_user(self, db_session):
        """患者无关联用户时返回 False"""
        # 创建一个没有关联用户的就诊人记录（user_id 指向不存在的用户）
        patient = Patient(
            id=str(uuid4()),
            user_id=str(uuid4()),  # 不存在的用户ID
            name="无关联用户患者",
            phone="13900000001",
            id_card="110101199001011111",
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(patient)
        await db_session.commit()

        service = PatientManageService(db_session)
        result = await service.add_to_blacklist(patient.id, reason="测试")

        # 由于 selectinload(Patient.user) 会返回 None，所以返回 False
        assert result is False


class TestRemoveFromBlacklist:
    """测试移出黑名单功能"""

    @pytest.mark.asyncio
    async def test_remove_from_blacklist_success(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """成功移出黑名单"""
        # 先将用户加入黑名单
        test_user.status = 0
        await db_session.commit()

        service = PatientManageService(db_session)
        result = await service.remove_from_blacklist(test_patient.id)

        assert result is True

        # 验证 User.status 已恢复为 1
        refreshed_user = await db_session.scalar(
            select(User).where(User.id == test_user.id)
        )
        assert refreshed_user.status == 1

    @pytest.mark.asyncio
    async def test_remove_from_blacklist_patient_not_found(self, db_session):
        """患者不存在时返回 False"""
        service = PatientManageService(db_session)
        non_existent_id = str(uuid4())

        result = await service.remove_from_blacklist(non_existent_id)

        assert result is False

    @pytest.mark.asyncio
    async def test_remove_from_blacklist_no_user(self, db_session):
        """患者无关联用户时返回 False"""
        patient = Patient(
            id=str(uuid4()),
            user_id=str(uuid4()),  # 不存在的用户ID
            name="无关联用户患者",
            phone="13900000002",
            id_card="110101199001012222",
            is_default=True,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(patient)
        await db_session.commit()

        service = PatientManageService(db_session)
        result = await service.remove_from_blacklist(patient.id)

        assert result is False


class TestGetBlacklist:
    """测试获取黑名单列表功能"""

    @pytest.mark.asyncio
    async def test_get_blacklist_with_store_filter(
        self,
        db_session,
        test_store,
        test_user,
        test_patient,
    ):
        """按门店筛选黑名单"""
        # 将用户加入黑名单
        test_user.status = 0
        # 设置患者的门店
        test_patient.store_id = test_store.id
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_blacklist(store_id=test_store.id)

        assert total >= 1
        # 验证返回的患者在黑名单中
        found_patient = next((p for p in items if p["id"] == test_patient.id), None)
        assert found_patient is not None
        assert found_patient["name"] == test_patient.name

    @pytest.mark.asyncio
    async def test_get_blacklist_pagination(
        self,
        db_session,
        test_store,
    ):
        """分页查询黑名单"""
        # 创建多个黑名单用户
        for i in range(15):
            user = User(
                id=str(uuid4()),
                phone=f"1390001000{i:02d}",
                password_hash="test_hash",
                nickname=f"黑名单用户{i}",
                status=0,  # 黑名单状态
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(user)
            await db_session.flush()

            patient = Patient(
                id=str(uuid4()),
                user_id=user.id,
                store_id=test_store.id,
                name=f"黑名单患者{i}",
                phone=f"1390002000{i:02d}",
                id_card=f"1101011990010133{i:02d}",
                is_default=True,
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            db_session.add(patient)

        await db_session.commit()

        service = PatientManageService(db_session)

        # 测试第一页
        items_page1, total = await service.get_blacklist(page=1, page_size=10)
        assert total >= 15
        assert len(items_page1) == 10

        # 测试第二页
        items_page2, _ = await service.get_blacklist(page=2, page_size=10)
        assert len(items_page2) >= 5

    @pytest.mark.asyncio
    async def test_get_blacklist_empty(self, db_session):
        """黑名单为空时返回空列表"""
        service = PatientManageService(db_session)
        items, total = await service.get_blacklist()

        assert total == 0
        assert items == []

    @pytest.mark.asyncio
    async def test_get_blacklist_excludes_normal_users(
        self,
        db_session,
        test_store,
        test_user,
        test_patient,
    ):
        """黑名单列表不包含正常状态用户"""
        # 确保用户是正常状态
        test_user.status = 1
        test_patient.store_id = test_store.id
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_blacklist(store_id=test_store.id)

        # 正常用户不应出现在黑名单中
        found_patient = next((p for p in items if p["id"] == test_patient.id), None)
        assert found_patient is None


class TestBlacklistIntegrationWithPatientList:
    """测试黑名单与患者列表的集成"""

    @pytest.mark.asyncio
    async def test_patient_list_shows_blacklist_status(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """患者列表中正确显示黑名单状态"""
        # 将用户加入黑名单
        test_user.status = 0
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_list()

        assert total >= 1
        # 查找测试患者
        found_patient = next((p for p in items if p["id"] == test_patient.id), None)
        assert found_patient is not None
        assert found_patient["isBlacklist"] is True

    @pytest.mark.asyncio
    async def test_patient_list_filter_by_blacklist_true(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """患者列表按黑名单筛选（只显示黑名单）"""
        # 将用户加入黑名单
        test_user.status = 0
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_list(is_blacklist=True)

        # 所有返回的患者都应该是黑名单用户
        for item in items:
            assert item["isBlacklist"] is True

    @pytest.mark.asyncio
    async def test_patient_list_filter_by_blacklist_false(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """患者列表按黑名单筛选（只显示非黑名单）"""
        # 确保用户是正常状态
        test_user.status = 1
        await db_session.commit()

        service = PatientManageService(db_session)
        items, total = await service.get_list(is_blacklist=False)

        # 所有返回的患者都不应该是黑名单用户
        for item in items:
            assert item["isBlacklist"] is False

    @pytest.mark.asyncio
    async def test_blacklist_status_after_add_and_remove(
        self,
        db_session,
        test_user,
        test_patient,
    ):
        """测试加入黑名单后再移出的状态变化"""
        service = PatientManageService(db_session)

        # 初始状态：正常
        assert test_user.status == 1
        items, _ = await service.get_list()
        found = next((p for p in items if p["id"] == test_patient.id), None)
        assert found["isBlacklist"] is False

        # 加入黑名单
        await service.add_to_blacklist(test_patient.id)
        await db_session.refresh(test_user)
        assert test_user.status == 0

        items, _ = await service.get_list()
        found = next((p for p in items if p["id"] == test_patient.id), None)
        assert found["isBlacklist"] is True

        # 移出黑名单
        await service.remove_from_blacklist(test_patient.id)
        await db_session.refresh(test_user)
        assert test_user.status == 1

        items, _ = await service.get_list()
        found = next((p for p in items if p["id"] == test_patient.id), None)
        assert found["isBlacklist"] is False
