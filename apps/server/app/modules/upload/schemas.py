from typing import Dict, Optional

from pydantic import BaseModel, HttpUrl


class ThumbnailInfo(BaseModel):
    url: str
    key: str
    width: int
    height: int
    size: int


class UploadResponse(BaseModel):
    url: str
    key: str
    size: int
    content_type: str
    thumbnails: Optional[Dict[str, ThumbnailInfo]] = None


class TransferRequest(BaseModel):
    url: HttpUrl
    folder: Optional[str] = "images"
