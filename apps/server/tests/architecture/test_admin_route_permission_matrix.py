"""管理端路由 ↔ 权限守卫覆盖矩阵（architecture fitness）

把「/api/v1/admin/** 每条路由要么带权限守卫、要么显式登记豁免原因」固化为测试，
防止后续新增管理端点悄悄漏掉权限检查（2026-10-23 盘点发现 GET /admins、
GET /roles 等读端点无守卫后建立的台账）。

规则：
1. 写端点（POST/PUT/DELETE/PATCH）必须有权限守卫：
   ``require_permission`` / ``require_all_permissions`` /
   ``require_account_permission`` / ``require_account_all_permissions`` /
   ``require_platform_admin`` 之一，或在豁免台账中登记原因。
2. 读端点（GET）同样要么有守卫、要么在台账中登记原因。
3. 台账里的每一条必须对应真实存在的路由——路由删除后台账不清理同样失败，
   避免台账腐化成“什么都能豁免”的白名单。

已知最小权限缺口（KNOWN_GAPS）：管理员/角色的列表与详情端点只受
``get_current_admin`` + 租户锚点约束，没有细粒度权限码。原因是权限目录
（scripts/init_permissions.py）没有 ``system:user:list`` / ``system:role:list``
码，直接加守卫会把所有非 ``*`` 角色锁死且无法授权。收口需要产品拍板：
新增权限码 + 前端角色页对齐，属于独立工作项，不在本测试里隐式决定。
"""
import pytest
from fastapi.routing import APIRoute

from app.main import app

pytestmark = pytest.mark.architecture

ADMIN_PREFIX = "/api/v1/admin"

# 识别为「权限守卫」的依赖工厂（qualname 前缀匹配，含 <locals> 内层函数）
GUARD_PREFIXES = (
    "require_permission",
    "require_all_permissions",
    "require_account_permission",
    "require_account_all_permissions",
    "require_platform_admin",
)

# ---------------------------------------------------------------------------
# 豁免台账：无守卫路由必须在此登记原因
# ---------------------------------------------------------------------------

# 预认证 / 匿名 / 本人自助端点——按设计不挂权限码
SELF_SERVICE_OR_PRE_AUTH = {
    "POST /api/v1/admin/login": "密码登录（预认证）",
    "POST /api/v1/admin/phone-login": "手机号登录（预认证）",
    "POST /api/v1/admin/sms/login": "短信登录（预认证）",
    "POST /api/v1/admin/sms/send": "发送短信验证码（预认证）",
    "POST /api/v1/admin/email/login": "邮箱登录（预认证）",
    "POST /api/v1/admin/email/send-code": "发送邮箱验证码（预认证）",
    "GET /api/v1/admin/public-key": "登录页公钥（预认证）",
    "GET /api/v1/admin/qrcode": "登录二维码（预认证）",
    "GET /api/v1/admin/wechat/qrcode": "微信扫码二维码（预认证）",
    "GET /api/v1/admin/wechat/check": "微信扫码轮询（预认证）",
    "POST /api/v1/admin/wechat/confirm": "微信扫码确认（预认证）",
    "POST /api/v1/admin/refresh": "刷新 token（预认证）",
    "POST /api/v1/admin/bind-phone": "第三方登录绑定手机号（预认证）",
    "POST /api/v1/admin/logout": "登出（本人操作）",
    "POST /api/v1/admin/bind": "绑定第三方账号（本人操作）",
    "GET /api/v1/admin/bindings": "查本人第三方绑定（本人操作）",
    "GET /api/v1/admin/me": "本人信息（本人操作）",
    "PUT /api/v1/admin/me": "改本人信息（本人操作）",
    "PUT /api/v1/admin/me/change-password": "改本人密码（本人操作）",
    "PUT /api/v1/admin/me/current-store": "切换本人门店（本人操作）",
    "PUT /api/v1/admin/me/current-tenant": "切换本人租户（本人操作）",
    "GET /api/v1/admin/me/stores": "查本人门店（本人操作）",
    "POST /api/v1/admin/me/email/bind": "绑本人邮箱（本人操作）",
    "POST /api/v1/admin/me/email/change": "换本人邮箱（本人操作）",
    "POST /api/v1/admin/me/email/send-code": "发本人邮箱验证码（本人操作）",
    "POST /api/v1/admin/me/email/unbind": "解绑本人邮箱（本人操作）",
}

