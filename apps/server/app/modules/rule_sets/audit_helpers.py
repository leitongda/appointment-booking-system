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


def make_rule_set_audit(
    rule_set_id: str,
    action: str,
    resource_type: str,
    resource_id: str,
    operator_id: Optional[str],
    snapshot_before: Optional[str] = None,
    snapshot_after: Optional[str] = None,
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
    )
