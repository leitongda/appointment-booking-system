"""统计模块共享工具函数"""
from typing import List, Optional, Union

from app.models.doctor import Doctor


def _build_store_filter_condition(store_filter: Union[None, str, List[str]]):
    """构建门店过滤条件"""
    if store_filter is None:
        return None
    if isinstance(store_filter, list):
        return Doctor.store_id.in_(store_filter)
    return Doctor.store_id == store_filter
