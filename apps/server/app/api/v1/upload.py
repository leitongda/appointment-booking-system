"""文件上传 API"""
from fastapi import APIRouter, UploadFile, File, HTTPException, status, Depends, Form
from pydantic import BaseModel, HttpUrl
from typing import Optional

from app.api.deps import get_current_admin
from app.services.storage import get_storage, UploadResult
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


class UploadResponse(BaseModel):
    """上传响应"""
    url: str
    key: str
    size: int
    content_type: str


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


@router.post("", response_model=UploadResponse)
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Form(default="images"),
    current_admin = Depends(get_current_admin),
):
    """
    上传图片
    
    - **file**: 图片文件（支持jpg, png, gif, webp, svg）
    - **folder**: 存储文件夹（默认images）
    
    返回图片URL和存储信息
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
        result = await storage.upload(
            file=file.file,
            filename=file.filename or "image.jpg",
            content_type=file.content_type or "image/jpeg",
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

