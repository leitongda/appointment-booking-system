"""Helpers for rule-set audit snapshots and log records."""

import json
import uuid
from datetime import date, datetime, time
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.rule_set import RuleSet
from app.models.rule_set_audit import RuleSetAuditLog


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    return value


def serialize_model(model: Any) -> Optional[dict[str, Any]]:
    if model is None:
        return None

    data: dict[str, Any] = {}
    for column in model.__table__.columns:
        data[column.name] = _serialize_value(getattr(model, column.name, None))
    return data


def _serialize_model_list(models: list[Any]) -> list[dict[str, Any]]:
    return [
        serialize_model(model) or {}
        for model in sorted(models, key=lambda item: getattr(item, "id", ""))
    ]


async def snapshot_rule_set(db, rule_set_id: str) -> Optional[str]:
    """Capture a stable aggregate snapshot for a rule-set and its child resources."""
    conditions = [RuleSet.id == rule_set_id]

    tenant_id = get_current_tenant_id()
    if tenant_id is not None:
        conditions.append(RuleSet.tenant_id == tenant_id)

    result = await db.execute(
        select(RuleSet)
        .options(
            selectinload(RuleSet.shift_types),
            selectinload(RuleSet.windows),
            selectinload(RuleSet.booking_policy),
            selectinload(RuleSet.checkin_policy),
            selectinload(RuleSet.capacity_policy),
        )
        .where(and_(*conditions))
        .execution_options(populate_existing=True)
    )
    rule_set = result.scalar_one_or_none()
    if rule_set is None:
        return None

    payload = serialize_model(rule_set) or {}
    payload["shift_types"] = _serialize_model_list(list(rule_set.shift_types or []))
    payload["windows"] = _serialize_model_list(list(rule_set.windows or []))
    payload["booking_policy"] = serialize_model(rule_set.booking_policy)
    payload["checkin_policy"] = serialize_model(rule_set.checkin_policy)
    payload["capacity_policy"] = serialize_model(rule_set.capacity_policy)

    return json.dumps(payload, ensure_ascii=False, default=str)


def _diff_value(key: str, before: Any, after: Any) -> dict[str, Any]:
    """Compute diff for a single value."""
    return {"key": key, "before": before, "after": after}


def _diff_dict(before: dict[str, Any], after: dict[str, Any]) -> list[dict[str, Any]]:
    """Compute diff between two dictionaries recursively."""
    changes: list[dict[str, Any]] = []
    all_keys = set(before.keys()) | set(after.keys())

    for key in all_keys:
        b_val = before.get(key)
        a_val = after.get(key)

        if b_val == a_val:
            continue

        if isinstance(b_val, dict) and isinstance(a_val, dict):
            nested_changes = _diff_dict(b_val, a_val)
            if nested_changes:
                changes.append({"key": key, "nested": nested_changes})
        elif isinstance(b_val, list) and isinstance(a_val, list):
            list_changes = _diff_list(b_val, a_val)
            if list_changes:
                changes.append({"key": key, "nested": list_changes})
        else:
            changes.append(_diff_value(key, b_val, a_val))

    return changes


def _diff_list(before: list[Any], after: list[Any]) -> list[dict[str, Any]]:
    """Compute diff between two lists of dictionaries (e.g., windows, shift_types)."""
    changes: list[dict[str, Any]] = []

    before_by_id = {item.get("id"): item for item in before if item.get("id")}
    after_by_id = {item.get("id"): item for item in after if item.get("id")}

    all_ids = set(before_by_id.keys()) | set(after_by_id.keys())

    for item_id in sorted(all_ids):
        b_item = before_by_id.get(item_id)
        a_item = after_by_id.get(item_id)

        if b_item is None:
            changes.append({"key": f"[新增] {item_id}", "after": a_item, "before": None})
        elif a_item is None:
            changes.append({"key": f"[删除] {item_id}", "before": b_item, "after": None})
        else:
            item_changes = _diff_dict(b_item, a_item)
            if item_changes:
                changes.append({"key": item_id, "nested": item_changes})

    return changes


def compute_rule_set_diff(before: Optional[str], after: Optional[str]) -> Optional[dict[str, Any]]:
    """
    Compute field-level diff between two rule set snapshots.

    Args:
        before: JSON string of before snapshot
        after: JSON string of after snapshot

    Returns:
        Dict with changes structure, or None if both snapshots are None/empty
    """
    if not before and not after:
        return None

    try:
        before_dict: dict[str, Any] = json.loads(before) if before else {}
        after_dict: dict[str, Any] = json.loads(after) if after else {}
    except (json.JSONDecodeError, TypeError):
        return None

    changes: list[dict[str, Any]] = []

    for key in set(before_dict.keys()) | set(after_dict.keys()):
        b_val = before_dict.get(key)
        a_val = after_dict.get(key)

        if b_val == a_val:
            continue

        if isinstance(b_val, dict) and isinstance(a_val, dict):
            nested_changes = _diff_dict(b_val, a_val)
            if nested_changes:
                changes.append({"key": key, "nested": nested_changes})
        elif isinstance(b_val, list) and isinstance(a_val, list):
            list_changes = _diff_list(b_val, a_val)
            if list_changes:
                changes.append({"key": key, "nested": list_changes})
        else:
            changes.append(_diff_value(key, b_val, a_val))

    return {"changes": changes} if changes else None


def make_rule_set_audit(
    rule_set_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    operator_id: Optional[str],
    snapshot_before: Optional[str] = None,
    snapshot_after: Optional[str] = None,
    changes: Optional[str] = None,
) -> RuleSetAuditLog:
    return RuleSetAuditLog(
        id=str(uuid.uuid4()),
        rule_set_id=rule_set_id,
        tenant_id=get_current_tenant_id() or "",
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        operator_id=operator_id,
        snapshot_before=snapshot_before,
        snapshot_after=snapshot_after,
        changes=changes,
    )
