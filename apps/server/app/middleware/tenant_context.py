"""
租户上下文中间件

从请求中提取租户信息并注入到请求上下文中。

支持的租户识别方式（按优先级）：
1. X-Tenant-ID Header（用于 API 调用）
2. X-Tenant-Code Header（用于 API 调用）
3. 子域名识别（如 tenant1.example.com）
4. 路径前缀识别（如 /t/tenant1/...）

对于平台管理员（无租户），tenant_id 为 None。

多租户隔离：
- 公开预约接口必须有租户上下文
- 租户间数据完全隔离
"""
import logging
import re
from collections.abc import Callable
from contextvars import ContextVar

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("tenant")

# 使用 ContextVar 存储当前请求的租户信息（支持异步任务）
_current_tenant_id: ContextVar[str | None] = ContextVar("current_tenant_id", default=None)
_current_tenant_code: ContextVar[str | None] = ContextVar("current_tenant_code", default=None)

# 公开接口租户校验路径前缀
PUBLIC_TENANT_REQUIRED_PATHS = [
    "/api/v1/public/appointments",
    "/api/v1/public/doctors",
    "/api/v1/public/schedules",
    "/api/v1/public/departments",
    "/api/v1/public/stores",
    "/api/v1/public/patients",
    "/api/v1/doctors/recommended",
    "/api/v1/doctors/by-department",
    "/api/v1/doctors/public",
    "/api/v1/stores/by-code",
]


def get_current_tenant_id() -> str | None:
    """获取当前请求上下文中的租户ID"""
    return _current_tenant_id.get()


def get_current_tenant_code() -> str | None:
    """获取当前请求上下文中的租户编码"""
    return _current_tenant_code.get()


def set_tenant_context(tenant_id: str | None, tenant_code: str | None = None) -> None:
    """设置当前请求上下文中的租户信息（主要用于测试和异步任务）"""
    _current_tenant_id.set(tenant_id)
    _current_tenant_code.set(tenant_code)


def clear_tenant_context() -> None:
    """清除当前请求上下文中的租户信息"""
    _current_tenant_id.set(None)
    _current_tenant_code.set(None)


def validate_public_tenant_context(path: str) -> None:
    """验证公开接口的租户上下文

    对于必须识别租户的公开接口，如果没有租户上下文则抛出异常。

    Args:
        path: 请求路径

    Raises:
        HTTPException: 如果缺少租户上下文
    """
    tenant_id = get_current_tenant_id()
    tenant_code = get_current_tenant_code()

    if not tenant_id and not tenant_code:
        for prefix in PUBLIC_TENANT_REQUIRED_PATHS:
            if path.startswith(prefix):
                raise HTTPException(
                    status_code=400,
                    detail="缺少租户上下文，请通过 X-Tenant-ID 或 X-Tenant-Code 指定租户"
                )


