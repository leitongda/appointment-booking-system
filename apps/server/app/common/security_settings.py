"""安全策略配置辅助函数（已迁移至 app.infrastructure.security_settings）

此文件保留为向后兼容的 re-export，新代码请直接导入 app.infrastructure.security_settings。
"""
from app.infrastructure.security_settings import get_default_password, get_token_expire_config

__all__ = ["get_token_expire_config", "get_default_password"]
