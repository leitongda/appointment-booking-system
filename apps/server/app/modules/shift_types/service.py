"""
班次类型管理服务

负责班次类型的 CRUD 操作
"""
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id

from app.models.rule_set import ShiftType
from app.utils.audit import set_create_audit, set_update_audit


class ShiftTypeService:
    """班次类型服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant(self, tenant_id: str | None) -> str | None:
        """显式锚点优先；未传时回退请求上下文（R1-12）"""
        return tenant_id if tenant_id is not None else get_current_tenant_id()

    async def get_list(
        self,
        enabled: bool | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
        tenant_id: str | None = None,
    ) -> tuple[list[ShiftType], int]:
        """获取班次类型列表

        Args:
            enabled: 是否启用
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            (班次类型列表, 总数)
        """
        # 构建查询条件
        conditions = []

        tenant_id = self._tenant(tenant_id)
        if tenant_id:
            conditions.append(ShiftType.tenant_id == tenant_id)

        if enabled is not None:
            conditions.append(ShiftType.enabled == enabled)

        if keyword:
            conditions.append(
                (ShiftType.name.ilike(f"%{keyword}%")) |
                (ShiftType.code.ilike(f"%{keyword}%"))
            )

        # 查询总数
        count_query = select(func.count(ShiftType.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        # 查询数据
        query = select(ShiftType)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(ShiftType.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        shift_types = result.scalars().all()

        return list(shift_types), total

    async def get_all_enabled(self, tenant_id: str | None = None) -> list[ShiftType]:
        """获取所有启用的班次类型

        Args:
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            班次类型列表
        """
        tenant_id = self._tenant(tenant_id)
        stmt = select(ShiftType).where(ShiftType.enabled == True)  # noqa: E712
        if tenant_id:
            stmt = stmt.where(ShiftType.tenant_id == tenant_id)
        result = await self.db.execute(stmt.order_by(ShiftType.code.asc()))
        return list(result.scalars().all())

    async def get_by_id(
        self, shift_type_id: str, tenant_id: str | None = None
    ) -> ShiftType | None:
        """获取班次类型详情

        Args:
            shift_type_id: 班次类型ID
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            班次类型
        """
        tenant_id = self._tenant(tenant_id)
        stmt = select(ShiftType).where(ShiftType.id == shift_type_id)
        if tenant_id:
            stmt = stmt.where(ShiftType.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str, tenant_id: str | None = None) -> ShiftType | None:
        """根据代码获取班次类型（按当前租户过滤）

        Args:
            code: 类型代码
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            班次类型
        """
        # 租户隔离：编码唯一性检查限定在当前租户范围内；
        # 无租户上下文时限定平台级记录（tenant_id IS NULL）
        tenant_id = self._tenant(tenant_id)
        conditions = [ShiftType.code == code]
        if tenant_id:
            conditions.append(ShiftType.tenant_id == tenant_id)
        else:
            conditions.append(ShiftType.tenant_id.is_(None))
        result = await self.db.execute(select(ShiftType).where(and_(*conditions)))
        return result.scalar_one_or_none()

    async def create(
        self,
        code: str,
        name: str,
        description: str | None = None,
        enabled: bool = True,
        operator_id: str | None = None,
        tenant_id: str | None = None,
    ) -> ShiftType:
        """创建班次类型

        Args:
            code: 类型代码
            name: 类型名称
            description: 描述
            enabled: 是否启用
            operator_id: 操作人ID
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            创建的班次类型

        Raises:
            ValueError: 代码已存在
        """
        tenant_id = self._tenant(tenant_id)

        # 检查代码是否已存在（同租户内）
        existing = await self.get_by_code(code, tenant_id=tenant_id)
        if existing:
            raise ValueError(f"类型代码 '{code}' 已存在")

        shift_type = ShiftType(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=description,
            enabled=enabled,
            tenant_id=tenant_id,
        )

        set_create_audit(shift_type, operator_id)

        self.db.add(shift_type)
        await self.db.commit()
        await self.db.refresh(shift_type)

        return shift_type

    async def update(
        self,
        shift_type_id: str,
        name: str | None = None,
        description: str | None = None,
        enabled: bool | None = None,
        operator_id: str | None = None,
        tenant_id: str | None = None,
    ) -> ShiftType | None:
        """更新班次类型

        Args:
            shift_type_id: 班次类型ID
            name: 类型名称
            description: 描述
            enabled: 是否启用
            operator_id: 操作人ID
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            更新后的班次类型
        """
        tenant_id = self._tenant(tenant_id)
        shift_type = await self.get_by_id(shift_type_id, tenant_id=tenant_id)
        if not shift_type:
            return None

        if name is not None:
            shift_type.name = name
        if description is not None:
            shift_type.description = description
        if enabled is not None:
            shift_type.enabled = enabled

        set_update_audit(shift_type, operator_id)

        await self.db.commit()
        await self.db.refresh(shift_type)

        if enabled is not None:
            await self._invalidate_rule_cache_for_shift_type(shift_type_id, tenant_id)

        return shift_type

    async def delete(self, shift_type_id: str, tenant_id: str | None = None) -> bool:
        """删除班次类型

        Args:
            shift_type_id: 班次类型ID
            tenant_id: 租户锚点（显式优先，未传回退请求上下文）

        Returns:
            是否删除成功
        """
        tenant_id = self._tenant(tenant_id)
        shift_type = await self.get_by_id(shift_type_id, tenant_id=tenant_id)
        if not shift_type:
            return False

        await self.db.delete(shift_type)
        await self.db.commit()

        await self._invalidate_rule_cache_for_shift_type(shift_type_id, tenant_id)

        return True

    async def _invalidate_rule_cache_for_shift_type(
        self, shift_type_id: str, tenant_id: str | None = None
    ) -> None:
        """禁用或删除班次类型后，清除该班次类型关联的规则引擎缓存。"""
        try:
            from app.core.redis import RedisCache
            from app.modules.rule_engine.cache import RuleCache

            # R1-12：缓存失效必须使用同一租户锚点，避免清错租户缓存
            tenant_id = self._tenant(tenant_id)
            rule_cache = RuleCache(RedisCache())
            await rule_cache.invalidate_v2(tenant_id, [shift_type_id])
        except Exception:
            pass
