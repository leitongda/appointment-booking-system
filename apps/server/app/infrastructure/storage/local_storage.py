"""Local file storage service."""

import io
from pathlib import Path
from typing import BinaryIO

import aiofiles
import httpx

from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.storage.base import BaseStorage, UploadResult


class LocalStorage(BaseStorage):
    def __init__(self):
        self.upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
        self.public_url = settings.LOCAL_PUBLIC_URL
        self._ensure_upload_dir()

    def _ensure_upload_dir(self):
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage directory: {self.upload_dir}")
        except Exception as exc:
            logger.error(f"Failed to create upload directory: {exc}")
            raise

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "images",
    ) -> UploadResult:
        try:
            key = self._generate_key(filename, folder)
            file_path = self.upload_dir / key
            file_path.parent.mkdir(parents=True, exist_ok=True)

            file.seek(0, 2)
            size = file.tell()
            file.seek(0)

            async with aiofiles.open(file_path, "wb") as handle:
                await handle.write(file.read())

            return UploadResult(
                url=self._build_url(key),
                key=key,
                size=size,
                content_type=content_type,
            )
        except Exception as exc:
            logger.error(f"Local upload error: {exc}")
            raise Exception(f"文件上传失败: {str(exc)}")

    async def upload_from_url(
        self,
        url: str,
        folder: str = "images",
    ) -> UploadResult:
        try:
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()

                content_type = response.headers.get("content-type", "").split(";")[0]
                if not content_type or "image" not in content_type:
                    content_type = self._get_content_type_from_url(url)

                filename = url.rsplit("/", 1)[-1].split("?")[0]
                if not filename or "." not in filename:
                    ext = content_type.split("/")[-1] if "/" in content_type else "jpg"
                    filename = f"transfer.{ext}"

                return await self.upload(
                    io.BytesIO(response.content),
                    filename,
                    content_type,
                    folder,
                )
        except httpx.HTTPError as exc:
            logger.error(f"Download from URL error: {exc}")
            raise Exception(f"下载图片失败: {str(exc)}")

    async def delete(self, key: str) -> bool:
        try:
            file_path = self.upload_dir / key
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file from local: {key}")
                return True
            return False
        except Exception as exc:
            logger.error(f"Local delete error: {exc}")
            return False

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str,
    ) -> UploadResult:
        try:
            file_path = self.upload_dir / key
            file_path.parent.mkdir(parents=True, exist_ok=True)

            async with aiofiles.open(file_path, "wb") as handle:
                await handle.write(data)

            return UploadResult(
                url=self._build_url(key),
                key=key,
                size=len(data),
                content_type=content_type,
            )
        except Exception as exc:
            logger.error(f"Local upload bytes error: {exc}")
            raise Exception(f"文件上传失败: {str(exc)}")

    async def get_url(self, key: str, expires: int = 3600) -> str:
        return self._build_url(key)

    def _build_url(self, key: str) -> str:
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{key}"
        return f"/uploads/{key}"
