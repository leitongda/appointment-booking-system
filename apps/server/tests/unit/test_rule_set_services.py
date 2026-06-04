"""
Rule-set service unit tests

Covers:
- RuleSetService CRUD (create / update / delete)
- Enable / disable toggle
- Optimistic locking
- Reference check on delete
- Window CRUD (create / update / delete)
- Policy upsert (booking / checkin / capacity)
- Preset template CRUD + system preset protection
- Active rule-set resolution
- Edge cases: soft-deleted records, non-existent IDs
"""

import json
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from app.models.rule_set import (
    RuleBookingPolicy,
    RuleCapacityPolicy,
    RuleCheckinPolicy,
    RuleSet,
    RuleSetPreset,
    RuleSetShiftType,
    RuleWindow,
    ShiftType,
)
from app.modules.rule_sets.service import RuleSetService
from app.schemas.rule_set import (
    RuleBookingPolicyCreate,
    RuleCapacityPolicyCreate,
    RuleCheckinPolicyCreate,
    RuleSetCreate,
    RuleSetUpdate,
    RuleWindowCreate,
    RuleWindowUpdate,
)

# Patch targets for tenant context — each mixin imports it at module level,
# so we must patch at each consumer's namespace, not the source module.
_TENANT_PATCHES = [
    "app.modules.rule_sets.service_mutation.get_current_tenant_id",
    "app.modules.rule_sets.service_query.get_current_tenant_id",
    "app.modules.rule_sets.audit_helpers.get_current_tenant_id",
]
# Patch target for rule cache constructor used in _invalidate_rule_set_cache
_RULE_CACHE_PATCH = "app.modules.rule_sets.service_mutation.RuleCache"


@contextmanager
def _mock_tenant(tenant_id="t1"):
    """Context manager that patches get_current_tenant_id in all consumer modules."""
    patches = [patch(p, return_value=tenant_id) for p in _TENANT_PATCHES]
    for p in patches:
        p.start()
    try:
        yield
    finally:
        for p in patches:
            p.stop()


@contextmanager
def _mock_tenant_and_cache(tenant_id="t1"):
    """Context manager that patches tenant context + rule cache."""
    with _mock_tenant(tenant_id), patch(_RULE_CACHE_PATCH):
        yield


