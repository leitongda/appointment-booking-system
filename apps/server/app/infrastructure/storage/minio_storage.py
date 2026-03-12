"""MinIO storage service."""

import io
import json
from typing import BinaryIO

import httpx
from minio import Minio
from minio.error import S3Error

from app.core.config import settings
from app.core.logging import logger
from app.infrastructure.storage.base import BaseStorage, UploadResult


class MinIOStorage(BaseStorage):
    def __init__(self):
        self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )
        self.bucket = settings.MINIO_BUCKET
        self.public_url = settings.MINIO_PUBLIC_URL
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket}/*"],
                        }
                    ],
                }
                self.client.set_bucket_policy(self.bucket, json.dumps(policy))
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as exc:
            logger.error(f"MinIO bucket error: {exc}")
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
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=file,
                length=size,
                content_type=content_type,
            )
            return UploadResult(
                url=self._build_url(key),
                key=key,
                size=size,
                content_type=content_type,
            )
        except S3Error as exc:
            logger.error(f"MinIO upload error: {exc}")
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
            self.client.remove_object(self.bucket, key)
            logger.info(f"Deleted file from MinIO: {key}")
            return True
        except S3Error as exc:
            logger.error(f"MinIO delete error: {exc}")
            return False

    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str,
    ) -> UploadResult:
        try:
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=io.BytesIO(data),
                length=len(data),
                content_type=content_type,
            )
            return UploadResult(
                url=self._build_url(key),
                key=key,
                size=len(data),
                content_type=content_type,
            )
        except S3Error as exc:
            logger.error(f"MinIO upload bytes error: {exc}")
            raise Exception(f"文件上传失败: {str(exc)}")

    async def get_url(self, key: str, expires: int = 3600) -> str:
        return self._build_url(key)

    def _build_url(self, key: str) -> str:
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{key}"
        protocol = "https" if settings.MINIO_SECURE else "http"
        return f"{protocol}://{settings.MINIO_ENDPOINT}/{self.bucket}/{key}"
