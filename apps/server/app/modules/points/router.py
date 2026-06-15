"""积分管理 API（独立路由）"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.modules.points.service import PointService
from app.schemas.point_log import PointAdjustData

router = APIRouter()


@router.get("/logs", summary="获取全局积分流水")
async def get_all_point_logs(
    keyword: str | None = Query(None, description="搜索用户姓名/手机号"),
    log_type: int | None = Query(None, ge=1, le=4, description="类型: 1消费 2充值 3赠送 4手动调整"),
    start_date: str | None = Query(None, description="开始日期 YYYY-MM-DD"),
    end_date: str | None = Query(None, description="结束日期 YYYY-MM-DD"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("points:list")),
):
    """获取全局积分流水列表（跨用户）"""
    service = PointService(db)
    items, total = await service.get_all_logs(
        keyword=keyword,
        log_type=log_type,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )
    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.get("/users", summary="获取用户积分排行")
async def get_point_users(
    keyword: str | None = Query(None, description="搜索用户姓名/手机号"),
    sort_by: str = Query("points", description="排序字段: points"),
    sort_order: str = Query("desc", description="排序方向: asc/desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("points:list")),
):
    """获取用户积分排行列表"""
    service = PointService(db)
    items, total = await service.get_user_ranking(
        keyword=keyword,
        sort_by=sort_by,
        sort_order=sort_order,
        page=page,
        page_size=page_size,
    )
    return {
        "data": items,
        "total": total,
        "page": page,
        "pageSize": page_size,
    }


@router.post("/{user_id}/adjust", summary="调整用户积分")
async def adjust_user_points(
    user_id: str,
    data: PointAdjustData,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("points:update")),
):
    """调整指定用户的积分"""
    service = PointService(db)
    result = await service.adjust_points_by_user_id(
        user_id=user_id,
        amount=data.amount,
        remark=data.remark,
        operator_id=current_admin.get("id"),
    )
    if result is None:
        from fastapi import HTTPException, status
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="积分调整失败，用户不存在或余额不足",
        )
    return {"message": "调整成功", "data": result}
