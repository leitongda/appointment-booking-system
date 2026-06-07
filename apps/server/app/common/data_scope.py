"""数据权限范围过滤器

根据角色关联的 DataScope 配置，自动为 SQLAlchemy 查询添加数据范围过滤条件。
支持四种范围类型：all / tenant / store / custom

典型用法：
    from app.common.data_scope import apply_data_scope
    query = apply_data_scope(query, Doctor, current_admin)
"""
import json
from typing import Any, Dict, List, Optional, Type, Union

from sqlalchemy import Select, and_, or_
from sqlalchemy.orm import DeclarativeBase


class DataScopeFilter:
    """数据权限范围过滤器

    从 admin_info (dict) 中读取角色关联的 DataScope 配置，
    根据 scope_type 自动构建 SQLAlchemy where 条件。
    """

    @staticmethod
    def _get_data_scope(admin_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """从 admin_info 中提取 data_scope 配置

        Args:
            admin_info: 管理员信息字典（来自 get_current_admin 返回）

        Returns:
            data_scope 字典或 None
        """
        # 优先从嵌套的 role 对象中读取
        role = admin_info.get("role")
        if role and isinstance(role, dict):
            ds = role.get("data_scope")
            if ds:
                return ds

        # 兼容平铺结构
        return admin_info.get("data_scope")

    @staticmethod
    def _parse_store_ids(store_ids_raw: Any) -> List[str]:
        """解析 store_ids 字段（可能为 JSON 字符串或列表）"""
        if not store_ids_raw:
            return []
        if isinstance(store_ids_raw, list):
            return store_ids_raw
        if isinstance(store_ids_raw, str):
            try:
                parsed = json.loads(store_ids_raw)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
        return []

    @classmethod
    def build_filter(
        cls,
        admin_info: Dict[str, Any],
        model: Type[DeclarativeBase],
        store_id_column: str = "store_id",
        tenant_id_column: str = "tenant_id",
    ) -> Optional[Any]:
        """构建数据范围过滤条件

        Args:
            admin_info: 管理员信息字典
            model: SQLAlchemy 模型类
            store_id_column: 模型中门店 ID 字段名
            tenant_id_column: 模型中租户 ID 字段名

        Returns:
            SQLAlchemy where 条件，或 None 表示不限制
        """
        # 超级管理员不限制
        if admin_info.get("is_super_admin"):
            return None

        data_scope = cls._get_data_scope(admin_info)
        if not data_scope:
            return cls._fallback_filter(admin_info, model, store_id_column, tenant_id_column)

        scope_type = data_scope.get("scope_type")
        if not scope_type:
            return cls._fallback_filter(admin_info, model, store_id_column, tenant_id_column)

        if scope_type == "all":
            return None

        if scope_type == "tenant":
            tenant_id = admin_info.get("tenant_id")
            if tenant_id and hasattr(model, tenant_id_column):
                return getattr(model, tenant_id_column) == tenant_id
            return None

        if scope_type == "store":
            # 优先使用当前选中门店
            current_store_id = admin_info.get("current_store_id") or admin_info.get("store_id")
            if current_store_id and hasattr(model, store_id_column):
                return getattr(model, store_id_column) == current_store_id
            # fallback 到 store_ids
            store_ids = admin_info.get("store_ids", [])
            if store_ids and hasattr(model, store_id_column):
                return getattr(model, store_id_column).in_(store_ids)
            return None

        if scope_type == "custom":
            store_ids_raw = data_scope.get("store_ids")
            store_ids = cls._parse_store_ids(store_ids_raw)
            if store_ids and hasattr(model, store_id_column):
                return getattr(model, store_id_column).in_(store_ids)
            # custom 但无门店列表 → 不返回数据
            return getattr(model, store_id_column).in_([]) if hasattr(model, store_id_column) else None

        return cls._fallback_filter(admin_info, model, store_id_column, tenant_id_column)

    @classmethod
    def _fallback_filter(
        cls,
        admin_info: Dict[str, Any],
        model: Type[DeclarativeBase],
        store_id_column: str = "store_id",
        tenant_id_column: str = "tenant_id",
    ) -> Optional[Any]:
        """无 DataScope 时的 fallback 逻辑（兼容旧系统）

        逻辑与原 get_store_filter 一致：
        - 超管：不过滤
        - 有 store_ids → 按当前门店过滤
        - 有 tenant_id → 按租户过滤
        """
        store_ids = admin_info.get("store_ids", [])
        current_store_id = admin_info.get("current_store_id") or admin_info.get("store_id")
        tenant_id = admin_info.get("tenant_id")

        if current_store_id and hasattr(model, store_id_column):
            return getattr(model, store_id_column) == current_store_id

        if store_ids and hasattr(model, store_id_column):
            return getattr(model, store_id_column).in_(store_ids)

        if tenant_id and hasattr(model, tenant_id_column):
            return getattr(model, tenant_id_column) == tenant_id

        return None


def apply_data_scope(
    query: Select,
    model: Type[DeclarativeBase],
    admin_info: Dict[str, Any],
    store_id_column: str = "store_id",
    tenant_id_column: str = "tenant_id",
) -> Select:
    """为 SQLAlchemy 查询应用数据权限范围过滤

    Args:
        query: SQLAlchemy Select 对象
        model: 模型类（用于获取列引用）
        admin_info: 管理员信息字典
        store_id_column: 门店 ID 字段名
        tenant_id_column: 租户 ID 字段名

    Returns:
        添加了过滤条件的 Select 对象
    """
    condition = DataScopeFilter.build_filter(
        admin_info, model, store_id_column, tenant_id_column
    )
    if condition is not None:
        query = query.where(condition)
    return query
