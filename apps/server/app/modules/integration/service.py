"""第三方集成配置服务。

负责 integrations 表的 CRUD、连接测试、绑定关系查询。
多租户隔离：所有操作限定在当前租户。
"""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.secret_refs import resolve_secret_ref
from app.infrastructure.integrations import get_provider
from app.middleware.tenant_context import get_current_tenant_id
from app.models.integration import Integration, IntegrationBinding
from app.modules.integration.schemas import (
    IntegrationCreate,
    IntegrationUpdate,
    SUPPORTED_PROVIDERS,
)

logger = logging.getLogger(__name__)


# 各平台展示信息
_PROVIDER_META: dict[str, dict[str, str]] = {
    "dingtalk": {"name": "钉钉", "description": "企业内部应用 + 群机器人"},
    "wecom": {"name": "企业微信", "description": "自建应用 + 群机器人"},
    "feishu": {"name": "飞书", "description": "自建应用 + 群机器人"},
}


class IntegrationService:
    """第三方集成配置服务。"""

    def __init__(self, db: AsyncSession):
        self.db = db

    def _tenant_id(self) -> str:
        tid = get_current_tenant_id()
        if not tid:
            raise ValueError("缺少租户上下文")
        return tid

    # ============================================================
    # 查询
    # ============================================================

    async def list_integrations(self) -> list[Integration]:
        """列出当前租户的所有集成配置。"""
        tid = self._tenant_id()
        stmt = select(Integration).where(Integration.tenant_id == tid).order_by(Integration.provider)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_by_provider(self, provider: str) -> Integration | None:
        tid = self._tenant_id()
        stmt = select(Integration).where(
            Integration.tenant_id == tid,
            Integration.provider == provider,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_bindings(self, provider: str | None = None) -> list[IntegrationBinding]:
        """列出账号绑定关系。"""
        tid = self._tenant_id()
        stmt = select(IntegrationBinding).where(IntegrationBinding.tenant_id == tid)
        if provider:
            stmt = stmt.where(IntegrationBinding.provider == provider)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    # ============================================================
    # 写入
    # ============================================================

    async def upsert(self, data: IntegrationCreate) -> Integration:
        """创建或更新集成配置（按 tenant+provider 唯一）。"""
        tid = self._tenant_id()
        if data.provider not in SUPPORTED_PROVIDERS:
            raise ValueError(f"不支持的平台: {data.provider}")

        existing = await self.get_by_provider(data.provider)
        if existing:
            existing.name = data.name
            existing.app_id = data.app_id
            if data.app_secret_ref is not None:
                existing.app_secret_ref = data.app_secret_ref
            existing.webhook_url = data.webhook_url
            if data.webhook_secret_ref is not None:
                existing.webhook_secret_ref = data.webhook_secret_ref
            existing.extra_config = data.extra_config
            existing.status = data.status
            await self.db.flush()
            return existing

        integration = Integration(
            tenant_id=tid,
            provider=data.provider,
            name=data.name,
            app_id=data.app_id,
            app_secret_ref=data.app_secret_ref,
            webhook_url=data.webhook_url,
            webhook_secret_ref=data.webhook_secret_ref,
            extra_config=data.extra_config,
            status=data.status,
        )
        self.db.add(integration)
        await self.db.flush()
        return integration

    async def update(self, provider: str, data: IntegrationUpdate) -> Integration | None:
        existing = await self.get_by_provider(provider)
        if not existing:
            return None
        update_data = data.model_dump(exclude_unset=True)
        for k, v in update_data.items():
            setattr(existing, k, v)
        await self.db.flush()
        return existing

    async def delete(self, provider: str) -> bool:
        existing = await self.get_by_provider(provider)
        if not existing:
            return False
        await self.db.delete(existing)
        await self.db.flush()
        return True

    # ============================================================
    # 连接测试
    # ============================================================

    async def test_connection(self, provider: str) -> dict[str, Any]:
        """测试平台连接是否正常（尝试获取 access_token）。"""
        integration = await self.get_by_provider(provider)
        if not integration:
            return {"success": False, "message": f"未配置 {provider} 集成"}

        impl = get_provider(provider)
        if not impl:
            return {"success": False, "message": f"Provider {provider} 未注册"}

        try:
            token = await impl.get_access_token(integration)
            if token:
                return {
                    "success": True,
                    "message": f"{_PROVIDER_META.get(provider, {}).get('name', provider)} 连接成功",
                    "detail": {"token_prefix": token[:8] + "..."},
                }
            return {"success": False, "message": "获取 access_token 返回空"}
        except Exception as e:
            logger.warning("[集成测试] %s 连接失败: %s", provider, e)
            return {"success": False, "message": f"连接失败: {e}", "detail": None}

    # ============================================================
    # 平台元信息
    # ============================================================

    async def list_providers(self) -> list[dict[str, Any]]:
        """列出所有支持的平台及当前配置状态。"""
        integrations = {i.provider: i for i in await self.list_integrations()}
        result = []
        for provider in SUPPORTED_PROVIDERS:
            meta = _PROVIDER_META.get(provider, {"name": provider, "description": ""})
            integ = integrations.get(provider)
            result.append({
                "provider": provider,
                "name": meta["name"],
                "description": meta["description"],
                "configured": integ is not None,
                "status": integ.status if integ else 0,
            })
        return result

    # ============================================================
    # 绑定关系创建（供 SSO 登录 / 通讯录同步调用）
    # ============================================================

    async def upsert_binding(
        self,
        user_id: str,
        user_type: str,
        provider: str,
        external_id: str,
        union_id: str | None = None,
        name: str | None = None,
    ) -> IntegrationBinding:
        tid = self._tenant_id()
        # 按 external_id 查（同一平台账号）
        stmt = select(IntegrationBinding).where(
            IntegrationBinding.tenant_id == tid,
            IntegrationBinding.provider == provider,
            IntegrationBinding.external_id == external_id,
        )
        result = await self.db.execute(stmt)
        binding = result.scalar_one_or_none()

        if binding:
            binding.user_id = user_id
            binding.user_type = user_type
            if union_id:
                binding.union_id = union_id
            if name:
                binding.name = name
            await self.db.flush()
            return binding

        binding = IntegrationBinding(
            tenant_id=tid,
            user_id=user_id,
            user_type=user_type,
            provider=provider,
            external_id=external_id,
            union_id=union_id,
            name=name,
        )
        self.db.add(binding)
        await self.db.flush()
        return binding

    async def get_binding_by_external(self, provider: str, external_id: str) -> IntegrationBinding | None:
        tid = self._tenant_id()
        stmt = select(IntegrationBinding).where(
            IntegrationBinding.tenant_id == tid,
            IntegrationBinding.provider == provider,
            IntegrationBinding.external_id == external_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_binding_by_user(self, provider: str, user_id: str) -> IntegrationBinding | None:
        tid = self._tenant_id()
        stmt = select(IntegrationBinding).where(
            IntegrationBinding.tenant_id == tid,
            IntegrationBinding.provider == provider,
            IntegrationBinding.user_id == user_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
