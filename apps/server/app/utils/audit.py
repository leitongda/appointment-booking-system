"""审计字段工具模块

提供设置 created_by 和 updated_by 审计字段的辅助函数。
"""
from typing import Any


def set_create_audit(obj: Any, operator_id: str | None = None) -> None:
    """设置创建审计字段
    
    Args:
        obj: 要设置的数据库对象（必须继承 AuditMixin）
        operator_id: 操作人ID
    """
    if hasattr(obj, 'created_by') and operator_id:
        obj.created_by = operator_id
    if hasattr(obj, 'updated_by') and operator_id:
        obj.updated_by = operator_id


def set_update_audit(obj: Any, operator_id: str | None = None) -> None:
    """设置更新审计字段
    
    Args:
        obj: 要设置的数据库对象（必须继承 AuditMixin）
        operator_id: 操作人ID
    """
    if hasattr(obj, 'updated_by') and operator_id:
        obj.updated_by = operator_id


def apply_audit_fields(
    obj: Any, 
    operator_id: str | None = None, 
    is_create: bool = True
) -> None:
    """通用的审计字段设置函数
    
    Args:
        obj: 要设置的数据库对象
        operator_id: 操作人ID
        is_create: 是否是创建操作，True 则设置 created_by，False 只设置 updated_by
    """
    if is_create:
        set_create_audit(obj, operator_id)
    else:
        set_update_audit(obj, operator_id)


def get_operator_id_from_admin(current_admin: dict | None = None) -> str | None:
    """从当前管理员信息中获取操作人ID
    
    Args:
        current_admin: 当前管理员信息字典（来自 get_current_admin 依赖）
    
    Returns:
        操作人ID 或 None
    """
    if current_admin and isinstance(current_admin, dict):
        return current_admin.get("id")
    return None


def get_operator_id_from_user(current_user: dict | None = None) -> str | None:
    """从当前用户信息中获取操作人ID
    
    Args:
        current_user: 当前用户信息字典（来自 get_current_user 依赖）
    
    Returns:
        操作人ID 或 None
    """
    if current_user and isinstance(current_user, dict):
        return current_user.get("id")
    return None

