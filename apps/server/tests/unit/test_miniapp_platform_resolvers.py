from datetime import date, datetime, time
from uuid import uuid4

import pytest

from app.infrastructure.payments.config_resolver import PaymentConfigResolver
from app.infrastructure.wechat.config_resolver import WechatConfigResolver
from app.models.appointment import Appointment
from app.models.miniapp_platform import AppTemplate, MiniappInstance, PaymentProfile, PaymentRoute, TemplateVersion
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.tenant import Tenant
from app.modules.payments.service import PaymentService


@pytest.mark.asyncio
async def test_wechat_config_resolver_prefers_miniapp_instance(db_session, monkeypatch):
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-a", name="租户A", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="测试门店",
        code="store-a",
        status=1,
        wechat_app_id="legacy-app",
        wechat_app_secret="legacy-secret",
    )
    template = AppTemplate(id=str(uuid4()), code="hospital", name="医院模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=store.id,
        name="实例A",
        app_id="instance-app",
        app_secret_ref="env:TEST_INSTANCE_SECRET",
        status=1,
    )
    monkeypatch.setenv("TEST_INSTANCE_SECRET", "instance-secret")

    db_session.add_all([tenant, store, template, version, instance])
    await db_session.commit()

    config = await WechatConfigResolver(db_session).resolve(
        store_id=store.id,
        miniapp_instance_id=instance.id,
    )

    assert config is not None
    assert config.source == "miniapp_instance"
    assert config.app_id == "instance-app"
    assert config.app_secret == "instance-secret"


@pytest.mark.asyncio
async def test_wechat_config_resolver_falls_back_to_store_when_instance_secret_missing(db_session):
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-b", name="租户B", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="测试门店B",
        code="store-b",
        status=1,
        wechat_app_id="legacy-app-b",
        wechat_app_secret="legacy-secret-b",
    )
    template = AppTemplate(id=str(uuid4()), code="dental", name="口腔模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=store.id,
        name="实例B",
        app_id="instance-app-b",
        app_secret_ref="env:MISSING_SECRET",
        status=1,
    )

    db_session.add_all([tenant, store, template, version, instance])
    await db_session.commit()

    config = await WechatConfigResolver(db_session).resolve(
        miniapp_instance_id=instance.id,
    )

    assert config is not None
    assert config.source == "store"
    assert config.app_id == "legacy-app-b"
    assert config.app_secret == "legacy-secret-b"


@pytest.mark.asyncio
async def test_payment_config_resolver_prefers_store_route_over_instance_default(db_session):
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-c", name="租户C", status=1)
    store = Store(id=str(uuid4()), tenant_id=tenant.id, name="测试门店C", code="store-c", status=1)
    template = AppTemplate(id=str(uuid4()), code="medical", name="医疗模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)
    instance_default_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="实例默认支付",
        code="instance-default",
        mode="direct",
        app_id="app-default",
        mch_id="mch-default",
        status=1,
    )
    store_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="门店覆盖支付",
        code="store-override",
        mode="service_provider",
        app_id="app-store",
        sub_mchid="sub-store",
        status=1,
    )
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=store.id,
        default_payment_profile_id=instance_default_profile.id,
        name="实例C",
        app_id="instance-app-c",
        status=1,
    )
    route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        miniapp_instance_id=instance.id,
        payment_profile_id=store_profile.id,
        priority=200,
        status=1,
    )

    db_session.add_all([
        tenant,
        store,
        template,
        version,
        instance_default_profile,
        store_profile,
        instance,
        route,
    ])
    await db_session.commit()

    config = await PaymentConfigResolver(db_session).resolve(
        store_id=store.id,
        miniapp_instance_id=instance.id,
    )

    assert config is not None
    assert config.source == "store_route"
    assert config.payment_profile_id == store_profile.id
    assert config.mode == "service_provider"
    assert config.sub_mchid == "sub-store"


@pytest.mark.asyncio
async def test_payment_config_resolver_falls_back_to_tenant_default_profile(db_session):
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-d", name="租户D", status=1)
    default_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="租户默认支付",
        code="tenant-default",
        mode="direct",
        app_id="tenant-default-app",
        mch_id="tenant-default-mch",
        is_default=True,
        status=1,
    )

    db_session.add_all([tenant, default_profile])
    await db_session.commit()

    config = await PaymentConfigResolver(db_session).resolve()

    assert config is not None
    assert config.source == "tenant_default"
    assert config.payment_profile_id == default_profile.id
    assert config.mch_id == "tenant-default-mch"


