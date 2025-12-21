"""本地文件存储服务实现"""
import io
from pathlib import Path
from typing import BinaryIO
import httpx
import aiofiles

from app.services.storage.base import BaseStorage, UploadResult
from app.core.config import settings
from app.core.logging import logger


class LocalStorage(BaseStorage):
    """本地文件存储服务"""
    
    def __init__(self):
        self.upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
        self.public_url = settings.LOCAL_PUBLIC_URL
        self._ensure_upload_dir()
    
    def _ensure_upload_dir(self):
        """确保上传目录存在"""
        try:
            self.upload_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Local storage directory: {self.upload_dir}")
        except Exception as e:
            logger.error(f"Failed to create upload directory: {e}")
            raise
    
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "images"
    ) -> UploadResult:
        """上传文件到本地"""
        try:
            # 生成存储键名
            key = self._generate_key(filename, folder)
            
            # 完整文件路径
            file_path = self.upload_dir / key
            
            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 获取文件大小
            file.seek(0, 2)
            size = file.tell()
            file.seek(0)
            
            # 保存文件
            content = file.read()
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(content)
            
            # 生成访问URL
            url = self._build_url(key)
            
            logger.info(f"Uploaded file to local: {key}")
            
            return UploadResult(
                url=url,
                key=key,
                size=size,
                content_type=content_type
            )
            
        except Exception as e:
            logger.error(f"Local upload error: {e}")
            raise Exception(f"文件上传失败: {str(e)}")
    
    async def upload_from_url(
        self,
        url: str,
        folder: str = "images"
    ) -> UploadResult:
        """从URL下载并上传到本地"""
        try:
            # 下载外部图片
            async with httpx.AsyncClient(timeout=30.0) as client:
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
        """删除本地文件"""
        try:
            file_path = self.upload_dir / key
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Deleted file from local: {key}")
                return True
            return False
        except Exception as e:
            logger.error(f"Local delete error: {e}")
            return False
    
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """获取文件访问URL"""
        return self._build_url(key)
    
    def _build_url(self, key: str) -> str:
        """构建文件访问URL"""
        if self.public_url:
            return f"{self.public_url.rstrip('/')}/{key}"
        
        # 默认使用相对路径
        return f"/uploads/{key}"

