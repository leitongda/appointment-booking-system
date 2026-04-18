"""结构化错误码

供前端按 code 精确分支，避免依赖 detail 字符串匹配。

仅用于"特殊业务错误"的 code 字段；通用错误仍走 HTTP 状态码。
"""


class TenantErrorCode:
    """租户/订阅相关错误码"""

    TENANT_DISABLED = "TENANT_DISABLED"                  # 租户被平台禁用
    TENANT_OVERDUE = "TENANT_OVERDUE"                    # 订阅欠费/已到期
    TENANT_TRIAL_EXPIRED = "TENANT_TRIAL_EXPIRED"        # 试用期到期
    TENANT_SUSPENDED_WRITE = "TENANT_SUSPENDED_WRITE"    # 写操作被拒（患者侧 / 通用写守卫）
