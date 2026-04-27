"""医生端专属 API - 聚合路由"""
from fastapi import APIRouter

from .router_profile import router as profile_router
from .router_schedules import router as schedules_router
from .router_appointments import router as appointments_router
from .router_queue import router as queue_router
from .router_patient import router as patient_router
from .router_rules import router as rules_router

router = APIRouter()

# 聚合子模块路由，router.include_router(profile_router, tags=["医生信息"])
router.include_router(schedules_router, prefix="/schedules", tags=["排班管理"])
router.include_router(appointments_router, prefix="/appointments", tags=["预约管理"])
router.include_router(queue_router, prefix="/queue", tags=["叫号管理"])
router.include_router(patient_router, prefix="/patients", tags=["患者管理"])
router.include_router(rules_router, tags=["预约规则"])
