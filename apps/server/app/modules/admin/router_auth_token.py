"""Token 和 Session 管理相关端点"""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from datetime import datetime
import json

from app.api.deps import get_current_admin
from app.core.config import settings
from app.core.redis import RedisCache
from app.db.session import get_db
from app.models.admin import Admin, Permission
from app.modules.admin.helpers import build_admin_response, build_stores_list
from app.modules.admin.schemas import AdminResponse, StoreInfo, SwitchStoreRequest
from app.modules.admin.service_admins import AdminService

router = APIRouter()
logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


@router.get("/me", response_model=AdminResponse, summary="获取当前管理员信息")
async def get_current_admin_info(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    admin_id = current_admin["id"]
    result = await db.execute(
        select(Admin)
        .options(selectinload(Admin.role), selectinload(Admin.current_store), selectinload(Admin.stores))
        .where(Admin.id == admin_id)
    )
    admin = result.unique().scalar_one_or_none()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")

    permissions = []
    if admin.role:
        if admin.role.code == "SUPER_ADMIN":
            perm_result = await db.execute(select(Permission.code).order_by(Permission.sort.asc()))
            permissions = list(perm_result.scalars().all())
        elif admin.role.permissions:
            try:
                permissions = json.loads(admin.role.permissions)
            except (json.JSONDecodeError, TypeError):
                permissions = []
    return build_admin_response(admin, permissions)


@router.post("/logout", summary="退出登录")
async def admin_logout(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_admin: dict = Depends(get_current_admin),
    db: AsyncSession = Depends(get_db),
):
    from app.models.admin import AdminLoginHistory

    admin_id = current_admin.get("id")
    admin_tenant_id = current_admin.get("tenant_id")
    token = credentials.credentials
    token_hash = __import__("hashlib").sha256(token.encode()).hexdigest()[:32]
    # 传递 tenant_id 实现多租户会话隔离
    session = await RedisCache.get_admin_session(admin_id, tenant_id=admin_tenant_id)
    session_key = RedisCache._build_admin_session_key(admin_id, tenant_id=admin_tenant_id)
    ttl = await RedisCache.ttl(session_key)

    if session:
        login_history_id = session.get("login_history_id")
        login_time_str = session.get("login_time")
        if login_history_id:
            result = await db.execute(select(AdminLoginHistory).where(AdminLoginHistory.id == login_history_id))
            login_history = result.scalar_one_or_none()
            if login_history:
                logout_time = datetime.utcnow()
                login_history.logout_time = logout_time
                login_history.logout_type = "manual"
                if login_time_str:
                    try:
                        login_time = datetime.fromisoformat(login_time_str)
                        login_history.duration = int((logout_time - login_time).total_seconds())
                    except Exception:
                        pass
                await db.commit()

    if ttl > 0:
        # 传递 tenant_id 实现多租户 Token 黑名单隔离
        await RedisCache.add_token_to_blacklist(token_hash, ttl, tenant_id=admin_tenant_id)
    await RedisCache.delete_admin_session(admin_id, tenant_id=admin_tenant_id)
    return {"message": "退出登录成功"}


@router.get("/me/stores", summary="获取绑定门店")
async def get_my_stores(
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    if current_admin.get("is_super_admin"):
        from app.modules.stores.service import StoreService

        store_service = StoreService(db)
        stores, _ = await store_service.get_list(None)
        return {
            "stores": [{"id": s.id, "name": s.name, "logo": s.logo, "themeStyle": s.theme_style} for s in stores],
            "currentStoreId": current_admin.get("current_store_id"),
            "canViewAllStores": True,
        }

    return {
        "stores": current_admin.get("stores", []),
        "currentStoreId": current_admin.get("current_store_id"),
        "canViewAllStores": current_admin.get("can_view_all_stores", False),
    }


@router.put("/me/current-store", summary="切换当前门店")
async def switch_current_store(
    data: SwitchStoreRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    from app.api.deps import check_store_access
    from app.models.store import Store

    target_store_id = data.store_id
    if not current_admin.get("is_super_admin") and not check_store_access(current_admin, target_store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此门店，请确认您已绑定该门店")

    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    admin.current_store_id = target_store_id
    await db.commit()
    result = await db.execute(select(Store).where(Store.id == target_store_id))
    store = result.scalar_one_or_none()
    return {
        "message": "门店切换成功",
        "currentStore": {"id": store.id, "name": store.name, "logo": store.logo, "themeStyle": store.theme_style} if store else None,
    }
