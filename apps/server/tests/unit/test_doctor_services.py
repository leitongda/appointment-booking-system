"""医生模块服务单元测试 — 边界条件与补充覆盖

覆盖不在 test_doctor_service.py 中的场景:
- get_list 状态过滤 + 组合过滤 + 分页
- get_recommended / get_by_department 的 store_id 过滤
- get_doctors_availability 边界 (空列表、无排班、排班已满)
- get_by_phone / get_by_username strict_tenant 多租户冲突
- authenticate 通过用户名登录
- create 不带电话号码 (不创建 User)
- delete 软删除幂等性
- batch_update_sort_order 异常输入
- 状态转换 (启用 -> 禁用 -> 启用)
"""

import pytest
from datetime import date, datetime, time, timedelta
from unittest.mock import AsyncMock, patch
from uuid import uuid4

from app.modules.doctors.service import DoctorService
from app.schemas.doctor import DoctorCreate, DoctorUpdate
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.appointment import Appointment
from app.core.security import get_password_hash, verify_password


@pytest.mark.unit
class TestDoctorServiceEdgeCases:
    """医生服务边界条件测试"""

    # ------------------------------------------------------------------ #
    # get_list: 状态过滤 + 组合过滤 + 分页
    # ------------------------------------------------------------------ #

    async def test_get_list_filter_by_status(self, db_session, test_doctor):
        """按状态过滤: 只返回 status=1 的医生"""
        # 创建一个禁用医生
        disabled = Doctor(
            id=str(uuid4()),
            name="禁用医生",
            department_id=test_doctor.department_id,
            store_id=test_doctor.store_id,
            tenant_id=test_doctor.tenant_id,
            status=0,
            created_at=test_doctor.created_at,
            updated_at=test_doctor.updated_at,
        )
        db_session.add(disabled)
        await db_session.commit()

        service = DoctorService(db_session)
        # status=1: 只拿到启用的
        doctors, total = await service.get_list(status=1)
        assert all(d.status == 1 for d in doctors)
        assert disabled.id not in [d.id for d in doctors]

        # status=0: 只拿到禁用的
        doctors, total = await service.get_list(status=0)
        assert all(d.status == 0 for d in doctors)
        assert test_doctor.id not in [d.id for d in doctors]

    async def test_get_list_combined_filters(self, db_session, test_doctor):
        """多条件组合过滤: name + department_id + status"""
        service = DoctorService(db_session)
        doctors, total = await service.get_list(
            name="测试",
            department_id=test_doctor.department_id,
            status=1,
        )
        assert total >= 1
        assert all(
            d.name == "测试医生"
            and d.department_id == test_doctor.department_id
            and d.status == 1
            for d in doctors
        )

    async def test_get_list_name_no_match(self, db_session, test_doctor):
        """名称搜索无匹配结果"""
        service = DoctorService(db_session)
        doctors, total = await service.get_list(name="不存在的医生名字XYZ")
        assert total == 0
        assert doctors == []

    async def test_get_list_pagination(self, db_session, test_doctor):
        """分页: page_size=1 时每页只返回1条"""
        # 再创建一条
        extra = Doctor(
            id=str(uuid4()),
            name="分页测试医生",
            department_id=test_doctor.department_id,
            store_id=test_doctor.store_id,
            tenant_id=test_doctor.tenant_id,
            status=1,
            sort_order=10,
            created_at=test_doctor.created_at,
            updated_at=test_doctor.updated_at,
        )
        db_session.add(extra)
        await db_session.commit()

        service = DoctorService(db_session)
        doctors_p1, total = await service.get_list(page=1, page_size=1)
        assert len(doctors_p1) == 1
        assert total >= 2

        doctors_p2, _ = await service.get_list(page=2, page_size=1)
        assert len(doctors_p2) == 1
        assert doctors_p1[0].id != doctors_p2[0].id

    # ------------------------------------------------------------------ #
    # get_recommended: store_id 过滤
    # ------------------------------------------------------------------ #

    async def test_get_recommended_filter_by_store(self, db_session, test_tenant, test_doctor, test_store):
        """推荐医生: 按 store_id 过滤"""
        # 设置推荐
        test_doctor.is_recommended = 1
        await db_session.commit()

        service = DoctorService(db_session)
        # 指定正确门店 -> 能找到
        doctors = await service.get_recommended(store_id=test_store.id)
        assert any(d.id == test_doctor.id for d in doctors)

        # 指定不存在的门店 -> 找不到
        doctors = await service.get_recommended(store_id=str(uuid4()))
        assert not any(d.id == test_doctor.id for d in doctors)

    async def test_get_recommended_respects_limit(self, db_session, test_tenant, test_doctor):
        """推荐医生: limit 生效"""
        test_doctor.is_recommended = 1
        await db_session.commit()

        service = DoctorService(db_session)
        doctors = await service.get_recommended(limit=1)
        assert len(doctors) <= 1

    # ------------------------------------------------------------------ #
    # get_by_department: store_id 过滤
    # ------------------------------------------------------------------ #

    async def test_get_by_department_with_store_filter(self, db_session, test_doctor, test_store):
        """按科室查询医生: 叠加 store_id 过滤"""
        service = DoctorService(db_session)
        doctors = await service.get_by_department(
            test_doctor.department_id, store_id=test_store.id
        )
        assert all(
            d.department_id == test_doctor.department_id and d.store_id == test_store.id
            for d in doctors
        )

    async def test_get_by_department_wrong_store(self, db_session, test_doctor):
        """按科室查询医生: 错误的 store_id 返回空"""
        service = DoctorService(db_session)
        doctors = await service.get_by_department(
            test_doctor.department_id, store_id=str(uuid4())
        )
        assert doctors == []

    # ------------------------------------------------------------------ #
    # get_doctors_availability: 边界场景
    # ------------------------------------------------------------------ #

    async def test_get_doctors_availability_empty_list(self, db_session):
        """空医生列表 -> 返回空字典"""
        service = DoctorService(db_session)
        result = await service.get_doctors_availability([])
        assert result == {}

    async def test_get_doctors_availability_no_schedules(self, db_session, test_doctor):
        """医生没有排班 -> 全部返回 False"""
        service = DoctorService(db_session)
        result = await service.get_doctors_availability([test_doctor.id], days=7)
        assert result == {test_doctor.id: False}

    async def test_get_doctors_availability_full_schedule(
        self, db_session, test_tenant, test_doctor, test_store
    ):
        """排班已满 (booked_slots == total_slots) -> 该医生返回 False"""
        tomorrow = date.today() + timedelta(days=1)
        schedule = Schedule(
            id=str(uuid4()),
            doctor_id=test_doctor.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            schedule_date=tomorrow,
            time_slot="morning",
            start_time=time(8, 0),
            end_time=time(12, 0),
            total_slots=5,
            booked_slots=5,  # 已满
            status=1,
            created_at=test_doctor.created_at,
            updated_at=test_doctor.updated_at,
        )
        db_session.add(schedule)
        await db_session.commit()

        service = DoctorService(db_session)
        result = await service.get_doctors_availability([test_doctor.id], days=7)
        assert result[test_doctor.id] is False

    # ------------------------------------------------------------------ #
    # get_by_phone / get_by_username: strict_tenant 多租户冲突
    # ------------------------------------------------------------------ #

    async def test_get_by_phone_strict_tenant_multi_tenant_conflict(
        self, db_session, test_doctor
    ):
        """strict_tenant 模式下, 同手机号出现在多个租户 -> 抛出 ValueError"""
        # 创建第二个租户的同手机号医生
        from app.models.tenant import Tenant, SubscriptionPlan
        from app.models.store import Store as StoreModel

        plan2 = SubscriptionPlan(
            id=str(uuid4()), plan_code="p2", name="P2", status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(plan2)
        await db_session.flush()
        tenant2 = Tenant(
            id=str(uuid4()), tenant_code="t2", name="T2", status=1,
            subscription_plan_id=plan2.id,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(tenant2)
        await db_session.flush()
        store2 = StoreModel(
            id=str(uuid4()), name="S2", address="A2", phone="0",
            tenant_id=tenant2.id, status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(store2)
        await db_session.flush()

        shared_phone = "13800009999"
        # 给 test_doctor 设置手机号
        test_doctor.phone = shared_phone
        # 创建第二个租户的同手机号医生
        d2 = Doctor(
            id=str(uuid4()), name="D2", phone=shared_phone,
            department_id=test_doctor.department_id,
            store_id=store2.id, tenant_id=tenant2.id, status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(d2)
        await db_session.commit()

        service = DoctorService(db_session)
        # 无租户上下文 + strict_tenant -> 冲突异常
        with patch("app.modules.doctors.service_query.get_current_tenant_id", return_value=None):
            with pytest.raises(ValueError, match="检测到多个租户医生账号"):
                await service.get_by_phone(shared_phone, strict_tenant=True)

    async def test_get_by_username_strict_tenant_multi_tenant_conflict(
        self, db_session, test_doctor
    ):
        """strict_tenant 模式下, 同用户名出现在多个租户 -> 抛出 ValueError"""
        from app.models.tenant import Tenant, SubscriptionPlan
        from app.models.store import Store as StoreModel

        plan2 = SubscriptionPlan(
            id=str(uuid4()), plan_code="p3", name="P3", status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(plan2)
        await db_session.flush()
        tenant2 = Tenant(
            id=str(uuid4()), tenant_code="t3", name="T3", status=1,
            subscription_plan_id=plan2.id,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(tenant2)
        await db_session.flush()
        store2 = StoreModel(
            id=str(uuid4()), name="S3", address="A3", phone="0",
            tenant_id=tenant2.id, status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(store2)
        await db_session.flush()

        shared_username = "conflict_user"
        test_doctor.username = shared_username
        d2 = Doctor(
            id=str(uuid4()), name="D3", username=shared_username,
            department_id=test_doctor.department_id,
            store_id=store2.id, tenant_id=tenant2.id, status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(d2)
        await db_session.commit()

        service = DoctorService(db_session)
        with patch("app.modules.doctors.service_query.get_current_tenant_id", return_value=None):
            with pytest.raises(ValueError, match="检测到多个租户医生账号"):
                await service.get_by_username(shared_username, strict_tenant=True)

    # ------------------------------------------------------------------ #
    # authenticate: 通过用户名登录
    # ------------------------------------------------------------------ #

    async def test_authenticate_by_username(self, db_session, test_doctor):
        """通过用户名登录 (phone 参数传入用户名)"""
        password = "doc_pass_456"
        test_doctor.username = "login_user"
        test_doctor.password_hash = get_password_hash(password)
        await db_session.commit()

        service = DoctorService(db_session)
        with patch("app.modules.doctors.service_query.get_current_tenant_id", return_value=None):
            doctor = await service.authenticate("login_user", password)

        assert doctor is not None
        assert doctor.username == "login_user"

    # ------------------------------------------------------------------ #
    # create: 不带电话号码 -> 不创建 User
    # ------------------------------------------------------------------ #

    async def test_create_doctor_without_phone(self, db_session, test_tenant, test_department, test_store):
        """创建医生不带电话 -> user_id 为 None"""
        from app.middleware.tenant_context import set_tenant_context

        service = DoctorService(db_session)
        data = DoctorCreate(
            name="无电话医生",
            store_id=test_store.id,
            department_id=test_department.id,
            phone=None,
            status=1,
        )

        token = set_tenant_context(test_tenant.id)
        with patch("app.common.quota.check_quota", new_callable=AsyncMock):
            doctor = await service.create(data)
        set_tenant_context(None)

        assert doctor.user_id is None
        assert doctor.name == "无电话医生"

    # ------------------------------------------------------------------ #
    # delete: 软删除幂等性 + 状态变更验证
    # ------------------------------------------------------------------ #

    async def test_delete_doctor_sets_status_zero(
        self, db_session, test_tenant, test_department, test_store
    ):
        """软删除: deleted_at 非空 且 status=0"""
        from datetime import datetime
        doctor = Doctor(
            id=str(uuid4()), name="待删除", tenant_id=test_tenant.id,
            department_id=test_department.id, store_id=test_store.id,
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(doctor)
        await db_session.commit()

        service = DoctorService(db_session)
        result = await service.delete(doctor.id)
        assert result is True

        await db_session.refresh(doctor)
        assert doctor.deleted_at is not None
        assert doctor.status == 0

    async def test_delete_nonexistent_doctor(self, db_session):
        """删除不存在的医生 -> 返回 False"""
        service = DoctorService(db_session)
        result = await service.delete(str(uuid4()))
        assert result is False

    # ------------------------------------------------------------------ #
    # update: 状态转换
    # ------------------------------------------------------------------ #

    async def test_update_status_enable_to_disable(self, db_session, test_doctor):
        """状态转换: 启用(1) -> 禁用(0)"""
        assert test_doctor.status == 1

        service = DoctorService(db_session)
        doctor = await service.update(test_doctor.id, DoctorUpdate(status=0))

        assert doctor is not None
        assert doctor.status == 0

    async def test_update_status_disable_to_enable(self, db_session, test_doctor):
        """状态转换: 禁用(0) -> 启用(1)"""
        test_doctor.status = 0
        await db_session.commit()

        service = DoctorService(db_session)
        doctor = await service.update(test_doctor.id, DoctorUpdate(status=1))

        assert doctor is not None
        assert doctor.status == 1

    # ------------------------------------------------------------------ #
    # update: department_id 变更
    # ------------------------------------------------------------------ #

    async def test_update_change_department(self, db_session, test_doctor, test_tenant, test_store):
        """变更医生所属科室"""
        from app.models.department import Department

        new_dept = Department(
            id=str(uuid4()), name="新科室", store_id=test_store.id,
            tenant_id=test_tenant.id, status=1,
            created_at=test_doctor.created_at, updated_at=test_doctor.updated_at,
        )
        db_session.add(new_dept)
        await db_session.commit()

        service = DoctorService(db_session)
        doctor = await service.update(test_doctor.id, DoctorUpdate(department_id=new_dept.id))

        assert doctor is not None
        assert doctor.department_id == new_dept.id

    # ------------------------------------------------------------------ #
    # batch_update_sort_order: 异常输入
    # ------------------------------------------------------------------ #

    async def test_batch_update_sort_order_invalid_items(self, db_session, test_tenant, test_doctor):
        """批量排序: 缺少 id 或 sort_order 的条目被跳过"""
        service = DoctorService(db_session)
        items = [
            {"id": test_doctor.id},  # 缺少 sort_order
            {"sort_order": 99},  # 缺少 id
            {},  # 空字典
        ]
        count = await service.batch_update_sort_order(items)
        assert count == 0  # 没有有效条目

    async def test_batch_update_sort_order_nonexistent_doctor(self, db_session, test_tenant):
        """批量排序: 不存在的医生 ID 被跳过"""
        service = DoctorService(db_session)
        items = [{"id": str(uuid4()), "sort_order": 42}]
        count = await service.batch_update_sort_order(items)
        assert count == 0

    # ------------------------------------------------------------------ #
    # get_list: 软删除过滤
    # ------------------------------------------------------------------ #

    async def test_get_list_excludes_deleted(self, db_session, test_doctor):
        """已软删除的医生不出现在列表中"""
        deleted = Doctor(
            id=str(uuid4()), name="已删除医生",
            department_id=test_doctor.department_id,
            store_id=test_doctor.store_id,
            tenant_id=test_doctor.tenant_id,
            status=0,
            created_at=test_doctor.created_at,
            updated_at=test_doctor.updated_at,
        )
        db_session.add(deleted)
        await db_session.flush()

        # 手动设置 deleted_at
        from datetime import datetime
        deleted.deleted_at = datetime.now()
        await db_session.commit()

        service = DoctorService(db_session)
        doctors, total = await service.get_list()
        assert deleted.id not in [d.id for d in doctors]

    # ------------------------------------------------------------------ #
    # get_all_active: 门店过滤
    # ------------------------------------------------------------------ #

    async def test_get_all_active_filter_by_store(self, db_session, test_doctor, test_store):
        """获取所有启用医生: 按 store_id 过滤"""
        service = DoctorService(db_session)
        doctors = await service.get_all_active(store_id=test_store.id)
        assert all(d.store_id == test_store.id for d in doctors)

    async def test_get_all_active_wrong_store(self, db_session, test_doctor):
        """获取所有启用医生: 错误的 store_id 返回空"""
        service = DoctorService(db_session)
        doctors = await service.get_all_active(store_id=str(uuid4()))
        assert doctors == []
