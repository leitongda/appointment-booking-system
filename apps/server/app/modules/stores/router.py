
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_store_access,
    get_current_admin,
    require_admin_tenant_anchor,
    require_permission,
    resolve_admin_tenant_anchor,
)
from app.core.config import settings
from app.db.session import get_db
from app.modules.stores.service import StoreService
from app.schemas.admin import AdminListResponse
from app.schemas.department import DepartmentResponse
from app.schemas.response import PageResponse
from app.schemas.store import (
    StoreCreate,
    StoreListResponse,
    StoreQuery,
    StoreResponse,
    StoreUpdate,
    StoreWechatConfigResponse,
    StoreWechatConfigUpdate,
)

router = APIRouter()


# ==================== 公开接口（无需登录） ====================

@router.get(
    "/by-code/{code}",
    response_model=StoreResponse,
    summary="获取门店",
    description="""
    通过门店编码获取门店信息（公开接口，无需登录）。

    **适用场景**：患者端 H5/小程序初始化时验证门店。

    **参数说明**：
    - code: 门店编码（路径参数）

    **业务规则**：
    - 已停业（status != 1）的门店返回 400 错误
    """,
)
async def get_store_by_code(
    code: str,
    db: AsyncSession = Depends(get_db)
):
    """通过编码获取门店（公开接口，无需登录）
    
    用于患者端H5/小程序初始化时验证门店
    """
    service = StoreService(db)
    store = await service.get_by_code(code)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    if store.status != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="门店已停业，暂不可用"
        )
    
    return StoreResponse.model_validate(store)


