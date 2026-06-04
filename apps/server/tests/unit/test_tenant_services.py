"""租户模块服务单元测试

覆盖范围：
- SubscriptionPlanService: CRUD、编码去重、默认计划、删除保护
- TenantService: CRUD、软删除/恢复、状态管理、批量计数
- TenantSubscriptionService: 创建订阅、降级配额校验
- TenantUsageService: 用量汇总、每日记录
- TenantNotificationService: 列表查询、已读标记
"""
from datetime import datetime, date, timedelta
from decimal import Decimal
from unittest.mock import patch, AsyncMock
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.models.tenant import (
    SubscriptionPlan,
    Tenant,
    TenantSubscription,
    TenantUsageLog,
    TenantNotification,
)
from app.models.store import Store
from app.models.admin import Admin
from app.modules.tenants.service_plan import SubscriptionPlanService
from app.modules.tenants.service_tenant import TenantService
from app.modules.tenants.service_subscription import TenantSubscriptionService
from app.modules.tenants.service_usage import TenantUsageService
from app.modules.tenants.service_notification import TenantNotificationService
from app.modules.tenants.schemas import (
    SubscriptionPlanCreate,
    SubscriptionPlanUpdate,
    TenantCreate,
    TenantUpdate,
    TenantQuery,
    TenantSubscriptionCreate,
)


# ====================================================================
# SubscriptionPlanService
# ====================================================================

@pytest.mark.unit
class TestSubscriptionPlanService:
    """订阅计划服务测试"""

    async def test_get_by_id(self, db_session):
        """通过 ID 获取订阅计划"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="basic", name="基础版",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        result = await service.get_by_id(plan.id)

        assert result is not None
        assert result.plan_code == "basic"
        assert result.name == "基础版"

    async def test_get_by_id_not_found(self, db_session):
        """获取不存在的计划返回 None"""
        service = SubscriptionPlanService(db_session)
        result = await service.get_by_id(str(uuid4()))
        assert result is None

    async def test_get_by_code(self, db_session):
        """通过编码获取订阅计划"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="pro", name="专业版",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        result = await service.get_by_code("pro")

        assert result is not None
        assert result.name == "专业版"

    async def test_get_list_with_status_filter(self, db_session):
        """按状态过滤计划列表"""
        now = datetime.now()
        for code, name, st in [("s1", "启用计划", 1), ("s2", "禁用计划", 0)]:
            db_session.add(SubscriptionPlan(
                id=str(uuid4()), plan_code=code, name=name,
                status=st, created_at=now, updated_at=now,
            ))
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        plans = await service.get_list(status=1)

        assert len(plans) == 1
        assert plans[0].plan_code == "s1"

    async def test_get_list_all(self, db_session):
        """获取全部计划"""
        now = datetime.now()
        for code in ["a", "b", "c"]:
            db_session.add(SubscriptionPlan(
                id=str(uuid4()), plan_code=code, name=code,
                status=1, created_at=now, updated_at=now,
            ))
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        plans = await service.get_list()
        assert len(plans) == 3

    async def test_get_default_plan(self, db_session):
        """获取默认计划"""
        now = datetime.now()
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="default", name="默认",
            is_default=True, status=1, created_at=now, updated_at=now,
        )
        db_session.add(plan)
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        result = await service.get_default_plan()
        assert result is not None
        assert result.plan_code == "default"

    async def test_get_default_plan_none_when_no_default(self, db_session):
        """无默认计划时返回 None"""
        service = SubscriptionPlanService(db_session)
        result = await service.get_default_plan()
        assert result is None

    async def test_create_success(self, db_session):
        """成功创建订阅计划"""
        service = SubscriptionPlanService(db_session)
        data = SubscriptionPlanCreate(
            plan_code="enterprise",
            name="企业版",
            price_monthly=Decimal("999.00"),
            price_yearly=Decimal("9999.00"),
        )
        plan = await service.create(data)

        assert plan.id is not None
        assert plan.plan_code == "enterprise"
        assert plan.name == "企业版"
        assert plan.price_monthly == Decimal("999.00")

    async def test_create_duplicate_code_raises(self, db_session):
        """创建重复编码的计划抛出 ValueError"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="dup", name="已有",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        data = SubscriptionPlanCreate(plan_code="dup", name="重复")
        with pytest.raises(ValueError, match="已存在"):
            await service.create(data)

    async def test_update_plan(self, db_session):
        """更新订阅计划字段"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="upd", name="旧名称",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        data = SubscriptionPlanUpdate(name="新名称", price_monthly=Decimal("199.00"))
        updated = await service.update(plan.id, data)

        assert updated is not None
        assert updated.name == "新名称"
        assert updated.price_monthly == Decimal("199.00")

    async def test_update_nonexistent_returns_none(self, db_session):
        """更新不存在的计划返回 None"""
        service = SubscriptionPlanService(db_session)
        result = await service.update(str(uuid4()), SubscriptionPlanUpdate(name="x"))
        assert result is None

    async def test_delete_success(self, db_session):
        """删除无租户使用的计划"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="del", name="待删",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        result = await service.delete(plan.id)
        assert result is True

        # 确认已删除
        assert await service.get_by_id(plan.id) is None

    async def test_delete_with_active_tenants_raises(self, db_session, test_tenant):
        """删除有活跃租户使用的计划抛出 ValueError"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="inuse", name="使用中",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.flush()

        test_tenant.subscription_plan_id = plan.id
        await db_session.commit()

        service = SubscriptionPlanService(db_session)
        with pytest.raises(ValueError, match="个租户正在使用"):
            await service.delete(plan.id)

    async def test_delete_nonexistent_returns_false(self, db_session):
        """删除不存在的计划返回 False"""
        service = SubscriptionPlanService(db_session)
        result = await service.delete(str(uuid4()))
        assert result is False


