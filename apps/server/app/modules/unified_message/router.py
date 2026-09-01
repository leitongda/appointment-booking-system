"""统一消息中心路由

提供消息发送、查询、模板管理、接收人规则管理等 API。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    get_current_account_dict,
    get_current_admin,
    require_permission,
)
from app.db.session import get_db
from app.modules.unified_message.schemas import (
    BatchSendResult,
    MessageQuery,
    MessageResponse,
    NotificationEvent,
    RecipientRuleCreate,
    RecipientRuleResponse,
    SendResult,
    UnifiedTemplateCreate,
    UnifiedTemplateResponse,
    UnreadCountResponse,
)
from app.modules.unified_message.service import UnifiedMessageService
from app.schemas.response import PageResponse

router = APIRouter()


# ========== 消息发送 ==========

@router.post("/send", response_model=SendResult, summary="发送统一通知")
async def send_notification(
    event: NotificationEvent,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send")),
):
    """发送统一通知"""
    service = UnifiedMessageService(db)
    return await service.send(event)


@router.post("/send-batch", response_model=BatchSendResult, summary="批量发送通知")
async def send_batch_notification(
    event: NotificationEvent,
    rule_id: str | None = Query(None, description="指定接收人规则ID"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send")),
):
    """根据规则批量发送通知"""
    service = UnifiedMessageService(db)
    return await service.send_to_rule(event, rule_id=rule_id)


# ========== 消息查询 ==========

def _get_user_info(current_user: dict) -> tuple[str, str]:
    """从 JWT 用户信息中提取 user_id 和 user_type

    Returns:
        (user_id, user_type): user_type 映射为 patient/doctor/admin
    """
    user_id = current_user.get("id")
    role_type = current_user.get("role_type", "user")

    # 映射 role_type 到 user_type
    role_type_map = {
        "user": "patient",
        "doctor": "doctor",
        "admin": "admin",
    }
    user_type = role_type_map.get(role_type, "patient")

    return user_id, user_type


@router.get("/my", response_model=PageResponse[MessageResponse], summary="获取我的消息")
async def get_my_messages(
    message_type: str | None = Query(None, description="消息类型"),
    is_read: int | None = Query(None, ge=0, le=1, description="已读状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """获取当前用户的消息列表（从 JWT 自动提取用户信息）"""
    user_id, user_type = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    query = MessageQuery(
        message_type=message_type,
        is_read=is_read,
        page=page,
        page_size=page_size,
    )
    messages, total = await service.get_user_messages(user_id, user_type, query)
    return PageResponse(
        data=[MessageResponse.model_validate(m) for m in messages],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/unread-count", response_model=UnreadCountResponse, summary="获取未读数")
async def get_unread_count(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """获取未读消息数量（从 JWT 自动提取用户信息）"""
    user_id, user_type = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    return await service.get_unread_count(user_id, user_type)


@router.post("/read/{message_id}", summary="标记已读")
async def mark_as_read(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """标记消息为已读（从 JWT 自动提取用户信息）"""
    user_id, _ = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    success = await service.mark_as_read(message_id, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    return {"message": "已标记为已读"}


@router.post("/read-all", summary="全部标记已读")
async def mark_all_as_read(
    message_type: str | None = Query(None, description="消息类型"),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """标记所有消息为已读（从 JWT 自动提取用户信息）"""
    user_id, user_type = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    count = await service.mark_all_as_read(user_id, user_type, message_type)
    return {"message": f"已标记 {count} 条消息为已读"}


@router.delete("/{message_id}", summary="删除消息")
async def delete_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """删除消息（从 JWT 自动提取用户信息）"""
    user_id, _ = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    success = await service.delete(message_id, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    return {"message": "删除成功"}


@router.delete("/clear/read", summary="清空已读消息")
async def clear_read_messages(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """清空已读消息（从 JWT 自动提取用户信息）"""
    user_id, user_type = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    count = await service.delete_all_read(user_id, user_type)
    return {"message": f"已删除 {count} 条已读消息"}


# ========== 模板管理 ==========

@router.get(
    "/templates",
    response_model=list[UnifiedTemplateResponse],
    summary="获取模板列表",
)
async def get_templates(
    message_type: str | None = Query(None, description="消息类型"),
    status: int | None = Query(None, ge=0, le=1, description="状态"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:list")),
):
    """获取统一模板列表"""
    service = UnifiedMessageService(db)
    return await service.get_templates(
        tenant_id=current_admin.get("tenant_id"),
        message_type=message_type,
        status=status,
    )


@router.post(
    "/templates",
    response_model=UnifiedTemplateResponse,
    summary="创建模板",
)
async def create_template(
    data: UnifiedTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send")),
):
    """创建统一模板"""
    service = UnifiedMessageService(db)
    try:
        template = await service.create_template(
            tenant_id=current_admin.get("tenant_id"),
            template_data=data.model_dump(),
        )
        return UnifiedTemplateResponse.model_validate(template)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/templates/{template_id}",
    response_model=UnifiedTemplateResponse,
    summary="更新模板",
)
async def update_template(
    template_id: str,
    data: UnifiedTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send")),
):
    """更新统一模板"""
    service = UnifiedMessageService(db)
    template = await service.update_template(
        template_id=template_id,
        tenant_id=current_admin.get("tenant_id"),
        template_data=data.model_dump(),
    )
    if not template:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return UnifiedTemplateResponse.model_validate(template)


@router.delete("/templates/{template_id}", summary="删除模板")
async def delete_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:delete")),
):
    """删除统一模板"""
    service = UnifiedMessageService(db)
    success = await service.delete_template(template_id, current_admin.get("tenant_id"))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模板不存在")
    return {"message": "删除成功"}


# ========== 接收人规则管理 ==========

@router.get(
    "/rules",
    response_model=list[RecipientRuleResponse],
    summary="获取规则列表",
)
async def get_rules(
    event_type: str | None = Query(None, description="事件类型"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:list")),
):
    """获取接收人规则列表"""
    service = UnifiedMessageService(db)
    return await service.get_rules(
        tenant_id=current_admin.get("tenant_id"),
        event_type=event_type,
    )


@router.post(
    "/rules",
    response_model=RecipientRuleResponse,
    summary="创建规则",
)
async def create_rule(
    data: RecipientRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send")),
):
    """创建接收人规则"""
    service = UnifiedMessageService(db)
    rule = await service.create_rule(
        tenant_id=current_admin.get("tenant_id"),
        rule_data=data.model_dump(),
    )
    return RecipientRuleResponse.model_validate(rule)


@router.put(
    "/rules/{rule_id}",
    response_model=RecipientRuleResponse,
    summary="更新规则",
)
async def update_rule(
    rule_id: str,
    data: RecipientRuleCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:send")),
):
    """更新接收人规则"""
    service = UnifiedMessageService(db)
    rule = await service.update_rule(
        rule_id=rule_id,
        tenant_id=current_admin.get("tenant_id"),
        rule_data=data.model_dump(),
    )
    if not rule:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    return RecipientRuleResponse.model_validate(rule)


@router.delete("/rules/{rule_id}", summary="删除规则")
async def delete_rule(
    rule_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("message:delete")),
):
    """删除接收人规则"""
    service = UnifiedMessageService(db)
    success = await service.delete_rule(rule_id, current_admin.get("tenant_id"))
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="规则不存在")
    return {"message": "删除成功"}


@router.get("/{message_id}", response_model=MessageResponse, summary="获取消息详情")
async def get_message(
    message_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_account_dict),
):
    """获取消息详情（从 JWT 自动提取用户信息）"""
    user_id, _ = _get_user_info(current_user)

    service = UnifiedMessageService(db)
    message = await service.get_by_id(message_id, user_id)
    if not message:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="消息不存在")
    return MessageResponse.model_validate(message)