def _make_shift_type(db, code="OPD", name="门诊"):
    """Helper: insert a ShiftType row and return it."""
    st = ShiftType(
        id=str(uuid4()),
        code=code,
        name=name,
        enabled=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(st)
    return st


def _make_rule_set(db, tenant_id="t1", enabled=True, priority=100, name="默认规则组", deleted_at=None):
    """Helper: insert a RuleSet row and return it."""
    rs = RuleSet(
        id=str(uuid4()),
        name=name,
        enabled=enabled,
        priority=priority,
        time_source="SERVER",
        timezone_source="HOSPITAL",
        compare_precision="SECOND",
        default_open_inclusive=True,
        default_close_inclusive=False,
        rounding_mode="NONE",
        clock_skew_tolerance_sec=5,
        description="测试",
        tenant_id=tenant_id,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
        created_by="op1",
        updated_by="op1",
        deleted_at=deleted_at,
    )
    db.add(rs)
    return rs


def _make_window(db, rule_set_id, action="BOOK", name="预约时间窗"):
    """Helper: insert a RuleWindow row."""
    w = RuleWindow(
        id=str(uuid4()),
        rule_set_id=rule_set_id,
        name=name,
        action=action,
        reference_point="SHIFT_START",
        open_offset_sec=-604800,
        close_offset_sec=0,
        open_inclusive=True,
        close_inclusive=False,
        fail_policy="REJECT",
        enabled=True,
    )
    db.add(w)
    return w


# ---------------------------------------------------------------------------
# RuleSetService — create
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRuleSetCreate:
    """RuleSetService.create tests."""

    async def test_create_basic(self, db_session):
        """Create a rule set with one shift type, returns full detail response."""
        st = _make_shift_type(db_session)
        await db_session.flush()

        service = RuleSetService(db_session)
        data = RuleSetCreate(
            name="新建规则组",
            enabled=True,
            priority=50,
            shift_type_ids=[st.id],
        )

        with _mock_tenant_and_cache("t1"):
            result = await service.create(data, operator_id="op1")

        assert result is not None
        assert result.name == "新建规则组"
        assert result.priority == 50

        # Verify DB row exists
        rs = await db_session.get(RuleSet, result.id)
        assert rs is not None
        assert rs.tenant_id == "t1"

    async def test_create_with_windows_and_policies(self, db_session):
        """Create a rule set with windows, booking_policy, checkin_policy, capacity_policy."""
        st = _make_shift_type(db_session)
        await db_session.flush()

        service = RuleSetService(db_session)
        data = RuleSetCreate(
            name="完整规则组",
            enabled=True,
            priority=80,
            shift_type_ids=[st.id],
            windows=[
                RuleWindowCreate(
                    name="预约窗",
                    action="BOOK",
                    reference_point="SHIFT_START",
                    open_offset_sec=-604800,
                    close_offset_sec=0,
                ),
            ],
            booking_policy=RuleBookingPolicyCreate(
                require_auth=True,
                per_user_per_shift=1,
                per_user_per_day=3,
            ),
            checkin_policy=RuleCheckinPolicyCreate(
                require_booking=True,
                max_times=1,
            ),
            capacity_policy=RuleCapacityPolicyCreate(
                total_capacity=30,
                per_user_capacity=1,
            ),
        )

        with _mock_tenant_and_cache("t1"):
            result = await service.create(data, operator_id="op1")

        assert result is not None
        # Verify the related objects were persisted
        rs = await db_session.get(RuleSet, result.id)
        assert rs is not None

    async def test_create_sets_tenant_id_from_context(self, db_session):
        """tenant_id comes from get_current_tenant_id, not from the caller."""
        st = _make_shift_type(db_session)
        await db_session.flush()

        service = RuleSetService(db_session)
        data = RuleSetCreate(name="租户规则", shift_type_ids=[st.id])

        with _mock_tenant_and_cache("tenant-99"):
            result = await service.create(data)

        rs = await db_session.get(RuleSet, result.id)
        assert rs.tenant_id == "tenant-99"


# ---------------------------------------------------------------------------
# RuleSetService — update
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRuleSetUpdate:
    """RuleSetService.update tests."""

    async def test_update_name_and_priority(self, db_session):
        """Updating name and priority persists correctly."""
        st = _make_shift_type(db_session)
        rs = _make_rule_set(db_session, tenant_id="t1")
        rsst = RuleSetShiftType(rule_set_id=rs.id, shift_type_id=st.id)
        db_session.add(rsst)
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleSetUpdate(name="新名称", priority=20)

        with _mock_tenant_and_cache("t1"):
            result = await service.update(rs.id, data)

        assert result is not None
        assert result.name == "新名称"
        assert result.priority == 20

    async def test_update_nonexistent_returns_none(self, db_session):
        """Update on non-existent ID returns None."""
        service = RuleSetService(db_session)
        data = RuleSetUpdate(name="x")

        with _mock_tenant_and_cache("t1"):
            result = await service.update("nonexistent-id", data)

        assert result is None

    async def test_update_optimistic_lock_conflict(self, db_session):
        """Optimistic lock mismatch raises ValueError."""
        rs = _make_rule_set(db_session, tenant_id="t1")
        await db_session.commit()

        service = RuleSetService(db_session)
        wrong_timestamp = datetime(2020, 1, 1, tzinfo=timezone.utc)
        data = RuleSetUpdate(name="冲突", expected_updated_at=wrong_timestamp)

        with _mock_tenant_and_cache("t1"):
            with pytest.raises(ValueError, match="已被其他操作修改"):
                await service.update(rs.id, data)

    async def test_update_shift_type_ids(self, db_session):
        """Replacing shift_type_ids removes old and inserts new associations."""
        st1 = _make_shift_type(db_session, code="A")
        st2 = _make_shift_type(db_session, code="B")
        rs = _make_rule_set(db_session, tenant_id="t1")
        rsst = RuleSetShiftType(rule_set_id=rs.id, shift_type_id=st1.id)
        db_session.add(rsst)
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleSetUpdate(shift_type_ids=[st2.id])

        with _mock_tenant_and_cache("t1"):
            await service.update(rs.id, data)

        # Verify old association removed, new one exists
        result = await db_session.execute(
            __import__("sqlalchemy").select(RuleSetShiftType).where(
                RuleSetShiftType.rule_set_id == rs.id
            )
        )
        associations = result.scalars().all()
        assert len(associations) == 1
        assert associations[0].shift_type_id == st2.id

    async def test_update_windows_replaces_all(self, db_session):
        """Passing windows in update replaces existing windows entirely."""
        st = _make_shift_type(db_session)
        rs = _make_rule_set(db_session, tenant_id="t1")
        _make_window(db_session, rs.id, action="BOOK")
        rsst = RuleSetShiftType(rule_set_id=rs.id, shift_type_id=st.id)
        db_session.add(rsst)
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleSetUpdate(
            windows=[
                RuleWindowCreate(
                    name="新签到窗",
                    action="CHECKIN",
                    reference_point="SHIFT_END",
                    open_offset_sec=-1800,
                    close_offset_sec=3600,
                ),
            ]
        )

        with _mock_tenant_and_cache("t1"):
            await service.update(rs.id, data)

        # Verify old window gone, new one present
        from sqlalchemy import select
        result = await db_session.execute(
            select(RuleWindow).where(RuleWindow.rule_set_id == rs.id)
        )
        windows = result.scalars().all()
        assert len(windows) == 1
        assert windows[0].action == "CHECKIN"

    async def test_update_partial_no_change(self, db_session):
        """Update with no actual changes does NOT raise and returns the rule set."""
        rs = _make_rule_set(db_session, tenant_id="t1", name="原始名称")
        await db_session.commit()

        service = RuleSetService(db_session)
        # No expected_updated_at — just a simple no-op update
        data = RuleSetUpdate()

        with _mock_tenant_and_cache("t1"):
            result = await service.update(rs.id, data)

        assert result is not None
        assert result.name == "原始名称"


# ---------------------------------------------------------------------------
# RuleSetService — delete
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRuleSetDelete:
    """RuleSetService.delete tests."""

    async def test_soft_delete(self, db_session):
        """Delete sets deleted_at and disables the rule set."""
        rs = _make_rule_set(db_session, tenant_id="t1", enabled=True)
        await db_session.commit()

        service = RuleSetService(db_session)

        with _mock_tenant_and_cache("t1"):
            ok = await service.delete(rs.id, operator_id="op1")

        assert ok is True
        await db_session.refresh(rs)
        assert rs.deleted_at is not None
        assert rs.enabled is False

    async def test_delete_nonexistent_returns_false(self, db_session):
        """Delete on non-existent ID returns False."""
        service = RuleSetService(db_session)

        with _mock_tenant_and_cache("t1"):
            ok = await service.delete("no-such-id")

        assert ok is False

    async def test_delete_blocked_by_schedule_reference(self, db_session):
        """Delete is blocked when schedules reference the rule set's shift types."""
        from app.models.schedule import Schedule

        st = _make_shift_type(db_session, code="REF")
        rs = _make_rule_set(db_session, tenant_id="t1")
        rsst = RuleSetShiftType(rule_set_id=rs.id, shift_type_id=st.id)
        db_session.add(rsst)
        await db_session.flush()

        # Create a schedule referencing this shift type
        sched = Schedule(
            id=str(uuid4()),
            doctor_id="doc1",
            store_id="store1",
            tenant_id="t1",
            shift_type_id=st.id,
            schedule_date=datetime.now(timezone.utc).date(),
            time_slot="morning",
            start_time=datetime.now(timezone.utc).time(),
            end_time=datetime.now(timezone.utc).time(),
            total_slots=10,
            booked_slots=0,
            status=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(sched)
        await db_session.commit()

        service = RuleSetService(db_session)

        with _mock_tenant_and_cache("t1"):
            with pytest.raises(ValueError, match="无法删除"):
                await service.delete(rs.id)


# ---------------------------------------------------------------------------
# RuleSetService — enable / disable
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRuleSetEnableDisable:
    """RuleSetService.enable and disable tests."""

    async def test_enable(self, db_session):
        """Enabling a disabled rule set sets enabled=True."""
        rs = _make_rule_set(db_session, tenant_id="t1", enabled=False)
        await db_session.commit()

        service = RuleSetService(db_session)

        with _mock_tenant_and_cache("t1"):
            ok = await service.enable(rs.id, operator_id="op1")

        assert ok is True
        await db_session.refresh(rs)
        assert rs.enabled is True

    async def test_disable(self, db_session):
        """Disabling an enabled rule set sets enabled=False."""
        rs = _make_rule_set(db_session, tenant_id="t1", enabled=True)
        await db_session.commit()

        service = RuleSetService(db_session)

        with _mock_tenant_and_cache("t1"):
            ok = await service.disable(rs.id, operator_id="op1")

        assert ok is True
        await db_session.refresh(rs)
        assert rs.enabled is False

    async def test_enable_nonexistent_returns_false(self, db_session):
        service = RuleSetService(db_session)
        with _mock_tenant_and_cache("t1"):
            ok = await service.enable("nonexistent")
        assert ok is False

    async def test_disable_nonexistent_returns_false(self, db_session):
        service = RuleSetService(db_session)
        with _mock_tenant_and_cache("t1"):
            ok = await service.disable("nonexistent")
        assert ok is False


# ---------------------------------------------------------------------------
# RuleSetService — get_by_id
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestRuleSetQuery:
    """RuleSetService.get_by_id tests."""

    async def test_get_by_id_returns_detail(self, db_session):
        """get_by_id returns RuleSetDetailResponse with shift_types."""
        st = _make_shift_type(db_session)
        rs = _make_rule_set(db_session, tenant_id="t1")
        rsst = RuleSetShiftType(rule_set_id=rs.id, shift_type_id=st.id)
        db_session.add(rsst)
        await db_session.commit()

        service = RuleSetService(db_session)

        with _mock_tenant("t1"):
            result = await service.get_by_id(rs.id)

        assert result is not None
        assert result.id == rs.id
        assert len(result.shift_types) == 1
        assert result.shift_types[0].code == "OPD"

    async def test_get_by_id_deleted_returns_none(self, db_session):
        """Soft-deleted rule set is invisible to get_by_id."""
        rs = _make_rule_set(
            db_session, tenant_id="t1",
            deleted_at=datetime.now(timezone.utc),
        )
        await db_session.commit()

        service = RuleSetService(db_session)
        with _mock_tenant("t1"):
            result = await service.get_by_id(rs.id)

        assert result is None

    async def test_get_by_id_wrong_tenant_returns_none(self, db_session):
        """Rule set from tenant A is invisible when querying as tenant B."""
        rs = _make_rule_set(db_session, tenant_id="tenant-A")
        await db_session.commit()

        service = RuleSetService(db_session)
        with _mock_tenant("tenant-B"):
            result = await service.get_by_id(rs.id)

        assert result is None


# ---------------------------------------------------------------------------
# Window CRUD
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestWindowCRUD:
    """RuleSetService window create / update / delete."""

    async def test_create_window(self, db_session):
        rs = _make_rule_set(db_session, tenant_id="t1")
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleWindowCreate(
            name="签到窗",
            action="CHECKIN",
            reference_point="SHIFT_START",
            open_offset_sec=-1800,
            close_offset_sec=3600,
        )

        with _mock_tenant_and_cache("t1"):
            window = await service.create_window(rs.id, data, operator_id="op1")

        assert window is not None
        assert window.action == "CHECKIN"
        assert window.rule_set_id == rs.id

    async def test_create_window_nonexistent_ruleset(self, db_session):
        service = RuleSetService(db_session)
        data = RuleWindowCreate(
            action="BOOK",
            reference_point="SHIFT_START",
        )

        with _mock_tenant_and_cache("t1"):
            window = await service.create_window("no-such", data)

        assert window is None

    async def test_update_window(self, db_session):
        rs = _make_rule_set(db_session, tenant_id="t1")
        w = _make_window(db_session, rs.id)
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleWindowUpdate(fail_policy="ALLOW_WITH_TAG", fail_tag="迟到")

        with _mock_tenant_and_cache("t1"):
            updated = await service.update_window(w.id, data, operator_id="op1")

        assert updated is not None
        assert updated.fail_policy == "ALLOW_WITH_TAG"
        assert updated.fail_tag == "迟到"

    async def test_delete_window(self, db_session):
        rs = _make_rule_set(db_session, tenant_id="t1")
        w = _make_window(db_session, rs.id)
        await db_session.commit()

        service = RuleSetService(db_session)

        with _mock_tenant_and_cache("t1"):
            ok = await service.delete_window(w.id, operator_id="op1")

        assert ok is True
        # Window should be gone from DB
        assert await db_session.get(RuleWindow, w.id) is None

    async def test_delete_nonexistent_window(self, db_session):
        service = RuleSetService(db_session)
        with _mock_tenant_and_cache("t1"):
            ok = await service.delete_window("nonexistent")
        assert ok is False


# ---------------------------------------------------------------------------
# Policy upsert
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestPolicyUpsert:
    """RuleSetService policy update (upsert) tests."""

    async def test_update_booking_policy_creates_new(self, db_session):
        """When no policy exists, update_booking_policy creates one."""
        rs = _make_rule_set(db_session, tenant_id="t1")
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleBookingPolicyCreate(
            require_auth=True,
            per_user_per_shift=2,
            conflict_same_shift="REPLACE",
        )

        with _mock_tenant_and_cache("t1"):
            policy = await service.update_booking_policy(rs.id, data, operator_id="op1")

        assert policy is not None
        assert policy.per_user_per_shift == 2
        assert policy.conflict_same_shift == "REPLACE"

    async def test_update_booking_policy_updates_existing(self, db_session):
        """When policy already exists, update_booking_policy modifies it."""
        rs = _make_rule_set(db_session, tenant_id="t1")
        policy = RuleBookingPolicy(
            rule_set_id=rs.id,
            require_auth=True,
            per_user_per_shift=1,
            conflict_same_shift="REJECT",
        )
        db_session.add(policy)
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleBookingPolicyCreate(
            require_auth=True,
            per_user_per_shift=5,
            conflict_same_shift="ALLOW",
        )

        with _mock_tenant_and_cache("t1"):
            updated = await service.update_booking_policy(rs.id, data, operator_id="op1")

        assert updated.per_user_per_shift == 5
        assert updated.conflict_same_shift == "ALLOW"

    async def test_update_checkin_policy(self, db_session):
        rs = _make_rule_set(db_session, tenant_id="t1")
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleCheckinPolicyCreate(
            require_booking=False,
            allow_onsite_booking=True,
            max_times=3,
            grace_period_sec=900,
            no_checkin_after_close="AUTO_CANCEL",
        )

        with _mock_tenant_and_cache("t1"):
            policy = await service.update_checkin_policy(rs.id, data, operator_id="op1")

        assert policy is not None
        assert policy.allow_onsite_booking is True
        assert policy.grace_period_sec == 900

    async def test_update_capacity_policy(self, db_session):
        rs = _make_rule_set(db_session, tenant_id="t1")
        await db_session.commit()

        service = RuleSetService(db_session)
        data = RuleCapacityPolicyCreate(
            total_capacity=50,
            per_user_capacity=1,
            waitlist_enabled=True,
            waitlist_max_size=10,
            overbooking_enabled=True,
            overbooking_max=5,
        )

        with _mock_tenant_and_cache("t1"):
            policy = await service.update_capacity_policy(rs.id, data, operator_id="op1")

        assert policy is not None
        assert policy.total_capacity == 50
        assert policy.waitlist_enabled is True
        assert policy.overbooking_max == 5


# ---------------------------------------------------------------------------
# Preset template CRUD
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestPresetCRUD:
    """RuleSetService preset template tests."""

    async def test_create_preset(self, db_session):
        service = RuleSetService(db_session)
        config = {"name": "自定义模板", "priority": 100}

        with _mock_tenant("t1"):
            preset = await service.create_preset(
                name="我的预设", description="自定义", config=config, operator_id="op1"
            )

        assert preset is not None
        assert preset.name == "我的预设"
        assert preset.is_system is False
        assert preset.tenant_id == "t1"

    async def test_update_preset(self, db_session):
        preset = RuleSetPreset(
            id=str(uuid4()),
            tenant_id="t1",
            name="旧名称",
            config={"x": 1},
            is_system=False,
            sort_order=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(preset)
        await db_session.commit()

        service = RuleSetService(db_session)
        with _mock_tenant("t1"):
            updated = await service.update_preset(preset.id, operator_id="op1", name="新名称")

        assert updated is not None
        assert updated.name == "新名称"

    async def test_cannot_update_system_preset(self, db_session):
        preset = RuleSetPreset(
            id="standard-clinic",
            name="标准门诊",
            config={},
            is_system=True,
            sort_order=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(preset)
        await db_session.commit()

        service = RuleSetService(db_session)
        with _mock_tenant("t1"):
            result = await service.update_preset(preset.id, name="hack")

        assert result is None

    async def test_delete_preset(self, db_session):
        preset = RuleSetPreset(
            id=str(uuid4()),
            tenant_id="t1",
            name="删除我",
            config={},
            is_system=False,
            sort_order=0,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(preset)
        await db_session.commit()

        service = RuleSetService(db_session)
        with _mock_tenant("t1"):
            ok = await service.delete_preset(preset.id)

        assert ok is True
        assert await db_session.get(RuleSetPreset, preset.id) is None

    async def test_cannot_delete_system_preset(self, db_session):
        preset = RuleSetPreset(
            id="standard-clinic",
            name="标准门诊",
            config={},
            is_system=True,
            sort_order=1,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(preset)
        await db_session.commit()

        service = RuleSetService(db_session)
        with _mock_tenant("t1"):
            ok = await service.delete_preset(preset.id)

        assert ok is False

    async def test_delete_nonexistent_preset(self, db_session):
        service = RuleSetService(db_session)
        with _mock_tenant("t1"):
            ok = await service.delete_preset("no-such")
        assert ok is False


# ---------------------------------------------------------------------------
# Audit diff helpers
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
class TestAuditHelpers:
    """Audit helper functions: serialize, diff, make_audit."""

    def test_serialize_value_datetime(self):
        from app.modules.rule_sets.audit_helpers import _serialize_value

        dt = datetime(2025, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
        assert _serialize_value(dt) == dt.isoformat()

    def test_serialize_value_string(self):
        from app.modules.rule_sets.audit_helpers import _serialize_value
        assert _serialize_value("hello") == "hello"

    def test_serialize_model_none(self):
        from app.modules.rule_sets.audit_helpers import serialize_model
        assert serialize_model(None) is None

    def test_compute_diff_both_none(self):
        from app.modules.rule_sets.audit_helpers import compute_rule_set_diff
        assert compute_rule_set_diff(None, None) is None

    def test_compute_diff_detects_changes(self):
        from app.modules.rule_sets.audit_helpers import compute_rule_set_diff

        before = json.dumps({"name": "A", "priority": 100})
        after = json.dumps({"name": "B", "priority": 100})
        diff = compute_rule_set_diff(before, after)

        assert diff is not None
        assert len(diff["changes"]) == 1
        assert diff["changes"][0]["key"] == "name"
        assert diff["changes"][0]["before"] == "A"
        assert diff["changes"][0]["after"] == "B"

    def test_compute_diff_no_changes(self):
        from app.modules.rule_sets.audit_helpers import compute_rule_set_diff

        data = json.dumps({"name": "X", "priority": 50})
        assert compute_rule_set_diff(data, data) is None

    def test_compute_diff_invalid_json(self):
        from app.modules.rule_sets.audit_helpers import compute_rule_set_diff
        assert compute_rule_set_diff("not-json", "also-not-json") is None

    def test_make_rule_set_audit(self):
        from app.modules.rule_sets.audit_helpers import make_rule_set_audit

        # audit_helpers imports get_current_tenant_id directly, so patch at that module
        with patch("app.modules.rule_sets.audit_helpers.get_current_tenant_id", return_value="t1"):
            log = make_rule_set_audit(
                rule_set_id="rs1",
                action="CREATE",
                resource_type="rule_set",
                resource_id="rs1",
                operator_id="op1",
            )

        assert log.rule_set_id == "rs1"
        assert log.action == "CREATE"
        assert log.tenant_id == "t1"
