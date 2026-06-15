"""小程序平台 - 构建发布路由 (BuildJob + ReleaseJob)"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common.deps import get_current_admin, get_tenant_from_admin
from app.db.session import get_db
from app.modules.miniapp_platform.service_instance import BuildJobService, ReleaseJobService
from app.schemas.miniapp_template import (
    BuildJobCreate,
    BuildJobListResponse,
    BuildJobResponse,
    ReleaseJobCreate,
    ReleaseJobListResponse,
    ReleaseJobResponse,
)
from app.schemas.response import PageResponse

router = APIRouter()


# ==================== BuildJob (构建任务) ====================

@router.get("/build-jobs", response_model=PageResponse[BuildJobListResponse], summary="获取构建任务列表")
async def get_build_jobs(
    instance_id: str | None = Query(None, description="小程序实例ID"),
    status: str | None = Query(None, description="任务状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: dict | None = Depends(get_tenant_from_admin)
):
    """获取构建任务列表

    平台管理员可以查看所有租户的构建任务。
    租户管理员只能查看自己租户的构建任务。
    """
    tenant_id = None if current_admin.get("is_super_admin") else (tenant["id"] if tenant else None)
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="未关联租户"
        )

    service = BuildJobService(db)

    jobs, total = await service.get_list(
        tenant_id=tenant_id,
        instance_id=instance_id,
        status=status,
        skip=(page - 1) * page_size,
        limit=page_size
    )

    result = []
    for job in jobs:
        result.append(BuildJobListResponse(
            id=job.id,
            miniapp_instance_id=job.miniapp_instance_id,
            miniapp_instance_name=job.miniapp_instance.name if job.miniapp_instance else None,
            template_version=job.template_version.version if job.template_version else None,
            trigger_source=job.trigger_source,
            status=job.status,
            started_at=job.started_at,
            finished_at=job.finished_at,
            created_at=job.created_at,
        ))

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/build-jobs/{job_id}", response_model=BuildJobResponse, summary="获取构建任务详情")
async def get_build_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取构建任务详情"""
    service = BuildJobService(db)
    job = await service.get_by_id(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="构建任务不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的任务
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and job.tenant_id != admin_tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权访问此构建任务"
            )

    return BuildJobResponse.model_validate(job)


@router.post("/build-jobs", response_model=BuildJobResponse, summary="创建构建任务")
async def create_build_job(
    data: BuildJobCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: dict | None = Depends(get_tenant_from_admin)
):
    """创建构建任务

    租户管理员可以为自己租户的实例创建构建任务。
    """
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = BuildJobService(db)

    try:
        job = await service.create(
            tenant_id=tenant_id,
            data=data,
            operator_id=current_admin.get("id")
        )
        return BuildJobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== ReleaseJob (发布任务) ====================

@router.get("/release-jobs", response_model=PageResponse[ReleaseJobListResponse], summary="获取发布任务列表")
async def get_release_jobs(
    instance_id: str | None = Query(None, description="小程序实例ID"),
    action: str | None = Query(None, description="动作类型"),
    status: str | None = Query(None, description="任务状态"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: dict | None = Depends(get_tenant_from_admin)
):
    """获取发布任务列表

    平台管理员可以查看所有租户的发布任务。
    租户管理员只能查看自己租户的发布任务。
    """
    # 由于 ReleaseJob 模型没有 tenant_id 字段，我们需要通过 miniapp_instance 来过滤
    # 这里暂时返回所有任务，在服务层进行过滤
    service = ReleaseJobService(db)

    # 获取当前租户
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        # 平台管理员查看所有
        jobs, total = await service.get_list(
            tenant_id=None,  # 不需要租户过滤
            instance_id=instance_id,
            action=action,
            status=status,
            skip=(page - 1) * page_size,
            limit=page_size
        )

        result = []
        for job in jobs:
            result.append(ReleaseJobListResponse(
                id=job.id,
                miniapp_instance_id=job.miniapp_instance_id,
                miniapp_instance_name=job.miniapp_instance.name if job.miniapp_instance else None,
                action=job.action,
                target_version=job.target_version,
                status=job.status,
                result=job.result,
                created_at=job.created_at,
            ))

        return PageResponse(
            data=result,
            total=total,
            page=page,
            page_size=page_size
        )

    # 对于租户管理员，需要在获取结果后进行过滤
    jobs, total = await service.get_list(
        tenant_id=None,
        instance_id=instance_id,
        action=action,
        status=status,
        skip=0,  # 先获取所有，然后过滤
        limit=1000
    )

    # 过滤出属于当前租户的任务
    filtered_jobs = []
    for job in jobs:
        if job.miniapp_instance and hasattr(job.miniapp_instance, 'tenant_id'):
            if job.miniapp_instance.tenant_id == tenant_id:
                filtered_jobs.append(job)

    # 手动分页
    filtered_total = len(filtered_jobs)
    start = (page - 1) * page_size
    end = start + page_size
    paginated_jobs = filtered_jobs[start:end]

    result = []
    for job in paginated_jobs:
        result.append(ReleaseJobListResponse(
            id=job.id,
            miniapp_instance_id=job.miniapp_instance_id,
            miniapp_instance_name=job.miniapp_instance.name if job.miniapp_instance else None,
            action=job.action,
            target_version=job.target_version,
            status=job.status,
            result=job.result,
            created_at=job.created_at,
        ))

    return PageResponse(
        data=result,
        total=filtered_total,
        page=page,
        page_size=page_size
    )


@router.get("/release-jobs/{job_id}", response_model=ReleaseJobResponse, summary="获取发布任务详情")
async def get_release_job(
    job_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin)
):
    """获取发布任务详情"""
    service = ReleaseJobService(db)
    job = await service.get_by_id(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="发布任务不存在"
        )

    # 权限检查：非平台管理员只能查看自己租户的任务
    if not current_admin.get("is_super_admin"):
        admin_tenant_id = current_admin.get("tenant_id")
        if admin_tenant_id and job.miniapp_instance and hasattr(job.miniapp_instance, 'tenant_id'):
            if job.miniapp_instance.tenant_id != admin_tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="您无权访问此发布任务"
                )

    return ReleaseJobResponse.model_validate(job)


@router.post("/release-jobs", response_model=ReleaseJobResponse, summary="创建发布任务")
async def create_release_job(
    data: ReleaseJobCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant: dict | None = Depends(get_tenant_from_admin)
):
    """创建发布任务

    租户管理员可以为自己租户的实例创建发布任务。
    """
    if not current_admin.get("is_super_admin"):
        if not tenant:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="未关联租户"
            )
        tenant_id = tenant["id"]
    else:
        tenant_id = tenant["id"] if tenant else None
        if not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="需要指定租户"
            )

    service = ReleaseJobService(db)

    try:
        job = await service.create(
            tenant_id=tenant_id,
            data=data,
            operator_id=current_admin.get("id")
        )
        return ReleaseJobResponse.model_validate(job)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
