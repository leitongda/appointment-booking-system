"""字典管理服务

负责字典类型和字典项的 CRUD 操作。
"""
import uuid

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.middleware.tenant_context import get_current_tenant_id
from app.models.dict_item import DictItem
from app.models.dict_type import DictType
from app.utils.audit import set_create_audit, set_update_audit


class DictService:
    """字典服务

    Args:
        db: 数据库会话
        tenant_id: 管理员账号租户锚点（R1-15）。查询/写入以锚点强过滤；
            未传入时才回退请求上下文（兼容公开端与内部调用）。
    """

    def __init__(self, db: AsyncSession, tenant_id: str | None = None):
        self.db = db
        self.tenant_id = tenant_id

    def _tenant(self) -> str | None:
        """账号锚点优先，未提供时回退请求上下文。"""
        if self.tenant_id is not None:
            return self.tenant_id
        return get_current_tenant_id()

    # ==================== 字典类型 ====================

    async def get_type_list(
        self,
        status: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 10,
    ) -> tuple[list[DictType], int]:
        """获取字典类型列表"""
        tenant_id = self._tenant()
        conditions = []

        if tenant_id:
            conditions.append(DictType.tenant_id == tenant_id)

        if status is not None:
            conditions.append(DictType.status == status)

        if keyword:
            conditions.append(
                (DictType.name.ilike(f"%{keyword}%"))
                | (DictType.code.ilike(f"%{keyword}%"))
            )

        count_query = select(func.count(DictType.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = select(DictType)
        if conditions:
            query = query.where(and_(*conditions))

        query = query.order_by(DictType.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_type_by_id(self, type_id: str) -> DictType | None:
        """获取字典类型详情（管理端按锚点过滤，跨租户返回 None）"""
        stmt = select(DictType).where(DictType.id == type_id)
        tenant_id = self._tenant()
        if tenant_id:
            stmt = stmt.where(DictType.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_type_by_code(self, code: str) -> DictType | None:
        """根据编码获取字典类型（平台管理员只看平台级，避免跨租户同码歧义）"""
        tenant_id = self._tenant()
        conditions = [DictType.code == code]
        if tenant_id:
            conditions.append(DictType.tenant_id == tenant_id)
        else:
            conditions.append(DictType.tenant_id.is_(None))
        result = await self.db.execute(
            select(DictType).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def create_type(
        self,
        code: str,
        name: str,
        description: str | None = None,
        operator_id: str | None = None,
    ) -> DictType:
        """创建字典类型"""
        existing = await self.get_type_by_code(code)
        if existing:
            raise ValueError(f"字典类型编码 '{code}' 已存在")

        tenant_id = self._tenant()
        dict_type = DictType(
            id=str(uuid.uuid4()),
            code=code,
            name=name,
            description=description,
            status=1,
            tenant_id=tenant_id,
        )

        set_create_audit(dict_type, operator_id)

        self.db.add(dict_type)
        await self.db.commit()
        await self.db.refresh(dict_type)

        return dict_type

    async def update_type(
        self,
        type_id: str,
        name: str | None = None,
        description: str | None = None,
        status: int | None = None,
        operator_id: str | None = None,
    ) -> DictType | None:
        """更新字典类型"""
        dict_type = await self.get_type_by_id(type_id)
        if not dict_type:
            return None

        if name is not None:
            dict_type.name = name
        if description is not None:
            dict_type.description = description
        if status is not None:
            dict_type.status = status

        set_update_audit(dict_type, operator_id)

        await self.db.commit()
        await self.db.refresh(dict_type)

        return dict_type

    async def delete_type(self, type_id: str) -> bool:
        """删除字典类型（软删除：禁用）"""
        dict_type = await self.get_type_by_id(type_id)
        if not dict_type:
            return False

        dict_type.status = 0
        await self.db.commit()
        return True

    # ==================== 字典项 ====================

    async def get_items(
        self,
        type_id: str,
        status: int | None = None,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[DictItem], int]:
        """获取字典项列表"""
        # 先确认字典类型在锚点内可见，避免跨租户枚举他租户字典项
        dict_type = await self.get_type_by_id(type_id)
        if not dict_type:
            return [], 0

        conditions = [DictItem.dict_type_id == type_id]

        if status is not None:
            conditions.append(DictItem.status == status)

        if keyword:
            conditions.append(
                (DictItem.label.ilike(f"%{keyword}%"))
                | (DictItem.value.ilike(f"%{keyword}%"))
            )

        count_query = select(func.count(DictItem.id)).where(and_(*conditions))
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one() or 0

        query = (
            select(DictItem)
            .where(and_(*conditions))
            .order_by(DictItem.sort_order.asc(), DictItem.created_at.asc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total

    async def get_item_by_id(self, item_id: str) -> DictItem | None:
        """获取字典项详情（管理端按锚点过滤，跨租户返回 None）"""
        stmt = select(DictItem).where(DictItem.id == item_id)
        tenant_id = self._tenant()
        if tenant_id:
            stmt = stmt.where(DictItem.tenant_id == tenant_id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_items_by_type_code(
        self, type_code: str, enabled_only: bool = True, tenant_id: str | None = None
    ) -> list[DictItem]:
        """根据字典类型编码获取字典项

        租户级别优先，缺失时回退平台级别；公开端可显式传入已解析的租户锚点。
        """
        effective_tenant = tenant_id if tenant_id is not None else self._tenant()

        base_conditions = [DictType.code == type_code, DictType.status == 1]

        # 先找租户级字典类型，再回退平台级（tenant_id IS NULL），
        # 避免两者同码时 scalar_one_or_none 抛 MultipleResultsFound。
        dict_type = None
        if effective_tenant:
            type_result = await self.db.execute(
                select(DictType).where(
                    *base_conditions, DictType.tenant_id == effective_tenant
                )
            )
            dict_type = type_result.scalar_one_or_none()

        if not dict_type:
            type_result = await self.db.execute(
                select(DictType).where(
                    *base_conditions, DictType.tenant_id.is_(None)
                )
            )
            dict_type = type_result.scalar_one_or_none()

        if not dict_type:
            return []

        # 查询字典项
        item_conditions = [DictItem.dict_type_id == dict_type.id]
        if enabled_only:
            item_conditions.append(DictItem.status == 1)

        result = await self.db.execute(
            select(DictItem)
            .where(and_(*item_conditions))
            .order_by(DictItem.sort_order.asc(), DictItem.created_at.asc())
        )
        return list(result.scalars().all())

    async def create_item(
        self,
        type_id: str,
        label: str,
        value: str,
        sort_order: int = 0,
        extra: dict | None = None,
        operator_id: str | None = None,
    ) -> DictItem:
        """创建字典项"""
        tenant_id = self._tenant()
        item = DictItem(
            id=str(uuid.uuid4()),
            dict_type_id=type_id,
            label=label,
            value=value,
            sort_order=sort_order,
            extra=extra,
            status=1,
            tenant_id=tenant_id,
        )

        set_create_audit(item, operator_id)

        self.db.add(item)
        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def update_item(
        self,
        item_id: str,
        label: str | None = None,
        value: str | None = None,
        sort_order: int | None = None,
        status: int | None = None,
        extra: dict | None = None,
        operator_id: str | None = None,
    ) -> DictItem | None:
        """更新字典项"""
        item = await self.get_item_by_id(item_id)
        if not item:
            return None

        if label is not None:
            item.label = label
        if value is not None:
            item.value = value
        if sort_order is not None:
            item.sort_order = sort_order
        if status is not None:
            item.status = status
        if extra is not None:
            item.extra = extra

        set_update_audit(item, operator_id)

        await self.db.commit()
        await self.db.refresh(item)

        return item

    async def delete_item(self, item_id: str) -> bool:
        """删除字典项（软删除：禁用）"""
        item = await self.get_item_by_id(item_id)
        if not item:
            return False

        item.status = 0
        await self.db.commit()
        return True

    async def sort_items(self, items: list[dict[str, int]]) -> bool:
        """批量更新字典项排序"""
        for sort_info in items:
            item = await self.get_item_by_id(sort_info["id"])
            if item:
                item.sort_order = sort_info["sort_order"]

        await self.db.commit()
        return True
