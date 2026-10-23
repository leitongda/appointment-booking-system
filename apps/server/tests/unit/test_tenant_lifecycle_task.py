"""B11：租户物理删除 dry-run 任务单测（R3-2 验收门）

覆盖 `app/tasks/tenant_lifecycle_task.py` 的安全边界：
1. ``TENANT_PURGE_ENABLED=False``（默认）：全程 no-op，不打开数据库会话；
2. ``ENABLED=True + DRY_RUN=True``：只列出超过 90 天保留期的软删除租户，
   ``deleted=0``，数据库行数不变；
3. 未满保留期的软删除租户与未删除租户不进候选；
4. ``DRY_RUN=False``：首版仍未实现物理删除，行为与 dry-run 一致（行数不变）；
5. 重复执行幂等（两次结果一致、行数不变）。

用内存 SQLite（StaticPool 单连接）承接真实的 `_find_expired_deleted_tenants`
查询，只替换 `get_sync_db` 的会话来源。
"""
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.models.tenant import Tenant
from app.tasks.tenant_lifecycle_task import (
    TENANT_PURGE_RETENTION_DAYS,
    purge_deleted_tenants_task,
)

pytestmark = pytest.mark.unit

NOW = datetime.utcnow()


class _FrozenDateTime(datetime):
    """冻结任务内 utcnow：cutoff 与种子数据的相对时间完全确定。"""

    @classmethod
    def utcnow(cls):
        return NOW


@pytest.fixture
def freeze_task_clock(monkeypatch):
    monkeypatch.setattr(
        "app.tasks.tenant_lifecycle_task.datetime", _FrozenDateTime
    )


@pytest.fixture
def sync_engine():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # 与 tests/conftest.py::_create_all_safe 相同的低代码重复索引去重
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

    yield engine
    engine.dispose()


@pytest.fixture
def sync_session_maker(sync_engine, monkeypatch):
    session_maker = sessionmaker(bind=sync_engine, expire_on_commit=False)

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

    monkeypatch.setattr(
        "app.tasks.tenant_lifecycle_task.get_sync_db", fake_get_sync_db
    )
    return session_maker


def _make_tenant(code: str, deleted_at: datetime | None) -> Tenant:
    return Tenant(
        id=str(uuid.uuid4()),
        tenant_code=code,
        name=f"租户-{code}",
        status=1,
        deleted_at=deleted_at,
    )


def _seed_three_tenants(session_maker) -> None:
    """三条租户：已过保留期 / 软删除未到期 / 未删除。"""
    with session_maker() as session:
        session.add_all(
            [
                _make_tenant("expired", NOW - timedelta(days=TENANT_PURGE_RETENTION_DAYS + 1)),
                _make_tenant("recent", NOW - timedelta(days=10)),
                _make_tenant("active", None),
            ]
        )
        session.commit()


def _tenant_rows(session_maker) -> list[Tenant]:
    with session_maker() as session:
        return list(session.execute(select(Tenant)).scalars().all())


def test_enabled_false_is_full_no_op(monkeypatch):
    """ENABLED=False：不开 DB 会话，直接返回空结果。"""
    monkeypatch.setattr(settings, "TENANT_PURGE_ENABLED", False)

    opened = []

    @contextmanager
    def guard():
        opened.append(True)
        yield None

    monkeypatch.setattr("app.tasks.tenant_lifecycle_task.get_sync_db", guard)

    result = purge_deleted_tenants_task()

    assert result == {
        "enabled": False,
        "dry_run": True,
        "deleted": 0,
        "candidates": [],
    }
    assert opened == []  # 未触碰数据库


def test_dry_run_lists_only_expired_tenants(sync_session_maker, monkeypatch, freeze_task_clock):
    """ENABLED=True + DRY_RUN=True：仅列出到期租户，不删除任何行。"""
    _seed_three_tenants(sync_session_maker)
    monkeypatch.setattr(settings, "TENANT_PURGE_ENABLED", True)
    monkeypatch.setattr(settings, "TENANT_PURGE_DRY_RUN", True)

    result = purge_deleted_tenants_task()

    assert result["enabled"] is True
    assert result["dry_run"] is True
    assert result["deleted"] == 0
    assert result["retention_days"] == TENANT_PURGE_RETENTION_DAYS == 90
    assert result["candidate_count"] == 1
    assert result["candidates"][0]["tenant_code"] == "expired"

    rows = _tenant_rows(sync_session_maker)
    assert len(rows) == 3  # 数据原样


def test_boundary_and_exclusion(sync_session_maker, monkeypatch, freeze_task_clock):
    """未到期软删除与未删除租户不进候选；恰好到期也未过保留期。"""
    with sync_session_maker() as session:
        session.add_all(
            [
                # deleted_at 恰好等于 cutoff 也不算（条件是 < cutoff）
                _make_tenant("exactly_cutoff", NOW - timedelta(days=TENANT_PURGE_RETENTION_DAYS)),
                _make_tenant("not_deleted", None),
            ]
        )
        session.commit()

    monkeypatch.setattr(settings, "TENANT_PURGE_ENABLED", True)
    monkeypatch.setattr(settings, "TENANT_PURGE_DRY_RUN", True)

    result = purge_deleted_tenants_task()
    assert result["candidate_count"] == 0
    assert result["candidates"] == []


def test_dry_run_false_still_deletes_nothing(sync_session_maker, monkeypatch, freeze_task_clock):
    """DRY_RUN=False：首版无物理删除实现，行为与 dry-run 一致。"""
    _seed_three_tenants(sync_session_maker)
    monkeypatch.setattr(settings, "TENANT_PURGE_ENABLED", True)
    monkeypatch.setattr(settings, "TENANT_PURGE_DRY_RUN", False)

    result = purge_deleted_tenants_task()

    assert result["deleted"] == 0
    assert result["candidate_count"] == 1
    assert len(_tenant_rows(sync_session_maker)) == 3


def test_repeated_runs_are_idempotent(sync_session_maker, monkeypatch, freeze_task_clock):
    """重复执行：结果一致，行数不变。"""
    _seed_three_tenants(sync_session_maker)
    monkeypatch.setattr(settings, "TENANT_PURGE_ENABLED", True)
    monkeypatch.setattr(settings, "TENANT_PURGE_DRY_RUN", True)

    first = purge_deleted_tenants_task()
    second = purge_deleted_tenants_task()

    assert first == second
    assert first["candidate_count"] == 1
    assert len(_tenant_rows(sync_session_maker)) == 3


def test_row_count_helper_sanity(sync_session_maker):
    """辅助断言自检：func.count 与 _tenant_rows 一致，避免误读空库。"""
    _seed_three_tenants(sync_session_maker)
    with sync_session_maker() as session:
        assert session.execute(select(func.count(Tenant.id))).scalar_one() == 3
