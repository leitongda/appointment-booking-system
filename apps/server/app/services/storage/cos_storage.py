"""腾讯云 COS 存储服务实现（预留）"""
import io
from typing import BinaryIO
import httpx

from app.services.storage.base import BaseStorage, UploadResult
from app.core.config import settings
from app.core.logging import logger


class TencentCOSStorage(BaseStorage):
    """腾讯云 COS 存储服务"""
    
    def __init__(self):
        # 延迟导入，避免未安装依赖时报错
        try:
            from qcloud_cos import CosConfig, CosS3Client
        except ImportError:
            raise ImportError(
                "腾讯云COS SDK未安装，请运行: pip install cos-python-sdk-v5"
            )
        
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
        folder: str = "images"
    ) -> UploadResult:
        """上传文件到COS"""
        try:
            # 生成存储键名
            key = self._generate_key(filename, folder)
            
            # 获取文件大小
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            
            # 上传到COS
            self.client.put_object(
                Bucket=self.bucket,
                Body=file,
                Key=key,
                ContentType=content_type,
            )
            
            # 生成访问URL
            url = self._build_url(key)
            
            logger.info(f"Uploaded file to COS: {key}")
            
            return UploadResult(
                url=url,
                key=key,
                size=size,
                content_type=content_type
            )
            
        except Exception as e:
            logger.error(f"COS upload error: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    async def upload_from_url(
        self,
        url: str,
        folder: str = "images"
    ) -> UploadResult:
        """从URL下载并上传到COS"""
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
        """删除COS中的文件"""
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key
            )
            logger.info(f"Deleted file from COS: {key}")
            return True
        except Exception as e:
            logger.error(f"COS delete error: {e}")
            return False
    
    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str
    ) -> UploadResult:
        """上传字节数据到COS"""
        try:
            # 创建BytesIO对象
            file_data = io.BytesIO(data)
            size = len(data)
            
            # 上传到COS
            self.client.put_object(
                Bucket=self.bucket,
                Body=file_data,
                Key=key,
                ContentType=content_type,
            )
            
            # 生成访问URL
            url = self._build_url(key)
            
            logger.info(f"Uploaded bytes to COS: {key}")
            
            return UploadResult(
                url=url,
                key=key,
                size=size,
                content_type=content_type
            )
            
        except Exception as e:
            logger.error(f"COS upload bytes error: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取文件访问URL"""
        return self._build_url(key)
    
    def _build_url(self, key: str) -> str:
        """构建文件访问URL"""
        if self.cdn_domain:
            return f"https://{self.cdn_domain.rstrip('/')}/{key}"
        
        return f"https://{self.bucket}.cos.{self.region}.myqcloud.com/{key}"

