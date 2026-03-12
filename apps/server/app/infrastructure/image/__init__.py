"""Image processing infrastructure package."""
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
