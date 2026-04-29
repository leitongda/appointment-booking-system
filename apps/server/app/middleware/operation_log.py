"""
操作日志中间件
拦截写操作（POST/PUT/DELETE）并记录到数据库
"""
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from typing import Callable, Optional
import time
import logging
import json

from app.core.security import decode_token
from app.core.config import settings
from app.utils.ip import get_client_ip as _get_client_ip_util
from app.middleware.tenant_context import get_current_tenant_id

logger = logging.getLogger(__name__)


# 模块路径映射：根据 API 路径识别模块名称
MODULE_MAPPING = {
    "/admin/roles": "角色管理",
    "/admin/admins": "管理员管理",
    "/admin/permissions": "权限管理",
    "/doctors": "医生管理",
    "/departments": "科室管理",
    "/stores": "门店管理",
    "/appointments": "预约管理",
    "/schedules": "排班管理",
    "/schedule-templates": "排班模板",
    "/custom-schedules": "自定义排班",
    "/rest-days": "休息日设置",
    "/schedule-suspensions": "停诊管理",
    "/leave-requests": "停诊申请",
    "/patients": "患者管理",
    "/users": "用户管理",
    "/blacklists": "黑名单管理",
    "/content/news": "新闻管理",
    "/content/notices": "公告管理",
    "/content/banners": "轮播图管理",
    "/messages": "消息管理",
    "/feedbacks": "用户反馈",
    "/settings": "系统设置",
    "/consultation-fees": "诊费管理",
    "/doctor-booking-settings": "预约设置",
    "/email-templates": "邮件模板",
}

# 操作映射：根据 HTTP 方法识别操作类型
ACTION_MAPPING = {
    "POST": "新增",
    "PUT": "编辑",
    "PATCH": "更新",
    "DELETE": "删除",
}

# 排除的路径后缀（相对路径，不记录日志）
# 使用相对路径，在检查时会动态拼接 API 前缀
EXCLUDE_PATH_SUFFIXES = [
    "/admin/login",
    "/admin/phone-login",
    "/admin/sms/send",
    "/admin/sms/login",
    "/admin/wechat",
    "/admin/public-key",
    "/admin/logs",  # 避免查看日志时产生日志
    "/auth",
    "/upload",
]

# 非 API 的排除路径
EXCLUDE_NON_API_PATHS = [
    "/health",
    "/docs",
    "/redoc",
    "/openapi.json",
]

# 敏感字段（需要脱敏）
SENSITIVE_FIELDS = ["password", "password_hash", "token", "secret", "access_token", "refresh_token"]


def _get_module_name(path: str) -> str:
    """根据请求路径获取模块名称"""
    # 移除 API 前缀（使用动态配置）
    clean_path = path.replace(settings.API_V1_STR, "")
    
    # 匹配模块
    for prefix, module_name in MODULE_MAPPING.items():
        if clean_path.startswith(prefix):
            return module_name
    
    return "其他"


def _get_action_name(method: str, path: str) -> str:
    """根据请求方法和路径获取操作名称"""
    base_action = ACTION_MAPPING.get(method, method)
    
    # 特殊路径的操作名称（使用动态配置）
    clean_path = path.replace(settings.API_V1_STR, "")
    
    # 处理一些特殊操作
    if "/status" in clean_path and method == "PUT":
        return "更新状态"
    if "/reset-password" in clean_path:
        return "重置密码"
    if "/permissions" in clean_path and method == "PUT":
        return "分配权限"
    if "/cancel" in clean_path:
        return "取消"
    if "/confirm" in clean_path:
        return "确认"
    if "/check-in" in clean_path:
        return "签到"
    if "/approve" in clean_path:
        return "审批通过"
    if "/reject" in clean_path:
        return "审批拒绝"
    if "/publish" in clean_path:
        return "发布"
    if "/unpublish" in clean_path:
        return "取消发布"
    
    return base_action


def _sanitize_params(params):
    """脱敏请求参数"""
    if not params:
        return params
    
    # 如果参数是列表，直接返回（或递归处理列表中的字典）
    if isinstance(params, list):
        return [_sanitize_params(item) if isinstance(item, dict) else item for item in params]
    
    # 如果不是字典，直接返回
    if not isinstance(params, dict):
        return params
    
    sanitized = {}
    for key, value in params.items():
        if any(sensitive in key.lower() for sensitive in SENSITIVE_FIELDS):
            sanitized[key] = "***"
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_params(value)
        elif isinstance(value, list):
            sanitized[key] = [_sanitize_params(item) if isinstance(item, dict) else item for item in value]
        else:
            sanitized[key] = value
    
    return sanitized


def _should_exclude_path(path: str) -> bool:
    """检查路径是否应该被排除"""
    # 检查非 API 路径
    if path in EXCLUDE_NON_API_PATHS:
        return True
    
    # 检查 API 路径（使用动态前缀）
    api_prefix = settings.API_V1_STR
    for suffix in EXCLUDE_PATH_SUFFIXES:
        full_path = f"{api_prefix}{suffix}"
        if path == full_path or path.startswith(f"{full_path}/"):
            return True
    
    return False


def _get_client_ip(request: Request) -> str:
    """获取客户端真实 IP（使用统一的工具函数）"""
    return _get_client_ip_util(request)


def _extract_admin_from_token(request: Request) -> tuple:
    """从请求中提取管理员信息"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        return None, None
    
    token = auth_header[7:]  # 移除 "Bearer " 前缀
    
    try:
        payload = decode_token(token)
        if payload:
            return payload.get("sub"), payload.get("name")
    except Exception as e:
        logger.debug(f"解析 Token 失败: {e}")
    
    return None, None


class OperationLogMiddleware(BaseHTTPMiddleware):
    """操作日志中间件"""
    
    def __init__(self, app, exclude_path_suffixes: list = None):
        super().__init__(app)
        self.exclude_path_suffixes = exclude_path_suffixes or EXCLUDE_PATH_SUFFIXES
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # 只记录写操作
        if request.method not in ["POST", "PUT", "PATCH", "DELETE"]:
            return await call_next(request)
        
        # 排除特定路径
        if _should_exclude_path(request.url.path):
            return await call_next(request)
        
        # 记录开始时间
        start_time = time.time()
        
        # 尝试读取请求体
        request_body = None
        try:
            body_bytes = await request.body()
            if body_bytes:
                try:
                    request_body = json.loads(body_bytes.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError):
                    request_body = {"_raw": "binary or invalid json"}
        except Exception:
            pass
        
        # 获取管理员信息
        admin_id, admin_name = _extract_admin_from_token(request)
        
        # 处理请求
        response = await call_next(request)
        
        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 确定结果
        result = "成功" if response.status_code < 400 else "失败"
        
        # 构建日志数据
        log_data = {
            "admin_id": admin_id,
            "admin_name": admin_name,
            "tenant_id": get_current_tenant_id(),
            "module": _get_module_name(request.url.path),
            "action": _get_action_name(request.method, request.url.path),
            "method": request.method,
            "path": request.url.path,
            "params": json.dumps(_sanitize_params(request_body), ensure_ascii=False) if request_body else None,
            "result": result,
            "ip": _get_client_ip(request),
            "user_agent": request.headers.get("User-Agent", "")[:500],
            "duration": duration_ms,
        }
        
        # 异步保存日志（通过 Celery）
        try:
            from app.tasks.operation_log_task import save_operation_log
            save_operation_log.delay(log_data)
        except Exception as e:
            logger.error(f"发送操作日志任务失败: {e}")
        
        return response

