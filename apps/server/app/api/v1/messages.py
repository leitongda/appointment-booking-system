from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_user
from app.schemas.message import (
    MessageCreate, MessageBatchCreate, MessageQuery,
    MessageResponse, MessageListResponse, UnreadCountResponse,
    MessageTemplateCreate, MessageTemplateUpdate, MessageTemplateResponse,
    MessageType
)
from app.schemas.response import PageResponse
from app.services.message_service import MessageService, MessageTemplateService

router = APIRouter()


# ========== 用户消息接口 ==========

@router.get("/my", response_model=PageResponse[MessageListResponse])
async def get_my_messages(
    message_type: Optional[MessageType] = None,
    is_read: Optional[int] = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型: patient/doctor"),
    db: AsyncSession = Depends(get_db)
):
    """获取我的消息列表"""
    service = MessageService(db)
    query = MessageQuery(
        message_type=message_type,
        is_read=is_read,
        page=page,
        page_size=page_size
    )
    messages, total = await service.get_user_messages(user_id, user_type, query)
    
    return PageResponse(
        data=[MessageListResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
async def get_unread_count(
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型"),
    db: AsyncSession = Depends(get_db)
):
    """获取未读消息数量"""
    service = MessageService(db)
    return await service.get_unread_count(user_id, user_type)


@router.get("/{message_id}", response_model=MessageResponse)
async def get_message(
    message_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取消息详情"""
    service = MessageService(db)
    message = await service.get_by_id(message_id)
    
    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    return MessageResponse.model_validate(message)


@router.post("/read/{message_id}")
async def mark_as_read(
    message_id: str,
    user_id: str = Query(..., description="用户ID"),
    db: AsyncSession = Depends(get_db)
):
    """标记消息为已读"""
    service = MessageService(db)
    success = await service.mark_as_read(message_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    return {"message": "已标记为已读"}


@router.post("/read-all")
async def mark_all_as_read(
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型"),
    message_type: Optional[str] = Query(None, description="消息类型"),
    db: AsyncSession = Depends(get_db)
):
    """标记所有消息为已读"""
    service = MessageService(db)
    count = await service.mark_all_as_read(user_id, user_type, message_type)
    return {"message": f"已标记 {count} 条消息为已读"}


@router.delete("/{message_id}")
async def delete_message(
    message_id: str,
    user_id: str = Query(..., description="用户ID"),
    db: AsyncSession = Depends(get_db)
):
    """删除消息"""
    service = MessageService(db)
    success = await service.delete(message_id, user_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="消息不存在"
        )
    
    return {"message": "删除成功"}


@router.delete("/clear/read")
async def clear_read_messages(
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型"),
    db: AsyncSession = Depends(get_db)
):
    """清空已读消息"""
    service = MessageService(db)
    count = await service.delete_all_read(user_id, user_type)
    return {"message": f"已删除 {count} 条已读消息"}


# ========== 管理端发送消息接口 ==========

@router.post("/send", response_model=MessageResponse)
async def send_message(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db)
):
    """发送消息（管理端）"""
    service = MessageService(db)
    message = await service.create(data)
    return MessageResponse.model_validate(message)


@router.post("/send-batch")
async def send_batch_messages(
    data: MessageBatchCreate,
    db: AsyncSession = Depends(get_db)
):
    """批量发送消息（管理端）"""
    service = MessageService(db)
    count = await service.batch_create(data)
    return {"message": f"成功发送 {count} 条消息"}


# ========== 消息模板接口 ==========

@router.get("/templates", response_model=List[MessageTemplateResponse])
async def get_templates(
    status: Optional[int] = Query(None, ge=0, le=1),
    db: AsyncSession = Depends(get_db)
):
    """获取消息模板列表"""
    service = MessageTemplateService(db)
    templates = await service.get_list(status)
    return [MessageTemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=MessageTemplateResponse)
async def create_template(
    data: MessageTemplateCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建消息模板"""
    service = MessageTemplateService(db)
    try:
        template = await service.create(data)
        return MessageTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.put("/templates/{template_id}", response_model=MessageTemplateResponse)
async def update_template(
    template_id: str,
    data: MessageTemplateUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新消息模板"""
    service = MessageTemplateService(db)
    template = await service.update(template_id, data)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在"
        )
    
    return MessageTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    """删除消息模板"""
    service = MessageTemplateService(db)
    success = await service.delete(template_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在"
        )
    
    return {"message": "删除成功"}
