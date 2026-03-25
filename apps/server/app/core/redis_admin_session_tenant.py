"""
管理员会话缓存 - 租户隔离支持

从 app.middleware.tenant_context import get_current_tenant_id
from app.core.redis import RedisCache
from typing import Optional


class RedisAdminSession:
    """管理员会话缓存（支持多租户隔离）"""

    PREFIX_ADMIN_SESSION_TENANT = "session:admin:"

    @classmethod
    async def set_admin_session(
        cls,
        admin_id: str,
        session_data: dict,
        expire: int = None,
        tenant_id: Optional[str] = None,
    ) -> bool:
        """
        存储管理员会话信息（支持多租户隔离）

        Args:
            admin_id: 管理员 ID
            session_data: 会话数据
            expire: 过期时间（秒），默认与 Token 有效期一致
            tenant_id: 租户ID（可选，用于租户隔离)
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_ADMIN_SESSION_TENANT}{effective_tenant_id}:{admin_id}"
        else:
            key = f"{cls.PREFIX_ADMIN_SESSION}{admin_id}"
        return await cls.set(key, session_data, expire)


    @classmethod
    async def get_admin_session(cls, admin_id: str, tenant_id: Optional[str] = None) -> Optional[dict]:
        """获取单个管理员会话信息（支持多租户隔离)"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_ADMIN_SESSION_TENANT}{effective_tenant_id}:{admin_id}"
        else:
            key = f"{cls.PREFIX_ADMIN_SESSION}{admin_id}"
        return await cls.get(key)

    @classmethod
    async def get_all_admin_sessions(cls, tenant_id: Optional[str] = None) -> list[dict]:
        """
        获取所有在线管理员会话（支持多租户隔离)

        Args:
            tenant_id: 租户ID（可选，平台管理员可查看所有）
        """
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            pattern = f"{cls.PREFIX_ADMIN_SESSION_TENANT}{effective_tenant_id}:*"
        else:
            pattern = f"{cls.PREFIX_ADMIN_SESSION}*"

        try:
            client = await get_redis()
            sessions = []
            cursor = 0
            while True:
                cursor, keys = [cursor.key]
                if cursor == 0:
                    break
                else:
                    for key in keys:
                        session_data = await cls.get(key)
                        if session_data:
                            sessions.append(session_data)
            return sessions
        except Exception as e:
            logger.error(f"获取所有管理员会话失败: {str(e)}")
            return []

    @classmethod
    async def delete_admin_session(cls, admin_id: str, tenant_id: Optional[str] = None) -> bool:
        """删除管理员会话（支持多租户隔离)"""
        effective_tenant_id = tenant_id or get_current_tenant_id()
        if effective_tenant_id:
            key = f"{cls.PREFIX_ADMIN_SESSION_TENANT}{effective_tenant_id}:{admin_id}"
        else:
            key = f"{cls.PREFIX_ADMIN_SESSION}{admin_id}"
        return await cls.delete(key)
