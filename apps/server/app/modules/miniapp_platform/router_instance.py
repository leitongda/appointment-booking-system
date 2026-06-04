"""小程序平台 - 实例管理路由 (MiniappInstance CRUD + activate/archive)"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional

from app.db.session import get_db
from app.common.deps import get_current_admin, get_tenant_from_admin
from app.modules.miniapp_platform.schemas import (
    MiniappInstanceCreate, MiniappInstanceUpdate, MiniappInstanceResponse,
    MiniappInstanceListResponse, MiniappInstanceQuery,
)
from app.modules.miniapp_platform.service_instance import MiniappInstanceService
from app.schemas.response import PageResponse

router = APIRouter()


# ==================== MiniappInstance (小程序实例) ====================

@router.get("/instances", response_model=PageResponse[MiniappInstanceListResponse], summary="获取小程序实例列表")
async def get_miniapp_instances(
    keyword: Optional[str] = None,
    status: Optional[int] = Query(None, ge=0, le=2),
    template_id: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """获取小程序实例列表

    平台管理员可以查看所有租户的实例。
    租户管理员只能查看自己租户的实例。
    """
    service = MiniappInstanceService(db)

    # 平台管理员可以指定任意租户，租户管理员只能查看自己的租户
    tenant_id = None if current_admin.get("is_super_admin") else (tenant["id"] if tenant else None)

    query = MiniappInstanceQuery(
        keyword=keyword,
        status=status,
        template_id=template_id,
        page=page,
        page_size=page_size
    )

    instances, total = await service.get_list(tenant_id=tenant_id, query=query)

    result = []
    for instance in instances:
        result.append(MiniappInstanceListResponse(
            id=instance.id,
            code=instance.code,
            name=instance.name,
            app_id=instance.app_id,
            status=instance.status,
            template_name=instance.template.name if instance.template else None,
            template_version=instance.template_version.version if instance.template_version else None,
            store_name=instance.default_store.name if instance.default_store else None,
            payment_profile_name=instance.default_payment_profile.name if instance.default_payment_profile else None,
            created_at=instance.created_at,
        ))

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.post("/instances", response_model=MiniappInstanceResponse, summary="创建小程序实例")
async def create_miniapp_instance(
    data: MiniappInstanceCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """创建小程序实例

    平台管理员可以为任意租户创建实例。
    租户管理员只能为自己租户创建实例。
    """
    # 非平台管理员需要关联租户
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        # 平台管理员需要从上下文获取租户ID（如果有的话）
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = MiniappInstanceService(db)

    try:
        instance = await service.create(data, tenant_id, operator_id=current_admin.get("id"))
        # 重新加载关联
        instance = await service.get_by_id(instance.id)
        return MiniappInstanceResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/instances/{instance_id}", response_model=MiniappInstanceResponse, summary="获取小程序实例详情")
async def get_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取小程序实例详情"""
    service = MiniappInstanceService(db)
    instance = await service.get_by_id(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的实例
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此实例"
            )

    return MiniappInstanceResponse.model_validate(instance)


@router.put("/instances/{instance_id}", response_model=MiniappInstanceResponse, summary="更新小程序实例")
async def update_miniapp_instance(
    instance_id: str,
    data: MiniappInstanceUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """更新小程序实例"""
    service = MiniappInstanceService(db)
    instance = await service.get_by_id(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    # 权限检查：非平台管理员只能修改自己租户的实例
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此实例"
            )

    try:
        instance = await service.update(instance_id, data, operator_id=current_admin.get("id"))
        # 重新加载关联
        instance = await service.get_by_id(instance.id)
        return MiniappInstanceResponse.model_validate(instance)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/instances/{instance_id}", summary="删除小程序实例")
async def delete_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """删除小程序实例（归档）"""
    service = MiniappInstanceService(db)
    instance = await service.get_by_id(instance_id)

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    # 权限检查：非平台管理员只能删除自己租户的实例
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权删除此实例"
            )

    try:
        success = await service.delete(instance_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="小程序实例不存在"
            )
        return {"message": "删除成功"}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/instances/{instance_id}/activate", summary="激活小程序实例")
async def activate_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """激活小程序实例"""
    service = MiniappInstanceService(db)

    # 权限检查
    instance = await service.get_by_id(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权操作此实例"
            )

    instance = await service.update_status(instance_id, 1)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    return {"message": "实例已激活"}


@router.post("/instances/{instance_id}/archive", summary="归档小程序实例")
async def archive_miniapp_instance(
    instance_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """归档小程序实例"""
    service = MiniappInstanceService(db)

    # 权限检查
    instance = await service.get_by_id(instance_id)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and instance.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权操作此实例"
            )

    instance = await service.update_status(instance_id, 2)
    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="小程序实例不存在"
        )

    return {"message": "实例已归档"}


@router.get("/instances/check-unique", summary="检查实例编码唯一性")
async def check_instance_code_unique(
    code: str = Query(None, min_length=1, max_length=50),
    app_id: str = Query(None, min_length=1, max_length=100),
    exclude_id: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: Optional[dict] = Depends(get_tenant_from_admin)
):
    """检查实例编码或AppID是否已存在"""
    # 非平台管理员需要关联租户
    if not current_admin.get("is_super_admin"):
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
    else:
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = MiniappInstanceService(db)
    result = {}

    if code:
        result["code_exists"] = await service.check_code_exists(code, tenant_id, exclude_id)

    if app_id:
        result["app_id_exists"] = await service.check_app_id_exists(app_id, tenant_id, exclude_id)

    return result
