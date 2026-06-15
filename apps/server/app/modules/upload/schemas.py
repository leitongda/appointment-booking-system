
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
    thumbnails: dict[str, ThumbnailInfo] | None = None


class TransferRequest(BaseModel):
    url: HttpUrl
    folder: str | None = "images"