# ====================================================================
# TenantService
# ====================================================================

@pytest.mark.unit
class TestTenantService:
    """租户服务测试"""

    async def test_get_by_id(self, db_session, test_tenant):
        """通过 ID 获取租户"""
        service = TenantService(db_session)
        tenant = await service.get_by_id(test_tenant.id)

        assert tenant is not None
        assert tenant.tenant_code == "test_tenant"
        assert tenant.subscription_plan is not None

    async def test_get_by_id_not_found(self, db_session):
        """获取不存在的租户返回 None"""
        service = TenantService(db_session)
        result = await service.get_by_id(str(uuid4()))
        assert result is None

    async def test_get_by_code(self, db_session, test_tenant):
        """通过编码获取租户"""
        service = TenantService(db_session)
        tenant = await service.get_by_code("test_tenant")
        assert tenant is not None
        assert tenant.id == test_tenant.id

    async def test_create_tenant(self, db_session):
        """创建租户并验证默认数据初始化"""
        service = TenantService(db_session)
        data = TenantCreate(
            tenant_code="new-tenant",
            name="新租户",
            billing_cycle="monthly",
        )
        tenant = await service.create(data, created_by="test_admin")

        assert tenant.id is not None
        assert tenant.tenant_code == "new-tenant"
        assert tenant.status == 1
        assert tenant.subscription_start_at is not None
        assert tenant.subscription_end_at is not None
        assert tenant.created_by == "test_admin"

        # 验证默认数据已初始化（门店、科室、角色）
        store_result = await db_session.execute(
            select(Store).where(Store.tenant_id == tenant.id)
        )
        stores = list(store_result.scalars().all())
        assert len(stores) == 1
        assert stores[0].code == "MAIN"

        from app.models.department import Department
        dept_result = await db_session.execute(
            select(Department).where(Department.tenant_id == tenant.id)
        )
        departments = list(dept_result.scalars().all())
        assert len(departments) == 1

        from app.models.admin import Role
        role_result = await db_session.execute(
            select(Role).where(Role.tenant_id == tenant.id)
        )
        roles = list(role_result.scalars().all())
        assert len(roles) == 1
        assert roles[0].code == "admin"

    async def test_create_trial_tenant(self, db_session):
        """创建试用租户状态为 3"""
        service = TenantService(db_session)
        data = TenantCreate(
            tenant_code="trial-tenant",
            name="试用租户",
            is_trial=True,
        )
        tenant = await service.create(data)
        assert tenant.status == 3

    async def test_create_duplicate_code_raises(self, db_session):
        """创建重复编码的租户抛出 ValueError"""
        # 先直接插入一个编码合规的租户
        existing = Tenant(
            id=str(uuid4()), tenant_code="dup-code", name="已存在",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(existing)
        await db_session.commit()

        service = TenantService(db_session)
        data = TenantCreate(tenant_code="dup-code", name="重复")
        with pytest.raises(ValueError, match="已存在"):
            await service.create(data)

    async def test_delete_nonexistent_returns_false(self, db_session):
        """删除不存在的租户返回 False"""
        service = TenantService(db_session)
        result = await service.delete(str(uuid4()))
        assert result is False

    async def test_get_list_empty(self, db_session):
        """空租户列表返回空"""
        service = TenantService(db_session)
        query = TenantQuery(page=1, page_size=10)
        tenants, total = await service.get_list(query)
        assert tenants == []
        assert total == 0

    async def test_get_admin_counts_batch(self, db_session, test_tenant, test_super_admin):
        """批量获取管理员数量"""
        service = TenantService(db_session)
        result = await service.get_admin_counts_batch([test_tenant.id])
        assert result[test_tenant.id] >= 1

    async def test_get_admin_counts_batch_empty(self, db_session):
        """空列表批量查询管理员返回空字典"""
        service = TenantService(db_session)
        result = await service.get_admin_counts_batch([])
        assert result == {}

    async def test_check_code_exists_false(self, db_session):
        """不存在的编码返回 False"""
        service = TenantService(db_session)
        assert await service.check_code_exists("nonexistent-code") is False

    async def test_get_list_subscription_plan_filter(self, db_session, test_tenant):
        """按订阅计划过滤"""
        service = TenantService(db_session)
        plan_id = test_tenant.subscription_plan_id
        query = TenantQuery(subscription_plan_id=plan_id, page=1, page_size=10)
        tenants, total = await service.get_list(query)
        assert total >= 1
        assert all(t.subscription_plan_id == plan_id for t in tenants)

    async def test_update_tenant(self, db_session, test_tenant):
        """更新租户信息"""
        service = TenantService(db_session)
        data = TenantUpdate(name="更新后名称", contact_phone="13900000000")
        updated = await service.update(test_tenant.id, data, updated_by="admin_id")

        assert updated is not None
        assert updated.name == "更新后名称"
        assert updated.contact_phone == "13900000000"
        assert updated.updated_by == "admin_id"

    async def test_update_nonexistent_returns_none(self, db_session):
        """更新不存在的租户返回 None"""
        service = TenantService(db_session)
        result = await service.update(str(uuid4()), TenantUpdate(name="x"))
        assert result is None

    async def test_suspend_and_activate(self, db_session, test_tenant):
        """暂停和激活租户"""
        service = TenantService(db_session)

        # 暂停
        suspended = await service.suspend(test_tenant.id)
        assert suspended.status == 0

        # 激活
        activated = await service.activate(test_tenant.id)
        assert activated.status == 1

    async def test_mark_overdue(self, db_session, test_tenant):
        """标记租户为欠费"""
        service = TenantService(db_session)
        result = await service.mark_overdue(test_tenant.id)
        assert result.status == 2

    async def test_soft_delete(self, db_session, test_tenant):
        """软删除租户"""
        service = TenantService(db_session)
        result = await service.delete(test_tenant.id, deleted_by="admin")

        assert result is True
        # 通过 selectinload 重新加载，检查 deleted_at
        refreshed = await db_session.get(Tenant, test_tenant.id)
        assert refreshed.deleted_at is not None
        assert refreshed.deleted_by == "admin"
        assert refreshed.status == 0

    async def test_soft_delete_already_deleted_raises(self, db_session, test_tenant):
        """对已软删除的租户再次删除抛出 ValueError"""
        service = TenantService(db_session)
        await service.delete(test_tenant.id)

        with pytest.raises(ValueError, match="已被删除"):
            await service.delete(test_tenant.id)

    async def test_restore(self, db_session, test_tenant):
        """恢复已软删除的租户"""
        service = TenantService(db_session)
        await service.delete(test_tenant.id)

        restored = await service.restore(test_tenant.id, restored_by="admin")
        assert restored.deleted_at is None
        assert restored.deleted_by is None
        assert restored.status == 1

    async def test_restore_not_deleted_raises(self, db_session, test_tenant):
        """恢复未被删除的租户抛出 ValueError"""
        service = TenantService(db_session)
        with pytest.raises(ValueError, match="未被删除"):
            await service.restore(test_tenant.id)

    async def test_restore_nonexistent_returns_none(self, db_session):
        """恢复不存在的租户返回 None"""
        service = TenantService(db_session)
        result = await service.restore(str(uuid4()))
        assert result is None

    async def test_get_store_count(self, db_session, test_tenant, test_store):
        """获取租户门店数量"""
        service = TenantService(db_session)
        count = await service.get_store_count(test_tenant.id)
        assert count == 1

    async def test_get_admin_count(self, db_session, test_tenant, test_super_admin):
        """获取租户管理员数量"""
        service = TenantService(db_session)
        count = await service.get_admin_count(test_tenant.id)
        assert count == 1

    async def test_get_store_counts_batch(self, db_session, test_tenant, test_store):
        """批量获取门店数量"""
        service = TenantService(db_session)
        result = await service.get_store_counts_batch([test_tenant.id])
        assert result[test_tenant.id] == 1

    async def test_get_store_counts_batch_empty(self, db_session):
        """空列表批量查询返回空字典"""
        service = TenantService(db_session)
        result = await service.get_store_counts_batch([])
        assert result == {}

    async def test_check_code_exists(self, db_session, test_tenant):
        """检查租户编码是否存在"""
        service = TenantService(db_session)
        assert await service.check_code_exists("test_tenant") is True
        assert await service.check_code_exists("nonexistent") is False

    async def test_check_code_exists_exclude_id(self, db_session, test_tenant):
        """排除自身后检查编码"""
        service = TenantService(db_session)
        assert await service.check_code_exists("test_tenant", exclude_id=test_tenant.id) is False

    async def test_get_list_excludes_deleted(self, db_session, test_tenant):
        """列表查询默认排除已删除租户"""
        service = TenantService(db_session)
        await service.delete(test_tenant.id)

        query = TenantQuery(page=1, page_size=10)
        tenants, total = await service.get_list(query, include_deleted=False)
        assert total == 0

    async def test_get_list_includes_deleted(self, db_session, test_tenant):
        """include_deleted=True 包含已删除租户"""
        service = TenantService(db_session)
        await service.delete(test_tenant.id)

        query = TenantQuery(page=1, page_size=10)
        tenants, total = await service.get_list(query, include_deleted=True)
        assert total == 1

    async def test_get_list_keyword_filter(self, db_session, test_tenant):
        """关键字过滤"""
        service = TenantService(db_session)
        query = TenantQuery(keyword="测试", page=1, page_size=10)
        tenants, total = await service.get_list(query)
        assert total >= 1

    async def test_get_list_status_filter(self, db_session, test_tenant):
        """状态过滤"""
        service = TenantService(db_session)
        query = TenantQuery(status=1, page=1, page_size=10)
        tenants, total = await service.get_list(query)
        assert total >= 1
        assert all(t.status == 1 for t in tenants)


# ====================================================================
# TenantSubscriptionService
# ====================================================================

@pytest.mark.unit
class TestTenantSubscriptionService:
    """租户订阅服务测试"""

    async def test_create_subscription_monthly(self, db_session, test_tenant):
        """创建月度订阅"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="monthly_plan", name="月度计划",
            price_monthly=Decimal("100.00"), price_yearly=Decimal("1000.00"),
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = TenantSubscriptionService(db_session)
        data = TenantSubscriptionCreate(
            plan_id=plan.id,
            billing_cycle="monthly",
        )
        subscription = await service.create_subscription(
            test_tenant.id, data, created_by="admin"
        )

        assert subscription.id is not None
        assert subscription.plan_code == "monthly_plan"
        assert subscription.plan_name == "月度计划"
        assert subscription.billing_cycle == "monthly"
        assert subscription.amount == Decimal("100.00")
        assert subscription.auto_renew is False
        assert subscription.payment_status == "pending"

        # 验证租户订阅信息已更新
        refreshed_tenant = await db_session.get(Tenant, test_tenant.id)
        assert refreshed_tenant.subscription_plan_id == plan.id
        assert refreshed_tenant.subscription_start_at is not None
        assert refreshed_tenant.subscription_end_at is not None

    async def test_create_subscription_yearly(self, db_session, test_tenant):
        """创建年度订阅"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="yearly_plan", name="年度计划",
            price_yearly=Decimal("999.00"),
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = TenantSubscriptionService(db_session)
        data = TenantSubscriptionCreate(
            plan_id=plan.id,
            billing_cycle="yearly",
            auto_renew=True,
        )
        subscription = await service.create_subscription(test_tenant.id, data)

        assert subscription.billing_cycle == "yearly"
        assert subscription.amount == Decimal("999.00")
        assert subscription.auto_renew is True

        # 年度订阅应有 ~365 天有效期
        refreshed_tenant = await db_session.get(Tenant, test_tenant.id)
        delta = refreshed_tenant.subscription_end_at - refreshed_tenant.subscription_start_at
        assert 364 <= delta.days <= 366

    async def test_create_subscription_nonexistent_tenant_raises(self, db_session):
        """不存在的租户创建订阅抛出 ValueError"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="x", name="x",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = TenantSubscriptionService(db_session)
        data = TenantSubscriptionCreate(plan_id=plan.id, billing_cycle="monthly")
        with pytest.raises(ValueError, match="租户不存在"):
            await service.create_subscription(str(uuid4()), data)

    async def test_create_subscription_nonexistent_plan_raises(self, db_session, test_tenant):
        """不存在的计划创建订阅抛出 ValueError"""
        service = TenantSubscriptionService(db_session)
        data = TenantSubscriptionCreate(
            plan_id=str(uuid4()), billing_cycle="monthly"
        )
        with pytest.raises(ValueError, match="订阅计划不存在"):
            await service.create_subscription(test_tenant.id, data)

    async def test_create_subscription_activates_overdue_tenant(self, db_session, test_tenant):
        """欠费状态的租户创建订阅后自动激活"""
        test_tenant.status = 2  # 欠费
        await db_session.commit()

        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="reactivate", name="重新激活",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = TenantSubscriptionService(db_session)
        data = TenantSubscriptionCreate(plan_id=plan.id, billing_cycle="monthly")
        await service.create_subscription(test_tenant.id, data)

        refreshed = await db_session.get(Tenant, test_tenant.id)
        assert refreshed.status == 1

    async def test_get_tenant_subscriptions(self, db_session, test_tenant):
        """获取租户的订阅记录列表"""
        plan = SubscriptionPlan(
            id=str(uuid4()), plan_code="list_plan", name="列表测试",
            status=1, created_at=datetime.now(), updated_at=datetime.now(),
        )
        db_session.add(plan)
        await db_session.commit()

        service = TenantSubscriptionService(db_session)
        data = TenantSubscriptionCreate(plan_id=plan.id, billing_cycle="monthly")
        await service.create_subscription(test_tenant.id, data)

        subscriptions = await service.get_tenant_subscriptions(test_tenant.id)
        assert len(subscriptions) == 1
        assert subscriptions[0].plan_code == "list_plan"


# ====================================================================
# TenantUsageService
# ====================================================================

@pytest.mark.unit
class TestTenantUsageService:
    """租户用量统计服务测试"""

    @patch("app.modules.tenants.service_usage.settings")
    async def test_get_usage_summary(self, mock_settings, db_session, test_tenant):
        """获取租户用量汇总"""
        mock_settings.STORAGE_TYPE = "minio"
        mock_settings.LOCAL_UPLOAD_DIR = "/tmp/test"

        service = TenantUsageService(db_session)
        summary = await service.get_usage_summary(test_tenant.id)

        assert summary["tenant_id"] == test_tenant.id
        assert summary["tenant_name"] == "测试租户"
        assert "max_stores" in summary
        assert "current_store_count" in summary
        assert "store_usage_rate" in summary
        assert "doctor_usage_rate" in summary

    async def test_get_usage_summary_nonexistent_tenant_raises(self, db_session):
        """获取不存在租户的用量汇总抛出 ValueError"""
        service = TenantUsageService(db_session)
        with pytest.raises(ValueError, match="租户不存在"):
            await service.get_usage_summary(str(uuid4()))

    async def test_record_daily_usage_creates_new(self, db_session, test_tenant):
        """记录每日用量 — 创建新记录"""
        service = TenantUsageService(db_session)
        usage_date = date(2026, 1, 15)

        log = await service.record_daily_usage(test_tenant.id, usage_date)

        assert log.id is not None
        assert log.tenant_id == test_tenant.id
        assert log.usage_date == usage_date
        assert log.appointment_count == 0
        assert log.new_user_count == 0

    async def test_record_daily_usage_updates_existing(self, db_session, test_tenant):
        """记录每日用量 — 更新已有记录"""
        service = TenantUsageService(db_session)
        usage_date = date(2026, 2, 10)

        log1 = await service.record_daily_usage(test_tenant.id, usage_date)
        log1_id = log1.id

        log2 = await service.record_daily_usage(test_tenant.id, usage_date)

        assert log2.id == log1_id  # 同一条记录

    async def test_get_usage_logs(self, db_session, test_tenant):
        """获取用量日志"""
        service = TenantUsageService(db_session)
        today = date.today()
        await service.record_daily_usage(test_tenant.id, today)

        logs = await service.get_usage_logs(
            test_tenant.id,
            start_date=today,
            end_date=today,
        )
        assert len(logs) >= 1

    async def test_get_usage_logs_empty(self, db_session, test_tenant):
        """无日志时返回空列表"""
        service = TenantUsageService(db_session)
        logs = await service.get_usage_logs(
            test_tenant.id,
            start_date=date(2000, 1, 1),
            end_date=date(2000, 1, 1),
        )
        assert logs == []

    @patch("app.modules.tenants.service_usage.settings")
    async def test_usage_rate_calculation(self, mock_settings, db_session, test_tenant):
        """用量使用率计算"""
        mock_settings.STORAGE_TYPE = "minio"
        mock_settings.LOCAL_UPLOAD_DIR = "/tmp/test"

        service = TenantUsageService(db_session)
        summary = await service.get_usage_summary(test_tenant.id)

        # 无数据时使用率为 0
        assert summary["store_usage_rate"] == 0
        assert summary["doctor_usage_rate"] == 0


# ====================================================================
# TenantNotificationService
# ====================================================================

@pytest.mark.unit
class TestTenantNotificationService:
    """租户通知服务测试"""

    async def _create_notifications(self, db_session, tenant_id, count=3):
        """辅助方法：创建多条通知"""
        notifications = []
        for i in range(count):
            n = TenantNotification(
                id=str(uuid4()),
                tenant_id=tenant_id,
                notification_type="subscription_expiry",
                title=f"通知{i}",
                content=f"内容{i}",
                is_read=(i == 0),  # 第一条已读
                created_at=datetime.now() - timedelta(hours=i),
            )
            db_session.add(n)
            notifications.append(n)
        await db_session.commit()
        return notifications

    async def test_get_notifications(self, db_session, test_tenant):
        """获取通知列表"""
        await self._create_notifications(db_session, test_tenant.id)

        service = TenantNotificationService(db_session)
        items, unread_count, total = await service.get_notifications(test_tenant.id)

        assert total == 3
        assert unread_count == 2  # 第一条已读
        assert len(items) == 3

    async def test_get_notifications_unread_only(self, db_session, test_tenant):
        """仅获取未读通知"""
        await self._create_notifications(db_session, test_tenant.id)

        service = TenantNotificationService(db_session)
        items, unread_count, total = await service.get_notifications(
            test_tenant.id, unread_only=True
        )

        assert total == 2  # 未读数
        assert unread_count == 2
        assert all(not n.is_read for n in items)

    async def test_get_notifications_pagination(self, db_session, test_tenant):
        """通知分页"""
        await self._create_notifications(db_session, test_tenant.id, count=5)

        service = TenantNotificationService(db_session)
        items, _, total = await service.get_notifications(
            test_tenant.id, page=1, page_size=2
        )

        assert total == 5
        assert len(items) == 2

    async def test_mark_read(self, db_session, test_tenant):
        """标记单条通知已读"""
        notifications = await self._create_notifications(db_session, test_tenant.id)
        unread_id = notifications[1].id  # 未读的

        service = TenantNotificationService(db_session)
        result = await service.mark_read(test_tenant.id, unread_id)
        assert result is True

        # 验证已读
        refreshed = await db_session.get(TenantNotification, unread_id)
        assert refreshed.is_read is True
        assert refreshed.read_at is not None

    async def test_mark_read_nonexistent_returns_false(self, db_session, test_tenant):
        """标记不存在的通知返回 False"""
        service = TenantNotificationService(db_session)
        result = await service.mark_read(test_tenant.id, str(uuid4()))
        assert result is False

    async def test_mark_read_wrong_tenant_returns_false(self, db_session, test_tenant):
        """标记其他租户的通知返回 False"""
        notifications = await self._create_notifications(db_session, test_tenant.id)

        # 创建另一个租户的通知
        other_tenant_id = str(uuid4())
        other_n = TenantNotification(
            id=str(uuid4()),
            tenant_id=other_tenant_id,
            notification_type="info",
            title="其他租户通知",
            content="其他",
            created_at=datetime.now(),
        )
        db_session.add(other_n)
        await db_session.commit()

        service = TenantNotificationService(db_session)
        result = await service.mark_read(test_tenant.id, other_n.id)
        assert result is False

    async def test_mark_all_read(self, db_session, test_tenant):
        """标记全部已读"""
        await self._create_notifications(db_session, test_tenant.id)

        service = TenantNotificationService(db_session)
        affected = await service.mark_all_read(test_tenant.id)
        assert affected == 2  # 只有 2 条未读

        # 验证全部已读
        items, unread_count, _ = await service.get_notifications(test_tenant.id)
        assert unread_count == 0
        assert all(n.is_read for n in items)

    async def test_mark_all_read_when_all_read(self, db_session, test_tenant):
        """全部已读时 mark_all_read 返回 0"""
        service = TenantNotificationService(db_session)
        affected = await service.mark_all_read(test_tenant.id)
        assert affected == 0

    async def test_get_notifications_empty(self, db_session, test_tenant):
        """无通知时返回空列表"""
        service = TenantNotificationService(db_session)
        items, unread_count, total = await service.get_notifications(test_tenant.id)
        assert items == []
        assert unread_count == 0
        assert total == 0
