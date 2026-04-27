"""常见服务模块路由"""
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.session import get_db
from app.modules.common_services.schemas import (
    CommonServiceListResponse,
    CommonServiceResponse,
    HealthReminderResponse,
    UserHealthReminderResponse,
)
from app.modules.common_services.service import CommonServiceService, HealthReminderService
from app.schemas.response import Response

router = APIRouter()


@router.get("/common-services", response_model=Response[CommonServiceListResponse], summary="获取常见服务列表")
async def get_common_services(
    store_id: Optional[str] = None,
    status: int = Query(1, description="状态过滤：0禁用 1启用"),
    db: AsyncSession = Depends(get_db),
):
    """获取常见服务列表

    返回租户级配置的常见服务，包含服务-科室映射信息
    """
    service = CommonServiceService(db)
    items = await service.get_list(store_id=store_id, status=status)

    # 加载科室名称
    for item in items:
        if item.department:
            item.department_name = item.department.name

    return Response(
        data=CommonServiceListResponse(
            items=[CommonServiceResponse.model_validate(item) for item in items]
        )
    )


@router.get("/health-reminders/config", response_model=Response[list[HealthReminderResponse]], summary="获取健康提醒配置")
async def get_health_reminder_config(
    store_id: Optional[str] = None,
    reminder_type: Optional[str] = Query(None, description="提醒类型过滤"),
    db: AsyncSession = Depends(get_db),
):
    """获取健康提醒配置（租户级静态配置）

    返回租户配置的健康提醒信息，不包含用户个性化数据
    """
    service = HealthReminderService(db)
    items = await service.get_config(store_id=store_id, reminder_type=reminder_type)

    # 解析贴士
    for item in items:
        if isinstance(item.tips, str):
            try:
                import json
                item.tips = json.loads(item.tips)
            except:
                item.tips = []

    return Response(
        data=[HealthReminderResponse.model_validate(item) for item in items]
    )


@router.get("/health-reminders/my", response_model=Response[UserHealthReminderResponse], summary="获取我的健康提醒")
async def get_my_health_reminder(
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """获取当前用户的健康提醒信息

    基于用户预约历史和租户配置返回个性化的健康提醒
    """
    service = HealthReminderService(db)
    user_id = current_user.get("sub") or current_user.get("user_id")

    result = await service.get_user_reminder(user_id=user_id, store_id=store_id)

    return Response(data=UserHealthReminderResponse(**result))
