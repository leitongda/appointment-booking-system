"""T-2：租户隔离矩阵注册表与断言工具

每个模块声明：列表路径、详情/写路径模板、跨租户期望状态。
新增模块时在 MATRIX_MODULES 追加一条，并在测试中提供本租户/他租户对象。
"""
from dataclasses import dataclass
from typing import Callable


def page_items(payload: dict) -> list:
    """PageResponse / 裸列表两种返回结构统一取 items"""
    if isinstance(payload, list):
        return payload
    return payload.get("data") or payload.get("items") or []


@dataclass(frozen=True)
class ModuleSpec:
    """一个待验证的租户隔离模块"""

    name: str  # 模块名（用于参数化与报错定位）
    list_path: str
    detail_path: str | None
    write_path: str | None
    cross_status: tuple[int, ...]  # 跨租户访问允许的状态码（其余状态一律失败）
    extract_items: Callable[[dict], list]
    # 写路径的 HTTP 方法与请求体（None 表示无 body，如 DELETE）
    write_method: str = "put"
    write_payload: dict | None = None


MATRIX_MODULES: list[ModuleSpec] = [
    ModuleSpec(
        name="stores",
        list_path="/api/v1/stores",
        detail_path="/api/v1/stores/{id}",
        write_path="/api/v1/stores/{id}",
        cross_status=(403, 404),
        extract_items=page_items,
        write_payload={"name": "门店改名"},
    ),
    ModuleSpec(
        name="doctors",
        list_path="/api/v1/doctors",
        detail_path="/api/v1/doctors/{id}",
        write_path="/api/v1/doctors/{id}",
        cross_status=(403, 404),
        extract_items=page_items,
        write_payload={"name": "医生改名"},
    ),
    ModuleSpec(
        # 列表走 /departments/all（裸列表），详情/写入走 /departments/{id}
        name="departments",
        list_path="/api/v1/departments/all",
        detail_path="/api/v1/departments/{id}",
        write_path="/api/v1/departments/{id}",
        cross_status=(403, 404),
        extract_items=page_items,
        write_payload={"name": "科室改名"},
    ),
]
