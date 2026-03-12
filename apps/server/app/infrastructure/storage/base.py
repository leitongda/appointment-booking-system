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
