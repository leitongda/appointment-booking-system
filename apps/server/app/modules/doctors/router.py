from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime

from app.db.session import get_db
from app.api.deps import get_current_admin, get_store_filter, check_store_access, get_current_doctor_by_token, require_permission
from app.models.doctor import Doctor
from app.schemas.doctor import DoctorCreate, DoctorUpdate, DoctorResponse, DoctorListResponse
from app.schemas.response import PageResponse
from app.modules.doctors.service import DoctorService
from app.core.security import create_access_token, create_refresh_token, verify_password
from app.core.config import settings
from app.utils.ip import get_client_ip
from app.modules.doctors.schemas import (
    BatchSortRequest,
    CheckUsernameRequest,
    CheckUsernameResponse,
    DoctorLoginRequest,
    DoctorLoginResponse,
    GenerateUsernameRequest,
    GenerateUsernameResponse,
)

router = APIRouter()


def doctor_to_response(doctor) -> DoctorResponse:
    """将医生模型转换为响应对象"""
    return DoctorResponse(
        id=doctor.id,
        user_id=doctor.user_id,
        store_id=doctor.store_id,
        store_name=doctor.store.name if doctor.store else None,
        department_id=doctor.department_id,
        department_name=doctor.department.name if doctor.department else None,
        name=doctor.name,
        username=doctor.username,
        phone=doctor.phone,
        gender=doctor.gender if doctor.gender is not None else 0,
        avatar=doctor.avatar,
        banner=doctor.banner,
        title=doctor.title,
        years_of_experience=doctor.years_of_experience or 0,
        education=doctor.education,
        graduate_school=doctor.graduate_school,
        license_number=doctor.license_number,
        license_image=doctor.license_image,
        honors=doctor.honors,
        schedule_desc=doctor.schedule_desc,
        max_daily_appointments=doctor.max_daily_appointments or 0,
        online_consult_enabled=doctor.online_consult_enabled or 0,
        online_consult_fee=doctor.online_consult_fee or 0,
        page_style=doctor.page_style or 1,
        promo_video=doctor.promo_video,
        tags=doctor.tags,
        specialty=doctor.specialty,
        introduction=doctor.introduction,
        is_recommended=doctor.is_recommended or 0,
        sort_order=doctor.sort_order or 0,
        status=doctor.status or 1,
        use_fee_template=doctor.use_fee_template or 0,
        created_at=doctor.created_at,
        updated_at=doctor.updated_at
    )


def doctor_to_list_response(doctor, has_available_slots: bool = False) -> DoctorListResponse:
    """将医生模型转换为列表响应对象
    
    Args:
        doctor: 医生模型对象
        has_available_slots: 是否有可预约号源
    """
    return DoctorListResponse(
        id=doctor.id,
        name=doctor.name,
        avatar=doctor.avatar,
        banner=doctor.banner,
        title=doctor.title,
        gender=doctor.gender if doctor.gender is not None else 0,
        store_id=doctor.store_id,
        store_name=doctor.store.name if doctor.store else None,
        department_id=doctor.department_id,
        department_name=doctor.department.name if doctor.department else None,
        specialty=doctor.specialty,
        is_recommended=doctor.is_recommended or 0,
        tags=doctor.tags,
        page_style=doctor.page_style or 1,
        has_available_slots=has_available_slots,
        status=doctor.status or 1
    )


@router.post(
    "/login",
    response_model=DoctorLoginResponse,
    summary="医生登录",
    description="""
    医生账号登录，支持手机号或账号密码方式。

    **业务规则**：
    - 账号被禁用（status != 1）时拒绝登录
    - 所属门店被禁用（store.status == 2）时拒绝登录
    - 登录成功后更新登录IP和最后登录时间
    - 返回 accessToken 和 refreshToken，有效期由系统配置控制

    **Token 说明**：
    - accessToken: 用于接口鉴权，payload 中 type=doctor
    - refreshToken: 用于刷新 accessToken
    """,
)
async def doctor_login(
    data: DoctorLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """医生登录（支持手机号或账号登录）"""
    service = DoctorService(db)
    doctor = await service.authenticate(data.phone, data.password)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号或密码错误，请检查后重试")
    
    if doctor.status != 1:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="账号已被禁用，请联系管理员")
    
    # 检查所属门店状态（status=2 表示禁用）
    if doctor.store and doctor.store.status == 2:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您所属的门店已被禁用，请联系管理员")
    
    # 更新登录信息
    client_ip = get_client_ip(request)
    await service.update_login_info(doctor.id, client_ip)
    
    # 生成Token
    access_token = create_access_token(data={"sub": doctor.id, "type": "doctor"})
    refresh_token = create_refresh_token(data={"sub": doctor.id, "type": "doctor"})
    
    return DoctorLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        doctor=doctor_to_response(doctor),
    )


