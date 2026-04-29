"""密码管理相关端点"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin
from app.db.session import get_db
from app.modules.admin.schemas import ChangePasswordRequest, UpdateProfileRequest
from app.modules.admin.service_admins import AdminService

router = APIRouter()


@router.put("/me", response_model=None, summary="更新个人信息")
async def update_current_admin_profile(
    data: UpdateProfileRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    from app.modules.admin.helpers import build_admin_response

    service = AdminService(db)
    admin = await service.update(current_admin["id"], data.model_dump(exclude_unset=True))
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    admin = await service.get_by_id(current_admin["id"])
    return build_admin_response(admin)


@router.put("/me/change-password", summary="修改密码")
async def change_current_admin_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
):
    from app.core.security import get_password_hash, verify_password

    service = AdminService(db)
    admin = await service.get_by_id(current_admin["id"])
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="管理员不存在，请检查后重试")
    if not verify_password(data.old_password, admin.password_hash):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码错误，请重新输入")

    # 密码策略校验
    from app.modules.tenants.password_policy import get_tenant_password_policy, PasswordPolicyValidator
    policy = await get_tenant_password_policy(db, admin.tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(
        data.new_password,
        username=admin.username,
        phone=admin.phone,
    )
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="; ".join(errors))

    admin.password_hash = get_password_hash(data.new_password)
    await db.commit()
    return {"message": "密码修改成功"}
