"""
前端性能数据上报 API
接收 Core Web Vitals、路由切换耗时等性能指标
"""
import logging
import time

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, ConfigDict, Field

from app.common.auth_unified import AccountInfo, get_optional_account
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.ip import get_client_ip

logger = logging.getLogger(__name__)

router = APIRouter()

# ========== 速率限制（独立桶，阈值更严） ==========

_perf_rate_limit: dict[str, list[float]] = {}
_RATE_LIMIT_WINDOW = 60
_RATE_LIMIT_MAX = 60  # 性能上报频率较低，限制更严


def _check_rate_limit(client_ip: str) -> None:
    now = time.time()
    window_start = now - _RATE_LIMIT_WINDOW

    if client_ip not in _perf_rate_limit:
        _perf_rate_limit[client_ip] = []

    _perf_rate_limit[client_ip] = [t for t in _perf_rate_limit[client_ip] if t > window_start]

    if len(_perf_rate_limit[client_ip]) >= _RATE_LIMIT_MAX:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="请求过于频繁，请稍后再试",
        )

    _perf_rate_limit[client_ip].append(now)

    if len(_perf_rate_limit) > 5000:
        cutoff = now - _RATE_LIMIT_WINDOW * 2
        stale = [ip for ip, ts in _perf_rate_limit.items() if not ts or ts[-1] < cutoff]
        for ip in stale:
            _perf_rate_limit.pop(ip, None)


# ========== Schema ==========

def _to_camel(s: str) -> str:
    parts = s.split("_")
    return parts[0] + "".join(x.title() for x in parts[1:])


class PerformanceMetricItem(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    type: str = Field(..., description="指标类型: FCP/LCP/CLS/FID/INP/TTFB/ROUTE_CHANGE")
    value: float = Field(..., description="指标值")
    rating: str = Field(..., description="评级: good/needs-improvement/poor")
    timestamp: int = Field(..., description="采集时间戳")
    metadata: dict | None = Field(None, description="额外信息")


class RouteMetricItem(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    path: str = Field(..., description="路由路径")
    duration: float = Field(..., description="切换耗时(ms)")
    timestamp: int = Field(..., description="采集时间戳")


class PerformanceReportRequest(BaseModel):
    model_config = ConfigDict(alias_generator=_to_camel, populate_by_name=True)

    page_url: str = Field("", description="页面 URL")
    user_agent: str = Field("", description="User-Agent")
    screen: dict | None = Field(None, description="屏幕信息 {width, height, dpr}")
    timestamp: int = Field(..., description="上报时间戳")
    session_id: str | None = Field(None, max_length=64, description="会话ID")
    metrics: list[PerformanceMetricItem] = Field(default_factory=list, description="性能指标")
    route_metrics: list[RouteMetricItem] = Field(default_factory=list, description="路由指标")


# ========== 端点 ==========

@router.post("/report", summary="上报性能数据")
async def report_performance(
    data: PerformanceReportRequest,
    request: Request,
    account: AccountInfo | None = Depends(get_optional_account),
):
    """
    接收前端性能指标（Core Web Vitals + 路由耗时）
    无需认证，允许匿名上报
    """
    client_ip = get_client_ip(request)
    _check_rate_limit(client_ip)

    tenant_id = get_current_tenant_id()
    user_id = None
    if account:
        user_id = getattr(account, "id", None)

    # 结构化日志输出（便于后续接入 ELK/Grafana）
    logger.info(
        "performance_report",
        extra={
            "tenant_id": tenant_id,
            "user_id": user_id,
            "session_id": data.session_id,
            "page_url": data.page_url,
            "metric_count": len(data.metrics),
            "route_metric_count": len(data.route_metrics),
            "metrics": [
                {"type": m.type, "value": m.value, "rating": m.rating}
                for m in data.metrics
            ],
            "route_metrics": [
                {"path": r.path, "duration": r.duration}
                for r in data.route_metrics
            ],
            "client_ip": client_ip,
        },
    )

    return {"success": True, "received": len(data.metrics) + len(data.route_metrics)}
