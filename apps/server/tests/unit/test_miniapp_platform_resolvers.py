from uuid import uuid4

import pytest

from app.infrastructure.payments.config_resolver import PaymentConfigResolver
from app.infrastructure.wechat.config_resolver import WechatConfigResolver
from app.models.miniapp_platform import AppTemplate, MiniappInstance, PaymentProfile, PaymentRoute, TemplateVersion
from app.models.store import Store
from app.models.tenant import Tenant


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
