
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_admin,
    get_store_filter,
    require_admin_tenant_anchor,
    require_permission,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.messages.service_messages import MessageService
from app.modules.messages.service_templates import MessageTemplateService
from app.schemas.message import (
    MessageBatchCreate,
    MessageCreate,
    MessageListResponse,
    MessageQuery,
    MessageResponse,
    MessageTemplateCreate,
    MessageTemplateResponse,
    MessageTemplateUpdate,
    MessageType,
    UnreadCountResponse,
)
from app.schemas.response import PageResponse

router = APIRouter()


# ========== 用户消息接口 ==========

@router.get(
    "/my",
    response_model=PageResponse[MessageListResponse],
    summary="获取我的消息",
    description="""获取当前用户的消息列表，支持多种过滤条件。

**功能说明：**
- 按用户ID和用户类型查询消息
- 支持按消息类型和已读状态过滤
- 支持分页查询
- 消息按创建时间倒序排列

**请求参数：**
- user_id: 用户ID（必需）
- user_type: 用户类型，patient/doctor（必需）
- message_type: 消息类型（可选）
- is_read: 已读状态，0-未读, 1-已读（可选）
- page: 页码，默认1
- page_size: 每页数量，默认10

**响应示例：**
```json
{
  "data": [
    {
      "id": "msg_123",
      "title": "预约提醒",
      "content": "您明天上午9点有预约",
      "message_type": "appointment",
      "is_read": 0,
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "total": 50,
  "page": 1,
  "page_size": 10
}
```

**多租户支持：**
- 通过 store_id 实现租户隔离
- user_id 跨租户唯一
"""
)
async def get_my_messages(
    message_type: MessageType | None = None,
    is_read: int | None = Query(None, ge=0, le=1),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
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


@router.get("/unread-count", response_model=UnreadCountResponse, summary="获取未读数")
async def get_unread_count(
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型"),
    db: AsyncSession = Depends(get_db)
):
    """获取未读消息数量"""
    service = MessageService(db)
    return await service.get_unread_count(user_id, user_type)


@router.get("/templates", response_model=list[MessageTemplateResponse], summary="获取模板列表")
async def get_templates(
    status: int | None = Query(None, ge=0, le=1),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:list"))
):
    """获取消息模板列表"""
    service = MessageTemplateService(db)
    templates = await service.get_list(status)
    return [MessageTemplateResponse.model_validate(t) for t in templates]


@router.post("/templates", response_model=MessageTemplateResponse, summary="创建消息模板")
async def create_template(
    data: MessageTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send"))
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


@router.put("/templates/{template_id}", response_model=MessageTemplateResponse, summary="更新消息模板")
async def update_template(
    template_id: str,
    data: MessageTemplateUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send"))
):
    """更新消息模板"""
    service = MessageTemplateService(db)
    template = await service.update(template_id, data)
    
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在，请检查后重试"
        )
    
    return MessageTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", summary="删除消息模板")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:delete"))
):
    """删除消息模板"""
    service = MessageTemplateService(db)
    success = await service.delete(template_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="模板不存在，请检查后重试"
        )
    
    return {"message": "删除成功"}


@router.get("/{message_id}", response_model=MessageResponse, summary="获取消息详情")
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
            detail="消息不存在，请检查后重试"
        )
    
    return MessageResponse.model_validate(message)


@router.post("/read/{message_id}", summary="标记已读")
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
            detail="消息不存在，请检查后重试"
        )
    
    return {"message": "已标记为已读"}


@router.post("/read-all", summary="全部标记已读")
async def mark_all_as_read(
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型"),
    message_type: str | None = Query(None, description="消息类型"),
    db: AsyncSession = Depends(get_db)
):
    """标记所有消息为已读"""
    service = MessageService(db)
    count = await service.mark_all_as_read(user_id, user_type, message_type)
    return {"message": f"已标记 {count} 条消息为已读"}


@router.delete("/{message_id}", summary="删除消息")
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
            detail="消息不存在，请检查后重试"
        )
    
    return {"message": "删除成功"}


@router.delete("/clear/read", summary="清空已读消息")
async def clear_read_messages(
    user_id: str = Query(..., description="用户ID"),
    user_type: str = Query(..., description="用户类型"),
    db: AsyncSession = Depends(get_db)
):
    """清空已读消息"""
    service = MessageService(db)
    count = await service.delete_all_read(user_id, user_type)
    return {"message": f"已删除 {count} 条已读消息"}


@router.get("", response_model=PageResponse[MessageListResponse], summary="获取消息列表")
async def get_all_messages(
    user_id: str | None = None,
    user_type: str | None = None,
    message_type: MessageType | None = None,
    is_read: int | None = Query(None, ge=0, le=1),
    keyword: str | None = None,
    store_id: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("message:list"))
):
    """获取所有消息列表（管理端）"""
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    service = MessageService(db)
    query = MessageQuery(
        message_type=message_type,
        is_read=is_read,
        page=page,
        page_size=page_size
    )
    messages, total = await service.get_all_messages(
        user_id=user_id,
        user_type=user_type,
        keyword=keyword,
        query=query,
        store_id=store_id,
        tenant_id=tenant_anchor,
    )
    
    return PageResponse(
        data=[MessageListResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/send", response_model=MessageResponse, summary="发送消息")
async def send_message(
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send"))
):
    """发送消息（管理端）"""
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")
    
    service = MessageService(db)
    message = await service.create(data, store_id=store_id)
    return MessageResponse.model_validate(message)


@router.post("/send-batch", summary="批量发送消息")
async def send_batch_messages(
    data: MessageBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send"))
):
    """批量发送消息（管理端）"""
    store_id = None
    if not current_admin.get("is_super_admin"):
        store_id = current_admin.get("current_store_id") or current_admin.get("store_id")
    
    service = MessageService(db)
    count = await service.batch_create(data, store_id=store_id)
    return {"message": f"成功发送 {count} 条消息"}
