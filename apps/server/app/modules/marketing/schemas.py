from pydantic import Field

from app.schemas.base import BaseSchema


class PosterQrcodeResponse(BaseSchema):
    """医生海报小程序码响应"""
    image: str = Field(..., description="小程序码 PNG 图片二进制的 base64 字符串")
