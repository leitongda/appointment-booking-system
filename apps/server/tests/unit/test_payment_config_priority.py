"""
测试支付配置解析优先级链

覆盖 PaymentService._resolve_payment_config 的 5 级优先级：
1. appointment.payment_profile_id (预约快照) - 最高优先级，返回 PaymentProfile 对象
2. miniapp_instance_id (请求参数传入)
3. appointment.payment_miniapp_instance_id (预约关联的小程序实例)
4. schedule.store_id -> PaymentRoute (门店路由)
5. 返回 None (当前代码未实现租户默认配置 fallback)

重要发现：
- 快照路径返回 PaymentProfile 对象（有 .mode, .mch_id 等属性）
- resolver 路径返回 PaymentRoutingConfig 对象（有 .source, .payment_profile_id 等属性）
- 当前代码在最后返回 None，未实现租户默认配置的 fallback
"""
from datetime import date, datetime, time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from app.infrastructure.payments.config_resolver import PaymentRoutingConfig
from app.models.appointment import Appointment
from app.models.miniapp_platform import (
    AppTemplate,
    MiniappInstance,
    PaymentProfile,
    PaymentRoute,
    TemplateVersion,
)
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.tenant import Tenant
from app.modules.payments.service import PaymentService


@pytest.mark.asyncio
async def test_snapshot_highest_priority(db_session):
    """预约快照优先级最高：当 appointment.payment_profile_id 存在时，忽略其他所有来源"""
    # 创建租户和门店
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-snap", name="租户快照测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="快照测试门店",
        code="store-snap",
        status=1,
    )
    template = AppTemplate(id=str(uuid4()), code="test", name="测试模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)

    # 创建多个不同的支付配置
    snapshot_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="快照支付配置",
        code="snapshot-profile",
        mode="direct",
        app_id="snap-app",
        mch_id="snap-mch",
        status=1,
    )
    request_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="请求参数支付配置",
        code="request-profile",
        mode="service_provider",
        app_id="req-app",
        sub_mchid="req-sub",
        status=1,
    )
    appointment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="预约关联支付配置",
        code="appointment-profile",
        mode="direct",
        app_id="apt-app",
        mch_id="apt-mch",
        status=1,
    )
    store_route_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="门店路由支付配置",
        code="store-route-profile",
        mode="service_provider",
        app_id="store-app",
        sub_mchid="store-sub",
        status=1,
    )

    # 创建小程序实例
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_payment_profile_id=appointment_profile.id,
        name="快照测试实例",
        app_id="snap-instance",
        status=1,
    )

    # 创建排班和预约
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        payment_profile_id=snapshot_profile.id,  # 快照指向 snapshot_profile
        payment_miniapp_instance_id=instance.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    # 创建门店路由
    route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        payment_profile_id=store_route_profile.id,
        priority=100,
        status=1,
    )

    db_session.add_all(
        [
            tenant,
            store,
            template,
            version,
            snapshot_profile,
            request_profile,
            appointment_profile,
            store_route_profile,
            instance,
            schedule,
            appointment,
            route,
        ]
    )
    await db_session.commit()

    # 设置租户上下文
    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)

        # 即使传入了 miniapp_instance_id，也应该使用快照
        result = await service._resolve_payment_config(
            appointment=appointment,
            miniapp_instance_id=instance.id,
        )

        # 快照路径返回 PaymentProfile 对象，不是 PaymentRoutingConfig
        assert result is not None
        assert isinstance(result, PaymentProfile)
        assert result.id == snapshot_profile.id
        assert result.mch_id == "snap-mch"
        assert result.mode == "direct"


@pytest.mark.asyncio
async def test_request_miniapp_instance_second(db_session):
    """无快照时，请求参数中的 miniapp_instance_id 生效"""
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-req", name="租户请求测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="请求测试门店",
        code="store-req",
        status=1,
    )
    template = AppTemplate(id=str(uuid4()), code="test", name="测试模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)

    request_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="请求支付配置",
        code="request-profile",
        mode="direct",
        app_id="req-app",
        mch_id="req-mch",
        status=1,
    )
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_payment_profile_id=request_profile.id,
        name="请求测试实例",
        app_id="req-instance",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        # 无 payment_profile_id
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all([tenant, store, template, version, request_profile, instance, schedule, appointment])
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(
            appointment=appointment,
            miniapp_instance_id=instance.id,
        )

        assert result is not None
        assert result.payment_profile_id == request_profile.id
        assert result.source == "miniapp_instance_default"


