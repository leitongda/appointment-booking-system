"""排班审计日志单元测试

测试 snapshot_schedule / compute_diff / make_schedule_audit 的核心行为。
"""

import json
import uuid
from datetime import date, datetime, time, timedelta

import pytest

from app.models.schedule import Schedule
from app.models.schedule_audit import ScheduleAuditLog
from app.modules.schedules.audit_helpers import (
    compute_diff,
    make_schedule_audit,
    snapshot_schedule,
)


# ==================== snapshot_schedule ====================


def test_snapshot_schedule_returns_expected_fields():
    """snapshot_schedule 返回所有指定字段"""
    schedule = Schedule(
        id="s-001",
        doctor_id="d-001",
        store_id="st-001",
        tenant_id="t-001",
        schedule_date=date(2026, 6, 1),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=3,
        schedule_status="published",
        status=1,
        online_quota=5,
        offline_quota=3,
        reserved_quota=1,
        extra_quota=1,
        fee=500,
        appointment_type="normal",
    )

    result = snapshot_schedule(schedule)

    assert result is not None
    assert result["id"] == "s-001"
    assert result["doctor_id"] == "d-001"
    assert result["store_id"] == "st-001"
    assert result["tenant_id"] == "t-001"
    assert result["schedule_date"] == "2026-06-01"
    assert result["time_slot"] == "morning"
    assert result["start_time"] == "08:00:00"
    assert result["end_time"] == "12:00:00"
    assert result["total_slots"] == 10
    assert result["booked_slots"] == 3
    assert result["schedule_status"] == "published"
    assert result["status"] == 1
    assert result["online_quota"] == 5
    assert result["offline_quota"] == 3
    assert result["reserved_quota"] == 1
    assert result["extra_quota"] == 1
    assert result["fee"] == 500
    assert result["appointment_type"] == "normal"


def test_snapshot_schedule_returns_none_for_none_input():
    """输入为 None 时返回 None"""
    result = snapshot_schedule(None)
    assert result is None


def test_snapshot_schedule_serializes_dates_and_times():
    """日期和时间字段正确序列化为 ISO 格式"""
    schedule = Schedule(
        id="s-002",
        doctor_id="d-002",
        store_id="st-002",
        tenant_id="t-002",
        schedule_date=date(2026, 12, 25),
        time_slot="afternoon",
        start_time=time(14, 30),
        end_time=time(17, 45),
        total_slots=20,
        booked_slots=0,
        schedule_status="draft",
        status=1,
    )

    result = snapshot_schedule(schedule)

    assert result["schedule_date"] == "2026-12-25"
    assert result["start_time"] == "14:30:00"
    assert result["end_time"] == "17:45:00"


def test_snapshot_schedule_handles_none_optional_fields():
    """可选字段为 None 时正确处理"""
    schedule = Schedule(
        id="s-003",
        doctor_id="d-003",
        schedule_date=date(2026, 1, 1),
        total_slots=5,
        booked_slots=0,
        schedule_status="draft",
        status=1,
    )

    result = snapshot_schedule(schedule)

    assert result["store_id"] is None
    assert result["tenant_id"] is None
    assert result["time_slot"] is None
    assert result["start_time"] is None
    assert result["end_time"] is None


# ==================== compute_diff ====================


def test_compute_diff_detects_field_changes():
    """能检测字段变更"""
    before = {
        "id": "s-001",
        "schedule_status": "draft",
        "status": 0,
        "total_slots": 10,
    }
    after = {
        "id": "s-001",
        "schedule_status": "published",
        "status": 1,
        "total_slots": 10,
    }

    result = compute_diff(before, after)

    assert result is not None
    changes = result["changes"]
    assert len(changes) == 2

    changed_keys = {c["key"] for c in changes}
    assert "schedule_status" in changed_keys
    assert "status" in changed_keys

    for c in changes:
        if c["key"] == "schedule_status":
            assert c["before"] == "draft"
            assert c["after"] == "published"
        elif c["key"] == "status":
            assert c["before"] == 0
            assert c["after"] == 1


def test_compute_diff_returns_none_when_no_changes():
    """无变更时返回 None"""
    before = {"id": "s-001", "status": 1, "name": "test"}
    after = {"id": "s-001", "status": 1, "name": "test"}

    result = compute_diff(before, after)
    assert result is None


def test_compute_diff_returns_none_when_both_none():
    """两者均为 None 时返回 None"""
    result = compute_diff(None, None)
    assert result is None


def test_compute_diff_handles_none_before():
    """before 为 None 时视为新增（所有 after 字段都是变更）"""
    after = {"id": "s-001", "status": 1}

    result = compute_diff(None, after)

    assert result is not None
    changes = result["changes"]
    changed_keys = {c["key"] for c in changes}
    assert "id" in changed_keys
    assert "status" in changed_keys


def test_compute_diff_handles_none_after():
    """after 为 None 时视为删除（所有 before 字段都是变更）"""
    before = {"id": "s-001", "status": 1}

    result = compute_diff(before, None)

    assert result is not None
    changes = result["changes"]
    changed_keys = {c["key"] for c in changes}
    assert "id" in changed_keys
    assert "status" in changed_keys


