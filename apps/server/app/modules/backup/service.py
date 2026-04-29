"""租户数据备份与恢复服务"""
import json
import hashlib
import time
from datetime import datetime
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import class_mapper

from app.models.tenant import Tenant
from app.models.store import Store
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.admin import Admin
from app.models.schedule import Schedule
from app.models.appointment import Appointment


BACKUP_MODELS = [
    ("stores", Store, "tenant_id"),
    ("departments", Department, "tenant_id"),
    ("doctors", Doctor, "tenant_id"),
    ("admins", Admin, "tenant_id"),
    ("schedules", Schedule, "tenant_id"),
    ("appointments", Appointment, "tenant_id"),
]


class BackupService:
    """租户数据备份与恢复"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def export_tenant_data(self, tenant_id: str) -> dict:
        """导出租户全部数据为 JSON"""
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("租户不存在")

        start_time = time.time()
        data = {}

        for name, model, tenant_col in BACKUP_MODELS:
            col = getattr(model, tenant_col)
            result = await self.db.execute(select(model).where(col == tenant_id))
            items = list(result.scalars().all())

            mapper = class_mapper(model)
            rows = []
            for item in items:
                row = {}
                for col_obj in mapper.columns:
                    val = getattr(item, col_obj.name, None)
                    if val is not None:
                        if hasattr(val, 'isoformat'):
                            val = val.isoformat()
                        elif isinstance(val, (bytes, bytearray)):
                            val = val.hex()
                    row[col_obj.name] = val
                rows.append(row)
            data[name] = rows

        tenant_data = {}
        tenant_mapper = class_mapper(Tenant)
        for col_obj in tenant_mapper.columns:
            val = getattr(tenant, col_obj.name, None)
            if val is not None and hasattr(val, 'isoformat'):
                val = val.isoformat()
            tenant_data[col_obj.name] = val
        data["tenant"] = [tenant_data]

        metadata = {
            "tenant_id": tenant_id,
            "tenant_code": tenant.tenant_code,
            "exported_at": datetime.utcnow().isoformat(),
            "version": "1.0",
            "duration_ms": int((time.time() - start_time) * 1000),
        }

        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        checksum = hashlib.sha256(content.encode()).hexdigest()

        return {
            "metadata": metadata,
            "data": data,
            "checksum": checksum,
            "stats": {k: len(v) for k, v in data.items()},
        }

    async def import_tenant_data(
        self,
        tenant_id: str,
        backup_data: dict,
        overwrite: bool = False,
        actor_id: Optional[str] = None,
    ) -> dict:
        """导入备份数据到指定租户"""
        tenant = await self.db.get(Tenant, tenant_id)
        if not tenant:
            raise ValueError("目标租户不存在")

        data = backup_data.get("data", {})
        content = json.dumps(data, sort_keys=True, ensure_ascii=False)
        expected_checksum = hashlib.sha256(content.encode()).hexdigest()
        actual_checksum = backup_data.get("checksum", "")
        if actual_checksum and actual_checksum != expected_checksum:
            raise ValueError("备份数据校验失败，文件可能已损坏")

        imported = {}
        skipped = {}
        errors = []

        for name, model, tenant_col in BACKUP_MODELS:
            rows = data.get(name, [])
            if not rows:
                imported[name] = 0
                continue

            count = 0
            skip_count = 0

            for row in rows:
                try:
                    existing = await self.db.get(model, row.get("id"))
                    if existing:
                        if overwrite:
                            await self.db.delete(existing)
                        else:
                            skip_count += 1
                            continue

                    row[tenant_col] = tenant_id

                    for field in ("created_at", "updated_at", "created_by", "updated_by"):
                        if field in row and row[field] and isinstance(row[field], str):
                            try:
                                row[field] = datetime.fromisoformat(row[field])
                            except (ValueError, TypeError):
                                row[field] = datetime.utcnow()

                    instance = model(**row)
                    self.db.add(instance)
                    count += 1

                except Exception as e:
                    errors.append({"entity": name, "id": row.get("id"), "error": str(e)})
                    continue

            imported[name] = count
            if skip_count > 0:
                skipped[name] = skip_count

        await self.db.commit()

        return {
            "tenant_id": tenant_id,
            "imported": imported,
            "skipped": skipped,
            "errors": errors,
        }

    async def precheck_import(self, tenant_id: str, backup_data: dict) -> dict:
        """导入前预检：检查 ID 冲突、数据量"""
        data = backup_data.get("data", {})
        conflicts = {}
        totals = {}

        for name, model, tenant_col in BACKUP_MODELS:
            rows = data.get(name, [])
            totals[name] = len(rows)

            conflict_count = 0
            for row in rows:
                rid = row.get("id")
                if rid:
                    existing = await self.db.get(model, rid)
                    if existing:
                        conflict_count += 1

            if conflict_count > 0:
                conflicts[name] = conflict_count

        return {
            "tenant_id": tenant_id,
            "totals": totals,
            "conflicts": conflicts,
            "has_conflicts": len(conflicts) > 0,
        }