@pytest.mark.asyncio
async def test_appointment_miniapp_instance_third(db_session):
    """无快照和请求参数时，预约关联的小程序实例生效"""
    tenant = Tenant(
        id=str(uuid4()),
        tenant_code="tenant-apt-inst",
        name="租户预约实例测试",
        status=1,
    )
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="预约实例测试门店",
        code="store-apt-inst",
        status=1,
    )
    template = AppTemplate(id=str(uuid4()), code="test", name="测试模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)

    appointment_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="预约实例支付配置",
        code="apt-inst-profile",
        mode="direct",
        app_id="apt-inst-app",
        mch_id="apt-inst-mch",
        status=1,
    )
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_payment_profile_id=appointment_profile.id,
        name="预约实例测试",
        app_id="apt-instance",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        payment_miniapp_instance_id=instance.id,  # 预约关联的小程序实例
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all(
        [tenant, store, template, version, appointment_profile, instance, schedule, appointment]
    )
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        # 不传 miniapp_instance_id，应使用预约关联的
        result = await service._resolve_payment_config(appointment=appointment)

        assert result is not None
        assert result.payment_profile_id == appointment_profile.id
        assert result.source == "miniapp_instance_default"


@pytest.mark.asyncio
async def test_store_route_fourth(db_session):
    """无以上时，通过 schedule.store_id 路由生效"""
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-store", name="租户门店测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="门店路由测试门店",
        code="store-route-test",
        status=1,
    )

    store_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="门店路由支付配置",
        code="store-route-profile",
        mode="service_provider",
        app_id="store-route-app",
        sub_mchid="store-route-sub",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        payment_profile_id=store_profile.id,
        priority=100,
        status=1,
    )

    db_session.add_all([tenant, store, store_profile, schedule, appointment, route])
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        assert result is not None
        assert result.payment_profile_id == store_profile.id
        assert result.source == "store_route"


@pytest.mark.asyncio
async def test_returns_none_when_no_config_available(db_session):
    """所有路由都无时返回 None

    注意：当前代码实现中，_resolve_payment_config 在门店路由后直接返回 None，
    没有显式调用 PaymentConfigResolver 的租户默认配置 fallback。
    待补充：应该在最后调用 resolver.resolve() 来获取租户默认配置。
    """
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-none", name="租户无配置测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="无配置门店",
        code="store-none",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all([tenant, store, schedule, appointment])
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        # 当前实现返回 None
        assert result is None


@pytest.mark.asyncio
async def test_tenant_default_fallback_via_resolver(db_session):
    """测试：PaymentConfigResolver 已实现租户默认配置 fallback

    当调用 resolver.resolve() 时，如果没有匹配的 store_id、miniapp_instance_id、
    payment_profile_id，会自动查找 PaymentProfile.is_default=True 的配置。
    """
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-default", name="租户默认测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="默认测试门店",
        code="store-default",
        status=1,
    )

    # 创建租户默认支付配置
    default_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="租户默认支付配置",
        code="tenant-default-profile",
        mode="direct",
        app_id="default-app",
        mch_id="default-mch",
        is_default=True,
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all([tenant, store, default_profile, schedule, appointment])
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        # PaymentConfigResolver.resolve() 会自动走到租户默认配置
        # 因为没有 PaymentRoute 绑定到该 store
        assert result is not None
        assert isinstance(result, PaymentRoutingConfig)
        assert result.payment_profile_id == default_profile.id
        assert result.mch_id == "default-mch"
        assert result.source == "tenant_default"


@pytest.mark.asyncio
async def test_disabled_profile_skipped(db_session):
    """快照指向的 PaymentProfile status=0 (禁用) 时应被跳过"""
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-disabled", name="租户禁用测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="禁用测试门店",
        code="store-disabled",
        status=1,
    )
    template = AppTemplate(id=str(uuid4()), code="test", name="测试模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)

    # 已禁用的支付配置（快照指向此配置）
    disabled_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="已禁用支付配置",
        code="disabled-profile",
        mode="direct",
        app_id="disabled-app",
        mch_id="disabled-mch",
        status=0,  # 禁用
    )
    fallback_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="回退支付配置",
        code="fallback-profile",
        mode="direct",
        app_id="fallback-app",
        mch_id="fallback-mch",
        status=1,
    )
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_payment_profile_id=fallback_profile.id,
        name="禁用测试实例",
        app_id="disabled-instance",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        payment_profile_id=disabled_profile.id,  # 快照指向已禁用的配置
        payment_miniapp_instance_id=instance.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all(
        [tenant, store, template, version, disabled_profile, fallback_profile, instance, schedule, appointment]
    )
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        # 快照指向的配置已禁用，应跳过并降级到下一优先级 (miniapp_instance)
        assert result is not None
        assert result.payment_profile_id == fallback_profile.id
        assert result.mch_id == "fallback-mch"
        assert result.source == "miniapp_instance_default"


