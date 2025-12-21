"""存储服务抽象基类"""
from abc import ABC, abstractmethod
from typing import Optional, BinaryIO
from dataclasses import dataclass


@dataclass
class UploadResult:
    """上传结果"""
    url: str  # 文件访问URL
    key: str  # 存储键名
    size: int  # 文件大小（字节）
    content_type: str  # 文件类型


class BaseStorage(ABC):
    """存储服务抽象基类"""
    
    @abstractmethod
    async def upload(
        self,
        file: BinaryIO,
        filename: str,
        content_type: str,
        folder: str = "images"
    ) -> UploadResult:
        """
        上传文件
        
        Args:
            file: 文件对象
            filename: 文件名
            content_type: 文件MIME类型
            folder: 存储文件夹
            
        Returns:
            UploadResult: 上传结果
        """
        pass
    
    @abstractmethod
    async def upload_from_url(
        self,
        url: str,
        folder: str = "images"
    ) -> UploadResult:
        """
        从URL下载并上传文件
        
        Args:
            url: 外部图片URL
            folder: 存储文件夹
            
        Returns:
            UploadResult: 上传结果
        """
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        删除文件
        
        Args:
            key: 存储键名
            
        Returns:
            bool: 是否删除成功
        """
        pass
    
    @abstractmethod
    async def upload_bytes(
        self,
        data: bytes,
        key: str,
        content_type: str
    ) -> UploadResult:
        """
        上传字节数据（用于上传处理后的图片）
        
        Args:
            data: 字节数据
            key: 存储键名（完整路径）
            content_type: 文件MIME类型
            
        Returns:
            UploadResult: 上传结果
        """
        pass
    
    @abstractmethod
    async def get_url(self, key: str, expires: int = 3600) -> str:
        """
        获取文件访问URL
        
        Args:
            key: 存储键名
            expires: URL过期时间（秒），仅对私有存储有效
            
        Returns:
            str: 文件访问URL
        """
        pass
    
    def _generate_key(self, filename: str, folder: str) -> str:
        """
        生成存储键名
        
        Args:
            filename: 原始文件名
            folder: 存储文件夹
            
        Returns:
            str: 存储键名
        """
        import uuid
        from datetime import datetime
        
        # 获取文件扩展名
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
        
        # 生成唯一文件名：folder/年月/uuid.ext
        date_path = datetime.now().strftime('%Y%m')
        unique_name = f"{uuid.uuid4().hex}.{ext}"
        
        return f"{folder}/{date_path}/{unique_name}"
    
    def _get_content_type_from_url(self, url: str) -> str:
        """根据URL推断content_type"""
        url_lower = url.lower()
        if '.png' in url_lower:
            return 'image/png'
        elif '.gif' in url_lower:
            return 'image/gif'
        elif '.webp' in url_lower:
            return 'image/webp'
        elif '.svg' in url_lower:
            return 'image/svg+xml'
        else:
            return 'image/jpeg'

