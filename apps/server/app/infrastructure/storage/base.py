"""Storage service abstractions."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import BinaryIO


@dataclass
class UploadResult:
    url: str
    key: str
    size: int
    content_type: str


class BaseStorage(ABC):
    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "images",
    ) -> UploadResult:
        pass

    @abstractmethod
    async def upload_from_url(
        self,
        url: str,
        folder: str = "images",
    ) -> UploadResult:
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        pass

    @abstractmethod
    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str,
    ) -> UploadResult:
        pass

    @abstractmethod
    async def get_url(self, key: str, expires: int = 3600) -> str:
        pass

    def _generate_key(self, filename: str, folder: str) -> str:
        import uuid
        from datetime import datetime

        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else "jpg"
        date_path = datetime.now().strftime("%Y%m")
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        return f"{folder}/{date_path}/{unique_name}"

    def _get_content_type_from_url(self, url: str) -> str:
        url_lower = url.lower()
        if ".png" in url_lower:
            return "image/png"
        if ".gif" in url_lower:
            return "image/gif"
        if ".webp" in url_lower:
            return "image/webp"
        if ".svg" in url_lower:
            return "image/svg+xml"
        return "image/jpeg"


def build_tenant_storage_folder(folder: str, tenant_id: str | None = None) -> str:
    """为上传目录添加租户前缀。

    没有租户上下文时保留原目录，便于平台级资源继续沿用旧路径。
    """
    normalized_folder = folder.strip("/") if folder else "images"
    if not tenant_id:
        return normalized_folder

    tenant_prefix = f"tenants/{tenant_id}"
    if normalized_folder == tenant_prefix or normalized_folder.startswith(f"{tenant_prefix}/"):
        return normalized_folder
    return f"{tenant_prefix}/{normalized_folder}"
