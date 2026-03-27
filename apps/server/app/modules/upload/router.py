import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.logging import logger
from app.db.session import get_db
from app.modules.upload.schemas import ThumbnailInfo, TransferRequest, UploadResponse
from app.infrastructure.image.processor import create_image_processor
from app.infrastructure.storage import get_storage

router = APIRouter()

ALLOWED_IMAGE_TYPES = {
    "image/jpeg": ["jpg", "jpeg"],
    "image/png": ["png"],
    "image/gif": ["gif"],
    "image/webp": ["webp"],
    "image/svg+xml": ["svg"],
}
MAX_FILE_SIZE = 5 * 1024 * 1024


def validate_image(file: UploadFile) -> None:
    if file.content_type not in ALLOWED_IMAGE_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片格式，请使用 jpg、png、gif、webp 或 svg 格式",
        )

    if file.filename:
        ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else ""
        valid_exts = []
        for exts in ALLOWED_IMAGE_TYPES.values():
            valid_exts.extend(exts)
        if ext and ext not in valid_exts:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="不支持的文件格式，请检查文件类型",
            )


def _generate_thumbnail_key(original_key: str, size_name: str) -> str:
    parts = original_key.rsplit("/", 1)
    if len(parts) == 2:
        folder_path, filename = parts
        return f"{folder_path}/thumb_{size_name}_{filename}"
    return f"thumb_{size_name}_{original_key}"


@router.post("", response_model=UploadResponse, summary="上传图片")
async def upload_image(
    file: UploadFile = File(...),
    folder: str = Form(default="images"),
    generate_thumbnails: bool = Form(default=False),
    db: AsyncSession = Depends(get_db),
    current_admin=Depends(get_current_admin),
):
    validate_image(file)

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制，最大支持{MAX_FILE_SIZE // 1024 // 1024}MB",
        )

    await file.seek(0)

    try:
        storage = get_storage()
        content_type = file.content_type or "image/jpeg"
        filename = file.filename or "image.jpg"

        if generate_thumbnails and content_type != "image/svg+xml":
            processor = await create_image_processor(db)
            file_io = io.BytesIO(content)
            original_img, thumbnails = processor.process(file_io, content_type)
            original_result = await storage.upload(
                file=io.BytesIO(original_img.data),
                filename=filename,
                content_type=content_type,
                folder=folder,
            )

            thumbnail_infos = {}
            for thumb in thumbnails:
                thumb_key = _generate_thumbnail_key(original_result.key, thumb.name)
                thumb_result = await storage.upload_bytes(
                    data=thumb.data,
                    key=thumb_key,
                    content_type=content_type,
                )
                thumbnail_infos[thumb.name] = ThumbnailInfo(
                    url=thumb_result.url,
                    key=thumb_result.key,
                    width=thumb.width,
                    height=thumb.height,
                    size=thumb.size,
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
                thumbnails=thumbnail_infos,
            )

        result = await storage.upload(
            file=file.file,
            filename=filename,
            content_type=content_type,
            folder=folder,
        )
        logger.info(f"Image uploaded: {result.key} by admin {current_admin.get('id')}")
        return UploadResponse(
            url=result.url,
            key=result.key,
            size=result.size,
            content_type=result.content_type,
        )
    except Exception as exc:
        logger.error(f"Upload failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.post("/transfer", response_model=UploadResponse, summary="URL转存")
async def transfer_from_url(
    data: TransferRequest,
    current_admin=Depends(get_current_admin),
):
    try:
        storage = get_storage()
        result = await storage.upload_from_url(url=str(data.url), folder=data.folder or "images")
        logger.info(f"Image transferred from {data.url} to {result.key} by admin {current_admin.get('id')}")
        return UploadResponse(
            url=result.url,
            key=result.key,
            size=result.size,
            content_type=result.content_type,
        )
    except Exception as exc:
        logger.error(f"Transfer failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.delete("/{key:path}", summary="删除图片")
async def delete_image(
    key: str,
    current_admin=Depends(get_current_admin),
):
    try:
        storage = get_storage()
        success = await storage.delete(key)
        if success:
            logger.info(f"Image deleted: {key} by admin {current_admin.get('id')}")
            return {"message": "删除成功"}
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在或删除失败，请检查后重试")
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Delete failed: {exc}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
