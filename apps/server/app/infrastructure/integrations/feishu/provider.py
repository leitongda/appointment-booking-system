"""飞书（Lark / Feishu）集成 Provider。

封装飞书自建应用能力：
- tenant_access_token: https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal
- 消息推送: https://open.feishu.cn/open-apis/im/v1/messages
- 群机器人: 自定义机器人 Webhook（签名校验）
- OAuth 登录: https://accounts.feishu.cn/open-apis/authen/v1/index + user_info
- 通讯录: https://open.feishu.cn/open-apis/contact/v3/departments|users
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
from typing import Any

import httpx

from app.infrastructure.integrations.base import BaseIntegrationProvider
from app.models.integration import Integration

logger = logging.getLogger(__name__)


class FeishuProvider(BaseIntegrationProvider):
    """飞书集成 Provider。"""

    provider_name = "feishu"
    API_BASE = "https://open.feishu.cn/open-apis"

    # ============================================================
    # access_token（飞书为 tenant_access_token）
    # ============================================================

    async def _fetch_access_token(self, integration: Integration) -> str:
        app_id = integration.app_id
        app_secret = self._resolve_secret(integration)
        if not app_id or not app_secret:
            raise ValueError("飞书配置不完整，缺少 App ID 或 App Secret")

        url = f"{self.API_BASE}/auth/v3/tenant_access_token/internal"
        body = {"app_id": app_id, "app_secret": app_secret}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(url, json=body)
            data = resp.json()

        if data.get("code") != 0:
            raise ValueError(f"飞书获取 tenant_access_token 失败: {data.get('msg')}")
        return data["tenant_access_token"]

    # ============================================================
    # 企业应用消息（点对点）
    # ============================================================

    async def send_work_message(
        self,
        integration: Integration,
        to_user_id: str,
        msg_type: str,
        msg_content: dict | str,
    ) -> bool:
        import json

        token = await self.get_access_token(integration)
        url = f"{self.API_BASE}/im/v1/messages?receive_id_type=open_id"

        # 飞书消息 content 必须是 JSON 字符串
        if isinstance(msg_content, str):
            if msg_type == "text":
                content_str = json.dumps({"text": msg_content}, ensure_ascii=False)
            else:
                content_str = json.dumps({"content": msg_content}, ensure_ascii=False)
        else:
            content_str = json.dumps(msg_content, ensure_ascii=False)

        body = {
            "receive_id": to_user_id,
            "msg_type": msg_type,
            "content": content_str,
        }
        headers = {"Authorization": f"Bearer {token}"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=body, headers=headers)
                data = resp.json()
            if data.get("code") != 0:
                logger.error("[飞书] 消息发送失败: %s", data.get("msg"))
                return False
            return True
        except Exception as e:
            logger.error("[飞书] 消息请求异常: %s", e, exc_info=True)
            return False

    # ============================================================
    # 群机器人消息（自定义机器人 + 签名）
    # ============================================================

    async def send_robot_message(
        self,
        webhook_url: str,
        secret: str | None,
        msg_type: str,
        content: str,
        at_list: list[str] | None = None,
    ) -> bool:
        import json

        body: dict[str, Any] = {"msg_type": msg_type}
        if msg_type == "text":
            body["content"] = json.dumps({"text": content}, ensure_ascii=False)
        elif msg_type == "interactive":
            # 飞书卡片，content 已是 JSON 字符串或结构
            body["card"] = content if isinstance(content, str) else json.dumps(content, ensure_ascii=False)
        else:
            body["content"] = json.dumps({"content": content}, ensure_ascii=False)

        # 加签
        if secret:
            timestamp = str(int(time.time()))
            string_to_sign = f"{timestamp}\n{secret}"
            hmac_code = hmac.new(
                string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
            ).digest()
            sign = base64.b64encode(hmac_code).decode("utf-8")
            body["timestamp"] = timestamp
            body["sign"] = sign

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(webhook_url, json=body)
                data = resp.json()
            # 飞书机器人成功返回 {"StatusCode":0} 或 {"code":0}
            code = data.get("StatusCode", data.get("code"))
            if code not in (0, None):
                logger.error("[飞书] 群机器人发送失败: %s", data)
                return False
            return True
        except Exception as e:
            logger.error("[飞书] 群机器人请求异常: %s", e, exc_info=True)
            return False

    # ============================================================
    # OAuth 扫码登录
    # ============================================================

    async def get_qrcode_login_url(
        self,
        integration: Integration,
        redirect_uri: str,
        state: str,
    ) -> str:
        import urllib.parse

        app_id = integration.app_id
        return (
            f"https://accounts.feishu.cn/open-apis/authen/v1/index"
            f"?app_id={app_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
            f"&response_type=code"
            f"&state={state}"
        )

    async def get_user_info_by_code(self, integration: Integration, code: str) -> dict:
        token = await self.get_access_token(integration)
        headers = {"Authorization": f"Bearer {token}"}

        # 1. code 换 user_access_token
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.post(
                f"{self.API_BASE}/authen/v1/access_token",
                headers=headers,
                json={"grant_type": "authorization_code", "code": code},
            )
            data = resp.json()
        if data.get("code") != 0:
            raise ValueError(f"飞书换取 user_access_token 失败: {data.get('msg')}")

        uat = data["data"]["access_token"]
        # 2. 获取用户信息
        async with httpx.AsyncClient(timeout=10) as client:
            info_resp = await client.get(
                f"{self.API_BASE}/authen/v1/user_info",
                headers={"Authorization": f"Bearer {uat}"},
            )
            info = info_resp.json()
        if info.get("code") != 0:
            raise ValueError(f"飞书获取用户信息失败: {info.get('msg')}")

        d = info.get("data", {}) or {}
        return {
            "external_id": d.get("open_id") or "",
            "union_id": d.get("union_id"),
            "name": d.get("name"),
            "email": d.get("email"),
            "phone": d.get("mobile"),
            "avatar": d.get("avatar_url"),
            "raw": d,
        }

    # ============================================================
    # 通讯录同步
    # ============================================================

    async def get_department_list(self, integration: Integration) -> list[dict]:
        token = await self.get_access_token(integration)
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.API_BASE}/contact/v3/departments"
        result: list[dict] = []
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=10) as client:
            while True:
                params: dict[str, Any] = {"page_size": 50, "fetch_child": True}
                if page_token:
                    params["page_token"] = page_token
                resp = await client.get(url, params=params, headers=headers)
                data = resp.json()
                if data.get("code") != 0:
                    logger.warning("[飞书] 获取部门列表失败: %s", data.get("msg"))
                    break
                d = data.get("data", {}) or {}
                for dept in d.get("items", []) or []:
                    result.append({
                        "dept_id": dept.get("department_id") or "",
                        "name": dept.get("name"),
                        "parent_id": dept.get("parent_open_department_id") or dept.get("parent_id"),
                    })
                if not d.get("has_more"):
                    break
                page_token = d.get("page_token")
        return result

    async def get_department_users(self, integration: Integration, dept_id: str) -> list[dict]:
        token = await self.get_access_token(integration)
        headers = {"Authorization": f"Bearer {token}"}
        url = f"{self.API_BASE}/contact/v3/users"
        result: list[dict] = []
        page_token: str | None = None
        async with httpx.AsyncClient(timeout=10) as client:
            while True:
                params: dict[str, Any] = {"department_id": dept_id, "department_id_type": "open_department_id", "page_size": 50}
                if page_token:
                    params["page_token"] = page_token
                resp = await client.get(url, params=params, headers=headers)
                data = resp.json()
                if data.get("code") != 0:
                    logger.warning("[飞书] 获取部门成员失败 dept=%s: %s", dept_id, data.get("msg"))
                    break
                d = data.get("data", {}) or {}
                for u in d.get("items", []) or []:
                    result.append({
                        "external_id": u.get("user_id") or u.get("open_id") or "",
                        "name": u.get("name"),
                        "phone": u.get("mobile"),
                        "email": u.get("email"),
                        "dept_id": dept_id,
                        "raw": u,
                    })
                if not d.get("has_more"):
                    break
                page_token = d.get("page_token")
        return result
