"""Image processing infrastructure package."""
from app.infrastructure.image.processor import (
    DEFAULT_COMPRESS_QUALITY,
    DEFAULT_THUMBNAIL_SIZES,
    ImageProcessor,
    ProcessedImage,
    ThumbnailSize,
)

__all__ = [
    "ThumbnailSize",
    "ProcessedImage",
    "ImageProcessor",
    "DEFAULT_THUMBNAIL_SIZES",
    "DEFAULT_COMPRESS_QUALITY",
]
