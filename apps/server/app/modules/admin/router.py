"""Aggregate admin router."""

from fastapi import APIRouter

from app.modules.admin.router_admins import router as admins_router
from app.modules.admin.router_auth import router as auth_router
from app.modules.admin.router_monitoring import router as monitoring_router
from app.modules.admin.router_permissions import router as permissions_router
from app.modules.admin.router_roles import router as roles_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(roles_router)
router.include_router(permissions_router)
router.include_router(admins_router)
router.include_router(monitoring_router)