@router.get(
    "/me",
    response_model=DoctorResponse,
    summary="获取当前医生信息",
    description="""
    获取当前登录医生的完整信息（医生端专用）。

    **权限要求**：需要医生 Token 认证。

    **返回数据**：
    - 包含医生基本信息、所属门店/科室、职称、排班描述等完整字段
    """,
)
async def get_current_doctor_info(
    doctor: Doctor = Depends(get_current_doctor_by_token),
):
    """获取当前登录医生信息"""
    return doctor_to_response(doctor)

@router.get(
    "",
    response_model=PageResponse[DoctorListResponse],
    summary="获取医生列表",
    description="""
    获取医生列表（管理端），支持分页和多条件筛选。

    **支持筛选条件**：
    - name: 按医生姓名模糊搜索
    - store_id: 按门店筛选
    - department_id: 按科室筛选
    - status: 按状态筛选（1=启用 0=禁用）

    **数据隔离**：
    - 门店管理员只能查看本门店的医生
    - 超级管理员可查看所有医生

    **返回数据**：
    - 包含 hasAvailableSlots 字段，标记该医生当前是否有可预约号源
    """,
)
async def get_doctors(
    name: Optional[str] = None,
    store_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[int] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取医生列表"""
    service = DoctorService(db)
    
    # 门店过滤：门店管理员只能看自己门店的医生
    store_filter = get_store_filter(current_admin)
    if store_filter:
        store_id = store_filter
    
    doctors, total = await service.get_list(
        name=name, store_id=store_id, department_id=department_id, 
        status=status, page=page, page_size=page_size
    )
    
    # 批量获取医生的号源状态
    doctor_ids = [d.id for d in doctors]
    availability_map = await service.get_doctors_availability(doctor_ids)
    
    result = [doctor_to_list_response(d, availability_map.get(d.id, False)) for d in doctors]
    
    return PageResponse(data=result, total=total, page=page, page_size=page_size)

@router.get(
    "/all",
    response_model=List[DoctorListResponse],
    summary="获取所有医生",
    description="""
    获取所有启用状态的医生列表（不分页），用于管理后台下拉选择等场景。

    **适用场景**：签到队列筛选、排班分配等需要完整医生列表的功能。

    **数据隔离**：
    - 门店管理员只能查看本门店的医生
    - 超级管理员可查看所有医生
    """,
)
async def get_all_doctors(
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取所有医生（管理端接口）

    用于管理后台需要获取完整医生列表的场景，如签到队列筛选
    """
    service = DoctorService(db)

    # 门店过滤：门店管理员只能看自己门店的医生
    store_filter = get_store_filter(current_admin)

    doctors = await service.get_all_active(store_id=store_filter)

    return [doctor_to_list_response(d) for d in doctors]


@router.get(
    "/recommended",
    response_model=List[DoctorListResponse],
    summary="获取推荐医生",
    description="""
    获取推荐医生列表（公开接口，无需登录）。

    **适用场景**：患者端首页推荐医生展示。

    **参数说明**：
    - limit: 返回数量（默认6，最大不超过系统配置）
    - store_id: 按门店筛选（可选）

    **返回数据**：
    - 只返回 is_recommended=1 且 status=1 的医生
    - 包含 hasAvailableSlots 字段标记号源状态
    """,
)
async def get_recommended_doctors(
    limit: int = Query(6, ge=1, le=settings.MAX_PAGE_SIZE),
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取推荐医生（公开接口，支持门店过滤）
    
    用于患者端首页推荐医生展示
    """
    service = DoctorService(db)
    doctors = await service.get_recommended(limit=limit, store_id=store_id)
    
    # 批量获取医生的号源状态
    doctor_ids = [d.id for d in doctors]
    availability_map = await service.get_doctors_availability(doctor_ids)
    
    return [doctor_to_list_response(d, availability_map.get(d.id, False)) for d in doctors]

@router.get(
    "/by-department/{department_id}",
    response_model=List[DoctorListResponse],
    summary="获取科室医生",
    description="""
    获取指定科室下的医生列表（公开接口，无需登录）。

    **适用场景**：患者端查看科室医生列表。

    **参数说明**：
    - department_id: 科室ID（路径参数）
    - store_id: 按门店筛选（可选）

    **返回数据**：
    - 只返回 status=1 的医生
    - 包含 hasAvailableSlots 字段标记号源状态
    """,
)
async def get_doctors_by_department(
    department_id: str,
    store_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    """获取科室下的医生（公开接口，支持门店过滤）
    
    用于患者端查看科室医生列表
    """
    service = DoctorService(db)
    doctors = await service.get_by_department(department_id, store_id=store_id)
    
    # 批量获取医生的号源状态
    doctor_ids = [d.id for d in doctors]
    availability_map = await service.get_doctors_availability(doctor_ids)
    
    return [doctor_to_list_response(d, availability_map.get(d.id, False)) for d in doctors]


@router.get(
    "/public/{doctor_id}",
    response_model=DoctorResponse,
    summary="获取医生详情(公开)",
    description="""
    获取医生详情（公开接口，用于患者端查看医生信息）。

    **参数说明**：
    - doctor_id: 医生ID（路径参数）

    **业务规则**：
    - 无需登录即可访问
    - 只返回 status=1（已启用）的医生，禁用/删除的医生返回404
    """,
)
async def get_doctor_public(
    doctor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取医生详情（公开接口，用于患者端查看医生信息）
    
    无需登录即可访问，只返回已启用的医生信息
    """
    service = DoctorService(db)
    doctor = await service.get_by_id(doctor_id)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在")
    
    # 只返回已启用的医生
    if doctor.status != 1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在")
    
    return doctor_to_response(doctor)


@router.put(
    "/batch-sort",
    summary="批量更新排序",
    description="""
    批量更新医生排序顺序。

    **权限要求**：管理员权限（doctor:update）。

    **参数说明**：
    - items: 数组，每项包含 id（医生ID）和 sort_order（排序值）
    - sort_order 值越小越靠前
    """,
)
async def batch_update_sort_order(
    data: BatchSortRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:update"))
):
    """批量更新医生排序"""
    service = DoctorService(db)
    items = [{"id": item.id, "sort_order": item.sort_order} for item in data.items]
    count = await service.batch_update_sort_order(items)
    return {"message": "排序更新成功", "count": count}


@router.get(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="获取医生详情",
    description="""
    获取医生详情（管理端接口）。

    **权限要求**：管理员登录，受门店访问控制（只能查看本门店医生）。

    **参数说明**：
    - doctor_id: 医生ID（路径参数）

    **返回数据**：
    - 包含医生完整信息、所属门店/科室名称、在线问诊配置等
    """,
)
async def get_doctor(
    doctor_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """获取医生详情（管理端接口，需要管理员权限）"""
    service = DoctorService(db)
    doctor = await service.get_by_id(doctor_id)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, doctor.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权访问此医生信息")
    
    return doctor_to_response(doctor)

@router.post(
    "",
    response_model=DoctorResponse,
    summary="创建医生",
    description="""
    创建医生账号。

    **权限要求**：管理员权限（doctor:create）。

    **业务规则**：
    - 门店管理员只能在本门店创建医生（自动绑定 store_id）
    - 超级管理员可指定任意门店
    - store_id 为必填字段
    - 创建后需重新加载关联关系以返回完整数据
    """,
)
async def create_doctor(
    data: DoctorCreate, 
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:create"))
):
    """创建医生"""
    # 检查门店访问权限
    store_filter = get_store_filter(current_admin)
    if store_filter:
        # 门店管理员只能在自己门店创建医生
        if data.store_id and data.store_id != store_filter:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="只能在本门店创建医生，请选择正确的门店")
        data.store_id = store_filter
    
    if not data.store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="请选择所属门店")
    
    service = DoctorService(db)
    doctor = await service.create(data)
    
    # 需要重新加载关联关系
    doctor = await service.get_by_id(doctor.id)
    
    return doctor_to_response(doctor)

@router.put(
    "/{doctor_id}",
    response_model=DoctorResponse,
    summary="更新医生",
    description="""
    更新医生信息。

    **权限要求**：管理员权限（doctor:update），受门店访问控制。

    **业务规则**：
    - 只能更新本门店的医生信息
    - 门店管理员不能修改医生的门店归属（store_id）
    - 超级管理员可修改任意医生的门店归属
    """,
)
async def update_doctor(
    doctor_id: str,
    data: DoctorUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:update"))
):
    """更新医生"""
    service = DoctorService(db)
    doctor = await service.get_by_id(doctor_id)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, doctor.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改此医生信息")
    
    # 门店管理员不能修改医生的门店归属
    store_filter = get_store_filter(current_admin)
    if store_filter and data.store_id and data.store_id != store_filter:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权修改医生的门店归属")
    
    doctor = await service.update(doctor_id, data)
    
    return doctor_to_response(doctor)

@router.delete(
    "/{doctor_id}",
    summary="删除医生",
    description="""
    删除医生（软删除）。

    **权限要求**：管理员权限（doctor:delete），受门店访问控制。

    **业务规则**：
    - 只能删除本门店的医生
    - 存在关联排班记录时可能拒绝删除（由 service 层判断）
    - 删除为软删除（设置 deleted_at 时间戳）
    """,
)
async def delete_doctor(
    doctor_id: str, 
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:delete"))
):
    """删除医生"""
    service = DoctorService(db)
    doctor = await service.get_by_id(doctor_id)
    
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    # 检查门店访问权限
    if not check_store_access(current_admin, doctor.store_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="您无权删除此医生")
    
    try:
        success = await service.delete(doctor_id)
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    return {"message": "删除成功"}


@router.post(
    "/check-username",
    response_model=CheckUsernameResponse,
    summary="检查账号是否存在",
    description="""
    检查医生登录账号是否已存在，如存在则返回推荐账号列表。

    **适用场景**：管理后台创建/编辑医生时的实时账号校验。

    **参数说明**：
    - username: 待检查的账号名
    - exclude_id: 排除的医生ID（编辑模式下排除自身）

    **返回数据**：
    - exists: 账号是否已存在
    - suggestions: 推荐的替代账号列表（仅在存在重复时返回）
    """,
)
async def check_username(
    data: CheckUsernameRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """检查医生账号是否已存在，如存在则返回推荐账号"""
    service = DoctorService(db)
    exists = await service.check_username_exists(data.username, data.exclude_id)
    
    suggestions = []
    if exists:
        # 获取基础用户名（去掉可能的数字后缀）
        base_username = data.username.rstrip('0123456789').rstrip('_')
        if not base_username:
            base_username = data.username
        suggestions = await service.suggest_usernames(base_username)
    
    return CheckUsernameResponse(exists=exists, suggestions=suggestions)


@router.post(
    "/generate-username",
    response_model=GenerateUsernameResponse,
    summary="生成唯一账号",
    description="""
    根据医生姓名自动生成唯一的登录账号。

    **适用场景**：管理后台创建医生时自动生成默认账号名。

    **参数说明**：
    - name: 医生姓名

    **返回数据**：
    - username: 生成的唯一账号名（基于姓名拼音 + 数字后缀）
    """,
)
async def generate_username(
    data: GenerateUsernameRequest,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin)
):
    """根据医生姓名生成唯一账号"""
    service = DoctorService(db)
    username = await service.generate_username(data.name)
    return GenerateUsernameResponse(username=username)