def test_compute_diff_detects_date_and_time_changes():
    """能检测日期和时间字段变更（drag 操作场景）"""
    before = {
        "schedule_date": "2026-06-01",
        "start_time": "08:00:00",
        "end_time": "12:00:00",
        "time_slot": "morning",
    }
    after = {
        "schedule_date": "2026-06-02",
        "start_time": "14:00:00",
        "end_time": "17:00:00",
        "time_slot": "afternoon",
    }

    result = compute_diff(before, after)

    assert result is not None
    changes = result["changes"]
    changed_keys = {c["key"] for c in changes}
    assert "schedule_date" in changed_keys
    assert "start_time" in changed_keys
    assert "end_time" in changed_keys
    assert "time_slot" in changed_keys


# ==================== make_schedule_audit ====================


def test_make_schedule_audit_creates_valid_instance():
    """make_schedule_audit 创建有效的 ScheduleAuditLog 实例"""
    audit = make_schedule_audit(
        schedule_id="s-001",
        tenant_id="t-001",
        action="publish",
        operator_id="admin-001",
        snapshot_before='{"schedule_status": "draft"}',
        snapshot_after='{"schedule_status": "published"}',
        changes='{"changes": [{"key": "schedule_status", "before": "draft", "after": "published"}]}',
    )

    assert isinstance(audit, ScheduleAuditLog)
    assert audit.schedule_id == "s-001"
    assert audit.tenant_id == "t-001"
    assert audit.action == "publish"
    assert audit.operator_id == "admin-001"
    assert audit.snapshot_before is not None
    assert audit.snapshot_after is not None
    assert audit.changes is not None
    assert audit.id is not None  # UUID auto-generated


def test_make_schedule_audit_with_none_schedule_id():
    """批量操作时 schedule_id 可以为 None"""
    audit = make_schedule_audit(
        schedule_id=None,
        tenant_id="t-001",
        action="batch_suspend",
        operator_id="admin-001",
    )

    assert audit.schedule_id is None
    assert audit.action == "batch_suspend"


def test_make_schedule_audit_with_minimal_fields():
    """最少字段也能创建有效实例"""
    audit = make_schedule_audit(
        schedule_id="s-002",
        tenant_id="t-002",
        action="delete",
        operator_id=None,
    )

    assert audit.schedule_id == "s-002"
    assert audit.tenant_id == "t-002"
    assert audit.action == "delete"
    assert audit.operator_id is None
    assert audit.snapshot_before is None
    assert audit.snapshot_after is None
    assert audit.changes is None


def test_make_schedule_audit_generates_unique_ids():
    """每次调用生成不同的 UUID"""
    audit1 = make_schedule_audit(
        schedule_id="s-001", tenant_id="t-001", action="publish", operator_id=None,
    )
    audit2 = make_schedule_audit(
        schedule_id="s-001", tenant_id="t-001", action="publish", operator_id=None,
    )

    assert audit1.id != audit2.id


# ==================== Integration: snapshot + diff + audit ====================


def test_full_audit_flow_publish():
    """完整审计流程：快照变更前 -> 模拟状态变更 -> 快照变更后 -> 计算差异 -> 创建审计日志"""
    schedule = Schedule(
        id="s-int-001",
        doctor_id="d-001",
        store_id="st-001",
        tenant_id="t-001",
        schedule_date=date(2026, 6, 1),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        schedule_status="draft",
        status=0,
        online_quota=5,
        offline_quota=3,
        reserved_quota=1,
        extra_quota=1,
        fee=500,
    )

    # 快照变更前
    before = snapshot_schedule(schedule)
    before_json = json.dumps(before, ensure_ascii=False, default=str)

    # 模拟发布操作
    schedule.schedule_status = "published"
    schedule.status = 1

    # 快照变更后
    after = snapshot_schedule(schedule)
    after_json = json.dumps(after, ensure_ascii=False, default=str)

    # 计算差异
    changes_data = compute_diff(before, after)
    changes_json = json.dumps(changes_data, ensure_ascii=False, default=str) if changes_data else None

    # 创建审计日志
    audit = make_schedule_audit(
        schedule_id=schedule.id,
        tenant_id=schedule.tenant_id,
        action="publish",
        operator_id="admin-001",
        snapshot_before=before_json,
        snapshot_after=after_json,
        changes=changes_json,
    )

    # 验证
    assert audit.action == "publish"
    assert audit.snapshot_before is not None
    assert audit.snapshot_after is not None
    assert audit.changes is not None

    # 验证快照内容
    before_parsed = json.loads(audit.snapshot_before)
    assert before_parsed["schedule_status"] == "draft"
    assert before_parsed["status"] == 0

    after_parsed = json.loads(audit.snapshot_after)
    assert after_parsed["schedule_status"] == "published"
    assert after_parsed["status"] == 1

    # 验证差异内容
    changes_parsed = json.loads(audit.changes)
    changed_keys = {c["key"] for c in changes_parsed["changes"]}
    assert "schedule_status" in changed_keys
    assert "status" in changed_keys
