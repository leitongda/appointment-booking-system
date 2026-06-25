"""企业微信（WeCom / WeWork）集成 Provider。

封装企业微信自建应用能力：
- access_token: https://qyapi.weixin.qq.com/cgi-bin/gettoken
- 应用消息: https://qyapi.weixin.qq.com/cgi-bin/message/send
- 群机器人: https://qyapi.weixin.qq.com/cgi-bin/webhook/send
- OAuth 登录: https://open.weixin.qq.com/connect/oauth2/authorize + userinfo
- 通讯录: https://qyapi.weixin.qq.com/cgi-bin/department/list|user/list
"""
from __future__ import annotations

import logging
from typing import Any

import httpx

from app.infrastructure.integrations.base import BaseIntegrationProvider
from app.models.integration import Integration

logger = logging.getLogger(__name__)


class WecomProvider(BaseIntegrationProvider):
    """企业微信集成 Provider。"""

    provider_name = "wecom"
    API_BASE = "https://qyapi.weixin.qq.com/cgi-bin"

    # ============================================================
    # access_token
    # ============================================================

    async def _fetch_access_token(self, integration: Integration) -> str:
        corp_id = integration.app_id  # 企业微信的 CorpID
        corp_secret = self._resolve_secret(integration)
        if not corp_id or not corp_secret:
            raise ValueError("企业微信配置不完整，缺少 CorpID 或 Secret")

        url = f"{self.API_BASE}/gettoken"
        params = {"corpid": corp_id, "corpsecret": corp_secret}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()

        if data.get("errcode") != 0:
            raise ValueError(f"企业微信获取 access_token 失败: {data.get('errmsg')}")
        return data["access_token"]

    # ============================================================
    # 企业应用消息（应用消息推送）
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
            logger.warning("[企业微信] 缺少 agent_id，无法发送应用消息")
            return False

        # 企业微信 text 传 {"content": "..."}
        if msg_type == "text":
            content = msg_content if isinstance(msg_content, str) else msg_content.get("content", "")
            body: dict[str, Any] = {
                "touser": to_user_id,
                "msgtype": "text",
                "agentid": agent_id,
                "text": {"content": content},
            }
        else:
            # 其它类型（markdown/markdown_card/textcard 等）直接透传
            body = {
                "touser": to_user_id,
                "msgtype": msg_type,
                "agentid": agent_id,
                msg_type: msg_content if isinstance(msg_content, dict) else {"content": msg_content},
            }

        url = f"{self.API_BASE}/message/send"
        params = {"access_token": token}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, params=params, json=body)
                data = resp.json()
            if data.get("errcode") != 0:
                logger.error("[企业微信] 应用消息发送失败: %s", data.get("errmsg"))
                return False
            return True
        except Exception as e:
            logger.error("[企业微信] 应用消息请求异常: %s", e, exc_info=True)
            return False

    # ============================================================
    # 群机器人消息
    # ============================================================

    async def send_robot_message(
        self,
        webhook_url: str,
        secret: str | None,
        msg_type: str,
        content: str,
        at_list: list[str] | None = None,
    ) -> bool:
        url = self._append_robot_key(webhook_url, secret)

        mentioned_list = at_list if at_list else []
        payload: dict[str, Any] = {"msgtype": msg_type}
        if msg_type == "text":
            payload["text"] = {"content": content, "mentioned_list": mentioned_list}
        elif msg_type == "markdown":
            payload["markdown"] = {"content": content}
        else:
            payload["text"] = {"content": content}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(url, json=payload)
                data = resp.json()
            if data.get("errcode") != 0:
                logger.error("[企业微信] 群机器人发送失败: %s", data.get("errmsg"))
                return False
            return True
        except Exception as e:
            logger.error("[企业微信] 群机器人请求异常: %s", e, exc_info=True)
            return False

    @staticmethod
    def _append_robot_key(webhook_url: str, secret: str | None) -> str:
        """企业微信群机器人 key 作为 query 参数。secret 在此即机器人 key。"""
        if not secret:
            return webhook_url
        sep = "&" if "?" in webhook_url else "?"
        return f"{webhook_url}{sep}key={secret}"

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

        corp_id = integration.app_id
        agent_id = (integration.extra_config or {}).get("agent_id", "")
        return (
            f"https://open.weixin.qq.com/connect/oauth2/authorize"
            f"?appid={corp_id}"
            f"&redirect_uri={urllib.parse.quote(redirect_uri, safe='')}"
            f"&response_type=code"
            f"&scope=snsapi_privateinfo"
            f"&agentid={agent_id}"
            f"&state={state}"
            f"#wechat_redirect"
        )

    async def get_user_info_by_code(self, integration: Integration, code: str) -> dict:
        token = await self.get_access_token(integration)

        # 1. code 换 userid
        url = f"{self.API_BASE}/auth/getuserinfo"
        params = {"access_token": token, "code": code}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        if data.get("errcode") != 0:
            raise ValueError(f"企业微信 getuserinfo 失败: {data.get('errmsg')}")

        userid = data.get("userid")
        if not userid:
            # 非企业成员（外部联系人），仅有 openid
            return {
                "external_id": data.get("openid") or "",
                "union_id": data.get("open_userid"),
                "name": None,
                "raw": data,
            }

        # 2. userid 换用户详情（手机号/邮箱/姓名）
        detail_url = f"{self.API_BASE}/user/get"
        async with httpx.AsyncClient(timeout=10) as client:
            detail_resp = await client.get(detail_url, params={"access_token": token, "userid": userid})
            detail = detail_resp.json()
        if detail.get("errcode") != 0:
            logger.warning("[企业微信] 获取用户详情失败 userid=%s: %s", userid, detail.get("errmsg"))

        return {
            "external_id": userid,
            "union_id": data.get("open_userid"),
            "name": detail.get("name"),
            "email": detail.get("email") or detail.get("biz_mail"),
            "phone": detail.get("mobile"),
            "avatar": detail.get("avatar"),
            "dept_ids": detail.get("department"),
            "raw": detail,
        }

    # ============================================================
    # 通讯录同步
    # ============================================================

    async def get_department_list(self, integration: Integration) -> list[dict]:
        token = await self.get_access_token(integration)
        url = f"{self.API_BASE}/department/list"
        params = {"access_token": token}
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url, params=params)
            data = resp.json()
        if data.get("errcode") != 0:
            logger.warning("[企业微信] 获取部门列表失败: %s", data.get("errmsg"))
            return []
        result: list[dict] = []
        for dept in data.get("department", []) or []:
            result.append({
                "dept_id": str(dept.get("id")),
                "name": dept.get("name"),
                "parent_id": str(dept["parentid"]) if dept.get("parentid") is not None else None,
            })
        return result

    async def get_department_users(self, integration: Integration, dept_id: str) -> list[dict]:
        token = await self.get_access_token(integration)
        url = f"{self.API_BASE}/user/list"
        params = {"access_token": token, "department_id": dept_id}
        result: list[dict] = []
        async with httpx.AsyncClient(timeout=10) as client:
            # simple list 返回成员（不含敏感字段足够）
            resp = await client.get(url, params={**params, "fetch_child": 0})
            data = resp.json()
        if data.get("errcode") != 0:
            logger.warning("[企业微信] 获取部门成员失败 dept=%s: %s", dept_id, data.get("errmsg"))
            return []
        for u in data.get("userlist", []) or []:
            result.append({
                "external_id": u.get("userid") or "",
                "name": u.get("name"),
                "phone": u.get("mobile"),
                "email": u.get("email"),
                "dept_id": dept_id,
                "raw": u,
            })
        return result
