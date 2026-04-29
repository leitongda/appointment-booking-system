import io

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.core.logging import logger
from app.db.session import get_db
from app.modules.upload.schemas import ThumbnailInfo, TransferRequest, UploadResponse
from app.infrastructure.image.processor import create_image_processor
from app.infrastructure.storage import get_storage
from app.infrastructure.storage.base import build_tenant_storage_folder

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
        tenant_folder = build_tenant_storage_folder(folder, current_admin.get("tenant_id"))

        if generate_thumbnails and content_type != "image/svg+xml":
            processor = await create_image_processor(db)
            file_io = io.BytesIO(content)
            original_img, thumbnails = processor.process(file_io, content_type)
            original_result = await storage.upload(
                file=io.BytesIO(original_img.data),
                filename=filename,
                content_type=content_type,
                folder=tenant_folder,
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
            folder=tenant_folder,
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
        tenant_folder = build_tenant_storage_folder(data.folder or "images", current_admin.get("tenant_id"))
        result = await storage.upload_from_url(url=str(data.url), folder=tenant_folder)
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


def _extract_tenant_id_from_key(key: str) -> str | None:
    """从存储 key 中提取租户 ID。

    租户文件的 key 格式为 tenants/{tenant_id}/...，
    平台级文件没有 tenants/ 前缀。
    """
    prefix = "tenants/"
    if key.startswith(prefix):
        remainder = key[len(prefix):]
        # 第一个 / 之前的部分即为 tenant_id
        tenant_id = remainder.split("/", 1)[0] if "/" in remainder else remainder
        return tenant_id
    return None


def _validate_tenant_access(key: str, current_admin: dict) -> None:
    """校验当前管理员是否有权操作指定 key 的文件。

    - 平台管理员 (无 tenant_id) 可操作所有文件
    - 租户管理员只能操作本租户目录下的文件
    """
    file_tenant_id = _extract_tenant_id_from_key(key)
    admin_tenant_id = current_admin.get("tenant_id")

    # 文件不属于任何租户目录 → 允许（平台级资源）
    if file_tenant_id is None:
        return

    # 管理员无租户（平台管理员）→ 允许
    if not admin_tenant_id:
        return

    # 租户匹配 → 允许
    if str(admin_tenant_id) == str(file_tenant_id):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="无权操作其他租户的文件",
    )


@router.delete("/{key:path}", summary="删除图片")
async def delete_image(
    key: str,
    current_admin=Depends(get_current_admin),
):
    _validate_tenant_access(key, current_admin)

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


# ---------- 文件下载（仅 local 存储模式） ----------

# MIME 类型映射
_MIME_TYPES: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".svg": "image/svg+xml",
}


def _get_content_type_from_ext(key: str) -> str:
    ext = key.rsplit(".", 1)[-1].lower() if "." in key else ""
    return _MIME_TYPES.get(f".{ext}", "application/octet-stream")


def _resolve_local_file(key: str):
    """解析本地文件路径，若文件不存在返回 None。"""
    from pathlib import Path
    from app.core.config import settings

    upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
    file_path = (upload_dir / key).resolve()

    # 防路径穿越：确保解析后的路径仍在 upload_dir 内
    if not str(file_path).startswith(str(upload_dir.resolve())):
        return None

    if file_path.is_file():
        return file_path
    return None


@router.get("/files/{key:path}", summary="下载文件（带租户校验）", include_in_schema=False)
async def download_file(
    key: str,
):
    """文件下载端点，仅用于 local 存储模式。

    租户校验逻辑：
    - 从 URL 路径中提取文件所属的 tenant_id（tenants/{tid}/...）
    - 从请求头中获取当前租户上下文（TenantContextMiddleware 已设置）
    - 如果文件属于某租户且请求上下文有租户信息，则必须匹配
    - 无租户上下文的请求（如患者端公开访问）暂时放行

    对于 MinIO/COS 模式，文件 URL 直接指向对象存储，不经过此端点。
    """
    from app.middleware.tenant_context import get_current_tenant_id
    from app.core.config import settings

    # 非 local 存储模式不接受此端点
    if settings.STORAGE_TYPE.lower() != "local":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="此端点仅用于本地存储模式")

    # 租户路径校验
    file_tenant_id = _extract_tenant_id_from_key(key)
    request_tenant_id = get_current_tenant_id()

    if file_tenant_id and request_tenant_id:
        if str(file_tenant_id) != str(request_tenant_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权访问其他租户的文件",
            )

    # 解析本地文件
    file_path = _resolve_local_file(key)
    if file_path is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="文件不存在")

    content_type = _get_content_type_from_ext(key)
    return FileResponse(
        path=str(file_path),
        media_type=content_type,
        headers={"Cache-Control": "public, max-age=86400"},
    )
