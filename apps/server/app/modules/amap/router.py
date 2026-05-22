"""高德地图 Web 服务 API 代理

通过后端代理转发高德地图请求，避免前端暴露 API Key。
代理接口：地理编码、逆地理编码、POI 搜索。
"""
import httpx
from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import get_current_admin
from app.core.config import settings

router = APIRouter()

AMAP_BASE_URL = settings.AMAP_SERVICE_BASE_URL
AMAP_KEY = settings.AMAP_KEY

# 复用连接池，避免每次请求新建连接
_http_client: httpx.AsyncClient | None = None


def _get_http_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None or _http_client.is_closed:
        _http_client = httpx.AsyncClient(
            base_url=AMAP_BASE_URL,
            timeout=10,
            limits=httpx.Limits(max_connections=20, max_keepalive_connections=10),
        )
    return _http_client


async def close_amap_client():
    """关闭高德地图 HTTP 连接池（应用退出时调用）"""
    global _http_client
    if _http_client is not None and not _http_client.is_closed:
        await _http_client.aclose()
        _http_client = None


def _require_amap_key() -> str:
    if not AMAP_KEY:
        raise HTTPException(
            status_code=503,
            detail="高德地图服务未配置，请联系管理员配置 AMAP_KEY",
        )
    return AMAP_KEY


# ========== Endpoints ==========

@router.get("/geocode", summary="地理编码（地址→经纬度）")
async def geocode(
    address: str = Query(..., description="结构化地址", min_length=1),
    city: str = Query("", description="限定城市（可选）"),
    _admin=Depends(get_current_admin),
):
    key = _require_amap_key()
    params = {"key": key, "address": address, "output": "JSON"}
    if city:
        params["city"] = city

    client = _get_http_client()
    resp = await client.get("/v3/geocode/geo", params=params)
    data = resp.json()

    if data.get("status") != "1":
        raise HTTPException(status_code=502, detail=f"高德 API 错误: {data.get('info', '未知错误')}")

    return {"code": 0, "message": "success", "data": {"geocodes": data.get("geocodes", [])}}


@router.get("/regeo", summary="逆地理编码（经纬度→地址）")
async def reverse_geocode(
    location: str = Query(..., description="经纬度，格式: lng,lat", min_length=3),
    _admin=Depends(get_current_admin),
):
    key = _require_amap_key()
    params = {"key": key, "location": location, "output": "JSON", "extensions": "base"}

    client = _get_http_client()
    resp = await client.get("/v3/geocode/regeo", params=params)
    data = resp.json()

    if data.get("status") != "1":
        raise HTTPException(status_code=502, detail=f"高德 API 错误: {data.get('info', '未知错误')}")

    regeo = data.get("regeocode", {})
    return {"code": 0, "message": "success", "data": regeo}


@router.get("/poi-search", summary="POI 搜索（关键词→地点列表）")
async def poi_search(
    keywords: str = Query(..., description="搜索关键词", min_length=1),
    city: str = Query("", description="限定城市（可选）"),
    types: str = Query("", description="POI 类型编码（可选）"),
    page_size: int = Query(10, ge=1, le=25, description="每页条数"),
    page_num: int = Query(1, ge=1, description="页码"),
    _admin=Depends(get_current_admin),
):
    key = _require_amap_key()
    params = {
        "key": key,
        "keywords": keywords,
        "output": "JSON",
        "offset": page_size,
        "page": page_num,
    }
    if city:
        params["city"] = city
    if types:
        params["types"] = types

    client = _get_http_client()
    resp = await client.get("/v3/place/text", params=params)
    data = resp.json()

    if data.get("status") != "1":
        raise HTTPException(status_code=502, detail=f"高德 API 错误: {data.get('info', '未知错误')}")

    return {
        "code": 0,
        "message": "success",
        "data": {
            "pois": data.get("pois", []),
            "count": int(data.get("count", 0)),
        },
    }
