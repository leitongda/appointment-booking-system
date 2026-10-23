"""统计模块共享工具函数"""

from sqlalchemy import false

from app.models.doctor import Doctor


def _build_store_filter_condition(store_filter: None | str | list[str]):
    """构建门店过滤条件"""
    if store_filter is None:
        return None
    if isinstance(store_filter, list):
        return Doctor.store_id.in_(store_filter)
    return Doctor.store_id == store_filter


def _build_tenant_condition(model, tenant_id: str | None):
    """构建租户过滤条件（R1-3）

    Args:
        model: 参与聚合的模型类（需带 tenant_id 列）
        tenant_id: 已解析的租户锚点；None 表示平台管理员（全平台视图，不过滤）

    Returns:
        SQLAlchemy 条件或 None（不过滤）。模型缺少 tenant_id 列时返回永假条件，
        避免统计结果跨租户泄露（fail-close）。
    """
    if tenant_id is None:
        return None

    tenant_column = getattr(model, "tenant_id", None)
    if tenant_column is None:
        return false()
    return tenant_column == tenant_id
