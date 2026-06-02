"""租户关键数据变更追踪

对 Tenant / Admin / Store / Doctor 的创建、更新、删除操作，
记录变更前后快照到 TenantAuditLog。

使用方式（在 service 层调用）：
    tracker = AuditTracker(db)
    await tracker.track_update(
        tenant, tenant_id=tenant.id,
        resource_type="tenant", resource_id=tenant.id,
        actor_id=admin_id, actor_type="admin", actor_name=admin_name,
    )
"""
import json
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import inspect as sa_inspect
from sqlalchemy.orm import class_mapper

from app.models.tenant_audit_log import TenantAuditLog


TRACKED_MODELS = {
    "tenant": [
        "name", "status", "subscription_plan_id", "billing_cycle",
        "max_stores", "max_admins", "max_doctors", "max_appointments_per_month",
        "max_lowcode_pages", "max_miniapp_instances",
        "features", "branding_config", "contact_name", "contact_phone",
        "contact_email", "address", "custom_domain", "subdomain",
    ],
    "admin": [
        "username", "name", "phone", "email", "status", "role_id",
        "store_ids", "is_super_admin",
    ],
    "store": [
        "name", "code", "status", "address", "phone", "business_hours",
    ],
    "doctor": [
        "name", "title", "status", "department_id", "store_id",
        "description", "specialties",
    ],
}

SENSITIVE_FIELDS = {"password_hash", "password"}


def _str_val(val):
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    return str(val)


class AuditTracker:
    """租户数据变更追踪器"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _snapshot(self, instance, fields: list[str]) -> dict:
        result = {}
        for field in fields:
            if field in SENSITIVE_FIELDS:
                continue
            result[field] = _str_val(getattr(instance, field, None))
        return result

    def _get_fields(self, resource_type: str) -> list[str]:
        return TRACKED_MODELS.get(resource_type, [])

    async def track_create(
        self,
        instance,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        actor_id: Optional[str] = None,
        actor_type: str = "system",
        actor_name: Optional[str] = None,
    ) -> TenantAuditLog:
        fields = self._get_fields(resource_type)
        after_data = self._snapshot(instance, fields) if fields else {"id": resource_id}

        log = TenantAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            event_type="create",
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            resource_type=resource_type,
            resource_id=resource_id,
            action="create",
            before_data=None,
            after_data=json.dumps(after_data, ensure_ascii=False, default=str),
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def track_update(
        self,
        instance,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        actor_id: Optional[str] = None,
        actor_type: str = "admin",
        actor_name: Optional[str] = None,
    ) -> Optional[TenantAuditLog]:
        fields = self._get_fields(resource_type)
        changes = {}

        state = sa_inspect(instance)
        for attr in state.attrs:
            field = attr.key
            if field in SENSITIVE_FIELDS:
                continue
            if fields and field not in fields:
                continue

            history = state.get_history(field, True)
            if history.has_changes():
                old_val = history.deleted[0] if history.deleted else None
                new_val = history.added[0] if history.added else None
                changes[field] = {
                    "before": _str_val(old_val),
                    "after": _str_val(new_val),
                }

        if not changes:
            return None

        log = TenantAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            event_type="update",
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            resource_type=resource_type,
            resource_id=resource_id,
            action="update",
            before_data=json.dumps({k: v["before"] for k, v in changes.items()}, ensure_ascii=False, default=str),
            after_data=json.dumps({k: v["after"] for k, v in changes.items()}, ensure_ascii=False, default=str),
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def track_delete(
        self,
        instance,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        actor_id: Optional[str] = None,
        actor_type: str = "admin",
        actor_name: Optional[str] = None,
    ) -> TenantAuditLog:
        fields = self._get_fields(resource_type)
        before_data = self._snapshot(instance, fields) if fields else {"id": resource_id}

        log = TenantAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            event_type="delete",
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            resource_type=resource_type,
            resource_id=resource_id,
            action="delete",
            before_data=json.dumps(before_data, ensure_ascii=False, default=str),
            after_data=None,
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def track_status_change(
        self,
        tenant_id: str,
        resource_type: str,
        resource_id: str,
        old_status,
        new_status,
        actor_id: Optional[str] = None,
        actor_type: str = "admin",
        actor_name: Optional[str] = None,
    ) -> TenantAuditLog:
        log = TenantAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            event_type="status_change",
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            resource_type=resource_type,
            resource_id=resource_id,
            action="status_change",
            before_data=json.dumps({"status": _str_val(old_status)}, ensure_ascii=False),
            after_data=json.dumps({"status": _str_val(new_status)}, ensure_ascii=False),
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.flush()
        return log

    async def track_subscription_change(
        self,
        tenant_id: str,
        old_plan_id: Optional[str],
        new_plan_id: str,
        old_end_at: Optional[str],
        new_end_at: str,
        actor_id: Optional[str] = None,
        actor_type: str = "admin",
        actor_name: Optional[str] = None,
    ) -> TenantAuditLog:
        log = TenantAuditLog(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            event_type="subscription_change",
            actor_id=actor_id,
            actor_type=actor_type,
            actor_name=actor_name,
            resource_type="tenant",
            resource_id=tenant_id,
            action="subscription_change",
            before_data=json.dumps({
                "subscription_plan_id": old_plan_id,
                "subscription_end_at": old_end_at,
            }, ensure_ascii=False, default=str),
            after_data=json.dumps({
                "subscription_plan_id": new_plan_id,
                "subscription_end_at": new_end_at,
            }, ensure_ascii=False, default=str),
            created_at=datetime.utcnow(),
        )
        self.db.add(log)
        await self.db.flush()
        return log
