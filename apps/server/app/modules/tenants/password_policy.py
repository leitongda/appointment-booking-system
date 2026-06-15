"""租户密码策略验证器

提供 PasswordPolicyValidator 用于校验密码是否符合租户配置的密码策略，
以及 get_tenant_password_policy 用于从数据库获取租户密码策略。
"""
import json
import re

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant

DEFAULT_POLICY = {
    "min_length": 6,
    "max_length": 20,
    "require_uppercase": False,
    "require_lowercase": False,
    "require_digit": False,
    "require_special": False,
    "special_chars": "!@#$%^&*",
    "disallow_username": False,
    "disallow_phone": False,
    "max_repeated_chars": 0,
    "history_count": 0,
    "expiry_days": 0,
}


class PasswordPolicyValidator:
    """密码策略验证器

    根据租户配置的密码策略校验密码强度，返回 (是否通过, 错误信息列表)。
    """

    def __init__(self, policy: dict | None = None):
        """初始化验证器

        Args:
            policy: 密码策略字典，None 时使用默认策略（仅最小长度 6）。
        """
        self.policy = {**DEFAULT_POLICY, **(policy or {})}

    def validate(
        self,
        password: str,
        username: str | None = None,
        phone: str | None = None,
    ) -> tuple[bool, list[str]]:
        """校验密码是否符合策略

        Args:
            password: 待校验的明文密码
            username: 用户名（用于 disallow_username 检查）
            phone: 手机号（用于 disallow_phone 检查）

        Returns:
            (is_valid, list_of_error_messages)
        """
        errors: list[str] = []
        p = self.policy

        # 长度检查
        min_len = p.get("min_length", 6)
        max_len = p.get("max_length", 20)
        if len(password) < min_len:
            errors.append(f"密码长度不能少于 {min_len} 位")
        if len(password) > max_len:
            errors.append(f"密码长度不能超过 {max_len} 位")

        # 大写字母
        if p.get("require_uppercase") and not re.search(r"[A-Z]", password):
            errors.append("密码必须包含至少一个大写字母")

        # 小写字母
        if p.get("require_lowercase") and not re.search(r"[a-z]", password):
            errors.append("密码必须包含至少一个小写字母")

        # 数字
        if p.get("require_digit") and not re.search(r"\d", password):
            errors.append("密码必须包含至少一个数字")

        # 特殊字符
        if p.get("require_special"):
            special_chars = p.get("special_chars", "!@#$%^&*")
            escaped = re.escape(special_chars)
            if not re.search(f"[{escaped}]", password):
                errors.append(f"密码必须包含至少一个特殊字符 ({special_chars})")

        # 禁止包含用户名
        if p.get("disallow_username") and username:
            if username.lower() in password.lower():
                errors.append("密码不能包含用户名")

        # 禁止包含手机号
        if p.get("disallow_phone") and phone:
            # 支持完整手机号或后 4 位匹配
            phone_digits = re.sub(r"\D", "", phone)
            if phone_digits in password:
                errors.append("密码不能包含手机号")
            if len(phone_digits) >= 4 and phone_digits[-4:] in password:
                errors.append("密码不能包含手机号后四位")

        # 连续重复字符
        max_repeated = p.get("max_repeated_chars", 0)
        if max_repeated > 0:
            for i in range(len(password) - max_repeated):
                chunk = password[i : i + max_repeated + 1]
                if len(set(chunk)) == 1:
                    errors.append(f"密码不能包含连续重复超过 {max_repeated} 次的字符")
                    break

        return (len(errors) == 0, errors)


async def get_tenant_password_policy(
    db: AsyncSession,
    tenant_id: str | None = None,
) -> dict:
    """获取租户密码策略

    从数据库查询租户的 password_policy 字段并解析为字典。
    如果租户不存在或未配置策略，返回默认策略。

    Args:
        db: 数据库会话
        tenant_id: 租户ID，None 时返回默认策略

    Returns:
        密码策略字典
    """
    if not tenant_id:
        return dict(DEFAULT_POLICY)

    result = await db.execute(
        select(Tenant.password_policy).where(Tenant.id == tenant_id)
    )
    raw = result.scalar_one_or_none()
    if not raw:
        return dict(DEFAULT_POLICY)

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {**DEFAULT_POLICY, **parsed}
    except (json.JSONDecodeError, TypeError):
        pass

    return dict(DEFAULT_POLICY)
