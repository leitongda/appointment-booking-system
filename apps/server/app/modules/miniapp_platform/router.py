"""小程序平台管理路由 - 聚合所有子路由"""
from fastapi import APIRouter

from app.modules.miniapp_platform.router_company import router as company_router
from app.modules.miniapp_platform.router_payment_profile import router as payment_profile_router
from app.modules.miniapp_platform.router_instance import router as instance_router
from app.modules.miniapp_platform.router_template import router as template_router
from app.modules.miniapp_platform.router_build_release import router as build_release_router

router = APIRouter()

router.include_router(company_router)
router.include_router(payment_profile_router)
router.include_router(instance_router)
router.include_router(template_router)
router.include_router(build_release_router)
