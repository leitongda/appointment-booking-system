"""
规则组管理 API

提供规则组的 CRUD 接口
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.api.deps import get_current_admin, get_current_super_admin
from app.schemas.rule_set import (
    PageResult, RuleSetCreate, RuleSetUpdate, RuleSetResponse, RuleSetDetailResponse,
    RulePreviewRequest, RulePreviewResponse,
    RuleWindowCreate, RuleWindowUpdate, RuleWindowResponse,
    RuleBookingPolicyCreate, RuleBookingPolicyResponse,
    RuleCheckinPolicyCreate, RuleCheckinPolicyResponse,
    RuleCapacityPolicyCreate, RuleCapacityPolicyResponse
)
from app.services.rule_set_service import RuleSetService
from app.services.rule_engine_service import RuleEngineService
from app.models.schedule import Schedule
from app.core.config import settings

router = APIRouter()


@router.get("", response_model=PageResult[RuleSetDetailResponse])
async def get_rule_sets(
    enabled: Optional[bool] = Query(None, description="是否启用"),
    shift_type_id: Optional[str] = Query(None, description="班次类型ID"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取规则组列表"""
    service = RuleSetService(db)
    rule_sets, total = await service.get_list(
        enabled=enabled,
        shift_type_id=shift_type_id,
        page=page,
        page_size=page_size
    )
    return {"data": rule_sets, "total": total}


@router.get("/{rule_set_id}", response_model=RuleSetDetailResponse)
async def get_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取规则组详情"""
    service = RuleSetService(db)
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return rule_set


@router.post("", response_model=RuleSetDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_rule_set(
    data: RuleSetCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """创建规则组（仅超级管理员）"""
    service = RuleSetService(db)
    try:
        rule_set = await service.create(data, current_admin["id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    return rule_set


@router.put("/{rule_set_id}", response_model=RuleSetDetailResponse)
async def update_rule_set(
    rule_set_id: str,
    data: RuleSetUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新规则组（仅超级管理员）"""
    service = RuleSetService(db)
    try:
        rule_set = await service.update(rule_set_id, data, current_admin["id"])
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return rule_set


@router.delete("/{rule_set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """删除规则组（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.delete(rule_set_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return None


@router.post("/{rule_set_id}/enable", status_code=status.HTTP_200_OK)
async def enable_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """启用规则组（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.enable(rule_set_id, current_admin["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return {"message": "启用成功"}


@router.post("/{rule_set_id}/disable", status_code=status.HTTP_200_OK)
async def disable_rule_set(
    rule_set_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """禁用规则组（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.disable(rule_set_id, current_admin["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return {"message": "禁用成功"}


@router.post("/preview", response_model=RulePreviewResponse)
async def preview_rule(
    data: RulePreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """预览规则效果

    根据输入的班次信息，计算各动作窗口的结果
    """
    engine = RuleEngineService(db)

    # 构造虚拟 schedule 对象
    schedule = Schedule()
    schedule.schedule_date = data.schedule_date
    schedule.start_time = data.start_time
    schedule.end_time = data.end_time
    schedule.shift_type_id = data.shift_type_id

    current_time = data.current_time

    # 检查各动作窗口
    book_result = await engine.check_action_window(schedule, 'BOOK', current_time)
    checkin_result = await engine.check_action_window(schedule, 'CHECKIN', current_time)
    cancel_result = await engine.check_action_window(schedule, 'CANCEL', current_time)

    return RulePreviewResponse(
        book_window=book_result,
        checkin_window=checkin_result,
        cancel_window=cancel_result
    )


# ==================== RuleWindow 独立管理 ====================

@router.post("/{rule_set_id}/windows", response_model=RuleWindowResponse, status_code=status.HTTP_201_CREATED)
async def create_window(
    rule_set_id: str,
    data: RuleWindowCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """创建时间窗（仅超级管理员）"""
    service = RuleSetService(db)
    window = await service.create_window(rule_set_id, data, current_admin["id"])
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )
    return window


@router.put("/windows/{window_id}", response_model=RuleWindowResponse)
async def update_window(
    window_id: str,
    data: RuleWindowUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新时间窗（仅超级管理员）"""
    service = RuleSetService(db)
    window = await service.update_window(window_id, data, current_admin["id"])
    if not window:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="时间窗不存在"
        )
    return window


@router.delete("/windows/{window_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_window(
    window_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """删除时间窗（仅超级管理员）"""
    service = RuleSetService(db)
    success = await service.delete_window(window_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="时间窗不存在"
        )
    return None


# ==================== Policy 独立管理 ====================

@router.put("/{rule_set_id}/booking-policy", response_model=RuleBookingPolicyResponse)
async def update_booking_policy(
    rule_set_id: str,
    data: RuleBookingPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新预约策略（仅超级管理员）

    如果策略不存在则创建，存在则更新
    """
    service = RuleSetService(db)

    # 先检查规则组是否存在
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )

    policy = await service.update_booking_policy(rule_set_id, data, current_admin["id"])
    return policy


@router.put("/{rule_set_id}/checkin-policy", response_model=RuleCheckinPolicyResponse)
async def update_checkin_policy(
    rule_set_id: str,
    data: RuleCheckinPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新签到策略（仅超级管理员）

    如果策略不存在则创建，存在则更新
    """
    service = RuleSetService(db)

    # 先检查规则组是否存在
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )

    policy = await service.update_checkin_policy(rule_set_id, data, current_admin["id"])
    return policy


@router.put("/{rule_set_id}/capacity-policy", response_model=RuleCapacityPolicyResponse)
async def update_capacity_policy(
    rule_set_id: str,
    data: RuleCapacityPolicyCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_super_admin)
):
    """更新容量策略（仅超级管理员）

    如果策略不存在则创建，存在则更新
    """
    service = RuleSetService(db)

    # 先检查规则组是否存在
    rule_set = await service.get_by_id(rule_set_id)
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="规则组不存在"
        )

    policy = await service.update_capacity_policy(rule_set_id, data, current_admin["id"])
    return policy
