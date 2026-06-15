"""租户过滤工具

提供统一的租户过滤逻辑，用于业务查询中添加租户条件。
"""
from typing import Any

from sqlalchemy import select
from sqlalchemy.sql import Select

from app.middleware.tenant_context import get_current_tenant_id


def add_tenant_filter(
    query: Select,
    model: type[Any],
    tenant_id: str | None = None,
    tenant_field: str = "tenant_id"
) -> Select:
    """
    为查询添加租户过滤条件

    Args:
        query: SQLAlchemy 查询对象
        model: 模型类
        tenant_id: 租户ID，如果为 None 则从上下文获取
        tenant_field: 租户字段名，默认为 "tenant_id"

    Returns:
        添加了租户过滤条件的查询对象
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    if not tenant_id:
        return query

    # 获取模型上的租户字段
    tenant_column = getattr(model, tenant_field, None)
    if tenant_column is None:
        return query

    return query.where(tenant_column == tenant_id)


def add_tenant_filter_with_store_fallback(
    query: Select,
    model: type[Any],
    tenant_id: str | None = None,
    store_model: type[Any] = None
) -> Select:
    """
    为查询添加租户过滤条件，支持通过门店间接关联

    对于没有直接 tenant_id 字段的模型，通过 store_id 关联到门店，
    再通过门店的 tenant_id 进行过滤。

    Args:
        query: SQLAlchemy 查询对象
        model: 模型类
        tenant_id: 租户ID
        store_model: 门店模型类

    Returns:
        添加了租户过滤条件的查询对象
    """
    if tenant_id is None:
        tenant_id = get_current_tenant_id()

    if not tenant_id:
        return query

    # 如果模型有 tenant_id 字段，直接使用
    if hasattr(model, 'tenant_id'):
        return query.where(model.tenant_id == tenant_id)

    # 如果模型有 store_id 字段但没有 tenant_id，通过门店关联
    if hasattr(model, 'store_id') and store_model is not None:
        query = query.join(store_model).where(store_model.tenant_id == tenant_id)
        return query

    return query


def get_tenant_id_for_create(
    tenant_id: str | None = None,
    store_id: str | None = None,
    store_model: type[Any] = None,
    db=None
) -> str | None:
    """
    获取创建数据时应使用的租户ID

    优先级：
    1. 显式传入的 tenant_id
    2. 从上下文获取的 tenant_id
    3. 通过 store_id 从门店获取

    Args:
        tenant_id: 显式指定的租户ID
        store_id: 门店ID（用于推断租户）
        store_model: 门店模型类
        db: 数据库会话（用于查询门店）

    Returns:
        租户ID
    """
    # 优先使用显式传入的租户ID
    if tenant_id:
        return tenant_id

    # 从上下文获取
    context_tenant_id = get_current_tenant_id()
    if context_tenant_id:
        return context_tenant_id

    # 通过门店推断
    if store_id and store_model is not None and db is not None:
        import asyncio

        from sqlalchemy import select

        async def get_store_tenant():
            result = await db.execute(
                select(store_model.tenant_id).where(store_model.id == store_id)
            )
            return result.scalar_one_or_none()

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果事件循环已在运行，创建任务
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, get_store_tenant())
                    return future.result()
            else:
                return loop.run_until_complete(get_store_tenant())
        except Exception:
            pass

    return None


class TenantFilteredQuery:
    """
    租户过滤查询构建器

    提供链式调用方式构建带租户过滤的查询。

    用法:
        query = TenantFilteredQuery(Model, tenant_id)
            .with_base_query(base_query)
            .with_store_fallback(Store)
            .build()
    """

    def __init__(
        self,
        model: type[Any],
        tenant_id: str | None = None
    ):
        self.model = model
        self.tenant_id = tenant_id or get_current_tenant_id()
        self.base_query = None
        self.store_model = None
        self.use_fallback = False

    def with_base_query(self, query: Select) -> "TenantFilteredQuery":
        """设置基础查询"""
        self.base_query = query
        return self

    def with_store_fallback(self, store_model: type[Any]) -> "TenantFilteredQuery":
        """启用门店关联回退"""
        self.store_model = store_model
        self.use_fallback = True
        return self

    def build(self) -> Select:
        """构建最终查询"""
        query = self.base_query or select(self.model)

        if not self.tenant_id:
            return query

        if self.use_fallback:
            return add_tenant_filter_with_store_fallback(
                query, self.model, self.tenant_id, self.store_model
            )
        else:
            return add_tenant_filter(query, self.model, self.tenant_id)
