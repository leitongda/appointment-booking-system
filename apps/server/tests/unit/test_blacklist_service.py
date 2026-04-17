from datetime import datetime
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.models.blacklist import Blacklist
from app.models.store import Store
from app.models.tenant import SubscriptionPlan, Tenant
from app.modules.blacklists.service import BlacklistService
from app.schemas.blacklist import BlacklistCreate


@pytest.mark.asyncio
async def test_create_blacklist_sets_current_tenant_id(db_session, test_tenant, test_store, test_user):
    service = BlacklistService(db_session)

    with patch("app.modules.blacklists.service.get_current_tenant_id", return_value=test_tenant.id):
        result = await service.create(
            BlacklistCreate(
                user_id=test_user.id,
                store_id=test_store.id,
                reason="测试租户黑名单",
            )
        )

    created = await db_session.get(Blacklist, result["id"])
    assert created is not None
    assert created.tenant_id == test_tenant.id


@pytest.mark.asyncio
async def test_check_blacklist_isolated_by_tenant(db_session, test_tenant):
    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_b",
        name="测试计划B",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    tenant_b = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_b",
        name="测试租户B",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([plan, tenant_b])
    await db_session.flush()

    blacklist_a = Blacklist(
        id=str(uuid4()),
        tenant_id=test_tenant.id,
        keyword="13800138000",
        reason="租户A黑名单",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    blacklist_b = Blacklist(
        id=str(uuid4()),
        tenant_id=tenant_b.id,
        keyword="13800138000",
        reason="租户B黑名单",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([blacklist_a, blacklist_b])
    await db_session.commit()

    service = BlacklistService(db_session)

    with patch("app.modules.blacklists.service.get_current_tenant_id", return_value=test_tenant.id):
        result_a = await service.check_blacklist(phone="13800138000")

    with patch("app.modules.blacklists.service.get_current_tenant_id", return_value=tenant_b.id):
        result_b = await service.check_blacklist(phone="13800138000")

    assert result_a.is_blacklisted is True
    assert result_a.reason == "租户A黑名单"
    assert result_b.is_blacklisted is True
    assert result_b.reason == "租户B黑名单"


@pytest.mark.asyncio
async def test_create_blacklist_rejects_foreign_store(db_session, test_tenant):
    plan = SubscriptionPlan(
        id=str(uuid4()),
        plan_code="test_plan_c",
        name="测试计划C",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    tenant_b = Tenant(
        id=str(uuid4()),
        tenant_code="test_tenant_c",
        name="测试租户C",
        status=1,
        subscription_plan_id=plan.id,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    store_b = Store(
        id=str(uuid4()),
        name="租户B门店",
        address="测试地址",
        phone="13800138111",
        tenant_id=tenant_b.id,
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    db_session.add_all([plan, tenant_b, store_b])
    await db_session.commit()

    service = BlacklistService(db_session)
    with patch("app.modules.blacklists.service.get_current_tenant_id", return_value=test_tenant.id):
        with pytest.raises(ValueError) as exc_info:
            await service.create(
                BlacklistCreate(store_id=store_b.id, reason="跨租户门店")
            )

    assert "门店不属于当前租户" in str(exc_info.value)
