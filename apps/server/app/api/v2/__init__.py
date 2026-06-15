"""API v2 路由注册入口（预留）

当前 v2 版本尚未开放任何端点。待 v1 中需要废弃的接口迁移完成后，
在此处注册 v2 路由。

迁移策略:
  1. v1 路由标记 deprecated=True + sunset_date，通过 DeprecationMiddleware 返回 Sunset header
  2. v2 实现新版本的接口（签名可能不兼容 v1）
  3. 客户端迁移完成后，v1 deprecated 路由移除
"""

from fastapi import APIRouter

# v2 主路由 — 当前为空，逐步迁移 v1 deprecated 端点
v2_router = APIRouter()


def build_v2_router() -> APIRouter:
    """构建 v2 API 路由器

    Returns:
        v2_router（当前为空）
    """
    return v2_router
