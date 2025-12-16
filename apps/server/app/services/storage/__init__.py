"""存储服务模块"""
from app.services.storage.base import BaseStorage, UploadResult
from app.core.config import settings
from app.core.logging import logger

# 存储服务单例
_storage_instance: BaseStorage | None = None


def get_storage() -> BaseStorage:
    """
    获取存储服务实例
    
    根据配置自动选择存储后端：
    - minio: MinIO 存储
    - cos: 腾讯云 COS 存储
    
    Returns:
        BaseStorage: 存储服务实例
    """
    global _storage_instance
    
    if _storage_instance is not None:
        return _storage_instance
    
    storage_type = settings.STORAGE_TYPE.lower()
    
    if storage_type == "minio":
        from app.services.storage.minio_storage import MinIOStorage
        _storage_instance = MinIOStorage()
        logger.info("Using MinIO storage backend")
        
    elif storage_type == "cos":
        from app.services.storage.cos_storage import TencentCOSStorage
        _storage_instance = TencentCOSStorage()
        logger.info("Using Tencent COS storage backend")
        
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")
    
    return _storage_instance


__all__ = ["BaseStorage", "UploadResult", "get_storage"]

