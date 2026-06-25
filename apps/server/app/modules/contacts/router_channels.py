"""渠道账号 CRUD 路由"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.auth_deps import get_current_admin
from app.common.permission_deps import require_permission
from app.db.session import get_db
from app.modules.contacts.schemas import (
    ChannelAccountCreate,
    ChannelAccountListResponse,
    ChannelAccountResponse,
    ChannelAccountTestResponse,
    ChannelAccountUpdate,
)
from app.modules.contacts.service import ChannelAccountService

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("", summary="获取渠道账号列表")
async def list_channel_accounts(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    channel_type: str | None = None,
    store_id: str | None = None,
    status: int | None = None,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ChannelAccountService(db)
    items, total = await service.get_list(
        tenant_id=current_admin["tenant_id"],
        channel_type=channel_type,
        store_id=store_id,
        status=status,
        page=page,
        page_size=page_size,
    )
    return {
        "items": [ChannelAccountListResponse.model_validate(item) for item in items],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{account_id}", summary="获取渠道账号详情")
async def get_channel_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:view")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ChannelAccountService(db)
    account = await service.get_by_id(account_id, current_admin["tenant_id"])
    if not account:
        raise HTTPException(status_code=404, detail="渠道账号不存在")
    return ChannelAccountResponse.model_validate(account)


@router.post("", summary="创建渠道账号")
async def create_channel_account(
    data: ChannelAccountCreate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:create")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ChannelAccountService(db)
    account = await service.create(
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        created_by=current_admin.get("id"),
    )
    await db.commit()
    return ChannelAccountResponse.model_validate(account)


@router.put("/{account_id}", summary="更新渠道账号")
async def update_channel_account(
    account_id: str,
    data: ChannelAccountUpdate,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ChannelAccountService(db)
    account = await service.update(
        account_id,
        data.model_dump(exclude_unset=True),
        tenant_id=current_admin["tenant_id"],
        updated_by=current_admin.get("id"),
    )
    if not account:
        raise HTTPException(status_code=404, detail="渠道账号不存在")
    await db.commit()
    return ChannelAccountResponse.model_validate(account)


@router.delete("/{account_id}", summary="删除渠道账号")
async def delete_channel_account(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:delete")),
    current_admin: dict = Depends(get_current_admin),
):
    service = ChannelAccountService(db)
    success = await service.delete(account_id, current_admin["tenant_id"])
    if not success:
        raise HTTPException(status_code=404, detail="渠道账号不存在")
    await db.commit()
    return {"deleted": True}


@router.post("/{account_id}/test", summary="测试渠道连接")
async def test_channel_connection(
    account_id: str,
    db: AsyncSession = Depends(get_db),
    _=Depends(require_permission("contact:edit")),
    current_admin: dict = Depends(get_current_admin),
):
    """测试渠道账号连接是否可用"""
    service = ChannelAccountService(db)
    account = await service.get_by_id(account_id, current_admin["tenant_id"])
    if not account:
        raise HTTPException(status_code=404, detail="渠道账号不存在")

    try:
        config = json.loads(account.config) if account.config else {}
    except json.JSONDecodeError:
        return ChannelAccountTestResponse(success=False, message="配置格式错误，不是有效的 JSON")

    # 根据渠道类型执行不同的测试逻辑
    channel_type = account.channel_type
    try:
        if channel_type == "email":
            success, msg = await _test_email(config)
        elif channel_type == "sms":
            success, msg = await _test_sms(config)
        elif channel_type == "wechat":
            success, msg = await _test_wechat(config)
        elif channel_type == "webhook":
            success, msg = await _test_webhook(config)
        else:
            success, msg = False, f"不支持的渠道类型: {channel_type}"
    except Exception as e:
        logger.error(f"测试渠道连接失败: account_id={account_id}, error={e}")
        success, msg = False, f"测试失败: {e!s}"

    # 更新最后同步时间和错误信息
    from datetime import datetime
    account.last_sync_at = datetime.utcnow()
    account.last_error = None if success else msg
    await db.commit()

    return ChannelAccountTestResponse(success=success, message=msg)


async def _test_email(config: dict) -> tuple[bool, str]:
    """测试邮件渠道连接"""
    host = config.get("smtp_host")
    port = config.get("smtp_port", 465)
    if not host:
        return False, "缺少 SMTP 服务器地址"
    try:
        import asyncio
        import aiosmtplib
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 在 async 上下文中，使用 run_in_executor
            import socket
            sock = socket.create_connection((host, int(port)), timeout=5)
            sock.close()
            return True, "SMTP 服务器连接成功"
        return False, "无法获取事件循环"
    except Exception as e:
        return False, f"SMTP 连接失败: {e!s}"


async def _test_sms(config: dict) -> tuple[bool, str]:
    """测试短信渠道连接"""
    access_key = config.get("access_key_id")
    if not access_key:
        return False, "缺少 AccessKey"
    return True, "短信渠道配置验证通过（需实际发送测试短信确认）"


async def _test_wechat(config: dict) -> tuple[bool, str]:
    """测试微信渠道连接"""
    app_id = config.get("app_id")
    if not app_id:
        return False, "缺少 AppID"
    return True, "微信渠道配置验证通过（需实际调用 API 确认）"


async def _test_webhook(config: dict) -> tuple[bool, str]:
    """测试 Webhook 连接"""
    url = config.get("url")
    if not url:
        return False, "缺少 Webhook URL"
    try:
        import httpx
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.options(url)
            return True, f"Webhook 端点可达 (HTTP {resp.status_code})"
    except httpx.TimeoutException:
        return False, "Webhook 端点连接超时"
    except Exception as e:
        return False, f"Webhook 连接失败: {e!s}"
