from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from app.models.department import Department
from app.models.doctor import Doctor
from app.schemas.department import DepartmentCreate, DepartmentUpdate, DepartmentTreeNode

class DepartmentService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_by_id(self, dept_id: str) -> Optional[Department]:
        result = await self.db.execute(
            select(Department)
            .options(selectinload(Department.store))
            .where(Department.id == dept_id)
        )
        return result.scalar_one_or_none()
    
    async def get_list(
        self,
        name: Optional[str] = None,
        status: Optional[int] = None,
        parent_id: Optional[str] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10
    ) -> tuple[List[Department], int]:
        query = select(Department).options(selectinload(Department.store))
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
        if store_id is not None:
            query = query.where(Department.store_id == store_id)
            count_query = count_query.where(Department.store_id == store_id)
        
        # 分页，按sort_order降序（数字越大越靠前）
        query = query.order_by(Department.sort_order.desc()).offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)
        
        return list(result.scalars().all()), count_result.scalar() or 0
    
    async def get_tree(self, status: Optional[int] = 1, store_id: Optional[str] = None) -> List[DepartmentTreeNode]:
        query = select(Department).order_by(Department.sort_order)
        if status is not None:
            query = query.where(Department.status == status)
        if store_id is not None:
            query = query.where(Department.store_id == store_id)
        
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
    
    async def get_hot(self, limit: int = 8, store_id: Optional[str] = None) -> List[Department]:
        query = select(Department).options(selectinload(Department.store)).where(
            Department.is_hot == 1, Department.status == 1
        )
        if store_id is not None:
            query = query.where(Department.store_id == store_id)
        
        query = query.order_by(Department.sort_order).limit(limit)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def create(self, data: DepartmentCreate) -> Department:
        department = Department(
            id=str(uuid.uuid4()),
            name=data.name,
            parent_id=data.parent_id,
            description=data.description,
            sort_order=data.sort_order,
            is_hot=data.is_hot,
            status=data.status,
            # 基础配置
            store_id=data.store_id,
            tag=data.tag,
            enable_banner=data.enable_banner,
            enable_intro=data.enable_intro,
            is_final=data.is_final,
            is_recommended=data.is_recommended,
            # 图片资源
            banner_image=data.banner_image,
            icon=data.icon,
            intro_images=data.intro_images,
            # 详情内容
            intro_content=data.intro_content,
            features=data.features,
            appointment_notice=data.appointment_notice,
            # 联系信息
            phone=data.phone,
            location=data.location,
            working_hours=data.working_hours,
        )
        self.db.add(department)
        await self.db.commit()
        await self.db.refresh(department)
        # 加载 store 关联
        result = await self.db.execute(
            select(Department)
            .options(selectinload(Department.store))
            .where(Department.id == department.id)
        )
        return result.scalar_one()
    
    async def update(self, dept_id: str, data: DepartmentUpdate) -> Optional[Department]:
        department = await self.get_by_id(dept_id)
        if not department:
            return None
        
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(department, field, value)
        
        await self.db.commit()
        # 重新加载 store 关联
        result = await self.db.execute(
            select(Department)
            .options(selectinload(Department.store))
            .where(Department.id == dept_id)
        )
        return result.scalar_one()
    
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
    
    async def get_doctors(self, dept_id: str) -> List[Doctor]:
        """获取科室已绑定的医生列表"""
        result = await self.db.execute(
            select(Doctor)
            .where(Doctor.department_id == dept_id)
            .order_by(Doctor.sort_order.desc(), Doctor.created_at.desc())
        )
        return list(result.scalars().all())
    
    async def get_all_doctors(self, store_id: Optional[str] = None) -> List[Doctor]:
        """获取所有可绑定的医生列表"""
        query = select(Doctor).where(Doctor.status == 1)
        if store_id:
            query = query.where(Doctor.store_id == store_id)
        query = query.order_by(Doctor.sort_order.desc(), Doctor.name)
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def batch_bind_doctors(self, dept_id: str, doctor_ids: List[str]) -> int:
        """批量绑定医生到科室
        
        Args:
            dept_id: 科室ID
            doctor_ids: 要绑定的医生ID列表
            
        Returns:
            绑定的医生数量
        """
        # 先验证科室是否存在
        department = await self.get_by_id(dept_id)
        if not department:
            raise ValueError("科室不存在")
        
        # 解绑当前科室的所有医生（不在新列表中的）
        current_doctors = await self.get_doctors(dept_id)
        current_ids = {d.id for d in current_doctors}
        new_ids = set(doctor_ids)
        
        # 需要解绑的医生（当前已绑定但不在新列表中）- 设为空科室不合适，这里保持不变
        # 医生必须有科室，所以我们不能解绑，只能绑定新的
        
        # 需要绑定的医生（在新列表中但当前未绑定到此科室）
        to_bind = new_ids - current_ids
        if to_bind:
            result = await self.db.execute(
                select(Doctor).where(Doctor.id.in_(to_bind))
            )
            for doctor in result.scalars().all():
                doctor.department_id = dept_id
                # 同时更新门店，保持科室和医生门店一致
                if department.store_id:
                    doctor.store_id = department.store_id
        
        await self.db.commit()
        return len(doctor_ids)