# 已知最小权限缺口：无（2026-10-24 收口：GET /admins*、/roles* 五条读端点已挂
# require_permission("system:*:list", "system:*")，OR 父码兼容存量授权；
# 权限目录 scripts/init_permissions.py 已补 system:user:list / system:role:list）
KNOWN_GAPS = {}

EXEMPT = {**SELF_SERVICE_OR_PRE_AUTH, **KNOWN_GAPS}


# ---------------------------------------------------------------------------
# 依赖树遍历：收集一条路由全部依赖的可调用限定名
# ---------------------------------------------------------------------------

def _collect_dependency_qualnames(route: APIRoute) -> set[str]:
    qualnames: set[str] = set()
    stack = [route.dependant]
    stack.extend(route.dependencies)
    while stack:
        dependant = stack.pop()
        qualnames.add(getattr(dependant.call, "__qualname__", repr(dependant.call)))
        stack.extend(dependant.dependencies)
    return qualnames


def _has_permission_guard(route: APIRoute) -> bool:
    return any(
        qualname.startswith(GUARD_PREFIXES)
        for qualname in _collect_dependency_qualnames(route)
    )


def _admin_routes() -> list[APIRoute]:
    return [
        route
        for route in app.routes
        if isinstance(route, APIRoute) and route.path.startswith(ADMIN_PREFIX)
    ]


def _route_key(route: APIRoute) -> str:
    method = next(iter(route.methods - {"HEAD"})) if route.methods else "GET"
    return f"{method} {route.path}"


def test_every_admin_route_is_guarded_or_registered():
    """所有 /api/v1/admin 路由：有守卫，或在豁免台账中带原因登记。"""
    violations = []
    for route in _admin_routes():
        key = _route_key(route)
        if _has_permission_guard(route):
            continue
        if key in EXEMPT:
            continue
        violations.append(
            f"{key} 无权限守卫且未在豁免台账登记——"
            f"请加 Depends(require_permission(...)) 或在 EXEMPT 台账登记原因"
        )
    assert not violations, "\n".join(violations)


def test_exempt_ledger_entries_all_exist():
    """台账反向校验：登记的每条路由必须真实存在，防止台账腐化。"""
    existing = {_route_key(route) for route in _admin_routes()}
    stale = [key for key in EXEMPT if key not in existing]
    assert not stale, (
        "豁免台账中的路由已不存在，请清理：\n" + "\n".join(sorted(stale))
    )


def test_write_endpoints_cannot_hide_in_self_service_ledger():
    """自助豁免只接受本人数据操作路径——管理类写端点不得借「预认证/本人操作」名义绕过守卫。"""
    allowed_prefixes = (
        f"{ADMIN_PREFIX}/login",
        f"{ADMIN_PREFIX}/phone-login",
        f"{ADMIN_PREFIX}/sms",
        f"{ADMIN_PREFIX}/email",
        f"{ADMIN_PREFIX}/public-key",
        f"{ADMIN_PREFIX}/qrcode",
        f"{ADMIN_PREFIX}/wechat",
        f"{ADMIN_PREFIX}/refresh",
        f"{ADMIN_PREFIX}/logout",
        f"{ADMIN_PREFIX}/bind",
        f"{ADMIN_PREFIX}/me",
    )
    stray = [
        key
        for key in SELF_SERVICE_OR_PRE_AUTH
        if not key.split(" ", 1)[1].startswith(allowed_prefixes)
    ]
    assert not stray, f"自助豁免出现预期外路径：{stray}"
