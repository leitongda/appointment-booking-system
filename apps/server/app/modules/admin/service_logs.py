"""Operation log service."""

import uuid
from datetime import datetime
from typing import List, Optional, Tuple

from sqlalchemy import and_, func, select

from app.models.admin import Admin, OperationLog


class OperationLogService:
    def __init__(self, db):
        self.db = db

    async def get_list(
        self,
        admin_id: Optional[str] = None,
        module: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
        tenant_id: Optional[str] = None,
    ) -> Tuple[List[OperationLog], int]:
        query = select(OperationLog)
        conditions = []
        joined_admin = False

        if tenant_id:
            query = query.join(Admin, Admin.id == OperationLog.admin_id)
            joined_admin = True
            conditions.append(Admin.tenant_id == tenant_id)

        if admin_id:
            conditions.append(OperationLog.admin_id == admin_id)
        if module:
            conditions.append(OperationLog.module == module)
        if start_time:
            conditions.append(OperationLog.created_at >= start_time)
        if end_time:
            conditions.append(OperationLog.created_at <= end_time)
        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(OperationLog.id))
        if joined_admin:
            count_query = count_query.select_from(OperationLog).join(Admin, Admin.id == OperationLog.admin_id)
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(OperationLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        return list(result.scalars().all()), total or 0

    async def create(self, data: dict) -> OperationLog:
        log = OperationLog(
            id=str(uuid.uuid4()),
            # 新字段：角色相关
            actor_id=data.get("actor_id"),
            actor_name=data.get("actor_name"),
            actor_role=data.get("actor_role"),
            # 保留旧字段以向后兼容
            admin_id=data.get("admin_id"),
            admin_name=data.get("admin_name"),
            tenant_id=data.get("tenant_id"),
            module=data.get("module"),
            action=data.get("action"),
            method=data.get("method"),
            path=data.get("path"),
            params=data.get("params"),
            result=data.get("result", "成功"),
            ip=data.get("ip"),
            user_agent=data.get("user_agent"),
            duration=data.get("duration"),
        )
        self.db.add(log)
        await self.db.commit()
        return log