@pytest.mark.asyncio
async def test_payment_route_priority_order(db_session):
    """多条 PaymentRoute 时按 priority 排序，值越大优先级越高"""
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-priority", name="租户优先级测试", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="优先级测试门店",
        code="store-priority",
        status=1,
    )

    low_priority_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="低优先级支付配置",
        code="low-priority-profile",
        mode="direct",
        app_id="low-app",
        mch_id="low-mch",
        status=1,
    )
    high_priority_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="高优先级支付配置",
        code="high-priority-profile",
        mode="service_provider",
        app_id="high-app",
        sub_mchid="high-sub",
        status=1,
    )
    medium_priority_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="中优先级支付配置",
        code="medium-priority-profile",
        mode="direct",
        app_id="medium-app",
        mch_id="medium-mch",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    # 创建不同优先级的路由
    low_route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        payment_profile_id=low_priority_profile.id,
        priority=50,  # 低优先级
        status=1,
    )
    high_route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        payment_profile_id=high_priority_profile.id,
        priority=200,  # 高优先级
        status=1,
    )
    medium_route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        payment_profile_id=medium_priority_profile.id,
        priority=100,  # 中优先级
        status=1,
    )

    db_session.add_all(
        [
            tenant,
            store,
            low_priority_profile,
            high_priority_profile,
            medium_priority_profile,
            schedule,
            appointment,
            low_route,
            high_route,
            medium_route,
        ]
    )
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        assert result is not None
        # 应该使用高优先级的路由配置
        assert result.payment_profile_id == high_priority_profile.id
        assert result.sub_mchid == "high-sub"
        assert result.source == "store_route"


@pytest.mark.asyncio
async def test_schedule_without_store(db_session):
    """当 schedule 没有 store_id 时，跳过门店路由逻辑"""
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-no-store", name="租户无门店测试", status=1)

    # 创建没有 store_id 的排班
    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        tenant_id=tenant.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant.id,
        queue_number=1,
        status=0,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all([tenant, schedule, appointment])
    await db_session.commit()

    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        # schedule 没有 store_id，跳过门店路由，返回 None
        assert result is None


@pytest.mark.asyncio
async def test_tenant_isolation(db_session):
    """验证租户隔离：只查询当前租户的支付配置"""
    tenant_a = Tenant(id=str(uuid4()), tenant_code="tenant-a", name="租户A", status=1)
    tenant_b = Tenant(id=str(uuid4()), tenant_code="tenant-b", name="租户B", status=1)

    profile_a = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant_a.id,
        name="租户A支付配置",
        code="profile-a",
        mode="direct",
        app_id="app-a",
        mch_id="mch-a",
        status=1,
    )
    # 租户B也有同名配置，但应该被隔离
    profile_b = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        name="租户B支付配置",
        code="profile-b",
        mode="direct",
        app_id="app-b",
        mch_id="mch-b",
        status=1,
    )

    schedule = Schedule(
        id=str(uuid4()),
        doctor_id=str(uuid4()),
        tenant_id=tenant_a.id,
        schedule_date=date.today(),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    appointment = Appointment(
        id=str(uuid4()),
        appointment_no=f"YY{uuid4().hex[:12].upper()}",
        user_id=str(uuid4()),
        patient_id=str(uuid4()),
        doctor_id=schedule.doctor_id,
        schedule_id=schedule.id,
        tenant_id=tenant_a.id,
        queue_number=1,
        status=0,
        payment_profile_id=profile_a.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    appointment.schedule = schedule

    db_session.add_all([tenant_a, tenant_b, profile_a, profile_b, schedule, appointment])
    await db_session.commit()

    # 设置租户A的上下文，应该只查询租户A的配置
    with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=tenant_a.id):
        service = PaymentService(db_session)
        result = await service._resolve_payment_config(appointment=appointment)

        # 快照路径返回 PaymentProfile 对象
        assert result is not None
        assert isinstance(result, PaymentProfile)
        assert result.id == profile_a.id
        assert result.mch_id == "mch-a"
        assert result.mch_id != "mch-b"
