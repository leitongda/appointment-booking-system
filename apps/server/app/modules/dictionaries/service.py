"""字典管理服务

负责字典类型和字典项的 CRUD 操作。
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, func
from typing import Optional, List, Tuple, Dict
import uuid

from app.models.dict_type import DictType
from app.models.dict_item import DictItem
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.audit import set_create_audit, set_update_audit


class DictService:
    """字典服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ==================== 字典类型 ====================

    async def get_type_list(
        self,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[DictType], int]:
        """获取字典类型列表"""
        tenant_id = get_current_tenant_id()
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

    async def get_type_by_id(self, type_id: str) -> Optional[DictType]:
        """获取字典类型详情"""
        result = await self.db.execute(
            select(DictType).where(DictType.id == type_id)
        )
        return result.scalar_one_or_none()

    async def get_type_by_code(self, code: str) -> Optional[DictType]:
        """根据编码获取字典类型"""
        tenant_id = get_current_tenant_id()
        conditions = [DictType.code == code]
        if tenant_id:
            conditions.append(DictType.tenant_id == tenant_id)
        result = await self.db.execute(
            select(DictType).where(and_(*conditions))
        )
        return result.scalar_one_or_none()

    async def create_type(
        self,
        code: str,
        name: str,
        description: Optional[str] = None,
        operator_id: Optional[str] = None,
    ) -> DictType:
        """创建字典类型"""
        existing = await self.get_type_by_code(code)
        if existing:
            raise ValueError(f"字典类型编码 '{code}' 已存在")

        tenant_id = get_current_tenant_id()
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
        name: Optional[str] = None,
        description: Optional[str] = None,
        status: Optional[int] = None,
        operator_id: Optional[str] = None,
    ) -> Optional[DictType]:
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
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> Tuple[List[DictItem], int]:
        """获取字典项列表"""
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

    async def get_item_by_id(self, item_id: str) -> Optional[DictItem]:
        """获取字典项详情"""
        result = await self.db.execute(
            select(DictItem).where(DictItem.id == item_id)
        )
        return result.scalar_one_or_none()

    async def get_items_by_type_code(
        self, type_code: str, enabled_only: bool = True
    ) -> List[DictItem]:
        """根据字典类型编码获取字典项"""
        tenant_id = get_current_tenant_id()

        # 先找到字典类型（租户级别优先，fallback 到平台级别）
        type_conditions = [DictType.code == type_code, DictType.status == 1]
        if tenant_id:
            type_conditions.append(or_(DictType.tenant_id == tenant_id, DictType.tenant_id.is_(None)))

        type_result = await self.db.execute(
            select(DictType).where(and_(*type_conditions))
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
        extra: Optional[dict] = None,
        operator_id: Optional[str] = None,
    ) -> DictItem:
        """创建字典项"""
        tenant_id = get_current_tenant_id()
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
        label: Optional[str] = None,
        value: Optional[str] = None,
        sort_order: Optional[int] = None,
        status: Optional[int] = None,
        extra: Optional[dict] = None,
        operator_id: Optional[str] = None,
    ) -> Optional[DictItem]:
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

    async def sort_items(self, items: List[Dict[str, int]]) -> bool:
        """批量更新字典项排序"""
        for sort_info in items:
            item = await self.get_item_by_id(sort_info["id"])
            if item:
                item.sort_order = sort_info["sort_order"]

        await self.db.commit()
        return True