@pytest.mark.asyncio
async def test_payment_service_prefers_explicit_miniapp_instance_before_store_route(db_session):
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-e", name="租户E", status=1)
    store = Store(id=str(uuid4()), tenant_id=tenant.id, name="测试门店E", code="store-e", status=1)
    template = AppTemplate(id=str(uuid4()), code="general", name="综合模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)

    instance_default_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="实例默认支付E",
        code="instance-default-e",
        mode="direct",
        app_id="instance-app-e",
        mch_id="mch-instance-e",
        status=1,
    )
    store_route_profile = PaymentProfile(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="门店路由支付E",
        code="store-route-e",
        mode="service_provider",
        app_id="store-app-e",
        sub_mchid="sub-store-e",
        status=1,
    )
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=store.id,
        default_payment_profile_id=instance_default_profile.id,
        name="实例E",
        app_id="miniapp-e",
        status=1,
    )
    route = PaymentRoute(
        id=str(uuid4()),
        tenant_id=tenant.id,
        store_id=store.id,
        payment_profile_id=store_route_profile.id,
        priority=100,
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

    db_session.add_all(
        [
            tenant,
            store,
            template,
            version,
            instance_default_profile,
            store_route_profile,
            instance,
            route,
            schedule,
            appointment,
        ]
    )
    await db_session.commit()

    config = await PaymentService(db_session)._resolve_payment_config(
        appointment=appointment,
        miniapp_instance_id=instance.id,
    )

    assert config is not None
    assert config.source == "miniapp_instance_default"
    assert config.payment_profile_id == instance_default_profile.id


# ==================== Deprecation Tests ====================


@pytest.mark.asyncio
async def test_wechat_store_fallback_emits_deprecation_warning(db_session, caplog):
    """Store fallback path must emit a DEPRECATION warning."""
    import logging

    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-dep", name="租户Dep", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="废弃测试门店",
        code="store-dep",
        status=1,
        wechat_app_id="legacy-dep-app",
        wechat_app_secret="legacy-dep-secret",
    )

    db_session.add_all([tenant, store])
    await db_session.commit()

    with caplog.at_level(logging.WARNING, logger="app.infrastructure.wechat.config_resolver"):
        config = await WechatConfigResolver(db_session).resolve(store_id=store.id)

    assert config is not None
    assert config.source == "store"
    assert config.app_id == "legacy-dep-app"

    deprecation_msgs = [r for r in caplog.records if "DEPRECATION" in r.message]
    assert len(deprecation_msgs) == 1
    assert store.id in deprecation_msgs[0].message


@pytest.mark.asyncio
async def test_wechat_miniapp_instance_path_does_not_emit_deprecation(db_session, caplog, monkeypatch):
    """When MiniappInstance resolves successfully, no deprecation warning should be emitted."""
    import logging

    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-nodep", name="租户NoDep", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="非废弃测试门店",
        code="store-nodep",
        status=1,
        wechat_app_id="legacy-nope",
        wechat_app_secret="legacy-nope-secret",
    )
    template = AppTemplate(id=str(uuid4()), code="nodep", name="无废弃模板", status=1)
    version = TemplateVersion(id=str(uuid4()), template_id=template.id, version="1.0.0", status=1)
    instance = MiniappInstance(
        id=str(uuid4()),
        tenant_id=tenant.id,
        template_id=template.id,
        template_version_id=version.id,
        default_store_id=store.id,
        name="实例NoDep",
        app_id="instance-nodep-app",
        app_secret_ref="env:TEST_NODEP_SECRET",
        status=1,
    )
    monkeypatch.setenv("TEST_NODEP_SECRET", "instance-nodep-secret")

    db_session.add_all([tenant, store, template, version, instance])
    await db_session.commit()

    with caplog.at_level(logging.WARNING, logger="app.infrastructure.wechat.config_resolver"):
        config = await WechatConfigResolver(db_session).resolve(
            store_id=store.id,
            miniapp_instance_id=instance.id,
        )

    assert config is not None
    assert config.source == "miniapp_instance"

    deprecation_msgs = [r for r in caplog.records if "DEPRECATION" in r.message]
    assert len(deprecation_msgs) == 0


@pytest.mark.asyncio
async def test_payment_config_resolver_ignores_legacy_store_wechat_fields(db_session):
    """PaymentConfigResolver must never use store.wechat_* fields.
    When no PaymentProfile/PaymentRoute exists, it returns None
    even if the store has legacy wechat fields populated.
    """
    tenant = Tenant(id=str(uuid4()), tenant_code="tenant-legacy", name="租户Legacy", status=1)
    store = Store(
        id=str(uuid4()),
        tenant_id=tenant.id,
        name="Legacy门店",
        code="store-legacy",
        status=1,
        wechat_mch_id="legacy-mch-id",
        wechat_api_key="legacy-api-key",
        wechat_notify_url="https://legacy.example.com/notify",
    )

    db_session.add_all([tenant, store])
    await db_session.commit()

    config = await PaymentConfigResolver(db_session).resolve(store_id=store.id)

    assert config is None
