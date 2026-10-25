"""R2-6/D17：auto_renew 到期续费测试（2026-10-23 已实现收口）

D17 采纳语义（docs/tenant-remaining-plan.md 第 7 节建议默认）：
到期时 ``auto_renew=True`` 的租户——延长订阅周期 + 生成 pending 应收账单
（``TenantSubscription.payment_status='pending'``）+ 不停服，无真实扣费；
未开自动续费的租户维持现行行为（置欠费 + 欠费通知）。
"""
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.models.tenant import SubscriptionPlan, Tenant, TenantSubscription
from app.tasks.tenant_usage_task import check_subscription_expiry

pytestmark = pytest.mark.unit

NOW = datetime.utcnow()


@pytest.fixture
def sync_session_maker(monkeypatch):
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    def _create_all_safe(connection):
        seen_indexes = set()
        for table in Base.metadata.sorted_tables:
            deduped = set()
            for idx in table.indexes:
                if idx.name not in seen_indexes:
                    seen_indexes.add(idx.name)
                    deduped.add(idx)
            table.indexes = deduped
        Base.metadata.create_all(connection)

    with engine.begin() as conn:
        _create_all_safe(conn)

    session_maker = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def fake_get_sync_db():
        session = session_maker()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    monkeypatch.setattr("app.tasks.tenant_usage_task.get_sync_db", fake_get_sync_db)

    # 到期通知走异步会话 + 邮件服务，骨架测试只关心租户/订阅状态机
    async def fake_async_db_context():
        yield MagicMock()

    class _NoopNotificationService:
        def __init__(self, *args, **kwargs):
            pass

        async def check_subscription_expiry(self, tenant_id):
            return None

        async def send_overdue_notification(self, tenant_id):
            return None

    monkeypatch.setattr("app.db.session.get_async_db_context", fake_async_db_context)
    monkeypatch.setattr(
        "app.infrastructure.notifications.service.TenantNotificationService",
        _NoopNotificationService,
    )
    return session_maker


def _seed(session_maker, auto_renew: bool, payment_status: str = "paid") -> Tenant:
    """一个已到期（昨天）的正常租户 + 一条指定支付状态的订阅。"""
    with session_maker() as session:
        plan = SubscriptionPlan(
            id=str(uuid.uuid4()),
            plan_code=f"basic-{auto_renew}-{payment_status}",
            name="基础版",
            status=1,
        )
        tenant = Tenant(
            id=str(uuid.uuid4()),
            tenant_code=f"ar-{auto_renew}-{payment_status[:3]}",
            name=f"自动续费={auto_renew}",
            status=1,
            subscription_end_at=NOW - timedelta(days=1),
        )
        session.add_all([plan, tenant])
        session.flush()
        session.add(
            TenantSubscription(
                id=str(uuid.uuid4()),
                tenant_id=tenant.id,
                plan_id=plan.id,
                plan_code=plan.plan_code,
                plan_name=plan.name,
                billing_cycle="monthly",
                start_at=NOW - timedelta(days=31),
                end_at=NOW - timedelta(days=1),
                payment_status=payment_status,
                status=1,
                auto_renew=auto_renew,
            )
        )
        session.commit()
        return tenant


def _reload(session_maker, tenant_id: str) -> Tenant:
    with session_maker() as session:
        return session.execute(
            select(Tenant).where(Tenant.id == tenant_id)
        ).scalar_one()


def test_expiry_without_auto_renew_still_marks_overdue(sync_session_maker):
    """现行契约：未开自动续费的租户到期置欠费（status=2）。"""
    tenant = _seed(sync_session_maker, auto_renew=False)

    result = check_subscription_expiry()

    reloaded = _reload(sync_session_maker, tenant.id)
    assert result["suspended_count"] == 1
    assert reloaded.status == 2


def test_unpaid_subscription_with_auto_renew_still_marks_overdue(sync_session_maker):
    """P4-5 负向：auto_renew=True 但本期订阅未支付（pending）→ 不续费，到期照常置欠费。"""
    tenant = _seed(sync_session_maker, auto_renew=True, payment_status="pending")

    result = check_subscription_expiry()

    assert result["renewed_count"] == 0
    assert result["suspended_count"] == 1
    assert _reload(sync_session_maker, tenant.id).status == 2


def test_expiry_with_auto_renew_keeps_tenant_active(sync_session_maker):
    """D17：auto_renew=True 到期不置欠费（不停服）。"""
    tenant = _seed(sync_session_maker, auto_renew=True)

    result = check_subscription_expiry()

    assert result["renewed_count"] == 1
    assert result["suspended_count"] == 0
    assert _reload(sync_session_maker, tenant.id).status == 1


def test_expiry_with_auto_renew_creates_pending_receivable(sync_session_maker):
    """D17：到期生成下周期 pending 应收（TenantSubscription.payment_status='pending'）。"""
    tenant = _seed(sync_session_maker, auto_renew=True)

    check_subscription_expiry()

    with sync_session_maker() as session:
        rows = (
            session.execute(
                select(TenantSubscription).where(
                    TenantSubscription.tenant_id == tenant.id
                )
            )
            .scalars()
            .all()
        )
    pending = [r for r in rows if r.payment_status == "pending"]
    expired = [r for r in rows if r.status == 2]
    assert len(pending) == 1
    assert pending[0].paid_at is None  # 无真实扣费
    assert pending[0].auto_renew is True
    assert pending[0].billing_cycle == "monthly"
    assert len(expired) == 1  # 旧订阅置为已过期


def test_expiry_with_auto_renew_extends_subscription_period(sync_session_maker):
    """D17：到期后租户订阅周期延长一个计费周期（monthly=30 天）。"""
    tenant = _seed(sync_session_maker, auto_renew=True)
    before = _reload(sync_session_maker, tenant.id).subscription_end_at

    check_subscription_expiry()

    after = _reload(sync_session_maker, tenant.id).subscription_end_at
    assert after == before + timedelta(days=30)
