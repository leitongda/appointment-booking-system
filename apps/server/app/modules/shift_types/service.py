"""
班次类型管理服务

负责班次类型的 CRUD 操作
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func
from typing import Optional, List, Tuple
import uuid

from app.models.rule_set import ShiftType
from app.utils.audit import set_create_audit, set_update_audit


class ShiftTypeService:
    """班次类型服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        enabled: Optional[bool] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[ShiftType], int]:
        """获取班次类型列表

        Args:
            enabled: 是否启用
            keyword: 搜索关键词
            page: 页码
            page_size: 每页数量

        Returns:
            (班次类型列表, 总数)
        """
        # 构建查询条件
        conditions = []

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

    async def get_all_enabled(self) -> List[ShiftType]:
        """获取所有启用的班次类型

        Returns:
            班次类型列表
        """
        result = await self.db.execute(
            select(ShiftType)
            .where(ShiftType.enabled == True)
            .order_by(ShiftType.code.asc())
        )
        return list(result.scalars().all())

    async def get_by_id(self, shift_type_id: str) -> Optional[ShiftType]:
        """获取班次类型详情

        Args:
            shift_type_id: 班次类型ID

        Returns:
            班次类型
        """
        result = await self.db.execute(
            select(ShiftType).where(ShiftType.id == shift_type_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, code: str) -> Optional[ShiftType]:
        """根据代码获取班次类型

        Args:
            code: 类型代码

        Returns:
            班次类型
        """
        result = await self.db.execute(
            select(ShiftType).where(ShiftType.code == code)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        enabled: bool = True,
        operator_id: Optional[str] = None
    ) -> ShiftType:
        """创建班次类型

        Args:
            code: 类型代码
            name: 类型名称
            description: 描述
            enabled: 是否启用
            operator_id: 操作人ID

        Returns:
            创建的班次类型

        Raises:
            ValueError: 代码已存在
        """
        # 检查代码是否已存在
        existing = await self.get_by_code(code)
        if existing:
            raise ValueError(f"类型代码 '{code}' 已存在")

        shift_type = ShiftType(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=description,
            enabled=enabled
        )

        set_create_audit(shift_type, operator_id)

        self.db.add(shift_type)
        await self.db.commit()
        await self.db.refresh(shift_type)

        return shift_type

    async def update(
        self,
        shift_type_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        enabled: Optional[bool] = None,
        operator_id: Optional[str] = None
    ) -> Optional[ShiftType]:
        """更新班次类型

        Args:
            shift_type_id: 班次类型ID
            name: 类型名称
            description: 描述
            enabled: 是否启用
            operator_id: 操作人ID

        Returns:
            更新后的班次类型
        """
        shift_type = await self.get_by_id(shift_type_id)
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
            await self._invalidate_rule_cache_for_shift_type(shift_type_id)

        return shift_type

    async def delete(self, shift_type_id: str) -> bool:
        """删除班次类型

        Args:
            shift_type_id: 班次类型ID

        Returns:
            是否删除成功
        """
        shift_type = await self.get_by_id(shift_type_id)
        if not shift_type:
            return False

        await self.db.delete(shift_type)
        await self.db.commit()

        await self._invalidate_rule_cache_for_shift_type(shift_type_id)

        return True

    async def _invalidate_rule_cache_for_shift_type(self, shift_type_id: str) -> None:
        """禁用或删除班次类型后，清除该班次类型关联的规则引擎缓存。"""
        try:
            from app.core.redis import RedisCache
            from app.middleware.tenant_context import get_current_tenant_id
            from app.modules.rule_engine.cache import RuleCache

            tenant_id = get_current_tenant_id()
            rule_cache = RuleCache(RedisCache())
            await rule_cache.invalidate_v2(tenant_id, [shift_type_id])
        except Exception:
            pass
