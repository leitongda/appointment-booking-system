"""
签到组管理服务

负责签到组及成员的 CRUD 操作
"""
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.account import Account
from app.models.attendance import AttendanceGroup, AttendanceGroupMember
from app.utils.audit import set_create_audit, set_update_audit


class AttendanceGroupService:
    """签到组服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self._tenant_id = get_current_tenant_id()

    def _apply_tenant(self, query):
        """对查询施加租户过滤"""
        if self._tenant_id:
            query = query.where(AttendanceGroup.tenant_id == self._tenant_id)
        return query

    async def get_list(
        self,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """获取签到组列表（含 member_count 子查询）

        Returns:
            (签到组字典列表, 总数)
        """
        conditions = []
        if keyword:
            conditions.append(
                AttendanceGroup.name.ilike(f"%{keyword}%")
            )

        # 成员数子查询
        member_count_sq = (
            select(func.count(AttendanceGroupMember.id))
            .where(AttendanceGroupMember.group_id == AttendanceGroup.id)
            .correlate(AttendanceGroup)
            .scalar_subquery()
            .label("member_count")
        )

        # 总数
        count_q = select(func.count(AttendanceGroup.id))
        count_q = self._apply_tenant(count_q)
        if conditions:
            count_q = count_q.where(and_(*conditions))
        total = (await self.db.execute(count_q)).scalar_one() or 0

        # 数据
        data_q = select(
            AttendanceGroup,
            member_count_sq,
        )
        data_q = self._apply_tenant(data_q)
        if conditions:
            data_q = data_q.where(and_(*conditions))
        data_q = data_q.order_by(AttendanceGroup.created_at.desc())
        data_q = data_q.offset((page - 1) * page_size).limit(page_size)

        rows = (await self.db.execute(data_q)).all()

        items = []
        for group, mc in rows:
            items.append({
                "id": group.id,
                "name": group.name,
                "description": group.description,
                "check_method": group.check_method,
                "location_lat": group.location_lat,
                "location_lng": group.location_lng,
                "location_radius": group.location_radius,
                "wifi_ssid": group.wifi_ssid,
                "wifi_ssids": group.wifi_ssids,
                "device_whitelist": group.device_whitelist,
                "require_device_bind": group.require_device_bind,
                "enabled": group.enabled,
                "member_count": mc or 0,
                "created_at": group.created_at.isoformat() if group.created_at else None,
            })

        return items, total

    async def get_by_id(self, group_id: str) -> AttendanceGroup | None:
        """获取签到组详情"""
        q = select(AttendanceGroup).where(AttendanceGroup.id == group_id)
        q = self._apply_tenant(q)
        result = await self.db.execute(q)
        return result.scalar_one_or_none()

    async def create(self, data: dict, operator_id: str | None = None) -> AttendanceGroup:
        """创建签到组"""
        group = AttendanceGroup(
            id=str(uuid.uuid4()),
            tenant_id=self._tenant_id,
            name=data["name"],
            description=data.get("description"),
            check_method=data.get("check_method", "gps"),
            location_lat=data.get("location_lat"),
            location_lng=data.get("location_lng"),
            location_radius=data.get("location_radius", 300),
            wifi_ssid=data.get("wifi_ssid"),
            wifi_ssids=data.get("wifi_ssids"),
            device_whitelist=data.get("device_whitelist"),
            require_device_bind=data.get("require_device_bind", False),
            enabled=data.get("enabled", True),
        )

        set_create_audit(group, operator_id)

        self.db.add(group)
        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def update(
        self,
        group_id: str,
        data: dict,
        operator_id: str | None = None,
    ) -> AttendanceGroup | None:
        """更新签到组"""
        group = await self.get_by_id(group_id)
        if not group:
            return None

        updatable_fields = [
            "name", "description", "check_method",
            "location_lat", "location_lng", "location_radius",
            "wifi_ssid", "wifi_ssids", "device_whitelist",
            "require_device_bind", "enabled",
        ]
        for field in updatable_fields:
            if field in data and data[field] is not None:
                setattr(group, field, data[field])

        set_update_audit(group, operator_id)

        await self.db.commit()
        await self.db.refresh(group)
        return group

    async def delete(self, group_id: str) -> bool:
        """删除签到组"""
        group = await self.get_by_id(group_id)
        if not group:
            return False

        await self.db.delete(group)
        await self.db.commit()
        return True

    async def add_members(self, group_id: str, account_ids: list[str]) -> int:
        """批量添加成员，返回实际新增数量"""
        group = await self.get_by_id(group_id)
        if not group:
            return 0

        # 查询已存在的成员
        existing_q = select(AttendanceGroupMember.account_id).where(
            AttendanceGroupMember.group_id == group_id,
            AttendanceGroupMember.account_id.in_(account_ids),
        )
        existing_ids = set((await self.db.execute(existing_q)).scalars().all())

        added = 0
        for aid in account_ids:
            if aid in existing_ids:
                continue
            member = AttendanceGroupMember(
                id=str(uuid.uuid4()),
                group_id=group_id,
                account_id=aid,
                tenant_id=self._tenant_id,
            )
            self.db.add(member)
            added += 1

        if added:
            await self.db.commit()

        return added

    async def remove_member(self, group_id: str, account_id: str) -> bool:
        """移除单个成员"""
        q = select(AttendanceGroupMember).where(
            AttendanceGroupMember.group_id == group_id,
            AttendanceGroupMember.account_id == account_id,
        )
        if self._tenant_id:
            q = q.where(AttendanceGroupMember.tenant_id == self._tenant_id)

        member = (await self.db.execute(q)).scalar_one_or_none()
        if not member:
            return False

        await self.db.delete(member)
        await self.db.commit()
        return True

    async def get_members(
        self,
        group_id: str,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[dict], int]:
        """获取组成员列表（分页）

        Returns:
            (成员字典列表, 总数)
        """
        base_cond = AttendanceGroupMember.group_id == group_id
        if self._tenant_id:
            base_cond = and_(base_cond, AttendanceGroupMember.tenant_id == self._tenant_id)

        # 总数
        count_q = select(func.count(AttendanceGroupMember.id)).where(base_cond)
        total = (await self.db.execute(count_q)).scalar_one() or 0

        # 数据：join Account 取 name
        data_q = (
            select(AttendanceGroupMember, Account.name)
            .outerjoin(Account, AttendanceGroupMember.account_id == Account.id)
            .where(base_cond)
            .order_by(AttendanceGroupMember.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        rows = (await self.db.execute(data_q)).all()

        items = []
        for member, account_name in rows:
            items.append({
                "id": member.id,
                "account_id": member.account_id,
                "account_name": account_name,
                "created_at": member.created_at.isoformat() if member.created_at else None,
            })

        return items, total
