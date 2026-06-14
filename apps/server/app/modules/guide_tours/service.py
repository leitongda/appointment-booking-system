"""操作指引 - 业务服务"""
from typing import List, Optional, Tuple

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.guide_tour import GuideTour, GuideTourProgress
from app.modules.guide_tours.schemas import (
    GuideTourCreate,
    GuideTourUpdate,
    ProgressUpdate,
)


class GuideTourService:
    """用户端指引服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_active_tours(self, admin_id: str) -> List[dict]:
        """获取当前用户可见的已发布指引 + 进度"""
        rows = (
            await self.db.execute(
                select(
                    GuideTour.id,
                    GuideTour.code,
                    GuideTour.title,
                    GuideTour.description,
                    GuideTour.steps,
                    GuideTourProgress.current_step,
                    GuideTourProgress.status.label("progress_status"),
                )
                .outerjoin(
                    GuideTourProgress,
                    and_(
                        GuideTourProgress.tour_id == GuideTour.id,
                        GuideTourProgress.admin_id == admin_id,
                    ),
                )
                .where(GuideTour.status == 1)
                .order_by(GuideTour.sort_order)
            )
        ).all()

        result = []
        for r in rows:
            result.append({
                "id": r.id,
                "code": r.code,
                "title": r.title,
                "description": r.description,
                "steps": r.steps or [],
                "currentStep": r.current_step or 0,
                "progressStatus": r.progress_status or 0,
            })
        return result

    async def get_progress(self, tour_id: str, admin_id: str) -> Optional[GuideTourProgress]:
        """获取指定指引的用户进度"""
        return (
            await self.db.execute(
                select(GuideTourProgress).where(
                    and_(
                        GuideTourProgress.tour_id == tour_id,
                        GuideTourProgress.admin_id == admin_id,
                    )
                )
            )
        ).scalar_one_or_none()

    async def update_progress(self, tour_id: str, admin_id: str, data: ProgressUpdate) -> GuideTourProgress:
        """更新用户指引进度（upsert）"""
        progress = await self.get_progress(tour_id, admin_id)

        if progress is None:
            progress = GuideTourProgress(
                tour_id=tour_id,
                admin_id=admin_id,
                current_step=data.current_step or 0,
                status=data.status or 0,
            )
            self.db.add(progress)
        else:
            if data.current_step is not None:
                progress.current_step = data.current_step
            if data.status is not None:
                progress.status = data.status

        await self.db.commit()
        await self.db.refresh(progress)
        return progress


class AdminGuideTourService:
    """管理端指引 CRUD 服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_list(
        self, page: int = 1, page_size: int = 20, status: Optional[int] = None
    ) -> Tuple[List[dict], int]:
        """分页获取指引列表"""
        conditions = []
        if status is not None:
            conditions.append(GuideTour.status == status)

        # 总数
        count_q = select(func.count(GuideTour.id))
        if conditions:
            count_q = count_q.where(and_(*conditions))
        total = (await self.db.execute(count_q)).scalar() or 0

        # 列表
        q = (
            select(GuideTour)
            .order_by(GuideTour.sort_order, GuideTour.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        if conditions:
            q = q.where(and_(*conditions))

        rows = (await self.db.execute(q)).scalars().all()

        items = []
        for t in rows:
            items.append({
                "id": t.id,
                "code": t.code,
                "title": t.title,
                "status": t.status,
                "sortOrder": t.sort_order,
                "stepCount": len(t.steps) if t.steps else 0,
                "createdAt": t.created_at,
            })
        return items, total

    async def get_by_id(self, tour_id: str) -> Optional[GuideTour]:
        """根据 ID 获取指引"""
        return (
            await self.db.execute(
                select(GuideTour).where(GuideTour.id == tour_id)
            )
        ).scalar_one_or_none()

    async def create(self, data: GuideTourCreate, created_by: str) -> GuideTour:
        """创建指引"""
        tour = GuideTour(
            code=data.code,
            title=data.title,
            description=data.description,
            steps=[s.model_dump(by_alias=True) for s in data.steps],
            sort_order=data.sort_order,
            tenant_id=data.tenant_id,
            created_by=created_by,
            updated_by=created_by,
        )
        self.db.add(tour)
        await self.db.commit()
        await self.db.refresh(tour)
        return tour

    async def update(self, tour_id: str, data: GuideTourUpdate, updated_by: str) -> Optional[GuideTour]:
        """更新指引"""
        tour = await self.get_by_id(tour_id)
        if tour is None:
            return None

        if data.code is not None:
            tour.code = data.code
        if data.title is not None:
            tour.title = data.title
        if data.description is not None:
            tour.description = data.description
        if data.steps is not None:
            tour.steps = [s.model_dump(by_alias=True) for s in data.steps]
        if data.sort_order is not None:
            tour.sort_order = data.sort_order
        if data.tenant_id is not None:
            tour.tenant_id = data.tenant_id

        tour.updated_by = updated_by
        await self.db.commit()
        await self.db.refresh(tour)
        return tour

    async def update_status(self, tour_id: str, status: int, updated_by: str) -> Optional[GuideTour]:
        """更新指引发布状态"""
        tour = await self.get_by_id(tour_id)
        if tour is None:
            return None

        tour.status = status
        tour.updated_by = updated_by
        await self.db.commit()
        await self.db.refresh(tour)
        return tour

    async def delete(self, tour_id: str) -> bool:
        """删除指引"""
        tour = await self.get_by_id(tour_id)
        if tour is None:
            return False

        await self.db.delete(tour)
        await self.db.commit()
        return True
