"""排班审计日志辅助函数

提供排班快照、差异计算和审计日志构造功能。
遵循 app/modules/rule_sets/audit_helpers.py 的模式。
"""

import json
import uuid
from datetime import date, datetime, time
from typing import Any, Optional

from app.models.schedule import Schedule
from app.models.schedule_audit import ScheduleAuditLog


def _serialize_value(value: Any) -> Any:
    """序列化特殊类型为 JSON 兼容格式。"""
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def snapshot_schedule(schedule: Schedule) -> Optional[dict[str, Any]]:
    """将 Schedule 对象序列化为字典快照。

    快照字段: id, doctor_id, store_id, schedule_date, time_slot,
    start_time, end_time, total_slots, booked_slots, schedule_status,
    status, online_quota, offline_quota, reserved_quota, extra_quota,
    fee, appointment_type, tenant_id, template_id, room_id, shift_type_id,
    rule_set_id, start_at, end_at, timezone。

    Args:
        schedule: Schedule ORM 实例

    Returns:
        序列化后的字典，schedule 为 None 时返回 None。
    """
    if schedule is None:
        return None

    fields = [
        "id", "doctor_id", "store_id", "schedule_date", "time_slot",
        "start_time", "end_time", "total_slots", "booked_slots",
        "schedule_status", "status", "online_quota", "offline_quota",
        "reserved_quota", "extra_quota", "fee", "appointment_type",
        "tenant_id", "template_id", "room_id", "shift_type_id",
        "rule_set_id", "start_at", "end_at", "timezone",
    ]

    data: dict[str, Any] = {}
    for field in fields:
        data[field] = _serialize_value(getattr(schedule, field, None))
    return data


def compute_diff(before: Optional[dict], after: Optional[dict]) -> Optional[dict[str, Any]]:
    """计算两个快照之间的字段级差异。

    Args:
        before: 操作前快照字典
        after: 操作后快照字典

    Returns:
        包含 changes 列表的字典，无差异或两者均为 None 时返回 None。
    """
    if not before and not after:
        return None

    before = before or {}
    after = after or {}

    changes: list[dict[str, Any]] = []
    all_keys = set(before.keys()) | set(after.keys())

    for key in sorted(all_keys):
        b_val = before.get(key)
        a_val = after.get(key)
        if b_val == a_val:
            continue
        changes.append({
            "key": key,
            "before": b_val,
            "after": a_val,
        })

    return {"changes": changes} if changes else None


def make_schedule_audit(
    schedule_id: Optional[str],
    tenant_id: str,
    action: str,
    operator_id: Optional[str],
    snapshot_before: Optional[str] = None,
    snapshot_after: Optional[str] = None,
    changes: Optional[str] = None,
) -> ScheduleAuditLog:
    """构造 ScheduleAuditLog 实例。

    Args:
        schedule_id: 排班 ID（批量操作可传 None）
        tenant_id: 租户 ID
        action: 操作类型
        operator_id: 操作人 ID
        snapshot_before: 操作前快照 JSON 字符串
        snapshot_after: 操作后快照 JSON 字符串
        changes: 变更差异 JSON 字符串

    Returns:
        未持久化的 ScheduleAuditLog 实例。
    """
    return ScheduleAuditLog(
        id=str(uuid.uuid4()),
        schedule_id=schedule_id,
        tenant_id=tenant_id,
        action=action,
        operator_id=operator_id,
        snapshot_before=snapshot_before,
        snapshot_after=snapshot_after,
        changes=changes,
    )
