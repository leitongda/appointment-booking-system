"""数据统计 API

子路由拆分:
- router_overview:        GET /overview, GET /store-dashboard
- router_appointment_stats: GET /appointments/trend, /appointments/status, /appointments/summary
- router_rankings:        GET /departments/ranking, /doctors/ranking, /stores/ranking
- router_distribution:    GET /time-slots/distribution, /weekday/distribution
- router_revenue:         GET /revenue/trend
- router_user_analytics:  GET /retention, /revisit-rate
"""
from fastapi import APIRouter

from app.modules.statistics.helpers import (
    _build_store_filter_condition,  # noqa: F401 — re-export for backward compatibility
)
from app.modules.statistics.router_appointment_stats import router as appointment_stats_router
from app.modules.statistics.router_distribution import router as distribution_router
from app.modules.statistics.router_overview import router as overview_router
from app.modules.statistics.router_rankings import router as rankings_router
from app.modules.statistics.router_revenue import router as revenue_router
from app.modules.statistics.router_user_analytics import router as user_analytics_router

router = APIRouter()

router.include_router(overview_router)
router.include_router(appointment_stats_router)
router.include_router(rankings_router)
router.include_router(distribution_router)
router.include_router(revenue_router)
router.include_router(user_analytics_router)
