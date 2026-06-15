"""Storage infrastructure services."""

from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.storage.base import BaseStorage, UploadResult

_storage_instance: BaseStorage | None = None


def get_storage() -> BaseStorage:
    global _storage_instance

    if _storage_instance is not None:
        return _storage_instance

    storage_type = settings.STORAGE_TYPE.lower()

    if storage_type == "local":
        from app.infrastructure.storage.local_storage import LocalStorage

        _storage_instance = LocalStorage()
        logger.info("Using local file storage backend")
    elif storage_type == "minio":
        from app.infrastructure.storage.minio_storage import MinIOStorage

        _storage_instance = MinIOStorage()
        logger.info("Using MinIO storage backend")
    elif storage_type == "cos":
        from app.infrastructure.storage.cos_storage import TencentCOSStorage

        _storage_instance = TencentCOSStorage()
        logger.info("Using Tencent COS storage backend")
    else:
        raise ValueError(f"Unsupported storage type: {storage_type}")

    return _storage_instance


__all__ = ["BaseStorage", "UploadResult", "get_storage"]
