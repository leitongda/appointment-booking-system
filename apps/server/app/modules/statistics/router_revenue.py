"""数据统计 - 收入趋势"""
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter
from app.schemas.response import ResponseModel
from app.db.session import get_db
from app.modules.revenue.service import RevenueService

router = APIRouter()


@router.get("/revenue/trend", response_model=ResponseModel, summary="获取收入趋势")
async def get_revenue_trend(
    days: int = Query(default=7, ge=1, le=30),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取收入趋势"""
    today = date.today()
    start_date = today - timedelta(days=days - 1)

    # 获取门店过滤条件
    store_filter = get_store_filter(current_admin)

    # 通过诊费系统计算收入
    revenue_service = RevenueService(db)
    data = await revenue_service.calculate_revenue_trend(
        start_date=start_date,
        end_date=today,
        store_id=store_filter if isinstance(store_filter, str) else None
    )

    trend = []
    for i in range(days):
        d = start_date + timedelta(days=i)
        trend.append({
            "date": str(d),
            "revenue": data.get(str(d), 0)
        })

    return ResponseModel(data=trend)
