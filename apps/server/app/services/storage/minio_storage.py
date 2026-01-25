"""MinIO 存储服务实现"""
import io
from typing import BinaryIO
from minio import Minio
from minio.error import S3Error
import httpx

from app.services.storage.base import BaseStorage, UploadResult
from app.core.config import settings
from app.core.logging import logger


class MinIOStorage(BaseStorage):
    """MinIO 存储服务"""
    
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
        """确保存储桶存在"""
        try:
            if not self.client.bucket_exists(self.bucket):
                self.client.make_bucket(self.bucket)
                # 设置桶策略为公开读取
                policy = {
                    "Version": "2012-10-17",
                    "Statement": [
                        {
                            "Effect": "Allow",
                            "Principal": {"AWS": "*"},
                            "Action": ["s3:GetObject"],
                            "Resource": [f"arn:aws:s3:::{self.bucket}/*"]
                        }
                    ]
                }
                import json
                self.client.set_bucket_policy(self.bucket, json.dumps(policy))
                logger.info(f"Created bucket: {self.bucket}")
        except S3Error as e:
            logger.error(f"MinIO bucket error: {e}")
            raise
    
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "images"
    ) -> UploadResult:
        """上传文件到MinIO"""
        try:
            # 生成存储键名
            key = self._generate_key(filename, folder)
            
            # 获取文件大小
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            
            # 上传到MinIO
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=file,
                length=size,
                content_type=content_type,
            )
            
            # 生成访问URL
            url = self._build_url(key)
            
            logger.info(f"Uploaded file to MinIO: {key}")
            
            return UploadResult(
                url=url,
                key=key,
                size=size,
                content_type=content_type
            )
            
        except S3Error as e:
            logger.error(f"MinIO upload error: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    async def upload_from_url(
        self,
        url: str,
        folder: str = "images"
    ) -> UploadResult:
        """从URL下载并上传到MinIO"""
        try:
            # 下载外部图片
            async with httpx.AsyncClient(timeout=30.0, trust_env=False) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                # 获取content_type
                content_type = response.headers.get('content-type', '').split(';')[0]
                if not content_type or 'image' not in content_type:
                    content_type = self._get_content_type_from_url(url)
                
                # 获取文件名
                filename = url.rsplit('/', 1)[-1].split('?')[0]
                if not filename or '.' not in filename:
                    ext = content_type.split('/')[-1] if '/' in content_type else 'jpg'
                    filename = f"transfer.{ext}"
                
                # 创建文件对象
                file_data = io.BytesIO(response.content)
                
                return await self.upload(file_data, filename, content_type, folder)
                
        except httpx.HTTPError as e:
            logger.error(f"Download from URL error: {e}")
            raise Exception(f"下载图片失败: {str(e)}")
    
    async def delete(self, key: str) -> bool:
        """删除MinIO中的文件"""
        try:
            self.client.remove_object(self.bucket, key)
            logger.info(f"Deleted file from MinIO: {key}")
            return True
        except S3Error as e:
            logger.error(f"MinIO delete error: {e}")
            return False
    
    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str
    ) -> UploadResult:
        """上传字节数据到MinIO"""
        try:
            # 创建BytesIO对象
            file_data = io.BytesIO(data)
            size = len(data)
            
            # 上传到MinIO
            self.client.put_object(
                bucket_name=self.bucket,
                object_name=key,
                data=file_data,
                length=size,
                content_type=content_type,
            )
            
            # 生成访问URL
            url = self._build_url(key)
            
            logger.info(f"Uploaded bytes to MinIO: {key}")
            
            return UploadResult(
                url=url,
                key=key,
                size=size,
                content_type=content_type
            )
            
        except S3Error as e:
            logger.error(f"MinIO upload bytes error: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取文件访问URL"""
        # 公开桶直接返回URL
        return self._build_url(key)
    
    def _build_url(self, key: str) -> str:
        """构建文件访问URL"""
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{key}"
        
        protocol = "https" if settings.MINIO_SECURE else "http"
        return f"{protocol}://{settings.MINIO_ENDPOINT}/{self.bucket}/{key}"

