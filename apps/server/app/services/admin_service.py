"""管理员和角色服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime
import uuid
import json

from app.models.admin import Admin, Role, OperationLog, Permission
from app.core.security import get_password_hash, verify_password


# ========== 角色服务 ==========
class RoleService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Role], int]:
        """获取角色列表"""
        query = select(Role)
        conditions = []
        
        if status is not None:
            conditions.append(Role.status == status)
        if keyword:
            conditions.append(Role.name.ilike(f"%{keyword}%"))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        count_query = select(func.count(Role.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Role.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def get_all(self) -> List[Role]:
        """获取所有启用的角色"""
        query = select(Role).where(Role.status == 1).order_by(Role.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_by_id(self, role_id: str) -> Optional[Role]:
        """获取角色详情"""
        return await self.db.get(Role, role_id)

    async def get_by_code(self, code: str) -> Optional[Role]:
        """根据编码获取角色"""
        result = await self.db.execute(select(Role).where(Role.code == code))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Role:
        """创建角色"""
        # 检查编码是否已存在
        existing = await self.get_by_code(data["code"])
        if existing:
            raise ValueError("角色编码已存在")
        
        permissions = data.get("permissions", [])
        role = Role(
            id=str(uuid.uuid4()),
            name=data["name"],
            code=data["code"],
            description=data.get("description"),
            permissions=json.dumps(permissions) if permissions else None,
            status=data.get("status", 1),
        )
        self.db.add(role)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update(self, role_id: str, data: dict) -> Optional[Role]:
        """更新角色"""
        role = await self.get_by_id(role_id)
        if not role:
            return None
        
        # 超级管理员不允许修改编码
        if role.code == "SUPER_ADMIN" and data.get("code") and data["code"] != "SUPER_ADMIN":
            raise ValueError("超级管理员编码不可修改")
        
        for key, value in data.items():
            if key == "permissions":
                value = json.dumps(value) if value else None
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)
        
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def update_permissions(self, role_id: str, permissions: List[str]) -> Optional[Role]:
        """更新角色权限"""
        role = await self.get_by_id(role_id)
        if not role:
            return None
        
        role.permissions = json.dumps(permissions)
        await self.db.commit()
        await self.db.refresh(role)
        return role

    async def delete(self, role_id: str) -> bool:
        """删除角色"""
        role = await self.get_by_id(role_id)
        if not role:
            return False
        
        # 超级管理员不允许删除
        if role.code == "SUPER_ADMIN":
            raise ValueError("超级管理员不可删除")
        
        # 检查是否有关联的管理员
        admin_count = await self.db.scalar(
            select(func.count(Admin.id)).where(Admin.role_id == role_id)
        )
        if admin_count and admin_count > 0:
            raise ValueError("该角色下有管理员，无法删除")
        
        await self.db.delete(role)
        await self.db.commit()
        return True


# ========== 管理员服务 ==========
class AdminService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        role_id: Optional[str] = None,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        store_id: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Admin], int]:
        """获取管理员列表"""
        query = select(Admin).options(selectinload(Admin.role), selectinload(Admin.store))
        conditions = []
        
        if role_id:
            conditions.append(Admin.role_id == role_id)
        if status is not None:
            conditions.append(Admin.status == status)
        if keyword:
            conditions.append(
                Admin.username.ilike(f"%{keyword}%") | 
                Admin.name.ilike(f"%{keyword}%") |
                Admin.phone.ilike(f"%{keyword}%")
            )
        if store_id is not None:
            conditions.append(Admin.store_id == store_id)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        count_query = select(func.count(Admin.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        query = query.order_by(Admin.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        items = result.unique().scalars().all()
        
        return list(items), total or 0

    async def get_by_id(self, admin_id: str) -> Optional[Admin]:
        """获取管理员详情"""
        result = await self.db.execute(
            select(Admin)
            .options(selectinload(Admin.role), selectinload(Admin.store))
            .where(Admin.id == admin_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[Admin]:
        """根据用户名获取管理员"""
        result = await self.db.execute(
            select(Admin)
            .options(selectinload(Admin.role), selectinload(Admin.store))
            .where(Admin.username == username)
        )
        return result.unique().scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[Admin]:
        """根据手机号获取管理员"""
        result = await self.db.execute(
            select(Admin)
            .options(selectinload(Admin.role), selectinload(Admin.store))
            .where(Admin.phone == phone)
        )
        return result.unique().scalar_one_or_none()

    async def authenticate(self, username: str, password: str) -> Optional[Admin]:
        """管理员登录认证（用户名+密码）"""
        admin = await self.get_by_username(username)
        if not admin:
            return None
        if not verify_password(password, admin.password_hash):
            return None
        return admin

    async def authenticate_by_phone(self, phone: str, password: str) -> Optional[Admin]:
        """管理员登录认证（手机号+密码）"""
        admin = await self.get_by_phone(phone)
        if not admin:
            return None
        if not admin.password_hash:
            return None
        if not verify_password(password, admin.password_hash):
            return None
        return admin

    async def create(self, data: dict) -> Admin:
        """创建管理员"""
        # 检查用户名是否已存在
        existing = await self.get_by_username(data["username"])
        if existing:
            raise ValueError("用户名已存在")
        
        admin = Admin(
            id=str(uuid.uuid4()),
            username=data["username"],
            password_hash=get_password_hash(data["password"]),
            name=data.get("name"),
            phone=data.get("phone"),
            email=data.get("email"),
            avatar=data.get("avatar"),
            role_id=data.get("role_id"),
            store_id=data.get("store_id"),
            status=data.get("status", 1),
        )
        self.db.add(admin)
        await self.db.commit()
        await self.db.refresh(admin)
        return admin

    async def update(self, admin_id: str, data: dict) -> Optional[Admin]:
        """更新管理员"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return None
        
        # 检查用户名是否被其他人使用
        if data.get("username") and data["username"] != admin.username:
            existing = await self.get_by_username(data["username"])
            if existing:
                raise ValueError("用户名已存在")
        
        for key, value in data.items():
            if key == "password" and value:
                admin.password_hash = get_password_hash(value)
            elif hasattr(admin, key) and value is not None:
                setattr(admin, key, value)
        
        await self.db.commit()
        await self.db.refresh(admin)
        return admin

    async def reset_password(self, admin_id: str, new_password: str) -> bool:
        """重置密码"""
        admin = await self.db.get(Admin, admin_id)
        if not admin:
            return False
        
        admin.password_hash = get_password_hash(new_password)
        await self.db.commit()
        return True

    async def update_login_info(self, admin_id: str, ip: str) -> None:
        """更新登录信息"""
        admin = await self.db.get(Admin, admin_id)
        if admin:
            admin.last_login_at = datetime.now()
            admin.last_login_ip = ip
            await self.db.commit()

    async def delete(self, admin_id: str) -> bool:
        """删除管理员"""
        admin = await self.get_by_id(admin_id)
        if not admin:
            return False
        
        # 检查是否是超级管理员
        if admin.role and admin.role.code == "SUPER_ADMIN":
            # 检查是否是最后一个超级管理员
            super_admin_count = await self.db.scalar(
                select(func.count(Admin.id)).join(Role).where(Role.code == "SUPER_ADMIN")
            )
            if super_admin_count and super_admin_count <= 1:
                raise ValueError("不能删除最后一个超级管理员")
        
        await self.db.delete(admin)
        await self.db.commit()
        return True


