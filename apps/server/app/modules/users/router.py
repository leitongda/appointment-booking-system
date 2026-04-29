from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.core.logging import logger
from app.db.session import get_db
from app.modules.users.schemas import AvatarUploadResponse
from app.schemas.user import (
    BindPhoneRequest,
    ChangePasswordRequest,
    PatientCreate,
    PatientResponse,
    PatientUpdate,
    UserResponse,
    UserUpdate,
)
from app.infrastructure.storage import get_storage
from app.infrastructure.storage.base import build_tenant_storage_folder
from app.modules.users.service import PatientService, UserService

router = APIRouter()

ALLOWED_AVATAR_TYPES = {
    "image/jpeg": ["jpg", "jpeg"],
    "image/png": ["png"],
    "image/gif": ["gif"],
    "image/webp": ["webp"],
}
MAX_AVATAR_SIZE = 2 * 1024 * 1024


@router.get("/profile", response_model=UserResponse, summary="获取当前用户信息")
async def get_profile(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    return UserResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar=user.avatar,
        gender=user.gender,
        status=user.status,
    )


@router.put("/profile", response_model=UserResponse, summary="更新用户信息")
async def update_profile(
    data: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service = UserService(db)
    user = await user_service.update(current_user["id"], data)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")
    return UserResponse(
        id=user.id,
        phone=user.phone,
        nickname=user.nickname,
        avatar=user.avatar,
        gender=user.gender,
        status=user.status,
    )


@router.post("/change-password", summary="修改密码")
async def change_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service = UserService(db)
    user = await user_service.get_by_id(current_user["id"])
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在，请检查后重试")

    # 密码策略校验
    from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
    from app.middleware.tenant_context import get_current_tenant_id
    tenant_id = get_current_tenant_id()
    policy = await get_tenant_password_policy(db, tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(data.new_password, phone=user.phone)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    success, message = await user_service.change_password(
        current_user["id"], data.old_password, data.new_password
    )
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"message": message}


@router.post("/bind-phone", summary="绑定手机号")
async def bind_phone(
    data: BindPhoneRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    user_service = UserService(db)
    success, message = await user_service.bind_phone(current_user["id"], data.phone)
    if not success:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)
    return {"message": message}


@router.post("/avatar", response_model=AvatarUploadResponse, summary="上传头像")
async def upload_avatar(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    if file.content_type not in ALLOWED_AVATAR_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的图片格式，请使用 jpg、png、gif 或 webp 格式",
        )

    content = await file.read()
    if len(content) > MAX_AVATAR_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制，最大支持{MAX_AVATAR_SIZE // 1024 // 1024}MB",
        )

    await file.seek(0)

    try:
        storage = get_storage()
        content_type = file.content_type or "image/jpeg"
        filename = file.filename or "avatar.jpg"
        tenant_folder = build_tenant_storage_folder("avatars", current_user.get("tenant_id"))
        result = await storage.upload(
            file=file.file,
            filename=filename,
            content_type=content_type,
            folder=tenant_folder,
        )
        logger.info(f"User avatar uploaded: {result.key} by user {current_user.get('id')}")
        return AvatarUploadResponse(url=result.url, key=result.key)
    except Exception as exc:
        logger.error(f"Avatar upload failed: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="头像上传失败，请稍后重试",
        ) from exc


@router.get("/patients", response_model=List[PatientResponse], summary="获取就诊人列表")
async def get_patients(
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patients = await patient_service.get_by_user_id(current_user["id"])
    return [PatientResponse.model_validate(p) for p in patients]


@router.get("/patients/{patient_id}", response_model=PatientResponse, summary="获取就诊人详情")
async def get_patient_detail(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patient = await patient_service.get_by_id_and_user(patient_id, current_user["id"])
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="就诊人不存在，请检查后重试")
    return PatientResponse.model_validate(patient)


@router.post("/patients", response_model=PatientResponse, summary="添加就诊人")
async def add_patient(
    data: PatientCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patient = await patient_service.create(current_user["id"], data)
    return PatientResponse.model_validate(patient)


@router.put("/patients/{patient_id}", response_model=PatientResponse, summary="更新就诊人")
async def update_patient(
    patient_id: str,
    data: PatientUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    patient_service = PatientService(db)
    patient = await patient_service.update(patient_id, current_user["id"], data)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="就诊人不存在，请检查后重试")
    return PatientResponse.model_validate(patient)


@router.delete("/patients/{patient_id}", summary="删除就诊人")
async def delete_patient(
    patient_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    patient_service = PatientService(db)
    success = await patient_service.delete(patient_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="就诊人不存在，请检查后重试")
    return {"message": "删除成功"}