@router.get(
    "/check-unique",
    summary="检查唯一性",
    description="""
    检查门店名称或编码是否已存在，用于前端表单实时校验。

    **参数说明**：
    - field: 检查字段，可选 "name"（名称）或 "code"（编码）
    - value: 字段值
    - exclude_id: 编辑时排除当前门店ID（可选）

    **返回数据**：
    - { "exists": bool } - 是否已存在
    """,
)
async def check_unique(
    field: str = Query(..., pattern="^(name|code)$", description="检查字段: name 或 code"),
    value: str = Query(..., min_length=1, description="字段值"),
    exclude_id: str | None = Query(None, description="排除的门店ID（编辑时使用）"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """检查门店名称或编码是否已存在
    
    用于前端表单实时验证唯一性
    
    Args:
        field: 检查字段，可选 "name" 或 "code"
        value: 字段值
        exclude_id: 编辑时排除当前门店ID
        
    Returns:
        { "exists": bool } - 是否已存在
    """
    service = StoreService(db)
    
    if field == "name":
        exists = await service.check_name_exists(value, exclude_id, tenant_id=tenant_anchor)
    else:  # field == "code"
        exists = await service.check_code_exists(value, exclude_id, tenant_id=tenant_anchor)
    
    return {"exists": exists}


# ==================== 需要登录的接口 ====================

@router.get(
    "",
    response_model=PageResponse[StoreListResponse],
    summary="获取门店列表",
    description="""
    获取门店列表（管理端），支持分页和筛选。

    **支持筛选条件**：
    - keyword: 关键字搜索（名称/地址）
    - status: 按状态筛选（0=停业 1=营业 2=禁用）
    - city: 按城市筛选

    **数据隔离**：
    - 门店管理员只能看到自己关联的门店（不分页，直接返回全量）
    - 超级管理员可看到所有门店（分页）

    **返回数据**：
    - 包含每个门店的科室数量（department_count）
    """,
)
async def get_stores(
    keyword: str | None = None,
    status: int | None = None,
    city: str | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取门店列表"""
    service = StoreService(db)
    query = StoreQuery(
        keyword=keyword,
        status=status,
        city=city,
        page=page,
        page_size=page_size
    )
    
    # 门店管理员只能看到自己关联的门店（支持多门店）
    store_ids = current_admin.get("store_ids")
    if store_ids and not current_admin.get("is_super_admin"):
        # 如果是门店管理员，只返回关联的门店
        stores_result = []
        for store_id in store_ids:
            store = await service.get_by_id(store_id, tenant_id=tenant_anchor)
            if store:
                stores_result.append(store)

        # 批量获取科室数量（1 次查询替代 N 次）
        dept_counts = await service.get_department_counts_batch(
            [s.id for s in stores_result], tenant_id=tenant_anchor
        )
        result = [
            StoreListResponse(
                id=store.id,
                name=store.name,
                code=store.code,
                address=store.address,
                phone=store.phone,
                logo=store.logo,
                theme_style=store.theme_style,
                status=store.status,
                department_count=dept_counts.get(store.id, 0),
                created_at=store.created_at,
            )
            for store in stores_result
        ]
        return PageResponse(data=result, total=len(result), page=1, page_size=page_size)

    # 超级管理员可以看到所有门店
    stores_anchor, total = await service.get_list(query, tenant_id=tenant_anchor)

    # 批量获取科室数量（1 次查询替代 N 次）
    dept_counts = await service.get_department_counts_batch(
        [s.id for s in stores_anchor], tenant_id=tenant_anchor
    )
    result = [
        StoreListResponse(
            id=store.id,
            name=store.name,
            code=store.code,
            address=store.address,
            phone=store.phone,
            logo=store.logo,
            theme_style=store.theme_style,
            status=store.status,
            department_count=dept_counts.get(store.id, 0),
            created_at=store.created_at,
        )
        for store in stores_anchor
    ]

    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/all",
    response_model=list[StoreResponse],
    summary="获取所有门店",
    description="""
    获取所有营业中的门店列表（不分页），用于管理后台下拉选择等场景。

    **数据隔离**：
    - 超级管理员可看到所有营业中的门店
    - 非超管只能看到自己绑定且营业中的门店
    """,
)
async def get_all_stores(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取所有营业中的门店（下拉选择用）"""
    service = StoreService(db)
    
    # 超级管理员可以看到所有门店
    if current_admin.get("is_super_admin"):
        stores = await service.get_all_active(tenant_id=tenant_anchor)
        return [StoreResponse.model_validate(s) for s in stores]
    
    # 非超管只能看到自己绑定的门店
    store_ids = current_admin.get("store_ids") or []
    result = []
    for sid in store_ids:
        store = await service.get_by_id(sid, tenant_id=tenant_anchor)
        if store and store.status == 1:
            result.append(StoreResponse.model_validate(store))
    return result


@router.get(
    "/{store_id}",
    response_model=StoreResponse,
    summary="获取门店详情",
    description="""
    获取门店详情（管理端接口）。

    **权限要求**：管理员登录，受门店访问控制。
    - 超级管理员可访问任意门店
    - 门店管理员只能访问绑定的门店

    **参数说明**：
    - store_id: 门店ID（路径参数）
    """,
)
async def get_store(
    store_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取门店详情"""
    # 权限检查：超级管理员可访问任意门店，其他用户只能访问绑定的门店
    if not check_store_access(current_admin, store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问此门店"
        )
    
    service = StoreService(db)
    store = await service.get_by_id(store_id, tenant_id=tenant_anchor)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在，请检查后重试"
        )
    
    return StoreResponse.model_validate(store)


@router.post(
    "",
    response_model=StoreResponse,
    summary="创建门店",
    description="""
    创建新门店。

    **权限要求**：管理员权限（store:create），仅超级管理员可操作。

    **业务规则**：
    - 门店名称和编码必须唯一
    - 创建后可绑定科室和管理员
    """,
)
async def create_store(
    data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("store:create"))
):
    """创建门店（仅超级管理员）"""
    # 只有超级管理员可以创建门店
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="门店管理员无权创建门店，请联系超级管理员"
        )
    
    service = StoreService(db)
    
    try:
        store = await service.create(
            data, tenant_id=resolve_admin_tenant_anchor(current_admin)
        )
        return StoreResponse.model_validate(store)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.put(
    "/{store_id}",
    response_model=StoreResponse,
    summary="更新门店",
    description="""
    更新门店信息。

    **权限要求**：管理员权限（store:update），受门店访问控制。
    - 超级管理员可更新任意门店
    - 门店管理员只能更新绑定的门店
    """,
)
async def update_store(
    store_id: str,
    data: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("store:update"))
):
    """更新门店"""
    # 权限检查：超级管理员可更新任意门店，其他用户只能更新绑定的门店
    if not check_store_access(current_admin, store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权修改此门店"
        )
    
    service = StoreService(db)
    
    try:
        store = await service.update(
            store_id, data, tenant_id=resolve_admin_tenant_anchor(current_admin)
        )
        if not store:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="门店不存在，请检查后重试"
            )
        return StoreResponse.model_validate(store)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.delete(
    "/{store_id}",
    summary="删除门店",
    description="""
    删除门店（仅超级管理员）。

    **权限要求**：管理员权限（store:delete），仅超级管理员可操作。

    **业务规则**：
    - 存在关联科室或医生的门店可能拒绝删除（由 service 层判断）
    """,
)
async def delete_store(
    store_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("store:delete"))
):
    """删除门店（仅超级管理员）"""
    # 只有超级管理员可以删除门店
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="门店管理员无权删除门店，请联系超级管理员"
        )
    
    service = StoreService(db)
    
    try:
        success = await service.delete(
            store_id, tenant_id=resolve_admin_tenant_anchor(current_admin)
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, 
                detail="门店不存在，请检查后重试"
            )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )
    
    return {"message": "删除成功"}


@router.patch(
    "/{store_id}/status",
    summary="更新门店状态",
    description="""
    更新门店营业状态。

    **参数说明**：
    - store_id: 门店ID（路径参数）
    - status: 新状态值（0=停业 1=营业 2=禁用）

    **权限规则**：
    - 停业(0)/营业(1): 门店管理员可操作（限本门店）
    - 禁用(2): 仅超级管理员可操作，禁用后该门店所有人员无法登录
    - 从禁用状态恢复: 仅超级管理员可操作
    """,
)
async def update_store_status(
    store_id: str,
    new_status: int = Query(..., ge=0, le=2, alias="status", description="状态: 0-停业 1-营业 2-禁用"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """更新门店状态
    
    - 0: 停业（门店管理员可操作）
    - 1: 营业（门店管理员可操作）
    - 2: 禁用（仅超级管理员可操作，禁用后该门店所有人员无法登录）
    """
    is_super_admin = current_admin.get("is_super_admin")
    
    # 禁用/启用操作仅超级管理员可执行
    if new_status == 2 and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="禁用门店需要超级管理员权限"
        )
    
    # 检查当前门店状态，如果是从禁用状态恢复，也需要超级管理员权限
    service = StoreService(db)
    current_store = await service.get_by_id(store_id, tenant_id=tenant_anchor)
    if current_store and current_store.status == 2 and not is_super_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="启用门店需要超级管理员权限"
        )
    
    # 门店管理员只能更新自己绑定门店的状态（非禁用操作）
    if not is_super_admin and not check_store_access(current_admin, store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权修改此门店状态"
        )
    
    store = await service.update_status(
        store_id, new_status, tenant_id=tenant_anchor
    )
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在，请检查后重试"
        )
    
    return {"message": "状态更新成功"}


@router.get(
    "/{store_id}/departments",
    response_model=list[DepartmentResponse],
    summary="获取科室列表",
    description="""
    获取门店已绑定的科室列表。

    **权限要求**：管理员登录，受门店访问控制。

    **参数说明**：
    - store_id: 门店ID（路径参数）
    """,
)
async def get_store_departments(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取门店已绑定的科室列表"""
    # 权限检查：超级管理员可访问任意门店，其他用户只能访问绑定的门店
    if not check_store_access(current_admin, store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问此门店"
        )
    
    service = StoreService(db)
    
    # 验证门店是否存在
    store = await service.get_by_id(store_id, tenant_id=tenant_anchor)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    departments = await service.get_departments(store_id, tenant_id=tenant_anchor)
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.put(
    "/{store_id}/departments/batch",
    summary="批量绑定科室",
    description="""
    批量绑定科室到门店（全量覆盖模式）。

    **权限要求**：管理员登录，受门店访问控制。

    **参数说明**：
    - store_id: 门店ID（路径参数）
    - Body: 科室ID列表（数组）

    **业务规则**：
    - 传入的科室ID列表会完全替换当前绑定关系
    - 无效的科室ID会被 service 层校验拒绝
    """,
)
async def batch_bind_departments(
    store_id: str,
    department_ids: list[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """批量绑定科室到门店"""
    # 权限检查：超级管理员可操作任意门店，其他用户只能操作绑定的门店
    if not check_store_access(current_admin, store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权操作此门店"
        )
    
    service = StoreService(db)
    
    try:
        count = await service.batch_bind_departments(
            store_id, department_ids, tenant_id=tenant_anchor
        )
        return {"message": "绑定成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get(
    "/{store_id}/admins",
    response_model=list[AdminListResponse],
    summary="获取管理员列表",
    description="""
    获取门店已绑定的管理员列表。

    **权限要求**：仅超级管理员可查看。

    **参数说明**：
    - store_id: 门店ID（路径参数）
    """,
)
async def get_store_admins(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店已绑定的管理员列表"""
    # 仅超级管理员可操作
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可查看门店用户"
        )
    
    service = StoreService(db)
    
    # 验证门店是否存在
    store = await service.get_by_id(store_id, tenant_id=tenant_anchor)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    admins = await service.get_admins(store_id, tenant_id=tenant_anchor)
    return [AdminListResponse.model_validate(a) for a in admins]


@router.put(
    "/{store_id}/admins/batch",
    summary="批量绑定管理员",
    description="""
    批量绑定管理员到门店（全量覆盖模式）。

    **权限要求**：仅超级管理员可操作。

    **参数说明**：
    - store_id: 门店ID（路径参数）
    - Body: 管理员ID列表（数组）

    **业务规则**：
    - 传入的管理员ID列表会完全替换当前绑定关系
    - 无效的管理员ID会被 service 层校验拒绝
    """,
)
async def batch_bind_admins(
    store_id: str,
    admin_ids: list[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """批量绑定管理员到门店"""
    # 仅超级管理员可操作
    if not current_admin.get("is_super_admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="仅超级管理员可分配用户"
        )
    
    service = StoreService(db)
    
    try:
        count = await service.batch_bind_admins(
            store_id, admin_ids, tenant_id=tenant_anchor
        )
        return {"message": "分配成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== 门店微信配置 (DEPRECATED) ====================
# These endpoints are deprecated.  Migrate to:
#   - MiniappInstance (POST /miniapp-platform/instances) for app_id/app_secret
#   - PaymentProfile (POST /miniapp-platform/payment-profiles) for payment config
#   - PaymentRoute (store-level routing) for store-to-profile binding

_DEPRECATION_HEADER = {
    "Deprecation": "true",
    "Link": '</api/v1/miniapp-platform/payment-profiles>; rel="successor-version"',
}

@router.get(
    "/{store_id}/wechat-config",
    response_model=StoreWechatConfigResponse,
    summary="[DEPRECATED] 获取微信配置",
    description="""
    获取门店的微信公众号/小程序配置信息。

    **DEPRECATED** — 此接口已废弃。请迁移到 miniapp-platform 管理 API:
    - 小程序配置: POST /miniapp-platform/instances
    - 支付配置: POST /miniapp-platform/payment-profiles
    - 门店路由: POST /miniapp-platform/payment-routes

    **权限要求**：管理员登录，受门店访问控制。

    **安全说明**：
    - app_secret 和 api_key 等敏感字段返回掩码处理（显示为 ******）
    - 用于管理后台微信配置页面回显
    """,
)
async def get_store_wechat_config(
    response: Response,
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店微信配置
    
    权限：
    - 超级管理员：可获取任意门店配置
    - 门店管理员：只能获取自己关联门店的配置
    """
    # 权限检查
    is_super_admin = current_admin.get("is_super_admin")
    admin_store_ids = current_admin.get("store_ids") or []
    
    if not is_super_admin and store_id not in admin_store_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问此门店的微信配置"
        )
    
    service = StoreService(db)
    store = await service.get_by_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在"
        )
    
    # 返回配置，敏感字段掩码处理
    for k, v in _DEPRECATION_HEADER.items():
        response.headers[k] = v
    return StoreWechatConfigResponse(
        app_id=store.wechat_app_id or '',
        app_secret='******' if store.wechat_app_secret else '',
        mch_id=store.wechat_mch_id or '',
        api_key='******' if store.wechat_api_key else '',
        notify_url=store.wechat_notify_url or ''
    )


@router.put(
    "/{store_id}/wechat-config",
    summary="[DEPRECATED] 更新微信配置",
    description="""
    更新门店的微信配置信息。

    **DEPRECATED** — 此接口已废弃。请迁移到 miniapp-platform 管理 API:
    - 小程序配置: POST /miniapp-platform/instances
    - 支付配置: POST /miniapp-platform/payment-profiles
    - 门店路由: POST /miniapp-platform/payment-routes

    **权限要求**：
    - 超级管理员：可更新任意门店
    - 门店管理员：需有 settings:wechat 或 settings:edit 权限，且只能更新本门店

    **安全说明**：
    - 传入值为 ****** 的字段会被忽略（前端未修改时不提交真实值）
    - 只有传入非掩码值时才会更新对应字段
    """,
)
async def update_store_wechat_config(
    response: Response,
    store_id: str,
    data: StoreWechatConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """更新门店微信配置
    
    权限：
    - 超级管理员：可更新任意门店配置
    - 门店管理员（有 settings:wechat 权限）：只能更新自己关联门店的配置
    """
    # 权限检查
    is_super_admin = current_admin.get("is_super_admin")
    admin_store_ids = current_admin.get("store_ids") or []
    permissions = current_admin.get("permissions") or []
    
    if not is_super_admin:
        if store_id not in admin_store_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您无权修改此门店的微信配置"
            )
        # 检查是否有微信配置权限
        if "settings:wechat" not in permissions and "settings:edit" not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="您没有修改微信配置的权限"
            )
    
    service = StoreService(db)
    store = await service.get_by_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在"
        )
    
    # 更新配置
    update_data = {}
    if data.app_id is not None:
        update_data['wechat_app_id'] = data.app_id
    if data.app_secret is not None and data.app_secret != '******':
        update_data['wechat_app_secret'] = data.app_secret
    if data.mch_id is not None:
        update_data['wechat_mch_id'] = data.mch_id
    if data.api_key is not None and data.api_key != '******':
        update_data['wechat_api_key'] = data.api_key
    if data.notify_url is not None:
        update_data['wechat_notify_url'] = data.notify_url
    
    if update_data:
        await service.update_wechat_config(store_id, update_data)

    for k, v in _DEPRECATION_HEADER.items():
        response.headers[k] = v
    return {"message": "微信配置更新成功"}


# ==================== 签到二维码 ====================

@router.get(
    "/{store_id}/checkin-qrcode",
    summary="获取签到二维码",
    description="""
    获取门店签到二维码内容（管理端获取，用于生成二维码图片供患者扫描）。

    **权限要求**：超级管理员或门店关联管理员。

    **参数说明**：
    - store_id: 门店ID（路径参数）

    **返回数据**：
    - storeId: 门店ID
    - storeName: 门店名称
    - qrcodeContent: 二维码内容（格式：store-checkin:{store_id}）
    - description: 二维码使用说明
    """,
)
async def get_store_checkin_qrcode(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店签到二维码
    
    返回二维码内容（用于前端生成二维码图片）
    二维码内容格式: store-checkin:{store_id}
    """
    service = StoreService(db)
    store = await service.get_by_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    # 权限检查：超级管理员或门店关联管理员可以获取
    store_ids = current_admin.get("store_ids")
    if store_ids and not current_admin.get("is_super_admin"):
        if store_id not in store_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="无权限操作此门店"
            )
    
    # 生成签到二维码内容
    qrcode_content = f"store-checkin:{store_id}"
    
    return {
        "storeId": store_id,
        "storeName": store.name,
        "qrcodeContent": qrcode_content,
        "description": "请使用微信扫描此二维码进行签到"
    }
