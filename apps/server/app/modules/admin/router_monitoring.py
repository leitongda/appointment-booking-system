"""Admin logs and online status router."""

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_admin
from app.common.deps import require_permission
from app.core.config import settings
from app.core.redis import RedisCache
from app.db.session import get_db
from app.models.admin import Admin, AdminLoginHistory
from app.modules.admin.schemas import (
    LoginHistoryResponse,
    OnlineUserResponse,
    OperationLogResponse,
    UserStatusResponse,
)
from app.schemas.response import PageResponse
from app.modules.admin.service_logs import OperationLogService

router = APIRouter()


@router.get("/logs", response_model=PageResponse[OperationLogResponse], summary="获取操作日志")
async def get_operation_logs(
    admin_id: Optional[str] = None,
    module: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    service = OperationLogService(db)
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    items, total = await service.get_list(
        admin_id=admin_id,
        module=module,
        start_time=start_time,
        end_time=end_time,
        page=page,
        page_size=page_size,
        tenant_id=tenant_id,
    )
    return PageResponse(
        data=[OperationLogResponse.model_validate(item) for item in items],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/online-users", summary="获取在线用户")
async def get_online_users(
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    # 非超管仅查看当前租户的在线用户，超管可查看全部
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    sessions = await RedisCache.get_all_admin_sessions(tenant_id=tenant_id)
    return [
        OnlineUserResponse(
            admin_id=session.get("admin_id", ""),
            username=session.get("username", ""),
            name=session.get("name"),
            role_name=session.get("role_name"),
            login_time=session.get("login_time", ""),
            login_ip=session.get("login_ip", ""),
            user_agent=session.get("user_agent", ""),
            device_info=session.get("device_info", {}),
            ttl=session.get("ttl", 0),
        ).model_dump(by_alias=True)
        for session in sessions
    ]


@router.post("/online-users/{admin_id}/kick", summary="强制用户下线")
async def kick_online_user(
    admin_id: str,
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    if not current_admin.get("is_super_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="需要超级管理员权限")
    if admin_id == current_admin.get("id"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不能强制自己下线")

    # 获取被踢管理员的租户ID，用于构建租户隔离的 Redis 键
    result = await db.execute(select(Admin).where(Admin.id == admin_id))
    target_admin = result.scalar_one_or_none()
    target_tenant_id = target_admin.tenant_id if target_admin else None

    session = await RedisCache.get_admin_session(admin_id, tenant_id=target_tenant_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不在线，无法执行此操作")

    login_history_id = session.get("login_history_id")
    login_time_str = session.get("login_time")
    if login_history_id:
        result = await db.execute(select(AdminLoginHistory).where(AdminLoginHistory.id == login_history_id))
        login_history = result.scalar_one_or_none()
        if login_history:
            logout_time = datetime.utcnow()
            login_history.logout_time = logout_time
            login_history.logout_type = "kicked"
            if login_time_str:
                try:
                    login_time = datetime.fromisoformat(login_time_str)
                    login_history.duration = int((logout_time - login_time).total_seconds())
                except Exception:
                    pass
            await db.commit()

    token_hash = session.get("token_hash")
    session_key = RedisCache._build_admin_session_key(admin_id, tenant_id=target_tenant_id)
    ttl = await RedisCache.ttl(session_key)
    if token_hash and ttl > 0:
        await RedisCache.add_token_to_blacklist(token_hash, ttl, tenant_id=target_tenant_id)
    await RedisCache.delete_admin_session(admin_id, tenant_id=target_tenant_id)
    return {"message": "用户已强制下线"}


@router.get("/user-status", summary="获取用户状态")
async def get_user_status(
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    # 非超管仅查看当前租户的在线用户，超管可查看全部
    tenant_id = None if current_admin.get("is_super_admin") else current_admin.get("tenant_id")
    sessions = await RedisCache.get_all_admin_sessions(tenant_id=tenant_id)
    online_admin_ids = {s.get("admin_id") for s in sessions}
    session_map = {s.get("admin_id"): s for s in sessions}

    admin_query = select(Admin).options(selectinload(Admin.role)).where(Admin.status == 1)
    if tenant_id:
        admin_query = admin_query.where(Admin.tenant_id == tenant_id)
    admin_query = admin_query.order_by(Admin.created_at.desc())
    result = await db.execute(admin_query)
    admins = result.scalars().all()

    user_status_list = []
    for admin in admins:
        if admin.id in online_admin_ids:
            session = session_map[admin.id]
            user_status_list.append(
                UserStatusResponse(
                    admin_id=admin.id,
                    username=admin.username,
                    name=admin.name,
                    role_name=admin.role.name if admin.role else None,
                    status="online",
                    login_time=session.get("login_time"),
                    login_ip=session.get("login_ip"),
                    device_info=session.get("device_info"),
                    ttl=session.get("ttl", 0),
                    last_login_at=None,
                    last_login_ip=None,
                ).model_dump(by_alias=True)
            )
        else:
            user_status_list.append(
                UserStatusResponse(
                    admin_id=admin.id,
                    username=admin.username,
                    name=admin.name,
                    role_name=admin.role.name if admin.role else None,
                    status="offline",
                    login_time=None,
                    login_ip=None,
                    device_info=None,
                    ttl=None,
                    last_login_at=admin.last_login_at.isoformat() if admin.last_login_at else None,
                    last_login_ip=admin.last_login_ip,
                ).model_dump(by_alias=True)
            )
    return user_status_list


@router.get("/login-history/{admin_id}", summary="获取登录历史")
async def get_login_history(
    admin_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=settings.MAX_PAGE_SIZE),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(require_permission("system:log", "log:list")),
):
    target_admin_result = await db.execute(select(Admin).where(Admin.id == admin_id))
    target_admin = target_admin_result.scalar_one_or_none()
    if not target_admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    if (
        not current_admin.get("is_super_admin")
        and target_admin.tenant_id != current_admin.get("tenant_id")
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权查看该用户的登录历史")

    count_stmt = select(func.count(AdminLoginHistory.id)).where(AdminLoginHistory.admin_id == admin_id)
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    stmt = (
        select(AdminLoginHistory)
        .where(AdminLoginHistory.admin_id == admin_id)
        .order_by(AdminLoginHistory.login_time.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    history_list = [
        LoginHistoryResponse(
            id=record.id,
            login_time=record.login_time.isoformat() if record.login_time else "",
            logout_time=record.logout_time.isoformat() if record.logout_time else None,
            logout_type=record.logout_type,
            login_ip=record.login_ip,
            browser=record.browser,
            os=record.os,
            device_type=record.device_type,
            duration=record.duration,
        ).model_dump(by_alias=True)
        for record in records
    ]
    return {"list": history_list, "total": total, "page": page, "pageSize": page_size}
