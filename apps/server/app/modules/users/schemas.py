from pydantic import BaseModel


class AvatarUploadResponse(BaseModel):
    """Avatar upload response."""

    url: str
    key: str