class TenantContextMiddleware(BaseHTTPMiddleware):
    """租户上下文中间件

    从请求中提取租户信息并设置到上下文中。
    """

    # 路径前缀模式：/t/{tenant_code}/...
    TENANT_PATH_PATTERN = re.compile(r"^/t/([^/]+)(?:/|$)")

    def __init__(
        self,
        app,
        exclude_paths: list = None,
        tenant_header: str = "X-Tenant-ID",
        tenant_code_header: str = "X-Tenant-Code",
        enable_subdomain: bool = True,
        enable_path_prefix: bool = True,
    ):
        super().__init__(app)
        self.exclude_paths = exclude_paths or ["/health", "/docs", "/redoc", "/openapi.json", "/api/v1/platform"]
        self.tenant_header = tenant_header
        self.tenant_code_header = tenant_code_header
        self.enable_subdomain = enable_subdomain
        self.enable_path_prefix = enable_path_prefix

    async def dispatch(self, request: Request, call_next: Callable):
        # 清除之前的上下文
        clear_tenant_context()

        # 跳过不需要租户识别的路径
        if self._should_exclude(request.url.path):
            # 清除租户上下文（平台级请求）
            return await call_next(request)

        # 提取租户信息
        tenant_id, tenant_code = await self._extract_tenant(request)

        # 设置到请求状态和上下文变量
        request.state.tenant_id = tenant_id
        request.state.tenant_code = tenant_code
        set_tenant_context(tenant_id, tenant_code)

        # 记录日志
        if tenant_id or tenant_code:
            logger.debug(f"Tenant context: id={tenant_id}, code={tenant_code}")

        # 验证公开接口的租户上下文
        try:
            validate_public_tenant_context(request.url.path)
        except HTTPException as e:
            # 返回错误响应
            from starlette.responses import JSONResponse
            return JSONResponse(
                status_code=e.status_code,
                content={"detail": e.detail}
            )

        # 继续处理请求
        response = await call_next(request)

        # 添加租户信息到响应头（便于调试）
        if tenant_id:
            response.headers["X-Tenant-ID"] = tenant_id
        if tenant_code:
            response.headers["X-Tenant-Code"] = tenant_code

        return response

    def _should_exclude(self, path: str) -> bool:
        """检查路径是否应该跳过租户识别"""
        for exclude_path in self.exclude_paths:
            if path.startswith(exclude_path):
                return True
        return False

    async def _extract_tenant(self, request: Request) -> tuple[str | None, str | None]:
        """从请求中提取租户信息

        返回: (tenant_id, tenant_code)
        """
        tenant_id = None
        tenant_code = None

        # 1. 优先从 Header 获取 Tenant ID
        tenant_id = request.headers.get(self.tenant_header)
        if tenant_id:
            return tenant_id, None

        # 2. 从 Header 获取 Tenant Code
        tenant_code = request.headers.get(self.tenant_code_header)
        if tenant_code:
            # 需要后续通过数据库查询获取 tenant_id
            return None, tenant_code

        # 3. 从子域名识别
        if self.enable_subdomain:
            tenant_code = self._extract_from_subdomain(request)
            if tenant_code:
                return None, tenant_code

        # 4. 从路径前缀识别
        if self.enable_path_prefix:
            tenant_code = self._extract_from_path(request)
            if tenant_code:
                return None, tenant_code

        return None, None

    def _extract_from_subdomain(self, request: Request) -> str | None:
        """从子域名提取租户编码

        例如: tenant1.example.com -> tenant1
        """
        host = request.headers.get("host", "")
        if not host:
            return None

        # 移除端口号
        host = host.split(":")[0]

        # 分割域名
        parts = host.split(".")
        if len(parts) >= 3:
            # 子域名模式：xxx.example.com
            potential_code = parts[0]
            # 排除常见的非租户子域名
            if potential_code not in ("www", "api", "admin", "app", "m", "mobile"):
                return potential_code

        return None

    def _extract_from_path(self, request: Request) -> str | None:
        """从路径前缀提取租户编码

        例如: /t/tenant1/api/v1/... -> tenant1
        """
        path = request.url.path
        match = self.TENANT_PATH_PATTERN.match(path)
        if match:
            return match.group(1)
        return None


class TenantContext:
    """租户上下文管理器（用于异步任务和后台脚本）"""

    def __init__(self, tenant_id: str | None = None, tenant_code: str | None = None):
        self.tenant_id = tenant_id
        self.tenant_code = tenant_code
        self._previous_tenant_id = None
        self._previous_tenant_code = None

    def __enter__(self):
        # 保存之前的值
        self._previous_tenant_id = _current_tenant_id.get()
        self._previous_tenant_code = _current_tenant_code.get()
        # 设置新值
        set_tenant_context(self.tenant_id, self.tenant_code)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # 恢复之前的值
        set_tenant_context(self._previous_tenant_id, self._previous_tenant_code)
        return False

    async def __aenter__(self):
        return self.__enter__()

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return self.__exit__(exc_type, exc_val, exc_tb)
