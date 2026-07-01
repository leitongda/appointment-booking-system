
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import (
    check_store_access,
    get_current_admin,
    get_current_doctor_by_token,
    get_store_filter,
    require_permission,
)
from app.common.account_sync import AccountSyncService
from app.modules.settings.security_helpers import get_token_expire_config
from app.core.config import settings
from app.core.redis import RedisCache
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.db.session import get_db
from app.infrastructure.email.service import EmailService
from app.modules.settings.service import SettingsService
from app.modules.email_templates.service import EmailTemplateService
from app.models.account import Account
from app.models.doctor import Doctor
from app.modules.doctors.schemas import (
    BatchSortRequest,
    CheckUsernameRequest,
    CheckUsernameResponse,
    DoctorLoginRequest,
    DoctorLoginResponse,
    GenerateUsernameRequest,
    GenerateUsernameResponse,
)
from app.modules.doctors.service import DoctorService
from app.schemas.common import ChangePasswordRequest
from app.schemas.auth import (
    EmailBindRequest,
    EmailChangeRequest,
    EmailSendCodeRequest,
    EmailUnbindRequest,
    RefreshTokenRequest,
    TokenResponse,
)
from app.schemas.doctor import DoctorCreate, DoctorListResponse, DoctorResponse, DoctorUpdate
from app.schemas.response import PageResponse
from app.utils.ip import get_client_ip

router = APIRouter()


def _build_doctor_access_token_payload(doctor: Doctor) -> dict:
    payload = {"sub": doctor.id, "type": "doctor"}
    if doctor.tenant_id:
        payload["tenant_id"] = doctor.tenant_id
    return payload


def _build_doctor_refresh_token_payload(doctor: Doctor) -> dict:
    payload = {"sub": doctor.id, "type": "refresh", "role_type": "doctor"}
    if doctor.tenant_id:
        payload["tenant_id"] = doctor.tenant_id
    return payload


def _validate_email_format(email: str) -> bool:
    import re

    if not email or not email.strip():
        return False
    return bool(re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", email))


def _normalize_email(email: str) -> str:
    return email.strip().lower()


async def _get_doctor_account(db: AsyncSession, doctor: Doctor) -> Account | None:
    account = await db.get(Account, doctor.id)
    if account:
        return account
    if doctor.phone:
        result = await db.execute(
            select(Account).where(
                Account.phone == doctor.phone,
                Account.tenant_id == doctor.tenant_id,
            )
        )
        return result.scalar_one_or_none()
    return None


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
    try:
        doctor = await service.authenticate(data.phone, data.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    
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
    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_doctor_access_token_payload(doctor), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_doctor_refresh_token_payload(doctor), expires_delta=refresh_delta)

    doctor_resp = doctor_to_response(doctor)
    # 从统一账号表补充 email
    account = await _get_doctor_account(db, doctor)
    if account:
        doctor_resp.email = account.email

    from fastapi.responses import JSONResponse
    resp = JSONResponse(content=DoctorLoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_seconds,
        doctor=doctor_resp,
    ).model_dump(mode="json"))
    if getattr(doctor, 'must_change_password', False):
        resp.headers["X-Password-Change-Required"] = "true"
    return resp


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
    db: AsyncSession = Depends(get_db),
):
    """获取当前登录医生信息"""
    resp = doctor_to_response(doctor)
    # 从统一账号表补充 email
    account = await _get_doctor_account(db, doctor)
    if account:
        resp.email = account.email
    return resp


@router.post("/refresh", response_model=TokenResponse, summary="刷新医生Token")
async def doctor_refresh_token(
    data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db),
):
    payload = decode_token(data.refresh_token)
    if not payload:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="身份验证失败，请重新登录")

    token_type = payload.get("type")
    role_type = payload.get("role_type")
    is_new_refresh = token_type == "refresh" and role_type == "doctor"
    is_legacy_refresh = token_type == "doctor"
    if not (is_new_refresh or is_legacy_refresh):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新凭证，请重新登录")

    doctor_id = payload.get("sub")
    if not doctor_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新凭证，请重新登录")

    service = DoctorService(db)
    doctor = await service.get_by_id(doctor_id)
    if not doctor or doctor.status != 1 or doctor.deleted_at is not None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="账号不存在或已被禁用，请检查后重试")

    token_tenant_id = payload.get("tenant_id")
    if token_tenant_id and token_tenant_id != doctor.tenant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="租户信息不匹配，请重新登录")

    # 轮换 Refresh Token: 将旧 token 加入黑名单
    from datetime import datetime as _dt

    from jose import jwt as _jwt
    try:
        old_claims = _jwt.get_unverified_claims(data.refresh_token)
        exp_ts = old_claims.get("exp", 0)
        remaining_ttl = max(1, int(exp_ts - _dt.utcnow().timestamp()))
    except Exception:
        remaining_ttl = 86400
    await RedisCache.add_refresh_token_to_blacklist(
        data.refresh_token, tenant_id=token_tenant_id, ttl=remaining_ttl
    )

    access_delta, refresh_delta, expires_seconds = await get_token_expire_config(db)
    access_token = create_access_token(data=_build_doctor_access_token_payload(doctor), expires_delta=access_delta)
    refresh_token = create_refresh_token(data=_build_doctor_refresh_token_payload(doctor), expires_delta=refresh_delta)
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_seconds,
    )


