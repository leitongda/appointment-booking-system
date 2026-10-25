
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, require_admin_tenant_anchor, require_permission
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.store import Store
from app.modules.consultation_fees.service import ConsultationFeeService
from app.schemas.consultation_fee import (
    ApplyTemplateRequest,
    ConsultationFeeTemplateCreate,
    ConsultationFeeTemplateResponse,
    ConsultationFeeTemplateWithType,
    ConsultationFeeTypeCreate,
    ConsultationFeeTypeResponse,
    ConsultationFeeTypeUpdate,
    DoctorConsultationFeeBatchCreate,
    DoctorConsultationFeeResponse,
    DoctorFeeSettingResponse,
    DoctorFeeSettingUpdate,
    StoreDepartmentFeeGroup,
    StoreFeeTemplateBatchCreate,
    StoreFeeTemplateWithType,
)


# ---------------------------------------------------------------------------
# p3a8 查询侧租户收口：传入的 store/doctor/行数据必须属于锚点租户
# （平台管理员 anchor=None 时放行；平台级行 tenant_id=NULL 对租户管理员共享）
# ---------------------------------------------------------------------------

async def _ensure_store_in_tenant(db: AsyncSession, store_id: str | None, tenant_anchor: str | None) -> None:
    if not store_id or not tenant_anchor:
        return
    store = await db.get(Store, store_id)
    if store is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店不存在，请检查后重试")
    if store.tenant_id != tenant_anchor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问其他租户的门店数据")


async def _ensure_doctor_in_tenant(db: AsyncSession, doctor_id: str, tenant_anchor: str | None) -> None:
    if not tenant_anchor:
        return
    doctor = await db.get(Doctor, doctor_id)
    if doctor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    if doctor.tenant_id != tenant_anchor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无权访问其他租户的医生数据")


def _ensure_row_tenant(row_tenant_id: str | None, tenant_anchor: str | None, label: str) -> None:
    if tenant_anchor and row_tenant_id is not None and row_tenant_id != tenant_anchor:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"无权访问其他租户的{label}")


router = APIRouter()


# ========== 诊费类型相关 API ==========

