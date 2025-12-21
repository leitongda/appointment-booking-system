"""文件上传 API"""
import io
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Form
from pydantic import BaseModel, HttpUrl
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, Dict

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.services.storage import get_storage, UploadResult
from app.services.image_processor import ImageProcessor, create_image_processor, ProcessedImage
from app.core.logging import logger

router = APIRouter()

# 允许的图片类型
ALLOWED_IMAGE_TYPES = {
    'image/jpeg': ['jpg', 'jpeg'],
    'image/png': ['png'],
    'image/gif': ['gif'],
    'image/webp': ['webp'],
    'image/svg+xml': ['svg'],
}

# 最大文件大小（5MB）
MAX_FILE_SIZE = 5 * 1024 * 1024


class ThumbnailInfo(BaseModel):
    """缩略图信息"""
    url: str
    key: str
    width: int
    height: int
    size: int


class UploadResponse(BaseModel):
    """上传响应"""
    url: str
    key: str
    size: int
    content_type: str
    thumbnails: Optional[Dict[str, ThumbnailInfo]] = None


class TransferRequest(BaseModel):
    """URL转存请求"""
    url: HttpUrl
    folder: Optional[str] = "images"


def validate_image(file: UploadFile) -> None:
    """验证图片文件"""
    # 检查content_type
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的图片格式: {file.content_type}，支持: jpg, png, gif, webp, svg"
        )
    
    # 检查文件扩展名
    if file.filename:
        ext = file.filename.rsplit('.', 1)[-1].lower() if '.' in file.filename else ''
        valid_exts = []
        for exts in ALLOWED_IMAGE_TYPES.values():
            valid_exts.extend(exts)
        if ext and ext not in valid_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"不支持的文件扩展名: {ext}"
            )


def _generate_thumbnail_key(original_key: str, size_name: str) -> str:
    """生成缩略图存储键名"""
    # 从原始键名中提取路径和文件名
    # 格式：folder/202501/uuid.ext -> folder/202501/thumb_small_uuid.ext
    parts = original_key.rsplit('/', 1)
    if len(parts) == 2:
        folder_path, filename = parts
        return f"{folder_path}/thumb_{size_name}_{filename}"
    return f"thumb_{size_name}_{original_key}"


@router.post("", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Form(default="images"),
    generate_thumbnails: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """
    上传图片
    
    - **file**: 图片文件（支持jpg, png, gif, webp, svg）
    - **folder**: 存储文件夹（默认images）
    - **generate_thumbnails**: 是否生成缩略图（默认false）
    
    返回图片URL和存储信息，如果启用缩略图则返回多尺寸URL
    """
    # 验证图片
    validate_image(file)
    
    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大{MAX_FILE_SIZE // 1024 // 1024}MB）"
        )
    
    # 重置文件指针
    await file.seek(0)
    
    try:
        storage = get_storage()
        content_type = file.content_type or "image/jpeg"
        filename = file.filename or "image.jpg"
        
        # 如果需要生成缩略图
        if generate_thumbnails and content_type != 'image/svg+xml':
            # 创建图片处理器
            processor = await create_image_processor(db)
            
            # 处理图片
            file_io = io.BytesIO(content)
            original_img, thumbnails = processor.process(file_io, content_type)
            
            # 上传原图
            original_result = await storage.upload(
                file=io.BytesIO(original_img.data),
                filename=filename,
                content_type=content_type,
                folder=folder
            )
            
            # 上传缩略图
            thumbnail_infos = {}
            for thumb in thumbnails:
                thumb_key = _generate_thumbnail_key(original_result.key, thumb.name)
                thumb_result = await storage.upload_bytes(
                    data=thumb.data,
                    key=thumb_key,
                    content_type=content_type
                )
                thumbnail_infos[thumb.name] = ThumbnailInfo(
                    url=thumb_result.url,
                    key=thumb_result.key,
                    width=thumb.width,
                    height=thumb.height,
                    size=thumb.size
                )
            
            logger.info(
                f"Image uploaded with {len(thumbnails)} thumbnails: "
                f"{original_result.key} by admin {current_admin.get('id')}"
            )
            
            return UploadResponse(
                url=original_result.url,
                key=original_result.key,
                size=original_result.size,
                content_type=original_result.content_type,
                thumbnails=thumbnail_infos
            )
        
        else:
            # 不生成缩略图，直接上传
            result = await storage.upload(
                file=file.file,
                filename=filename,
                content_type=content_type,
                folder=folder
            )
            
            logger.info(f"Image uploaded: {result.key} by admin {current_admin.get('id')}")
            
            return UploadResponse(
                url=result.url,
                key=result.key,
                size=result.size,
                content_type=result.content_type
            )
        
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.post("/transfer", response_model=UploadResponse)
async def transfer_from_url(
    data: TransferRequest,
    current_admin = Depends(get_current_admin),
):
    """
    从URL转存图片
    
    下载外部图片并上传到存储服务
    
    - **url**: 外部图片URL
    - **folder**: 存储文件夹（默认images）
    
    返回新的图片URL和存储信息
    """
    try:
        storage = get_storage()
        result = await storage.upload_from_url(
            url=str(data.url),
            folder=data.folder or "images"
        )
        
        logger.info(f"Image transferred from {data.url} to {result.key} by admin {current_admin.get('id')}")
        
        return UploadResponse(
            url=result.url,
            key=result.key,
            size=result.size,
            content_type=result.content_type
        )
        
    except Exception as e:
        logger.error(f"Transfer failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )


@router.delete("/{key:path}")
async def delete_image(
    key: str,
    current_admin = Depends(get_current_admin),
):
    """
    删除图片
    
    - **key**: 图片存储键名
    """
    try:
        storage = get_storage()
        success = await storage.delete(key)
        
        if success:
            logger.info(f"Image deleted: {key} by admin {current_admin.get('id')}")
            return {"message": "删除成功"}
        else:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="文件不存在或删除失败"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Delete failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )

