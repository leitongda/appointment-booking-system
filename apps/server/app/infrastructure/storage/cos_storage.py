"""Tencent COS storage service."""

import io
from typing import BinaryIO

import httpx

from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.storage.base import BaseStorage, UploadResult


class TencentCOSStorage(BaseStorage):
    def __init__(self):
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError as exc:
            raise ImportError("腾讯云COS SDK未安装，请运行: pip install cos-python-sdk-v5") from exc

        config = CosConfig(
            Region=settings.COS_REGION,
            SecretId=settings.COS_SECRET_ID,
            SecretKey=settings.COS_SECRET_KEY,
        )
        self.client = CosS3Client(config)
        self.bucket = settings.COS_BUCKET
        self.region = settings.COS_REGION
        self.cdn_domain = settings.COS_CDN_DOMAIN

    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "images",
    ) -> UploadResult:
        try:
            key = self._generate_key(filename, folder)
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            self.client.put_object(
                Bucket=self.bucket,
                Body=file,
                Key=key,
                ContentType=content_type,
            )
            return UploadResult(
                url=self._build_url(key),
                key=key,
                size=size,
                content_type=content_type,
            )
        except Exception as exc:
            logger.error(f"COS upload error: {exc}")
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
            self.client.delete_object(Bucket=self.bucket, Key=key)
            logger.info(f"Deleted file from COS: {key}")
            return True
        except Exception as exc:
            logger.error(f"COS delete error: {exc}")
            return False

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str,
    ) -> UploadResult:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Body=io.BytesIO(data),
                Key=key,
                ContentType=content_type,
            )
            return UploadResult(
                url=self._build_url(key),
                key=key,
                size=len(data),
                content_type=content_type,
            )
        except Exception as exc:
            logger.error(f"COS upload bytes error: {exc}")
            raise Exception(f"文件上传失败: {str(exc)}")

    async def get_url(self, key: str, expires: int = 3600) -> str:
        return self._build_url(key)

    def _build_url(self, key: str) -> str:
        if self.cdn_domain:
            return f"https://{self.cdn_domain.rstrip('/')}/{key}"
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"
