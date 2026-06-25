"""考勤规则管理 API

提供考勤规则的 CRUD 接口
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.config import settings
from app.db.session import get_db
from app.modules.attendance_rules.schemas import (
    AttendanceRuleCreate,
    AttendanceRuleResponse,
    AttendanceRuleUpdate,
)
from app.modules.attendance_rules.service import AttendanceRuleService
from app.schemas.rule_set import PageResult

router = APIRouter()


@router.get("", response_model=PageResult[AttendanceRuleResponse], summary="获取考勤规则列表")
async def get_attendance_rules(
    keyword: str | None = Query(None, description="搜索关键词"),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE, description="每页数量"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取考勤规则列表"""
    service = AttendanceRuleService(db)
    items, total = await service.get_list(
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResult(data=items, total=total)


@router.get("/{rule_id}", response_model=AttendanceRuleResponse, summary="获取考勤规则详情")
async def get_attendance_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """获取考勤规则详情"""
    service = AttendanceRuleService(db)
    rule = await service.get_by_id(rule_id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤规则不存在",
        )
    return rule


@router.post("", response_model=AttendanceRuleResponse, status_code=status.HTTP_201_CREATED, summary="创建考勤规则")
async def create_attendance_rule(
    data: AttendanceRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """创建考勤规则"""
    service = AttendanceRuleService(db)
    rule = await service.create(
        data=data.model_dump(),
        operator_id=current_admin["id"],
    )
    return rule


@router.put("/{rule_id}", response_model=AttendanceRuleResponse, summary="更新考勤规则")
async def update_attendance_rule(
    rule_id: str,
    data: AttendanceRuleUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """更新考勤规则"""
    service = AttendanceRuleService(db)
    rule = await service.update(
        rule_id=rule_id,
        data=data.model_dump(exclude_unset=True),
        operator_id=current_admin["id"],
    )
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤规则不存在",
        )
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT, summary="删除考勤规则")
async def delete_attendance_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    """删除考勤规则"""
    service = AttendanceRuleService(db)
    success = await service.delete(rule_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="考勤规则不存在",
        )
    return None
