"""数据导入导出 API - 聚合路由"""
from fastapi import APIRouter

from .router_export import router as export_router
from .router_import import router as import_router
from .router_template import router as template_router

router = APIRouter()

# 聚合子模块路由，添加正确的前缀
router.include_router(export_router, prefix="/export", tags=["导出"])
router.include_router(import_router, prefix="/import", tags=["导入"])
router.include_router(template_router, prefix="/template", tags=["导入模板"])
