"""第三方集成平台 Provider 抽象基类。

统一封装钉钉 / 企业微信 / 飞书 的能力差异，包括：
- access_token 获取（带 Redis 缓存）
- 企业应用点对点消息（工作通知，支持 @ 人）
- 群机器人消息推送
- OAuth 扫码登录（code 换取用户信息）
- 通讯录（部门/成员）同步

所有第三方平台能力收敛在各自 Provider 子类中，业务层面向统一接口编程。
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.redis import RedisCache
from app.models.integration import Integration


class BaseIntegrationProvider(ABC):
    """第三方集成平台抽象基类。

    子类需设置 ``provider_name`` 类属性，并实现各抽象方法。
    """

    provider_name: str = ""
    # access_token 默认缓存时长（秒），各平台 token 有效期约 7200s
    TOKEN_CACHE_EXPIRE = 7000

    # ============================================================
    # access_token
    # ============================================================

    async def get_access_token(self, integration: Integration) -> str:
        """获取平台 access_token（带 Redis 缓存，多租户隔离）。

        缓存未命中时调用子类 ``_fetch_access_token`` 向平台刷新。
        """
        cached = await RedisCache.get_integration_token(
            self.provider_name, integration.app_id, tenant_id=integration.tenant_id
        )
        if cached:
            return cached

        token = await self._fetch_access_token(integration)
        await RedisCache.set_integration_token(
            self.provider_name,
            integration.app_id,
            token,
            expire=self.TOKEN_CACHE_EXPIRE,
            tenant_id=integration.tenant_id,
        )
        return token

    @abstractmethod
    async def _fetch_access_token(self, integration: Integration) -> str:
        """向平台刷新 access_token（子类实现具体 HTTP 调用）。"""
        ...

    # ============================================================
    # 企业应用消息（点对点工作通知）
    # ============================================================

    @abstractmethod
    async def send_work_message(
        self,
        integration: Integration,
        to_user_id: str,
        msg_type: str,
        msg_content: dict | str,
    ) -> bool:
        """通过企业自建应用给指定 userId 发送工作通知。

        Args:
            integration: 集成配置（含 app_id / agent_id 等）
            to_user_id: 接收人在该平台的 userId（见 IntegrationBinding.external_id）
            msg_type: text / markdown / action_card 等
            msg_content: 消息内容（text 传字符串，其它传各平台结构 dict）

        Returns:
            是否发送成功
        """
        ...

    # ============================================================
    # 群机器人消息
    # ============================================================

    @abstractmethod
    async def send_robot_message(
        self,
        webhook_url: str,
        secret: str | None,
        msg_type: str,
        content: str,
        at_list: list[str] | None = None,
    ) -> bool:
        """通过群机器人 Webhook 推送消息。

        Args:
            webhook_url: 群机器人 Webhook 地址
            secret: 加签密钥（明文，已由调用方解析 secret_ref）
            msg_type: text / markdown
            content: 消息文本/markdown 正文
            at_list: 需要 @ 的手机号或 userId 列表

        Returns:
            是否发送成功
        """
        ...

    # ============================================================
    # OAuth 扫码登录
    # ============================================================

    @abstractmethod
    async def get_qrcode_login_url(
        self,
        integration: Integration,
        redirect_uri: str,
        state: str,
    ) -> str:
        """生成扫码登录的授权 URL（前端展示二维码或跳转）。"""
        ...

    @abstractmethod
    async def get_user_info_by_code(self, integration: Integration, code: str) -> dict:
        """用 OAuth 回调 code 换取平台用户信息。

        Returns:
            至少包含: {"external_id": "...", "union_id": "...", "name": "..."}
        """
        ...

    # ============================================================
    # 通讯录同步
    # ============================================================

    @abstractmethod
    async def get_department_list(self, integration: Integration) -> list[dict]:
        """获取部门列表。

        Returns:
            [{"dept_id": "...", "name": "...", "parent_id": "..."}, ...]
        """
        ...

    @abstractmethod
    async def get_department_users(self, integration: Integration, dept_id: str) -> list[dict]:
        """获取指定部门下的成员列表。

        Returns:
            [{"external_id": "...", "name": "...", "phone": "...", "email": "...", "dept_id": "..."}, ...]
        """
        ...

    # ============================================================
    # 通用工具
    # ============================================================

    @staticmethod
    def _resolve_secret(integration: Integration, attr: str = "app_secret_ref") -> str | None:
        """解析集成配置中的 secret 引用（env:VAR 形式）。"""
        from app.common.secret_refs import resolve_secret_ref

        ref = getattr(integration, attr, None)
        return resolve_secret_ref(ref)

    @staticmethod
    def _build_text_content(title: str, content: str) -> str:
        """构造纯文本消息体（title + content）。"""
        if title and content:
            return f"{title}\n{content}"
        return content or title or ""

    @staticmethod
    def _build_markdown_content(title: str, content: str) -> str:
        """构造 markdown 消息体。"""
        if title and content:
            return f"## {title}\n\n{content}"
        return content or title or ""
