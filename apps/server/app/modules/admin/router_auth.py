"""Admin authentication and profile router - 聚合路由"""
from fastapi import APIRouter

from .router_auth_login import router as login_router
from .router_auth_token import router as token_router
from .router_auth_password import router as password_router

router = APIRouter()

# 聚合子模块路由
router.include_router(login_router, tags=["登录"])
router.include_router(token_router, tags=["Token管理"])
router.include_router(password_router, tags=["密码管理"])
