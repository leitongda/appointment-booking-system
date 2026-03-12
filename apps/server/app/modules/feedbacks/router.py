import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_current_user, require_permission
from app.core.config import settings
from app.db.session import get_db
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackQuery,
    FeedbackReply,
    FeedbackResponse,
    FeedbackStatus,
    FeedbackType,
)
from app.schemas.response import PageResponse
from app.services.feedback_service import FeedbackService

router = APIRouter()


def parse_feedback_response(feedback) -> FeedbackResponse:
    images = None
    if feedback.images:
        try:
            images = json.loads(feedback.images)
        except Exception:
            pass

    return FeedbackResponse(
        id=feedback.id,
        user_id=feedback.user_id,
        user_type=feedback.user_type,
        feedback_type=feedback.feedback_type,
        title=feedback.title,
        content=feedback.content,
        images=images,
        contact=feedback.contact,
        status=feedback.status,
        handler_id=feedback.handler_id,
        reply=feedback.reply,
        handled_at=feedback.handled_at,
        created_at=feedback.created_at,
    )


@router.get("", response_model=PageResponse[FeedbackResponse], summary="获取反馈列表")
async def get_feedbacks(
    user_id: Optional[str] = None,
    feedback_type: Optional[FeedbackType] = None,
    status: Optional[FeedbackStatus] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("feedback:list")),
):
    service = FeedbackService(db)
    query = FeedbackQuery(
        user_id=user_id,
        feedback_type=feedback_type,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    feedbacks, total = await service.get_list(query)
    return PageResponse(
        data=[parse_feedback_response(f) for f in feedbacks],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/pending-count", summary="获取待处理数")
async def get_pending_count(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("feedback:list")),
):
    service = FeedbackService(db)
    return {"count": await service.get_pending_count()}


@router.get("/statistics", summary="获取反馈统计")
async def get_statistics(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("feedback:list")),
):
    service = FeedbackService(db)
    return await service.get_statistics()


@router.get("/my", response_model=List[FeedbackResponse], summary="获取我的反馈")
async def get_my_feedbacks(
    user_id: str = Query(..., description="用户ID"),
    db: AsyncSession = Depends(get_db),
):
    service = FeedbackService(db)
    feedbacks = await service.get_user_feedbacks(user_id)
    return [parse_feedback_response(f) for f in feedbacks]


@router.get("/{feedback_id}", response_model=FeedbackResponse, summary="获取反馈详情")
async def get_feedback(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
):
    service = FeedbackService(db)
    feedback = await service.get_by_id(feedback_id)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="反馈不存在，请检查后重试")
    return parse_feedback_response(feedback)


@router.post("", response_model=FeedbackResponse, summary="提交反馈")
async def create_feedback(
    data: FeedbackCreate,
    db: AsyncSession = Depends(get_db),
):
    service = FeedbackService(db)
    feedback = await service.create(data)
    return parse_feedback_response(feedback)


@router.post("/{feedback_id}/reply", response_model=FeedbackResponse, summary="回复反馈")
async def reply_feedback(
    feedback_id: str,
    data: FeedbackReply,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("feedback:reply")),
):
    service = FeedbackService(db)
    handler_id = current_admin.get("id")
    feedback = await service.reply(feedback_id, handler_id, data)
    if not feedback:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="反馈不存在，请检查后重试")
    return parse_feedback_response(feedback)


@router.patch("/{feedback_id}/status", summary="更新反馈状态")
async def update_feedback_status(
    feedback_id: str,
    new_status: FeedbackStatus = Query(..., alias="status", description="状态"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("feedback:reply")),
):
    service = FeedbackService(db)
    feedback = await service.update_status(feedback_id, new_status.value)
    if not feedback:
        raise HTTPException(status_code=404, detail="反馈不存在，请检查后重试")
    return {"message": "状态更新成功"}


@router.delete("/{feedback_id}", summary="删除反馈")
async def delete_feedback(
    feedback_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("feedback:delete")),
):
    service = FeedbackService(db)
    success = await service.delete(feedback_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="反馈不存在，请检查后重试")
    return {"message": "删除成功"}
