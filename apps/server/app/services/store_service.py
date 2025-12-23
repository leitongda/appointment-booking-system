from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete, and_
from typing import Optional, List
import uuid

from app.models.store import Store
from app.models.department import Department
from app.models.admin import Admin, admin_stores
from app.schemas.store import StoreCreate, StoreUpdate, StoreQuery


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
        
        # 准备数据，如果未提供密码则使用默认密码
        store_data = data.model_dump()
        if not store_data.get("password"):
            store_data["password"] = "123456"
        
        store = Store(
            id=str(uuid.uuid4()),
            **store_data
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
        
        # 检查是否有关联的科室（通过 Department.store_id）
        result = await self.db.execute(
            select(func.count(Department.id))
            .where(Department.store_id == store_id)
        )
        if result.scalar() > 0:
            raise ValueError("该门店下有关联科室，请先删除或转移科室")
        
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
    
    async def get_department_count(self, store_id: str) -> int:
        """获取门店科室数量（通过 Department.store_id 统计）"""
        result = await self.db.execute(
            select(func.count(Department.id))
            .where(Department.store_id == store_id)
        )
        return result.scalar() or 0
    
    async def get_departments(self, store_id: str) -> List[Department]:
        """获取门店已绑定的科室列表"""
        result = await self.db.execute(
            select(Department)
            .where(Department.store_id == store_id)
            .order_by(Department.sort_order.desc(), Department.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def batch_bind_departments(self, store_id: str, department_ids: List[str]) -> int:
        """批量绑定科室到门店
        
        Args:
            store_id: 门店ID
            department_ids: 要绑定的科室ID列表
            
        Returns:
            绑定的科室数量
        """
        # 先验证门店是否存在
        store = await self.get_by_id(store_id)
        if not store:
            raise ValueError("门店不存在")
        
        # 解绑当前门店的所有科室（不在新列表中的）
        current_departments = await self.get_departments(store_id)
        current_ids = {d.id for d in current_departments}
        new_ids = set(department_ids)
        
        # 需要解绑的科室（当前已绑定但不在新列表中）
        to_unbind = current_ids - new_ids
        if to_unbind:
            result = await self.db.execute(
                select(Department).where(Department.id.in_(to_unbind))
            )
            for dept in result.scalars().all():
                dept.store_id = None
        
        # 需要绑定的科室（在新列表中但当前未绑定）
        to_bind = new_ids - current_ids
        if to_bind:
            result = await self.db.execute(
                select(Department).where(Department.id.in_(to_bind))
            )
            for dept in result.scalars().all():
                # 只绑定未绑定到其他门店的科室
                if dept.store_id is None:
                    dept.store_id = store_id
        
        await self.db.commit()
        return len(department_ids)
    
    async def get_admins(self, store_id: str) -> List[Admin]:
        """获取门店已绑定的管理员列表"""
        result = await self.db.execute(
            select(Admin)
            .join(admin_stores, Admin.id == admin_stores.c.admin_id)
            .where(admin_stores.c.store_id == store_id)
            .order_by(Admin.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def batch_bind_admins(self, store_id: str, admin_ids: List[str]) -> int:
        """批量绑定管理员到门店
        
        Args:
            store_id: 门店ID
            admin_ids: 要绑定的管理员ID列表
            
        Returns:
            绑定的管理员数量
        """
        # 先验证门店是否存在
        store = await self.get_by_id(store_id)
        if not store:
            raise ValueError("门店不存在")
        
        # 获取当前已绑定的管理员ID
        current_admins = await self.get_admins(store_id)
        current_ids = {a.id for a in current_admins}
        new_ids = set(admin_ids)
        
        # 需要解绑的管理员（当前已绑定但不在新列表中）
        to_unbind = current_ids - new_ids
        if to_unbind:
            await self.db.execute(
                delete(admin_stores).where(
                    and_(
                        admin_stores.c.store_id == store_id,
                        admin_stores.c.admin_id.in_(to_unbind)
                    )
                )
            )
        
        # 需要绑定的管理员（在新列表中但当前未绑定）
        to_bind = new_ids - current_ids
        if to_bind:
            for admin_id in to_bind:
                # 验证管理员是否存在
                result = await self.db.execute(
                    select(Admin).where(Admin.id == admin_id)
                )
                admin = result.scalar_one_or_none()
                if admin:
                    await self.db.execute(
                        admin_stores.insert().values(
                            admin_id=admin_id,
                            store_id=store_id
                        )
                    )
        
        await self.db.commit()
        return len(admin_ids)