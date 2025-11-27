from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional, List
import uuid

from app.models.department import Department
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentTreeNode

class DepartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, dept_id: str) -> Optional[Department]:
        result = await self.db.execute(select(Department).where(Department.id == dept_id))
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        name: Optional[str] = None,
        status: Optional[int] = None,
        parent_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Department], int]:
        query = select(Department)
        count_query = select(func.count(Department.id))
        
        if name:
            query = query.where(Department.name.contains(name))
            count_query = count_query.where(Department.name.contains(name))
        if status is not None:
            query = query.where(Department.status == status)
            count_query = count_query.where(Department.status == status)
        if parent_id is not None:
            query = query.where(Department.parent_id == parent_id)
            count_query = count_query.where(Department.parent_id == parent_id)
        
        # 分页
        query = query.order_by(Department.sort_order).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_tree(self, status: Optional[int] = 1) -> List[DepartmentTreeNode]:
        query = select(Department).order_by(Department.sort_order)
        if status is not None:
            query = query.where(Department.status == status)
        
        result = await self.db.execute(query)
        departments = list(result.scalars().all())
        
        # 构建树
        dept_map = {d.id: DepartmentTreeNode(id=d.id, name=d.name, parent_id=d.parent_id, children=[]) for d in departments}
        tree = []
        
        for dept in departments:
            node = dept_map[dept.id]
            if dept.parent_id and dept.parent_id in dept_map:
                dept_map[dept.parent_id].children.append(node)
            else:
                tree.append(node)
        
        return tree
    
    async def get_hot(self, limit: int = 8) -> List[Department]:
        result = await self.db.execute(
            select(Department)
            .where(Department.is_hot == 1, Department.status == 1)
            .order_by(Department.sort_order)
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def create(self, data: DepartmentCreate) -> Department:
        department = Department(
            id=str(uuid.uuid4()),
            name=data.name,
            parent_id=data.parent_id,
            description=data.description,
            sort_order=data.sort_order,
            is_hot=data.is_hot,
            status=data.status
        )
        self.db.add(department)
        await self.db.commit()
        await self.db.refresh(department)
        return department
    
    async def update(self, dept_id: str, data: DepartmentUpdate) -> Optional[Department]:
        department = await self.get_by_id(dept_id)
        if not department:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(department, field, value)
        
        await self.db.commit()
        await self.db.refresh(department)
        return department
    
    async def delete(self, dept_id: str) -> bool:
        department = await self.get_by_id(dept_id)
        if not department:
            return False
        
        # 检查是否有子科室
        result = await self.db.execute(
            select(func.count(Department.id)).where(Department.parent_id == dept_id)
        )
        if result.scalar() > 0:
            raise ValueError("该科室下有子科室，无法删除")
        
        await self.db.delete(department)
        await self.db.commit()
        return True