# ========== 操作日志服务 ==========
class OperationLogService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self,
        admin_id: Optional[str] = None,
        module: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[OperationLog], int]:
        """获取操作日志列表"""
        query = select(OperationLog)
        conditions = []
        
        if admin_id:
            conditions.append(OperationLog.admin_id == admin_id)
        if module:
            conditions.append(OperationLog.module == module)
        if start_time:
            conditions.append(OperationLog.created_at >= start_time)
        if end_time:
            conditions.append(OperationLog.created_at <= end_time)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        count_query = select(func.count(OperationLog.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)
        
        query = query.order_by(OperationLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        result = await self.db.execute(query)
        items = result.scalars().all()
        
        return list(items), total or 0

    async def create(self, data: dict) -> OperationLog:
        """创建操作日志"""
        log = OperationLog(
            id=str(uuid.uuid4()),
            admin_id=data.get("admin_id"),
            admin_name=data.get("admin_name"),
            module=data.get("module"),
            action=data.get("action"),
            method=data.get("method"),
            path=data.get("path"),
            params=data.get("params"),
            result=data.get("result", "成功"),
            ip=data.get("ip"),
            user_agent=data.get("user_agent"),
            duration=data.get("duration"),
        )
        self.db.add(log)
        await self.db.commit()
        return log


# ========== 权限服务 ==========
class PermissionService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> List[Permission]:
        """获取所有权限（平铺列表）"""
        query = select(Permission).order_by(Permission.sort.asc(), Permission.created_at.asc())
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_tree(self) -> List[Dict[str, Any]]:
        """获取权限树形结构"""
        permissions = await self.get_all()
        
        # 构建树形结构
        perm_dict = {p.code: {
            "id": p.id,
            "code": p.code,
            "name": p.name,
            "type": p.type,
            "parentCode": p.parent_code,
            "icon": p.icon,
            "sort": p.sort,
            "children": []
        } for p in permissions}
        
        tree = []
        for p in permissions:
            node = perm_dict[p.code]
            if p.parent_code and p.parent_code in perm_dict:
                perm_dict[p.parent_code]["children"].append(node)
            else:
                tree.append(node)
        
        return tree

    async def get_by_code(self, code: str) -> Optional[Permission]:
        """根据权限码获取权限"""
        result = await self.db.execute(select(Permission).where(Permission.code == code))
        return result.scalar_one_or_none()

    async def create(self, data: dict) -> Permission:
        """创建权限"""
        existing = await self.get_by_code(data["code"])
        if existing:
            raise ValueError("权限码已存在")
        
        permission = Permission(
            id=str(uuid.uuid4()),
            code=data["code"],
            name=data["name"],
            type=data["type"],
            parent_code=data.get("parent_code"),
            icon=data.get("icon"),
            sort=data.get("sort", 0),
        )
        self.db.add(permission)
        await self.db.commit()
        await self.db.refresh(permission)
        return permission

    async def batch_create(self, permissions_data: List[dict]) -> List[Permission]:
        """批量创建权限"""
        created = []
        for data in permissions_data:
            existing = await self.get_by_code(data["code"])
            if not existing:
                permission = Permission(
                    id=str(uuid.uuid4()),
                    code=data["code"],
                    name=data["name"],
                    type=data["type"],
                    parent_code=data.get("parent_code"),
                    icon=data.get("icon"),
                    sort=data.get("sort", 0),
                )
                self.db.add(permission)
                created.append(permission)
        
        if created:
            await self.db.commit()
        return created

    async def delete(self, code: str) -> bool:
        """删除权限"""
        permission = await self.get_by_code(code)
        if not permission:
            return False
        
        await self.db.delete(permission)
        await self.db.commit()
        return True

    async def get_admin_permissions(self, admin_id: str) -> List[str]:
        """获取管理员的权限码列表"""
        # 获取管理员及其角色
        result = await self.db.execute(
            select(Admin).options(selectinload(Admin.role)).where(Admin.id == admin_id)
        )
        admin = result.unique().scalar_one_or_none()
        
        if not admin or not admin.role:
            return []
        
        # 超级管理员拥有所有权限
        if admin.role.code == "SUPER_ADMIN":
            all_perms = await self.get_all()
            return [p.code for p in all_perms]
        
        # 其他角色从角色的 permissions 字段获取
        if admin.role.permissions:
            try:
                return json.loads(admin.role.permissions)
            except:
                return []
        
        return []

