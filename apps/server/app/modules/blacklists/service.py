"""黑名单服务"""
import uuid
from datetime import datetime, timedelta

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.middleware.tenant_context import get_current_tenant_id
from app.models.blacklist import Blacklist
from app.models.store import Store
from app.models.user import User
from app.schemas.blacklist import BlacklistCheckResult, BlacklistCreate
from app.utils.audit import set_create_audit, set_update_audit


class BlacklistService:
    """黑名单服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-14）。查询/写入以锚点强过滤；
            未传入时才回退请求上下文（兼容预约检查等内部调用）。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _tenant(self) -> str | None:
        """账号锚点优先，未提供时回退请求上下文。"""
        if self.tenant_id is not None:
            return self.tenant_id
        return get_current_tenant_id()

    async def get_list(
        self,
        keyword: str | None = None,
        store_id: str | None = None,
        status: int | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[dict], int]:
        """获取黑名单列表"""
        tenant_id = self._tenant()
        query = select(Blacklist).options(
            selectinload(Blacklist.user),
            selectinload(Blacklist.store)
        )
        conditions = []

        if tenant_id:
            conditions.append(Blacklist.tenant_id == tenant_id)

        # 关键词搜索（用户昵称/电话/身份证/黑名单关键词）
        if keyword:
            # 需要搜索关联用户的信息
            user_subquery = select(User.id).where(
                or_(
                    User.nickname.ilike(f"%{keyword}%"),
                    User.phone.ilike(f"%{keyword}%")
                )
            )
            conditions.append(
                or_(
                    Blacklist.keyword.ilike(f"%{keyword}%"),
                    Blacklist.user_id.in_(user_subquery)
                )
            )

        if store_id:
            conditions.append(Blacklist.store_id == store_id)

        if status is not None:
            conditions.append(Blacklist.status == status)

        if conditions:
            query = query.where(and_(*conditions))

        # 统计总数
        count_query = select(func.count(Blacklist.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        # 分页查询
        query = query.order_by(Blacklist.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        blacklists = result.unique().scalars().all()

        data = []
        for item in blacklists:
            user = item.user
            store = item.store

            data.append({
                'id': item.id,
                'userId': item.user_id,
                'userName': user.nickname if user else None,
                'userPhone': user.phone if user else None,
                'storeId': item.store_id,
                'storeName': store.name if store else '全部门店',
                'keyword': item.keyword,
                'reason': item.reason,
                'noShowCount': item.no_show_count,
                'source': item.source,
                'expireAt': item.expire_at.isoformat() if item.expire_at else None,
                'releasedAt': item.released_at.isoformat() if item.released_at else None,
                'status': item.status,
                'createdAt': item.created_at.isoformat() if item.created_at else None,
            })

        return data, total or 0

    async def create(self, data: BlacklistCreate, operator_id: str | None = None) -> dict:
        """添加黑名单"""
        tenant_id = self._tenant()

        if tenant_id and data.user_id:
            user = await self.db.scalar(select(User).where(User.id == data.user_id))
            if not user or user.tenant_id != tenant_id:
                raise ValueError("用户不属于当前租户")

        if tenant_id and data.store_id:
            store = await self.db.scalar(select(Store).where(Store.id == data.store_id))
            if not store or store.tenant_id != tenant_id:
                raise ValueError("门店不属于当前租户")

        blacklist = Blacklist(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=data.user_id,
            store_id=data.store_id,
            keyword=data.keyword,
            reason=data.reason,
            source=1,  # 手动添加
            expire_at=data.expire_at,
            status=1,
        )
        set_create_audit(blacklist, operator_id)

        self.db.add(blacklist)
        await self.db.commit()
        await self.db.refresh(blacklist)

        # 加载关联数据
        await self.db.execute(
            select(Blacklist)
            .options(selectinload(Blacklist.user), selectinload(Blacklist.store))
            .where(Blacklist.id == blacklist.id)
        )

        return {
            'id': blacklist.id,
            'userId': blacklist.user_id,
            'storeId': blacklist.store_id,
            'keyword': blacklist.keyword,
            'reason': blacklist.reason,
            'source': blacklist.source,
            'expireAt': blacklist.expire_at.isoformat() if blacklist.expire_at else None,
            'status': blacklist.status,
            'createdAt': blacklist.created_at.isoformat() if blacklist.created_at else None,
        }

    async def remove(self, blacklist_id: str, operator_id: str | None = None) -> bool:
        """移除黑名单（解禁）"""
        tenant_id = self._tenant()
        query = select(Blacklist).where(Blacklist.id == blacklist_id)
        if tenant_id:
            query = query.where(Blacklist.tenant_id == tenant_id)
        result = await self.db.execute(query)
        blacklist = result.scalar_one_or_none()

        if not blacklist:
            return False

        blacklist.status = 0
        blacklist.released_at = datetime.now()
        set_update_audit(blacklist, operator_id)
        await self.db.commit()
        return True

    async def delete(self, blacklist_id: str) -> bool:
        """删除黑名单记录"""
        tenant_id = self._tenant()
        query = select(Blacklist).where(Blacklist.id == blacklist_id)
        if tenant_id:
            query = query.where(Blacklist.tenant_id == tenant_id)
        result = await self.db.execute(query)
        blacklist = result.scalar_one_or_none()

        if not blacklist:
            return False

        await self.db.delete(blacklist)
        await self.db.commit()
        return True

    async def check_blacklist(
        self,
        user_id: str | None = None,
        phone: str | None = None,
        id_card: str | None = None,
        store_id: str | None = None,
    ) -> BlacklistCheckResult:
        """检查是否在黑名单中"""
        tenant_id = self._tenant()
        conditions = [Blacklist.status == 1]

        if tenant_id:
            conditions.append(Blacklist.tenant_id == tenant_id)

        # 检查是否过期
        now = datetime.now()
        conditions.append(
            or_(
                Blacklist.expire_at.is_(None),
                Blacklist.expire_at > now
            )
        )

        # 门店条件：要么没有指定门店（全部门店），要么指定的门店匹配
        if store_id:
            conditions.append(
                or_(
                    Blacklist.store_id.is_(None),
                    Blacklist.store_id == store_id
                )
            )

        # 匹配条件（满足任一即被拉黑）
        match_conditions = []

        if user_id:
            match_conditions.append(Blacklist.user_id == user_id)

        if phone:
            match_conditions.append(Blacklist.keyword == phone)

        if id_card:
            match_conditions.append(Blacklist.keyword == id_card)

        if not match_conditions:
            return BlacklistCheckResult(is_blacklisted=False)

        conditions.append(or_(*match_conditions))

        result = await self.db.execute(
            select(Blacklist).where(and_(*conditions)).limit(1)
        )
        blacklist = result.scalar_one_or_none()

        if blacklist:
            return BlacklistCheckResult(
                is_blacklisted=True,
                reason=blacklist.reason,
                expire_at=blacklist.expire_at
            )

        return BlacklistCheckResult(is_blacklisted=False)

    async def auto_add_blacklist(
        self,
        user_id: str,
        no_show_count: int,
        blacklist_days: int,
    ) -> dict | None:
        """自动添加到黑名单（爽约触发）"""
        tenant_id = self._tenant()
        # 检查是否已在黑名单中
        existing_query = select(Blacklist).where(
            Blacklist.user_id == user_id,
            Blacklist.status == 1,
        )
        if tenant_id:
            existing_query = existing_query.where(Blacklist.tenant_id == tenant_id)
        existing = await self.db.execute(existing_query)
        if existing.scalar_one_or_none():
            return None

        # 计算解禁时间
        expire_at = datetime.now() + timedelta(days=blacklist_days)

        blacklist = Blacklist(
            id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            user_id=user_id,
            reason=f'爽约{no_show_count}次，自动加入黑名单',
            no_show_count=no_show_count,
            source=2,  # 自动触发
            expire_at=expire_at,
            status=1,
        )

        self.db.add(blacklist)
        await self.db.commit()
        await self.db.refresh(blacklist)

        return {
            'id': blacklist.id,
            'userId': blacklist.user_id,
            'reason': blacklist.reason,
            'noShowCount': blacklist.no_show_count,
            'source': blacklist.source,
            'expireAt': blacklist.expire_at.isoformat() if blacklist.expire_at else None,
        }

    async def auto_release_expired(self) -> list[dict]:
        """自动解禁到期的黑名单"""
        now = datetime.now()
        tenant_id = self._tenant()

        # 查询到期的黑名单
        query = (
            select(Blacklist)
            .options(selectinload(Blacklist.user))
            .where(
                and_(
                    Blacklist.status == 1,
                    Blacklist.expire_at <= now,
                    Blacklist.expire_at.isnot(None)
                )
            )
        )
        if tenant_id:
            query = query.where(Blacklist.tenant_id == tenant_id)
        result = await self.db.execute(query)
        expired_list = result.unique().scalars().all()

        released = []
        for item in expired_list:
            item.status = 0
            item.released_at = now

            user = item.user
            released.append({
                'id': item.id,
                'userId': item.user_id,
                'userName': user.nickname if user else None,
                'userPhone': user.phone if user else None,
                'keyword': item.keyword,
                'expireAt': item.expire_at.isoformat() if item.expire_at else None,
            })

        if released:
            await self.db.commit()

        return released
