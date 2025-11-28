"""微信服务"""
import httpx
from typing import Optional, Dict, Any
from app.services.settings_service import SettingsService
from sqlalchemy.ext.asyncio import AsyncSession


class WechatService:
    """微信小程序服务"""
    
    WECHAT_API_URL = "https://api.weixin.qq.com"
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self._app_id: Optional[str] = None
        self._app_secret: Optional[str] = None
    
    async def _load_config(self):
        """加载微信配置"""
        if self._app_id and self._app_secret:
            return
        
        settings_service = SettingsService(self.db)
        config = await settings_service.get_by_category('wechat')
        self._app_id = config.get('app_id', '')
        self._app_secret = config.get('app_secret', '')
    
    async def code2session(self, code: str) -> Dict[str, Any]:
        """
        通过 code 获取 session_key 和 openid
        https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-login/code2Session.html
        """
        await self._load_config()
        
        if not self._app_id or not self._app_secret:
            raise ValueError("微信配置不完整，请先在系统设置中配置 AppID 和 Secret")
        
        url = f"{self.WECHAT_API_URL}/sns/jscode2session"
        params = {
            "appid": self._app_id,
            "secret": self._app_secret,
            "js_code": code,
            "grant_type": "authorization_code"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            error_msg = data.get("errmsg", "微信登录失败")
            raise ValueError(f"微信登录失败: {error_msg}")
        
        return {
            "openid": data.get("openid"),
            "session_key": data.get("session_key"),
            "unionid": data.get("unionid"),
        }
    
    async def get_phone_number(self, code: str) -> Optional[str]:
        """
        通过 code 获取用户手机号
        https://developers.weixin.qq.com/miniprogram/dev/OpenApiDoc/user-info/phone-number/getPhoneNumber.html
        """
        await self._load_config()
        
        # 先获取 access_token
        access_token = await self._get_access_token()
        
        url = f"{self.WECHAT_API_URL}/wxa/business/getuserphonenumber?access_token={access_token}"
        
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json={"code": code})
            data = response.json()
        
        if data.get("errcode", 0) != 0:
            return None
        
        phone_info = data.get("phone_info", {})
        return phone_info.get("purePhoneNumber") or phone_info.get("phoneNumber")
    
    async def _get_access_token(self) -> str:
        """获取小程序 access_token"""
        await self._load_config()
        
        url = f"{self.WECHAT_API_URL}/cgi-bin/token"
        params = {
            "grant_type": "client_credential",
            "appid": self._app_id,
            "secret": self._app_secret
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params)
            data = response.json()
        
        if "errcode" in data and data["errcode"] != 0:
            raise ValueError(f"获取 access_token 失败: {data.get('errmsg')}")
        
        return data.get("access_token", "")

