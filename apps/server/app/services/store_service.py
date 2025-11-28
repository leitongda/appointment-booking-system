from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import Optional, List
import uuid

from app.models.store import Store, StoreDepartment
from app.models.department import Department
from app.schemas.store import (
    StoreCreate, StoreUpdate, StoreQuery,
    StoreDepartmentCreate, StoreDepartmentUpdate
)


class StoreService:
    """门店服务"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, store_id: str) -> Optional[Store]:
        """根据ID获取门店"""
        result = await self.db.execute(
            select(Store).where(Store.id == store_id)
        )
        return result.scalar_one_or_none()
    
    async def get_by_code(self, code: str) -> Optional[Store]:
        """根据编码获取门店"""
        result = await self.db.execute(
            select(Store).where(Store.code == code)
        )
        return result.scalar_one_or_none()
    
    async def get_list(self, query: StoreQuery) -> tuple[List[Store], int]:
        """获取门店列表"""
        stmt = select(Store)
        count_stmt = select(func.count(Store.id))
        
        # 关键词搜索
        if query.keyword:
            keyword_filter = Store.name.contains(query.keyword) | Store.code.contains(query.keyword)
            stmt = stmt.where(keyword_filter)
            count_stmt = count_stmt.where(keyword_filter)
        
        # 状态筛选
        if query.status is not None:
            stmt = stmt.where(Store.status == query.status)
            count_stmt = count_stmt.where(Store.status == query.status)
        
        # 城市筛选
        if query.city:
            stmt = stmt.where(Store.city == query.city)
            count_stmt = count_stmt.where(Store.city == query.city)
        
        # 排序和分页
        stmt = stmt.order_by(Store.sort_order, Store.created_at.desc())
        stmt = stmt.offset((query.page - 1) * query.page_size).limit(query.page_size)
        
        result = await self.db.execute(stmt)
        count_result = await self.db.execute(count_stmt)
        
        stores = list(result.scalars().all())
        total = count_result.scalar() or 0
        
        return stores, total
    
    async def get_all_active(self) -> List[Store]:
        """获取所有营业中的门店"""
        result = await self.db.execute(
            select(Store)
            .where(Store.status == 1)
            .order_by(Store.sort_order)
        )
        return list(result.scalars().all())
    
    async def create(self, data: StoreCreate) -> Store:
        """创建门店"""
        # 检查编码是否重复
        if data.code:
            existing = await self.get_by_code(data.code)
            if existing:
                raise ValueError(f"门店编码 {data.code} 已存在")
        
        store = Store(
            id=str(uuid.uuid4()),
            **data.model_dump()
        )
        self.db.add(store)
        await self.db.commit()
        await self.db.refresh(store)
        return store
    
    async def update(self, store_id: str, data: StoreUpdate) -> Optional[Store]:
        """更新门店"""
        store = await self.get_by_id(store_id)
        if not store:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        
        # 检查编码是否重复
        if 'code' in update_data and update_data['code']:
            existing = await self.get_by_code(update_data['code'])
            if existing and existing.id != store_id:
                raise ValueError(f"门店编码 {update_data['code']} 已存在")
        
        for field, value in update_data.items():
            setattr(store, field, value)
        
        await self.db.commit()
        await self.db.refresh(store)
        return store
    
    async def delete(self, store_id: str) -> bool:
        """删除门店"""
        store = await self.get_by_id(store_id)
        if not store:
            return False
        
        # 检查是否有关联的科室
        result = await self.db.execute(
            select(func.count(StoreDepartment.id))
            .where(StoreDepartment.store_id == store_id)
        )
        if result.scalar() > 0:
            raise ValueError("该门店下有关联科室，请先解除关联")
        
        await self.db.delete(store)
        await self.db.commit()
        return True
    
    async def update_status(self, store_id: str, status: int) -> Optional[Store]:
        """更新门店状态"""
        store = await self.get_by_id(store_id)
        if not store:
            return None
        
        store.status = status
        await self.db.commit()
        await self.db.refresh(store)
        return store
    
    # ========== 门店科室关联 ==========
    
    async def get_store_departments(self, store_id: str) -> List[dict]:
        """获取门店的科室列表"""
        result = await self.db.execute(
            select(StoreDepartment, Department.name.label('department_name'))
            .join(Department, StoreDepartment.department_id == Department.id)
            .where(StoreDepartment.store_id == store_id)
            .order_by(StoreDepartment.created_at)
        )
        
        items = []
        for row in result.all():
            sd = row[0]
            items.append({
                'id': sd.id,
                'store_id': sd.store_id,
                'department_id': sd.department_id,
                'department_name': row[1],
                'floor': sd.floor,
                'room': sd.room,
                'status': sd.status,
                'created_at': sd.created_at
            })
        return items
    
    async def add_department(self, data: StoreDepartmentCreate) -> StoreDepartment:
        """添加门店科室关联"""
        # 检查是否已存在
        result = await self.db.execute(
            select(StoreDepartment).where(
                and_(
                    StoreDepartment.store_id == data.store_id,
                    StoreDepartment.department_id == data.department_id
                )
            )
        )
        if result.scalar_one_or_none():
            raise ValueError("该科室已关联到此门店")
        
        store_dept = StoreDepartment(
            id=str(uuid.uuid4()),
            **data.model_dump()
        )
        self.db.add(store_dept)
        await self.db.commit()
        await self.db.refresh(store_dept)
        return store_dept
    
    async def update_department(
        self, 
        relation_id: str, 
        data: StoreDepartmentUpdate
    ) -> Optional[StoreDepartment]:
        """更新门店科室关联"""
        result = await self.db.execute(
            select(StoreDepartment).where(StoreDepartment.id == relation_id)
        )
        store_dept = result.scalar_one_or_none()
        if not store_dept:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(store_dept, field, value)
        
        await self.db.commit()
        await self.db.refresh(store_dept)
        return store_dept
    
    async def remove_department(self, relation_id: str) -> bool:
        """移除门店科室关联"""
        result = await self.db.execute(
            select(StoreDepartment).where(StoreDepartment.id == relation_id)
        )
        store_dept = result.scalar_one_or_none()
        if not store_dept:
            return False
        
        await self.db.delete(store_dept)
        await self.db.commit()
        return True
    
    async def get_department_count(self, store_id: str) -> int:
        """获取门店科室数量"""
        result = await self.db.execute(
            select(func.count(StoreDepartment.id))
            .where(StoreDepartment.store_id == store_id)
        )
        return result.scalar() or 0
