"""用户收藏服务"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload
from typing import Optional, List, Dict, Any
import uuid

from app.models.user_favorite import UserFavorite
from app.models.doctor import Doctor
from app.models.department import Department
from app.schemas.user_favorite import UserFavoriteCreate
from app.utils.audit import set_create_audit
from app.middleware.tenant_context import get_current_tenant_id


class UserFavoriteService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_filter(self, stmt):
        """为查询添加租户过滤"""
        tenant_id = get_current_tenant_id()
        if tenant_id:
            return stmt.where(UserFavorite.tenant_id == tenant_id)
        return stmt

    async def get_by_id(self, favorite_id: str) -> Optional[UserFavorite]:
        """根据ID获取收藏"""
        stmt = self._tenant_filter(
            select(UserFavorite).where(UserFavorite.id == favorite_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def check_favorite(self, user_id: str, target_type: str, target_id: str) -> tuple[bool, Optional[str]]:
        """检查是否已收藏

        Returns:
            (is_favorited, favorite_id)
        """
        stmt = self._tenant_filter(
            select(UserFavorite).where(
                and_(
                    UserFavorite.user_id == user_id,
                    UserFavorite.target_type == target_type,
                    UserFavorite.target_id == target_id
                )
            )
        )
        result = await self.db.execute(stmt)
        favorite = result.scalar_one_or_none()
        if favorite:
            return True, favorite.id
        return False, None

    async def get_list(
        self,
        user_id: str,
        target_type: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> tuple[List[Dict[str, Any]], int]:
        """获取用户收藏列表（包含目标详情）"""
        query = self._tenant_filter(select(UserFavorite).where(UserFavorite.user_id == user_id))
        count_query = self._tenant_filter(select(func.count(UserFavorite.id)).where(UserFavorite.user_id == user_id))

        if target_type:
            query = query.where(UserFavorite.target_type == target_type)
            count_query = count_query.where(UserFavorite.target_type == target_type)

        query = query.order_by(UserFavorite.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        count_result = await self.db.execute(count_query)

        favorites = list(result.scalars().all())
        total = count_result.scalar() or 0

        # 获取目标详情
        favorites_with_target = []
        for favorite in favorites:
            target = await self._get_target_detail(favorite.target_type, favorite.target_id)
            favorites_with_target.append({
                "id": favorite.id,
                "userId": favorite.user_id,
                "targetType": favorite.target_type,
                "targetId": favorite.target_id,
                "createdAt": favorite.created_at.isoformat() if favorite.created_at else None,
                "target": target
            })

        return favorites_with_target, total

    async def _get_target_detail(self, target_type: str, target_id: str) -> Optional[Dict[str, Any]]:
        """获取收藏目标详情"""
        if target_type == "doctor":
            result = await self.db.execute(
                select(Doctor)
                .options(selectinload(Doctor.department))
                .where(Doctor.id == target_id, Doctor.deleted_at.is_(None))
            )
            doctor = result.scalar_one_or_none()
            if doctor:
                return {
                    "id": doctor.id,
                    "name": doctor.name,
                    "title": doctor.title,
                    "avatar": doctor.avatar,
                    "departmentId": doctor.department_id,
                    "departmentName": doctor.department.name if doctor.department else None,
                    "specialty": doctor.specialty,
                    "status": doctor.status
                }
        elif target_type == "department":
            result = await self.db.execute(
                select(Department).where(Department.id == target_id)
            )
            department = result.scalar_one_or_none()
            if department:
                return {
                    "id": department.id,
                    "name": department.name,
                    "description": department.description,
                    "icon": department.icon,
                    "status": department.status
                }
        return None

    async def create(self, user_id: str, data: UserFavoriteCreate) -> UserFavorite:
        """添加收藏"""
        # 检查是否已收藏
        is_favorited, _ = await self.check_favorite(user_id, data.target_type, data.target_id)
        if is_favorited:
            raise ValueError("已收藏该项目")

        # 验证目标是否存在
        target = await self._get_target_detail(data.target_type, data.target_id)
        if not target:
            raise ValueError("收藏目标不存在")

        favorite = UserFavorite(
            id=str(uuid.uuid4()),
            tenant_id=get_current_tenant_id(),
            user_id=user_id,
            target_type=data.target_type,
            target_id=data.target_id
        )
        set_create_audit(favorite, user_id)
        self.db.add(favorite)

        await self.db.commit()
        await self.db.refresh(favorite)
        return favorite

    async def delete(self, favorite_id: str, user_id: str) -> bool:
        """取消收藏"""
        stmt = self._tenant_filter(
            select(UserFavorite).where(
                and_(
                    UserFavorite.id == favorite_id,
                    UserFavorite.user_id == user_id
                )
            )
        )
        result = await self.db.execute(stmt)
        favorite = result.scalar_one_or_none()

        if not favorite:
            return False

        await self.db.delete(favorite)
        await self.db.commit()
        return True

    async def delete_by_target(self, user_id: str, target_type: str, target_id: str) -> bool:
        """根据目标取消收藏"""
        stmt = self._tenant_filter(
            select(UserFavorite).where(
                and_(
                    UserFavorite.user_id == user_id,
                    UserFavorite.target_type == target_type,
                    UserFavorite.target_id == target_id
                )
            )
        )
        result = await self.db.execute(stmt)
        favorite = result.scalar_one_or_none()

        if not favorite:
            return False

        await self.db.delete(favorite)
        await self.db.commit()
        return True
