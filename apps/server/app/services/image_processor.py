"""图片处理服务 - 兼容层

实际实现已迁移至 app.infrastructure.image
"""
from app.infrastructure.image.processor import (
    ThumbnailSize,
    ProcessedImage,
    ImageProcessor,
    get_image_settings,
    create_image_processor,
    DEFAULT_THUMBNAIL_SIZES,
    DEFAULT_COMPRESS_QUALITY,
)

__all__ = [
    "ThumbnailSize",
    "ProcessedImage",
    "ImageProcessor",
    "get_image_settings",
    "create_image_processor",
    "DEFAULT_THUMBNAIL_SIZES",
    "DEFAULT_COMPRESS_QUALITY",
]
