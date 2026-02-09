from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from app.db.session import get_db
from app.api.deps import get_current_admin, require_permission, check_store_access
from app.schemas.store import (
    StoreCreate, StoreUpdate, StoreResponse, StoreListResponse, StoreQuery,
    StoreWechatConfigUpdate, StoreWechatConfigResponse
)
from app.schemas.department import DepartmentResponse
from app.schemas.admin import AdminListResponse
from app.schemas.response import PageResponse
from app.services.store_service import StoreService
from app.core.config import settings

router = APIRouter()


# ==================== 公开接口（无需登录） ====================

@router.get("/by-code/{code}", response_model=StoreResponse, summary="获取门店")
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


@router.get("/check-unique", summary="检查唯一性")
async def check_unique(
    field: str = Query(..., pattern="^(name|code)$", description="检查字段: name 或 code"),
    value: str = Query(..., min_length=1, description="字段值"),
    exclude_id: Optional[str] = Query(None, description="排除的门店ID（编辑时使用）"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
        exists = await service.check_name_exists(value, exclude_id)
    else:  # field == "code"
        exists = await service.check_code_exists(value, exclude_id)
    
    return {"exists": exists}


# ==================== 需要登录的接口 ====================

@router.get("", response_model=PageResponse[StoreListResponse], summary="获取门店列表")
async def get_stores(
    keyword: Optional[str] = None,
    status: Optional[int] = None,
    city: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
            store = await service.get_by_id(store_id)
            if store:
                stores_result.append(StoreListResponse(
                    id=store.id,
                    name=store.name,
                    code=store.code,
                    address=store.address,
                    phone=store.phone,
                    logo=store.logo,
                    theme_style=store.theme_style,
                    status=store.status,
                    department_count=await service.get_department_count(store.id),
                    created_at=store.created_at
                ))
        return PageResponse(data=stores_result, total=len(stores_result), page=1, page_size=page_size)
    
    # 超级管理员可以看到所有门店
    stores, total = await service.get_list(query)
    
    # 获取每个门店的科室数量
    result = []
    for store in stores:
        dept_count = await service.get_department_count(store.id)
        result.append(StoreListResponse(
            id=store.id,
            name=store.name,
            code=store.code,
            address=store.address,
            phone=store.phone,
            logo=store.logo,
            theme_style=store.theme_style,
            status=store.status,
            department_count=dept_count,
            created_at=store.created_at
        ))
    
    return PageResponse(
        data=result,
        total=total,
        page=page,
        page_size=page_size
    )


@router.get("/all", response_model=List[StoreResponse], summary="获取所有门店")
async def get_all_stores(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取所有营业中的门店（下拉选择用）"""
    service = StoreService(db)
    
    # 超级管理员可以看到所有门店
    if current_admin.get("is_super_admin"):
        stores = await service.get_all_active()
        return [StoreResponse.model_validate(s) for s in stores]
    
    # 非超管只能看到自己绑定的门店
    store_ids = current_admin.get("store_ids") or []
    result = []
    for sid in store_ids:
        store = await service.get_by_id(sid)
        if store and store.status == 1:
            result.append(StoreResponse.model_validate(store))
    return result


@router.get("/{store_id}", response_model=StoreResponse, summary="获取门店详情")
async def get_store(
    store_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取门店详情"""
    # 权限检查：超级管理员可访问任意门店，其他用户只能访问绑定的门店
    if not check_store_access(current_admin, store_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="您无权访问此门店"
        )
    
    service = StoreService(db)
    store = await service.get_by_id(store_id)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在，请检查后重试"
        )
    
    return StoreResponse.model_validate(store)


@router.post("", response_model=StoreResponse, summary="创建门店")
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
        store = await service.create(data)
        return StoreResponse.model_validate(store)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=str(e)
        )


@router.put("/{store_id}", response_model=StoreResponse, summary="更新门店")
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
        store = await service.update(store_id, data)
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


@router.delete("/{store_id}", summary="删除门店")
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
        success = await service.delete(store_id)
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


@router.patch("/{store_id}/status", summary="更新门店状态")
async def update_store_status(
    store_id: str,
    new_status: int = Query(..., ge=0, le=2, alias="status", description="状态: 0-停业 1-营业 2-禁用"),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
    current_store = await service.get_by_id(store_id)
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
    
    store = await service.update_status(store_id, new_status)
    
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, 
            detail="门店不存在，请检查后重试"
        )
    
    return {"message": "状态更新成功"}


@router.get("/{store_id}/departments", response_model=List[DepartmentResponse], summary="获取科室列表")
async def get_store_departments(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
    store = await service.get_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    departments = await service.get_departments(store_id)
    return [DepartmentResponse.model_validate(d) for d in departments]


@router.put("/{store_id}/departments/batch", summary="批量绑定科室")
async def batch_bind_departments(
    store_id: str,
    department_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
        count = await service.batch_bind_departments(store_id, department_ids)
        return {"message": "绑定成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{store_id}/admins", response_model=List[AdminListResponse], summary="获取管理员列表")
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
    store = await service.get_by_id(store_id)
    if not store:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="门店不存在，请检查后重试"
        )
    
    admins = await service.get_admins(store_id)
    return [AdminListResponse.model_validate(a) for a in admins]


@router.put("/{store_id}/admins/batch", summary="批量绑定管理员")
async def batch_bind_admins(
    store_id: str,
    admin_ids: List[str],
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
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
        count = await service.batch_bind_admins(store_id, admin_ids)
        return {"message": "分配成功", "count": count}
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


# ==================== 门店微信配置 ====================

@router.get("/{store_id}/wechat-config", response_model=StoreWechatConfigResponse, summary="获取微信配置")
async def get_store_wechat_config(
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
    return StoreWechatConfigResponse(
        app_id=store.wechat_app_id or '',
        app_secret='******' if store.wechat_app_secret else '',
        mch_id=store.wechat_mch_id or '',
        api_key='******' if store.wechat_api_key else '',
        notify_url=store.wechat_notify_url or ''
    )


@router.put("/{store_id}/wechat-config", summary="更新微信配置")
async def update_store_wechat_config(
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
    
    return {"message": "微信配置更新成功"}


# ==================== 签到二维码 ====================

@router.get("/{store_id}/checkin-qrcode", summary="获取签到二维码")
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
