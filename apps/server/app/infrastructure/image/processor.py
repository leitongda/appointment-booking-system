"""图片处理服务"""
import io
import json
from typing import BinaryIO, Optional
from dataclasses import dataclass
from PIL import Image

from app.core.logging import logger


@dataclass
class ThumbnailSize:
    """缩略图尺寸配置"""
    name: str
    width: int
    height: int


@dataclass
class ProcessedImage:
    """处理后的图片"""
    name: str  # 尺寸名称，如 "small", "medium", "original"
    data: bytes  # 图片字节数据
    width: int
    height: int
    size: int  # 文件大小


# 默认缩略图尺寸配置
DEFAULT_THUMBNAIL_SIZES = [
    {"name": "small", "width": 200, "height": 200},
    {"name": "medium", "width": 800, "height": 800},
]

# 默认压缩质量
DEFAULT_COMPRESS_QUALITY = 85


class ImageProcessor:
    """图片处理器"""

    def __init__(
        self,
        thumbnail_sizes: Optional[list] = None,
        compress_quality: int = DEFAULT_COMPRESS_QUALITY
    ):
        """
        初始化图片处理器

        Args:
            thumbnail_sizes: 缩略图尺寸列表，格式如 [{"name": "small", "width": 200, "height": 200}]
            compress_quality: 压缩质量 1-100
        """
        self.thumbnail_sizes = self._parse_sizes(thumbnail_sizes)
        self.compress_quality = max(1, min(100, compress_quality))

    def _parse_sizes(self, sizes: Optional[list]) -> list[ThumbnailSize]:
        """解析尺寸配置"""
        if not sizes:
            sizes = DEFAULT_THUMBNAIL_SIZES

        result = []
        for size in sizes:
            if isinstance(size, dict):
                result.append(ThumbnailSize(
                    name=size.get("name", "thumb"),
                    width=size.get("width", 200),
                    height=size.get("height", 200)
                ))
            elif isinstance(size, ThumbnailSize):
                result.append(size)

        return result

    def process(
        self,
        file: BinaryIO,
        content_type: str
    ) -> tuple[ProcessedImage, list[ProcessedImage]]:
        """
        处理图片，生成原图和缩略图

        Args:
            file: 图片文件对象
            content_type: 图片MIME类型

        Returns:
            tuple: (原图ProcessedImage, 缩略图列表)
        """
        try:
            # 读取原图
            file.seek(0)
            original_data = file.read()
            img = Image.open(io.BytesIO(original_data))

            # 确定输出格式
            output_format = self._get_output_format(content_type, img)

            # 处理原图（可能需要压缩）
            original_processed = self._compress_image(img, output_format)
            original_result = ProcessedImage(
                name="original",
                data=original_processed,
                width=img.width,
                height=img.height,
                size=len(original_processed)
            )

            # 生成缩略图
            thumbnails = []
            for size in self.thumbnail_sizes:
                thumb_data, thumb_width, thumb_height = self._create_thumbnail(
                    img, size, output_format
                )
                thumbnails.append(ProcessedImage(
                    name=size.name,
                    data=thumb_data,
                    width=thumb_width,
                    height=thumb_height,
                    size=len(thumb_data)
                ))

            logger.info(
                f"Image processed: original {img.width}x{img.height}, "
                f"{len(thumbnails)} thumbnails generated"
            )

            return original_result, thumbnails

        except Exception as e:
            logger.error(f"Image processing error: {e}")
            raise Exception(f"图片处理失败: {str(e)}")

    def _get_output_format(self, content_type: str, img: Image.Image) -> str:
        """确定输出格式"""
        # 根据content_type确定格式
        format_map = {
            "image/jpeg": "JPEG",
            "image/jpg": "JPEG",
            "image/png": "PNG",
            "image/gif": "GIF",
            "image/webp": "WEBP",
        }

        output_format = format_map.get(content_type.lower())

        if not output_format:
            # 尝试从图片获取格式
            output_format = img.format or "JPEG"

        return output_format

    def _compress_image(self, img: Image.Image, output_format: str) -> bytes:
        """压缩图片"""
        buffer = io.BytesIO()

        # 处理RGBA模式
        save_img = img
        if output_format == "JPEG" and img.mode in ("RGBA", "P"):
            # JPEG不支持透明，转换为RGB
            save_img = img.convert("RGB")

        # 保存图片
        save_kwargs = {"format": output_format}
        if output_format in ("JPEG", "WEBP"):
            save_kwargs["quality"] = self.compress_quality
            save_kwargs["optimize"] = True
        elif output_format == "PNG":
            save_kwargs["optimize"] = True

        save_img.save(buffer, **save_kwargs)
        return buffer.getvalue()

    def _create_thumbnail(
        self,
        img: Image.Image,
        size: ThumbnailSize,
        output_format: str
    ) -> tuple[bytes, int, int]:
        """
        创建缩略图（等比例缩放）

        Returns:
            tuple: (图片字节, 宽度, 高度)
        """
        # 计算等比例缩放后的尺寸
        original_width, original_height = img.size
        ratio = min(size.width / original_width, size.height / original_height)

        # 如果原图比目标尺寸小，不放大
        if ratio >= 1:
            return self._compress_image(img, output_format), original_width, original_height

        new_width = int(original_width * ratio)
        new_height = int(original_height * ratio)

        # 使用高质量重采样
        resized = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return self._compress_image(resized, output_format), new_width, new_height


async def get_image_settings(db) -> tuple[list, int]:
    """
    从数据库获取图片处理配置

    Args:
        db: 数据库会话

    Returns:
        tuple: (缩略图尺寸列表, 压缩质量)
    """
    from app.modules.settings.service import SettingsService

    settings_service = SettingsService(db)

    # 获取缩略图尺寸配置
    sizes_str = await settings_service.get_value(
        "image",
        "thumbnail_sizes",
        json.dumps(DEFAULT_THUMBNAIL_SIZES)
    )

    if isinstance(sizes_str, str):
        try:
            thumbnail_sizes = json.loads(sizes_str)
        except json.JSONDecodeError:
            thumbnail_sizes = DEFAULT_THUMBNAIL_SIZES
    else:
        thumbnail_sizes = sizes_str if sizes_str else DEFAULT_THUMBNAIL_SIZES

    # 获取压缩质量配置
    quality = await settings_service.get_value(
        "image",
        "compress_quality",
        DEFAULT_COMPRESS_QUALITY
    )

    if isinstance(quality, str):
        try:
            quality = int(quality)
        except ValueError:
            quality = DEFAULT_COMPRESS_QUALITY

    return thumbnail_sizes, quality


async def create_image_processor(db) -> ImageProcessor:
    """
    创建图片处理器（从数据库读取配置）

    Args:
        db: 数据库会话

    Returns:
        ImageProcessor: 图片处理器实例
    """
    thumbnail_sizes, compress_quality = await get_image_settings(db)
    return ImageProcessor(
        thumbnail_sizes=thumbnail_sizes,
        compress_quality=compress_quality
    )
