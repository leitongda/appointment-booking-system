"""低代码页面服务。"""

import logging

logger = logging.getLogger(__name__)

import time
from typing import Any, Optional, List, Tuple

import httpx
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.lowcode_page import LowCodePage
from app.models.lowcode_audit_log import LowCodePageAuditLog
from app.utils.audit import set_create_audit, set_update_audit

# 沙箱限制
_TEST_TIMEOUT_SECONDS = 5.0
_TEST_MAX_RESPONSE_BYTES = 1 * 1024 * 1024  # 1 MB
_TEST_MAX_SAMPLE_ITEMS = 5


def _extract_fields(data: Any, prefix: str = "") -> list[dict[str, Any]]:
    """递归提取 JSON 数据的字段结构，用于字段建议。"""
    fields: list[dict[str, Any]] = []
    if isinstance(data, dict):
        for key, val in data.items():
            path = f"{prefix}.{key}" if prefix else key
            if isinstance(val, dict):
                fields.append({"path": path, "type": "object", "sample": None})
                fields.extend(_extract_fields(val, path))
            elif isinstance(val, list):
                fields.append({"path": path, "type": "array", "sample": None})
                if val and isinstance(val[0], dict):
                    fields.extend(_extract_fields(val[0], f"{path}[0]"))
            elif isinstance(val, bool):
                fields.append({"path": path, "type": "boolean", "sample": val})
            elif isinstance(val, (int, float)):
                fields.append({"path": path, "type": "number", "sample": val})
            else:
                fields.append({"path": path, "type": "string", "sample": val})
    elif isinstance(data, list) and data and isinstance(data[0], dict):
        fields.extend(_extract_fields(data[0], f"{prefix}[0]" if prefix else "[0]"))
    return fields


def _truncate_sample(data: Any) -> Any:
    """截取样本数据，列表最多保留 _TEST_MAX_SAMPLE_ITEMS 条。"""
    if isinstance(data, list):
        return data[:_TEST_MAX_SAMPLE_ITEMS]
    if isinstance(data, dict):
        return {k: _truncate_sample(v) for k, v in data.items()}
    return data


def _mock_for_type(field_type: str) -> Any:
    """根据字段类型生成模拟值。"""
    mapping = {
        "string": "示例文本",
        "number": 0,
        "boolean": True,
        "array": [],
        "object": {},
    }
    return mapping.get(field_type, None)