@router.get("/types", response_model=list[ConsultationFeeTypeResponse], summary="获取诊费类型列表")
async def get_fee_types(
    status: int | None = Query(None, description="状态筛选"),
    store_id: str | None = Query(None, description="门店ID，获取门店可用的诊费类型（全局+门店专属）"),
    include_global: bool = Query(True, description="是否包含全局类型"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    # p3a8：传入的门店必须属于锚点租户
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    """
    获取诊费类型列表
    - 不传 store_id：返回全局类型
    - 传 store_id：返回门店可用的类型（全局类型 + 门店专属类型）
    """
    service = ConsultationFeeService(db)
    fee_types = await service.get_fee_types(status=status, store_id=store_id, include_global=include_global)
    return [ConsultationFeeTypeResponse(
        id=ft.id,
        store_id=ft.store_id,
        store_name=ft.store.name if ft.store else None,
        name=ft.name,
        code=ft.code,
        description=ft.description,
        sort_order=ft.sort_order,
        status=ft.status,
        is_global=ft.store_id is None,
        created_at=ft.created_at,
        updated_at=ft.updated_at
    ) for ft in fee_types]


@router.get("/types/{fee_type_id}", response_model=ConsultationFeeTypeResponse, summary="获取诊费类型详情")
async def get_fee_type(
    fee_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取诊费类型详情"""
    # p3a8：租户管理员只能看本租户专属类型与共享的平台级类型
    fee_type = await ConsultationFeeService(db).get_fee_type_by_id(fee_type_id)
    if not fee_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    _ensure_row_tenant(fee_type.tenant_id, tenant_anchor, "诊费类型")
    service = ConsultationFeeService(db)
    fee_type = await service.get_fee_type_by_id(fee_type_id)
    
    if not fee_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    
    return ConsultationFeeTypeResponse(
        id=fee_type.id,
        store_id=fee_type.store_id,
        store_name=fee_type.store.name if fee_type.store else None,
        name=fee_type.name,
        code=fee_type.code,
        description=fee_type.description,
        sort_order=fee_type.sort_order,
        status=fee_type.status,
        is_global=fee_type.store_id is None,
        created_at=fee_type.created_at,
        updated_at=fee_type.updated_at
    )


@router.post("/types", response_model=ConsultationFeeTypeResponse, summary="创建诊费类型")
async def create_fee_type(
    data: ConsultationFeeTypeCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """
    创建诊费类型
    - store_id 为空：创建全局类型
    - store_id 有值：创建门店专属类型
    """
    await _ensure_store_in_tenant(db, data.store_id, tenant_anchor)
    service = ConsultationFeeService(db)
    
    # 检查编码是否已存在（在同一门店或全局范围内）
    if data.code:
        existing = await service.get_fee_type_by_code(data.code, data.store_id)
        if existing:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="类型编码已存在，请使用其他编码")
    
    fee_type = await service.create_fee_type(data)
    
    return ConsultationFeeTypeResponse(
        id=fee_type.id,
        store_id=fee_type.store_id,
        store_name=fee_type.store.name if fee_type.store else None,
        name=fee_type.name,
        code=fee_type.code,
        description=fee_type.description,
        sort_order=fee_type.sort_order,
        status=fee_type.status,
        is_global=fee_type.store_id is None,
        created_at=fee_type.created_at,
        updated_at=fee_type.updated_at
    )


@router.put("/types/{fee_type_id}", response_model=ConsultationFeeTypeResponse, summary="更新诊费类型")
async def update_fee_type(
    fee_type_id: str,
    data: ConsultationFeeTypeUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """更新诊费类型"""
    service = ConsultationFeeService(db)
    
    # 获取现有记录
    existing_type = await service.get_fee_type_by_id(fee_type_id)
    if not existing_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    _ensure_row_tenant(existing_type.tenant_id, tenant_anchor, "诊费类型")
    await _ensure_store_in_tenant(
        db, data.store_id if data.store_id is not None else existing_type.store_id, tenant_anchor
    )
    
    # 检查编码是否已存在
    if data.code:
        store_id = data.store_id if data.store_id is not None else existing_type.store_id
        existing = await service.get_fee_type_by_code(data.code, store_id)
        if existing and existing.id != fee_type_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="类型编码已存在，请使用其他编码")
    
    fee_type = await service.update_fee_type(fee_type_id, data)
    
    return ConsultationFeeTypeResponse(
        id=fee_type.id,
        store_id=fee_type.store_id,
        store_name=fee_type.store.name if fee_type.store else None,
        name=fee_type.name,
        code=fee_type.code,
        description=fee_type.description,
        sort_order=fee_type.sort_order,
        status=fee_type.status,
        is_global=fee_type.store_id is None,
        created_at=fee_type.created_at,
        updated_at=fee_type.updated_at
    )


@router.delete("/types/{fee_type_id}", summary="删除诊费类型")
async def delete_fee_type(
    fee_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """删除诊费类型"""
    existing_type = await ConsultationFeeService(db).get_fee_type_by_id(fee_type_id)
    if not existing_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    _ensure_row_tenant(existing_type.tenant_id, tenant_anchor, "诊费类型")
    service = ConsultationFeeService(db)
    success = await service.delete_fee_type(fee_type_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    
    return {"message": "删除成功"}


# ========== 全局诊费模板相关 API ==========

@router.get("/templates", response_model=list[ConsultationFeeTemplateWithType], summary="获取全局诊费模板列表")
async def get_fee_templates(
    db: AsyncSession = Depends(get_db)
):
    """获取全局诊费模板列表（带类型信息）"""
    service = ConsultationFeeService(db)
    templates = await service.get_fee_templates_with_types()
    return [ConsultationFeeTemplateWithType(**t) for t in templates]


@router.put("/templates", summary="批量更新全局诊费模板")
async def update_fee_templates(
    templates: list[dict],
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """批量更新全局诊费模板"""
    service = ConsultationFeeService(db)
    await service.batch_update_fee_templates(templates)
    return {"message": "更新成功"}


@router.post("/templates", response_model=ConsultationFeeTemplateResponse, summary="创建或更新全局诊费模板")
async def create_or_update_fee_template(
    data: ConsultationFeeTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """创建或更新全局诊费模板"""
    service = ConsultationFeeService(db)
    
    # 验证诊费类型是否存在
    fee_type = await service.get_fee_type_by_id(data.fee_type_id)
    if not fee_type:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="诊费类型不存在")
    
    template = await service.create_or_update_fee_template(data)
    
    return ConsultationFeeTemplateResponse(
        id=template.id,
        fee_type_id=template.fee_type_id,
        fee_type_name=fee_type.name,
        fee_type_code=fee_type.code,
        initial_fee=template.initial_fee,
        follow_up_fee=template.follow_up_fee,
        status=template.status,
        created_at=template.created_at,
        updated_at=template.updated_at
    )


# ========== 门店诊费模板相关 API ==========

@router.get("/store-templates/{store_id}", response_model=list[StoreFeeTemplateWithType], summary="获取门店诊费模板列表")
async def get_store_fee_templates(
    store_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """
    获取门店诊费模板列表（带类型信息）
    返回门店可用的所有诊费类型及其模板配置，包含全局模板金额作为参考
    """
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    service = ConsultationFeeService(db)
    templates = await service.get_store_fee_templates_with_types(store_id)
    return [StoreFeeTemplateWithType(**t) for t in templates]


@router.post("/store-templates/{store_id}/batch", summary="批量保存门店诊费模板")
async def batch_save_store_fee_templates(
    store_id: str,
    data: StoreFeeTemplateBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """批量保存门店诊费模板"""
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    if data.store_id != store_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="门店信息不匹配，请检查后重试")
    
    service = ConsultationFeeService(db)
    await service.batch_save_store_fee_templates(data)
    
    return {"message": "保存成功"}


@router.delete("/store-templates/{store_id}/{fee_type_id}", summary="删除门店诊费模板")
async def delete_store_fee_template(
    store_id: str,
    fee_type_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """删除门店诊费模板"""
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    service = ConsultationFeeService(db)
    success = await service.delete_store_fee_template(store_id, fee_type_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店诊费模板不存在，请检查后重试")
    
    return {"message": "删除成功"}


# ========== 医生诊费配置相关 API ==========

@router.get("/doctors/{doctor_id}", response_model=DoctorFeeSettingResponse, summary="获取医生诊费设置")
async def get_doctor_fee_setting(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取医生诊费设置"""
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    service = ConsultationFeeService(db)
    result = await service.get_doctor_fee_setting(doctor_id)
    
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    fees = [DoctorConsultationFeeResponse(
        id=f.id,
        doctor_id=f.doctor_id,
        store_id=f.store_id,
        store_name=f.store.name if f.store else None,
        department_id=f.department_id,
        department_name=f.department.name if f.department else None,
        fee_type_id=f.fee_type_id,
        fee_type_name=f.fee_type.name if f.fee_type else None,
        fee_type_code=f.fee_type.code if f.fee_type else None,
        initial_fee=f.initial_fee,
        follow_up_fee=f.follow_up_fee,
        status=f.status,
        created_at=f.created_at,
        updated_at=f.updated_at
    ) for f in result['fees']]
    
    return DoctorFeeSettingResponse(
        doctor_id=result['doctor_id'],
        doctor_name=result['doctor_name'],
        use_fee_template=result['use_fee_template'],
        fees=fees
    )


@router.get("/doctors/{doctor_id}/grouped", response_model=list[StoreDepartmentFeeGroup], summary="获取医生诊费配置（分组）")
async def get_doctor_fees_grouped(
    doctor_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取医生诊费配置（按门店-科室分组）"""
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    service = ConsultationFeeService(db)
    groups = await service.get_doctor_fees_grouped(doctor_id)
    return groups


@router.put("/doctors/{doctor_id}/use-template", summary="更新医生使用模板设置")
async def update_doctor_use_template(
    doctor_id: str,
    data: DoctorFeeSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("doctor:update"))
):
    """更新医生是否使用诊费模板"""
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    service = ConsultationFeeService(db)
    success = await service.update_doctor_use_template(doctor_id, data.use_fee_template)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    return {"message": "更新成功"}


@router.get("/doctors/{doctor_id}/fees", response_model=list[DoctorConsultationFeeResponse], summary="获取医生诊费配置列表")
async def get_doctor_fees(
    doctor_id: str,
    store_id: str | None = Query(None, description="门店ID"),
    department_id: str | None = Query(None, description="科室ID"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
):
    """获取医生诊费配置列表"""
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    service = ConsultationFeeService(db)
    fees = await service.get_doctor_fees(doctor_id, store_id, department_id)
    
    return [DoctorConsultationFeeResponse(
        id=f.id,
        doctor_id=f.doctor_id,
        store_id=f.store_id,
        store_name=f.store.name if f.store else None,
        department_id=f.department_id,
        department_name=f.department.name if f.department else None,
        fee_type_id=f.fee_type_id,
        fee_type_name=f.fee_type.name if f.fee_type else None,
        fee_type_code=f.fee_type.code if f.fee_type else None,
        initial_fee=f.initial_fee,
        follow_up_fee=f.follow_up_fee,
        status=f.status,
        created_at=f.created_at,
        updated_at=f.updated_at
    ) for f in fees]


@router.post("/doctors/{doctor_id}/fees/batch", summary="批量保存医生诊费配置")
async def batch_save_doctor_fees(
    doctor_id: str,
    data: DoctorConsultationFeeBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("doctor:update"))
):
    """批量保存医生诊费配置"""
    if data.doctor_id != doctor_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="医生信息不匹配，请检查后重试")
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    await _ensure_store_in_tenant(db, data.store_id, tenant_anchor)

    service = ConsultationFeeService(db)
    await service.batch_save_doctor_fees(data)
    
    return {"message": "保存成功"}


@router.post("/doctors/{doctor_id}/apply-template", summary="应用模板到医生")
async def apply_template_to_doctor(
    doctor_id: str,
    data: ApplyTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("doctor:update"))
):
    """
    一键带入模板：将门店模板的金额应用到医生诊费配置
    优先使用门店模板，如果门店未配置则使用全局模板
    """
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    await _ensure_store_in_tenant(db, data.store_id, tenant_anchor)
    service = ConsultationFeeService(db)
    
    # 验证医生是否存在
    doctor_setting = await service.get_doctor_fee_setting(doctor_id)
    if not doctor_setting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    fees = await service.apply_template_to_doctor(doctor_id, data.store_id, data.department_id)
    
    return {
        "message": "模板应用成功",
        "count": len(fees)
    }


@router.delete("/doctors/{doctor_id}/fees/{store_id}/{department_id}", summary="删除医生门店科室诊费配置")
async def delete_doctor_fees_by_store_department(
    doctor_id: str,
    store_id: str,
    department_id: str,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    tenant_anchor: str | None = Depends(require_admin_tenant_anchor),
    _: None = Depends(require_permission("doctor:update"))
):
    """删除医生在指定门店科室的所有诊费配置"""
    await _ensure_doctor_in_tenant(db, doctor_id, tenant_anchor)
    await _ensure_store_in_tenant(db, store_id, tenant_anchor)
    service = ConsultationFeeService(db)
    count = await service.delete_doctor_fees_by_store_department(doctor_id, store_id, department_id)

    return {"message": f"删除成功，共删除{count}条记录"}


# ========== 小程序预约相关 API ==========


@router.get("/amount", summary="获取诊费金额")
async def get_consultation_fee_amount(
    doctor_id: str = Query(..., description="医生ID"),
    store_id: str = Query(..., description="门店ID"),
    department_id: str = Query(..., description="科室ID"),
    db: AsyncSession = Depends(get_db),
):
    """获取诊费金额

    小程序在预约页面获取诊费金额，按优先级查询：
    1. 医生诊费配置
    2. 门店诊费模板
    3. 全局诊费模板

    返回默认的初诊金额。
    """
    from app.modules.appointments.service_booking import AppointmentBookingService

    service = AppointmentBookingService(db)

    try:
        amount = await service._get_consultation_fee(
            doctor_id=doctor_id,
            store_id=store_id,
            department_id=department_id,
        )
        return {"amount": float(amount) if amount else 0.0}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取诊费金额失败: {str(e)}"
        )