@router.post(
    "/me/email/send-code",
    summary="发送医生邮箱验证码（兼容接口）",
    deprecated=True,
)
async def send_current_doctor_email_code(
    data: EmailSendCodeRequest,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_by_token),
):
    account = await _get_doctor_account(db, current_doctor)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号未同步，请联系管理员处理")

    target_email = data.email or account.email
    if not target_email or not _validate_email_format(target_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    target_email = _normalize_email(target_email)
    can_send, wait_seconds = await RedisCache.check_email_rate_limit(target_email, "doctor_bind")
    if not can_send:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"发送过于频繁，请{wait_seconds}秒后重试",
        )

    from app.infrastructure.sms.service import SmsService

    code = SmsService.generate_code()
    await RedisCache.set_email_code(target_email, code, "doctor_bind")

    try:
        email_service = EmailService(db, config_provider=SettingsService(db), template_provider=EmailTemplateService(db))
        await email_service.send_verification_code_email(target_email, code, "doctor_bind")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="验证码发送失败，请稍后重试",
        ) from exc

    if settings.DEBUG:
        return {"message": "验证码发送成功", "code": code}
    return {"message": "验证码发送成功"}


@router.post(
    "/me/email/bind",
    summary="绑定医生邮箱（兼容接口）",
    deprecated=True,
)
async def bind_current_doctor_email(
    data: EmailBindRequest,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_by_token),
):
    if not _validate_email_format(data.email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱格式不正确")

    email = _normalize_email(data.email)
    is_valid = await RedisCache.verify_email_code(email, data.code, "doctor_bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    existing = await db.execute(
        select(Account).where(
            Account.tenant_id == current_doctor.tenant_id,
            Account.email == email,
        )
    )
    existing_account = existing.scalar_one_or_none()
    if existing_account and existing_account.id != current_doctor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="该邮箱已被其他账号绑定")

    account = await _get_doctor_account(db, current_doctor)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号未同步，请联系管理员处理")

    account.email = email
    await db.commit()
    return {"message": "邮箱绑定成功"}


@router.post(
    "/me/email/unbind",
    summary="解绑医生邮箱（兼容接口）",
    deprecated=True,
)
async def unbind_current_doctor_email(
    data: EmailUnbindRequest,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_by_token),
):
    account = await _get_doctor_account(db, current_doctor)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号未同步，请联系管理员处理")
    if not account.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱")

    is_valid = await RedisCache.verify_email_code(account.email, data.code, "doctor_bind")
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期")

    account.email = None
    await db.commit()
    return {"message": "邮箱解绑成功"}


@router.post(
    "/me/email/change",
    summary="更换医生邮箱（兼容接口）",
    deprecated=True,
)
async def change_current_doctor_email(
    data: EmailChangeRequest,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_by_token),
):
    if not _validate_email_format(data.new_email):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱格式不正确")

    new_email = _normalize_email(data.new_email)
    account = await _get_doctor_account(db, current_doctor)
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="账号未同步，请联系管理员处理")
    if not account.email:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前账号未绑定邮箱，请先绑定")

    old_valid = await RedisCache.verify_email_code(account.email, data.old_email_code, "doctor_bind")
    if not old_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="当前邮箱验证码错误或已过期")

    new_valid = await RedisCache.verify_email_code(new_email, data.new_email_code, "doctor_bind")
    if not new_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱验证码错误或已过期")

    existing = await db.execute(
        select(Account).where(
            Account.tenant_id == current_doctor.tenant_id,
            Account.email == new_email,
        )
    )
    existing_account = existing.scalar_one_or_none()
    if existing_account and existing_account.id != current_doctor.id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="新邮箱已被其他账号绑定")

    account.email = new_email
    await db.commit()
    return {"message": "邮箱换绑成功"}

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
    name: str | None = None,
    store_id: str | None = None,
    department_id: str | None = None,
    status: int | None = None,
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
    response_model=list[DoctorListResponse],
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
    response_model=list[DoctorListResponse],
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
    store_id: str | None = None,
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
    response_model=list[DoctorListResponse],
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
    store_id: str | None = None,
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


@router.post(
    "/change-password",
    summary="医生修改密码",
    description="""
    修改当前登录医生的密码。

    **权限要求**：需要医生 Token 认证。

    **业务规则**：
    - 需要验证旧密码正确性
    - 新密码长度 6-20 位
    - 遵循租户密码策略
    - 修改成功后不强制退出登录

    **参数说明**：
    - old_password: 原密码
    - new_password: 新密码（6-20位）
    """,
)
async def change_doctor_password(
    data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_doctor: Doctor = Depends(get_current_doctor_by_token),
):
    """医生修改密码"""
    from app.core.security import get_password_hash, verify_password
    from app.modules.tenants.password_policy import PasswordPolicyValidator, get_tenant_password_policy

    # 验证旧密码
    if not verify_password(data.old_password, current_doctor.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="原密码错误，请重新输入"
        )

    # 验证新旧密码不能相同
    if data.old_password == data.new_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与原密码相同"
        )

    # 密码长度校验已迁移到 Pydantic schema 层（app.schemas.common.ChangePasswordRequest），
    # 由 min_length=6/max_length=20 在 422 拦截；不再在此处手动 raise HTTPException(400)。

    # 密码策略校验
    policy = await get_tenant_password_policy(db, current_doctor.tenant_id)
    validator = PasswordPolicyValidator(policy)
    is_valid, errors = validator.validate(
        data.new_password,
        username=current_doctor.username,
        phone=current_doctor.phone,
    )
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="; ".join(errors)
        )

    # 更新密码
    current_doctor.password_hash = get_password_hash(data.new_password)
    current_doctor.must_change_password = False
    await db.flush()

    # 双写同步: 密码变更同步到 accounts
    await AccountSyncService.sync_doctor_to_account(
        db, current_doctor.id, operator_id=current_doctor.id
    )

    await db.commit()

    return {"message": "密码修改成功"}