class LowCodePageService:
    """低代码页面 CRUD 服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _log_audit(
        self,
        page_id: str,
        operator_id: str,
        action: str,
        detail: Optional[dict] = None,
    ) -> None:
        """记录审计日志。"""
        log = LowCodePageAuditLog(
            page_id=page_id,
            operator_id=operator_id,
            action=action,
            detail=detail,
        )
        self.db.add(log)

    async def get_list(
        self,
        tenant_id: str,
        status: Optional[int] = None,
        keyword: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[LowCodePage], int]:
        """获取页面列表。"""
        query = select(LowCodePage).where(LowCodePage.tenant_id == tenant_id)
        conditions = []

        if status is not None:
            conditions.append(LowCodePage.status == status)
        if keyword:
            conditions.append(LowCodePage.name.ilike(f"%{keyword}%"))

        if conditions:
            query = query.where(and_(*conditions))

        count_query = select(func.count(LowCodePage.id)).where(
            LowCodePage.tenant_id == tenant_id
        )
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total = await self.db.scalar(count_query)

        query = query.order_by(LowCodePage.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await self.db.execute(query)
        items = result.scalars().all()

        return list(items), total or 0

    async def get_by_id(self, tenant_id: str, page_id: str) -> Optional[LowCodePage]:
        """根据ID获取页面。"""
        query = select(LowCodePage).where(
            LowCodePage.tenant_id == tenant_id,
            LowCodePage.id == page_id,
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def create(
        self,
        tenant_id: str,
        name: str,
        slug: str,
        description: Optional[str] = None,
        schema_data: Optional[dict] = None,
        thumbnail_url: Optional[str] = None,
        miniapp_instance_id: Optional[str] = None,
        created_by: Optional[str] = None,
    ) -> LowCodePage:
        """创建页面。"""
        page = LowCodePage(
            tenant_id=tenant_id,
            name=name,
            slug=slug,
            description=description,
            schema_data=schema_data or {},
            thumbnail_url=thumbnail_url,
            miniapp_instance_id=miniapp_instance_id,
        )
        set_create_audit(page, created_by)
        self.db.add(page)
        await self.db.flush()
        await self._log_audit(
            page_id=str(page.id),
            operator_id=created_by or "system",
            action="create",
            detail={"name": name, "slug": slug},
        )
        await self.db.commit()
        await self.db.refresh(page)
        return page

    async def update(
        self,
        tenant_id: str,
        page_id: str,
        name: Optional[str] = None,
        slug: Optional[str] = None,
        description: Optional[str] = None,
        schema_data: Optional[dict] = None,
        status: Optional[int] = None,
        thumbnail_url: Optional[str] = None,
        miniapp_instance_id: Optional[str] = None,
        updated_by: Optional[str] = None,
    ) -> Optional[LowCodePage]:
        """更新页面。"""
        page = await self.get_by_id(tenant_id, page_id)
        if not page:
            return None

        # 收集变更前的值用于审计日志
        changes: dict[str, Any] = {}
        if name is not None and page.name != name:
            changes["name"] = {"old": page.name, "new": name}
        if slug is not None and page.slug != slug:
            changes["slug"] = {"old": page.slug, "new": slug}
        if description is not None and page.description != description:
            changes["description"] = {"old": page.description, "new": description}
        if schema_data is not None:
            changes["schema_data"] = {"changed": True}
        if status is not None and page.status != status:
            changes["status"] = {"old": page.status, "new": status}
        if thumbnail_url is not None and page.thumbnail_url != thumbnail_url:
            changes["thumbnail_url"] = {"changed": True}
        if miniapp_instance_id is not None and page.miniapp_instance_id != miniapp_instance_id:
            changes["miniapp_instance_id"] = {"changed": True}

        if name is not None:
            page.name = name
        if slug is not None:
            page.slug = slug
        if description is not None:
            page.description = description
        if schema_data is not None:
            page.schema_data = schema_data
        if status is not None:
            page.status = status
        if thumbnail_url is not None:
            page.thumbnail_url = thumbnail_url
        if miniapp_instance_id is not None:
            page.miniapp_instance_id = miniapp_instance_id

        set_update_audit(page, updated_by)
        await self.db.flush()

        # 根据变更内容确定操作类型
        action = "update"
        if status is not None and "status" in changes:
            old_status = changes["status"]["old"]
            new_status = changes["status"]["new"]
            if new_status == 1 and old_status != 1:
                action = "publish"
            elif new_status == 2 and old_status != 2:
                action = "archive"

        await self._log_audit(
            page_id=page_id,
            operator_id=updated_by or "system",
            action=action,
            detail=changes if changes else None,
        )
        await self.db.commit()
        await self.db.refresh(page)
        return page

    async def delete(self, tenant_id: str, page_id: str, deleted_by: Optional[str] = None) -> bool:
        """删除页面(仅草稿状态可删)。"""
        page = await self.get_by_id(tenant_id, page_id)
        if not page or page.status != 0:
            return False

        await self._log_audit(
            page_id=page_id,
            operator_id=deleted_by or "system",
            action="delete",
            detail={"name": page.name, "slug": page.slug},
        )
        await self.db.delete(page)
        await self.db.commit()
        return True

    async def check_slug_unique(
        self, tenant_id: str, slug: str, exclude_id: Optional[str] = None
    ) -> bool:
        """检查 slug 是否唯一。"""
        query = select(LowCodePage.id).where(
            LowCodePage.tenant_id == tenant_id,
            LowCodePage.slug == slug,
        )
        if exclude_id:
            query = query.where(LowCodePage.id != exclude_id)
        result = await self.db.execute(query)
        return result.scalar_one_or_none() is None

    async def get_audit_logs(
        self,
        page_id: str,
        tenant_id: str,
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[List[LowCodePageAuditLog], int]:
        """获取页面审计日志列表。"""
        # 先校验页面归属
        target_page = await self.get_by_id(tenant_id, page_id)
        if not target_page:
            return [], 0

        query = (
            select(LowCodePageAuditLog)
            .where(LowCodePageAuditLog.page_id == page_id)
            .order_by(LowCodePageAuditLog.created_at.desc())
        )
        count_query = select(func.count(LowCodePageAuditLog.id)).where(
            LowCodePageAuditLog.page_id == page_id
        )

        total = await self.db.scalar(count_query)
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await self.db.execute(query)
        items = result.scalars().all()
        return list(items), total or 0

    async def get_with_data_sources(
        self, tenant_id: str, page_id: str
    ) -> Optional[LowCodePage]:
        """获取页面 (含 dataSources 校验)。"""
        return await self.get_by_id(tenant_id, page_id)

    @staticmethod
    async def test_data_source(
        url: str,
        method: str = "GET",
        headers: Optional[dict[str, str]] = None,
        params: Optional[dict[str, Any]] = None,
        body: Optional[dict[str, Any]] = None,
        response_path: Optional[str] = None,
    ) -> dict[str, Any]:
        """沙箱测试数据源请求。

        限制:
        - 超时 5 秒
        - 响应体最大 1 MB
        - 样本数据列表最多 5 条
        """
        t0 = time.monotonic()
        try:
            async with httpx.AsyncClient(
                timeout=_TEST_TIMEOUT_SECONDS,
                follow_redirects=False,
                max_redirects=0,
            ) as client:
                resp = await client.request(
                    method=method.upper(),
                    url=url,
                    headers=headers,
                    params=params,
                    json=body if body and method.upper() in ("POST", "PUT") else None,
                )
                elapsed = int((time.monotonic() - t0) * 1000)

                # 读取并限制响应大小
                raw = resp.content
                if len(raw) > _TEST_MAX_RESPONSE_BYTES:
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "error": f"响应体超过 {_TEST_MAX_RESPONSE_BYTES // 1024} KB 限制",
                        "elapsed_ms": elapsed,
                    }

                # 尝试解析 JSON
                try:
                    data = resp.json()
                except Exception:
                    return {
                        "success": False,
                        "status_code": resp.status_code,
                        "error": "响应不是有效 JSON",
                        "elapsed_ms": elapsed,
                    }

                # 按 response_path 提取子数据
                target = data
                if response_path:
                    for key in response_path.split("."):
                        if isinstance(target, dict) and key in target:
                            target = target[key]
                        else:
                            return {
                                "success": False,
                                "status_code": resp.status_code,
                                "error": f"response_path '{response_path}' 不存在",
                                "elapsed_ms": elapsed,
                            }

                sample_data = _truncate_sample(target)
                fields = _extract_fields(target)

                return {
                    "success": True,
                    "status_code": resp.status_code,
                    "sample_data": sample_data,
                    "fields": fields,
                    "elapsed_ms": elapsed,
                }

        except httpx.TimeoutException:
            elapsed = int((time.monotonic() - t0) * 1000)
            return {
                "success": False,
                "error": f"请求超时 ({_TEST_TIMEOUT_SECONDS}s)",
                "elapsed_ms": elapsed,
            }
        except httpx.RequestError as exc:
            elapsed = int((time.monotonic() - t0) * 1000)
            return {
                "success": False,
                "error": f"请求失败: {exc}",
                "elapsed_ms": elapsed,
            }

    @staticmethod
    def build_data_preview(page: LowCodePage) -> list[dict[str, Any]]:
        """根据页面 schema_data.dataSources 构建模拟数据预览。"""
        schema_data = page.schema_data or {}
        data_sources = schema_data.get("dataSources", [])
        results: list[dict[str, Any]] = []

        for ds in data_sources:
            source_id = ds.get("id", "")
            url = ds.get("url", "")
            method = ds.get("method", "GET")

            # 从 dataBinding 中找到引用该数据源的字段，推断结构
            data_binding = schema_data.get("dataBinding", {})
            mock_fields: list[dict[str, Any]] = []
            mock_data: dict[str, Any] = {}

            # 收集所有引用该数据源的绑定路径
            bound_paths: list[str] = []
            for _binding_key, binding_expr in data_binding.items():
                if isinstance(binding_expr, str) and source_id in binding_expr:
                    bound_paths.append(binding_expr)

            # 如果有 state 定义了 defaultValue，作为 mock 数据的起点
            state = schema_data.get("state", {})
            for state_key, state_def in state.items():
                if isinstance(state_def, dict):
                    dv = state_def.get("defaultValue")
                    if dv is not None:
                        mock_data[state_key] = dv
                        mock_fields.append({
                            "name": state_key,
                            "type": state_def.get("type", "string"),
                            "sample": dv,
                        })

            # 如果没有从 state 推断出数据，用通用 mock 结构
            if not mock_data:
                mock_data = {
                    "list": [
                        {"id": 1, "name": "示例项目 1", "description": "示例描述"},
                        {"id": 2, "name": "示例项目 2", "description": "示例描述"},
                    ],
                    "total": 2,
                    "page": 1,
                    "page_size": 10,
                }
                mock_fields = [
                    {"name": "list", "type": "array", "sample": None},
                    {"name": "total", "type": "number", "sample": 2},
                    {"name": "page", "type": "number", "sample": 1},
                    {"name": "page_size", "type": "number", "sample": 10},
                ]

            results.append({
                "source_id": source_id,
                "url": url,
                "method": method,
                "mock_data": mock_data,
                "fields": mock_fields,
            })

        return results
