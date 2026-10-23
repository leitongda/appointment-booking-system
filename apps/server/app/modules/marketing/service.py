"""医生海报物料服务

生成医生海报底部的小程序码：取当前租户最新启用的小程序实例，
经 access_token 调用微信 getwxacodeunlimit，返回 PNG 二进制的 base64。
"""

import base64
import os

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.wechat.miniapp_publisher import MiniappPublisher
from app.middleware.exception import BusinessError
from app.middleware.tenant_context import get_current_tenant_id
from app.models.miniapp_platform import MiniappInstance

# 未配置实例 / 凭据时的统一错误
POSTER_QRCODE_UNCONFIGURED_MESSAGE = "小程序未配置，无法生成小程序码"


def resolve_app_secret(secret_ref: str | None) -> str | None:
    """解析小程序 Secret 引用

    当前仅支持 ``env:VAR_NAME`` 形式的环境变量引用；
    引用缺失或格式不识别（含空变量名、环境变量不存在）一律视为未配置。

    注意与 app/common/secret_refs.py 的 resolve_secret_ref 不同：
    那里为兼容迁移中的配置会把非 env: 前缀的值原样返回，
    而海报小程序码必须严格 fail-closed，避免把库中明文误当 Secret。
    """
    if not secret_ref:
        return None

    value = secret_ref.strip()
    if not value.startswith("env:"):
        return None

    env_name = value[4:].strip()
    if not env_name:
        return None

    return os.environ.get(env_name)


class MarketingPosterService:
    """医生海报物料服务"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_latest_enabled_instance(self, tenant_id: str) -> MiniappInstance | None:
        """获取租户最新启用的小程序实例"""
        result = await self.db.execute(
            select(MiniappInstance)
            .where(
                MiniappInstance.tenant_id == tenant_id,
                MiniappInstance.status == 1,
            )
            .order_by(MiniappInstance.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def generate_poster_qrcode(self, scene: str, page: str | None = None) -> str:
        """生成海报小程序码，返回 PNG 二进制的 base64 字符串

        Args:
            scene: 场景值（如医生ID），最长 32 字符
            page: 扫码进入的页面路径（可选，缺省进入主页）

        Raises:
            BusinessError: 缺少租户上下文（400）或小程序未配置（404）
        """
        tenant_id = get_current_tenant_id()
        if not tenant_id:
            raise BusinessError("缺少租户上下文，请通过 X-Tenant-ID 或 X-Tenant-Code 指定租户", code=400)

        instance = await self.get_latest_enabled_instance(tenant_id)
        app_secret = resolve_app_secret(instance.app_secret_ref) if instance else None
        if not instance or not app_secret:
            raise BusinessError(POSTER_QRCODE_UNCONFIGURED_MESSAGE, code=404)

        publisher = MiniappPublisher(app_id=instance.app_id, app_secret=app_secret)
        png_bytes = await publisher.get_unlimited_wxacode(scene=scene, page=page)
        return base64.b64encode(png_bytes).decode("ascii")
