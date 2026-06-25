"""钉钉（DingTalk）集成 Provider。

封装钉钉企业内部应用能力：
- access_token: https://oapi.dingtalk.com/gettoken
- 工作通知: https://oapi.dingtalk.com/topapi/message/corpconversation/asyncsend_v2
- 群机器人: 自定义机器人 Webhook（加签算法）
- OAuth 登录: https://login.dingtalk.com（扫码）/ oauth2/userinfo
- 通讯录: https://oapi.dingtalk.com/topapi/v2/department/list|user/list
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import urllib.parse
from typing import Any

import httpx

from app.infrastructure.integrations.base import BaseIntegrationProvider
from app.models.integration import Integration

logger = logging.getLogger(__name__)


class DingtalkProvider(BaseIntegrationProvider):
    """钉钉集成 Provider。"""

    provider_name = "dingtalk"
    OAPI_BASE = "https://oapi.dingtalk.com"
    LOGIN_BASE = "https://login.dingtalk.com"

    # ============================================================
    # access_token
    # ============================================================

    async def _fetch_access_token(self, integration: Integration) -> str:
        app_key = integration.app_id
        app_secret = self._resolve_secret(integration)
        if not app_key or not app_secret:
            raise ValueError("钉钉配置不完整，缺少 AppKey 或 AppSecret")

        url = f"{self.OAPI_BASE}/gettoken"
        params = {"appkey": app_key, "appsecret": app_secret}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if data.get("errcode") != 0:
            raise ValueError(f"钉钉获取 access_token 失败: {data.get('errmsg')}")
        return data["access_token"]

    # ============================================================
    # 企业应用消息（工作通知）
    # ============================================================

    async def send_work_message(
        self,
        integration: Integration,
        to_user_id: str,
        msg_type: str,
        msg_content: dict | str,
    ) -> bool:
        token = await self.get_access_token(integration)
        agent_id = (integration.extra_config or {}).get("agent_id")
        if not agent_id:
            logger.warning("[钉钉] 缺少 agent_id，无法发送工作通知")
            return False

        # 钉钉工作通知 msg_content 需为字符串形式
        if isinstance(msg_content, str):
            content_payload = msg_content
        else:
            import json

            content_payload = json.dumps(msg_content, ensure_ascii=False)

        body = {
            "agent_id": agent_id,
            "userid_list": to_user_id,
            "msg": {
                "msgtype": msg_type,
                msg_type: {"content": content_payload} if msg_type == "text" else msg_content,
            },
        }
        url = f"{self.OAPI_BASE}/topapi/message/corpconversation/asyncsend_v2"
        params = {"access_token": token}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, params=params, json=body)
                data = resp.json()
            if data.get("errcode") != 0:
                logger.error("[钉钉] 工作通知发送失败: %s", data.get("errmsg"))
                return False
            return True
        except Exception as e:
            logger.error("[钉钉] 工作通知请求异常: %s", e, exc_info=True)
            return False

    # ============================================================
    # 群机器人消息（自定义机器人 + 加签）
    # ============================================================

    async def send_robot_message(
        self,
        webhook_url: str,
        secret: str | None,
        msg_type: str,
        content: str,
        at_list: list[str] | None = None,
    ) -> bool:
        url = self._sign_webhook_url(webhook_url, secret)

        at_block: dict[str, Any] = {"isAtAll": False}
        if at_list:
            at_block["atMobiles"] = at_list

        payload: dict[str, Any] = {"msgtype": msg_type, "at": at_block}
        if msg_type == "text":
            payload["text"] = {"content": content}
        elif msg_type == "markdown":
            payload["markdown"] = {"title": content.split("\n")[0][:20] or "通知", "text": content}
        else:
            payload["text"] = {"content": content}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
            if data.get("errcode") != 0:
                logger.error("[钉钉] 群机器人发送失败: %s", data.get("errmsg"))
                return False
            return True
        except Exception as e:
            logger.error("[钉钉] 群机器人请求异常: %s", e, exc_info=True)
            return False

    @staticmethod
    def _sign_webhook_url(webhook_url: str, secret: str | None) -> str:
        """钉钉群机器人加签：timestamp + sign 追加到 URL query。"""
        if not secret:
            return webhook_url
        timestamp = str(round(time.time() * 1000))
        string_to_sign = f"{timestamp}\n{secret}"
        hmac_code = hmac.new(
            secret.encode("utf-8"), string_to_sign.encode("utf-8"), digestmod=hashlib.sha256
        ).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        sep = "&" if "?" in webhook_url else "?"
        return f"{webhook_url}{sep}timestamp={timestamp}&sign={sign}"

    # ============================================================
    # OAuth 扫码登录
    # ============================================================

    async def get_qrcode_login_url(
        self,
        integration: Integration,
        redirect_uri: str,
        state: str,
    ) -> str:
        app_key = integration.app_id
        return (
            f"https://login.dingtalk.com/login/qrcode.htm"
            f"?client_id={app_key}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
            f"&response_type=code"
            f"&scope=openid"
            f"&state={state}"
            f"&prompt=consent"
        )

    async def get_user_info_by_code(self, integration: Integration, code: str) -> dict:
        """钉钉 OAuth2.0：code → 用户个人信息。

        https://login.dingtalk.com 的新版 OAuth2 接口。
        """
        app_key = integration.app_id
        app_secret = self._resolve_secret(integration)
        headers = {"Content-Type": "application/json"}

        # 1. code 换 accessToken（用户级）
        async with httpx.AsyncClient(timeout=10) as client:
            token_resp = await client.post(
                f"{self.LOGIN_BASE}/v1.0/oauth2/userAccessToken",
                headers=headers,
                json={"clientId": app_key, "clientSecret": app_secret, "code": code, "grantType": "authorization_code"},
            )
        token_data = token_resp.json()
        user_access_token = token_data.get("accessToken")
        if not user_access_token:
            raise ValueError(f"钉钉换取 userAccessToken 失败: {token_data}")

        # 2. accessToken 换用户信息
        async with httpx.AsyncClient(timeout=10) as client:
            info_resp = await client.get(
                f"{self.LOGIN_BASE}/v1.0/contact/users/me",
                headers={"x-acs-dingtalk-access-token": user_access_token},
            )
        info = info_resp.json()

        return {
            "external_id": info.get("openId") or "",
            "union_id": info.get("unionId"),
            "name": info.get("nick") or info.get("name"),
            "email": info.get("email"),
            "phone": info.get("mobile"),
            "avatar": info.get("avatarUrl"),
            "raw": info,
        }

    # ============================================================
    # 通讯录同步
    # ============================================================

    async def get_department_list(self, integration: Integration) -> list[dict]:
        token = await self.get_access_token(integration)
        url = f"{self.OAPI_BASE}/topapi/v2/department/listsub"
        params = {"access_token": token}
        result: list[dict] = []
        # 从根部门(1)开始拉取所有子部门
        queue = ["1"]
        visited: set[str] = set()
        async with httpx.AsyncClient(timeout=10) as client:
            while queue:
                parent_id = queue.pop(0)
                if parent_id in visited:
                    continue
                visited.add(parent_id)
                resp = await client.post(url, params=params, json={"dept_id": int(parent_id)})
                data = resp.json()
                if data.get("errcode") != 0:
                    logger.warning("[钉钉] 获取子部门失败 parent=%s: %s", parent_id, data.get("errmsg"))
                    continue
                for dept in data.get("result", []):
                    dept_id = str(dept.get("dept_id"))
                    result.append({
                        "dept_id": dept_id,
                        "name": dept.get("name"),
                        "parent_id": str(dept.get("parent_id")) if dept.get("parent_id") else None,
                    })
                    queue.append(dept_id)
        return result

    async def get_department_users(self, integration: Integration, dept_id: str) -> list[dict]:
        token = await self.get_access_token(integration)
        url = f"{self.OAPI_BASE}/topapi/v2/user/list"
        params = {"access_token": token}
        result: list[dict] = []
        cursor, has_more = 0, True
        async with httpx.AsyncClient(timeout=10) as client:
            while has_more:
                resp = await client.post(
                    url,
                    params=params,
                    json={"dept_id": int(dept_id), "cursor": cursor, "size": 100},
                )
                data = resp.json()
                if data.get("errcode") != 0:
                    logger.warning("[钉钉] 获取部门成员失败 dept=%s: %s", dept_id, data.get("errmsg"))
                    break
                page = data.get("result", {}) or {}
                for u in page.get("list", []) or []:
                    result.append({
                        "external_id": u.get("userid") or "",
                        "name": u.get("name"),
                        "phone": u.get("mobile"),
                        "email": u.get("email"),
                        "dept_id": dept_id,
                        "raw": u,
                    })
                has_more = page.get("has_more", False)
                cursor = page.get("next_cursor", 0)
        return result
