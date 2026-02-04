from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from decimal import Decimal

from app.db.session import get_db
from app.api.deps import get_current_admin, require_permission
from app.schemas.consultation_fee import (
    ConsultationFeeTypeCreate, ConsultationFeeTypeUpdate, ConsultationFeeTypeResponse,
    ConsultationFeeTemplateCreate, ConsultationFeeTemplateResponse, ConsultationFeeTemplateWithType,
    DoctorConsultationFeeResponse, DoctorConsultationFeeBatchCreate,
    DoctorFeeSettingResponse, DoctorFeeSettingUpdate, StoreDepartmentFeeGroup,
    StoreFeeTemplateResponse, StoreFeeTemplateBatchCreate, StoreFeeTemplateWithType,
    ApplyTemplateRequest
)
from app.services.consultation_fee_service import ConsultationFeeService

router = APIRouter()


# ========== 诊费类型相关 API ==========

@router.get("/types", response_model=List[ConsultationFeeTypeResponse], summary="获取诊费类型列表")
async def get_fee_types(
    status: Optional[int] = Query(None, description="状态筛选"),
    store_id: Optional[str] = Query(None, description="门店ID，获取门店可用的诊费类型（全局+门店专属）"),
    include_global: bool = Query(True, description="是否包含全局类型"),
    db: AsyncSession = Depends(get_db)
):
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
    db: AsyncSession = Depends(get_db)
):
    """获取诊费类型详情"""
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
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """
    创建诊费类型
    - store_id 为空：创建全局类型
    - store_id 有值：创建门店专属类型
    """
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
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """更新诊费类型"""
    service = ConsultationFeeService(db)
    
    # 获取现有记录
    existing_type = await service.get_fee_type_by_id(fee_type_id)
    if not existing_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    
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
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """删除诊费类型"""
    service = ConsultationFeeService(db)
    success = await service.delete_fee_type(fee_type_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="诊费类型不存在，请检查后重试")
    
    return {"message": "删除成功"}


# ========== 全局诊费模板相关 API ==========

@router.get("/templates", response_model=List[ConsultationFeeTemplateWithType], summary="获取全局诊费模板列表")
async def get_fee_templates(
    db: AsyncSession = Depends(get_db)
):
    """获取全局诊费模板列表（带类型信息）"""
    service = ConsultationFeeService(db)
    templates = await service.get_fee_templates_with_types()
    return [ConsultationFeeTemplateWithType(**t) for t in templates]


@router.put("/templates", summary="批量更新全局诊费模板")
async def update_fee_templates(
    templates: List[dict],
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

@router.get("/store-templates/{store_id}", response_model=List[StoreFeeTemplateWithType], summary="获取门店诊费模板列表")
async def get_store_fee_templates(
    store_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    获取门店诊费模板列表（带类型信息）
    返回门店可用的所有诊费类型及其模板配置，包含全局模板金额作为参考
    """
    service = ConsultationFeeService(db)
    templates = await service.get_store_fee_templates_with_types(store_id)
    return [StoreFeeTemplateWithType(**t) for t in templates]


@router.post("/store-templates/{store_id}/batch", summary="批量保存门店诊费模板")
async def batch_save_store_fee_templates(
    store_id: str,
    data: StoreFeeTemplateBatchCreate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """批量保存门店诊费模板"""
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
    _: None = Depends(require_permission("system:consultation-fee"))
):
    """删除门店诊费模板"""
    service = ConsultationFeeService(db)
    success = await service.delete_store_fee_template(store_id, fee_type_id)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="门店诊费模板不存在，请检查后重试")
    
    return {"message": "删除成功"}


# ========== 医生诊费配置相关 API ==========

@router.get("/doctors/{doctor_id}", response_model=DoctorFeeSettingResponse, summary="获取医生诊费设置")
async def get_doctor_fee_setting(
    doctor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取医生诊费设置"""
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


@router.get("/doctors/{doctor_id}/grouped", response_model=List[StoreDepartmentFeeGroup], summary="获取医生诊费配置（分组）")
async def get_doctor_fees_grouped(
    doctor_id: str,
    db: AsyncSession = Depends(get_db)
):
    """获取医生诊费配置（按门店-科室分组）"""
    service = ConsultationFeeService(db)
    groups = await service.get_doctor_fees_grouped(doctor_id)
    return groups


@router.put("/doctors/{doctor_id}/use-template", summary="更新医生使用模板设置")
async def update_doctor_use_template(
    doctor_id: str,
    data: DoctorFeeSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:update"))
):
    """更新医生是否使用诊费模板"""
    service = ConsultationFeeService(db)
    success = await service.update_doctor_use_template(doctor_id, data.use_fee_template)
    
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="医生不存在，请检查后重试")
    
    return {"message": "更新成功"}


@router.get("/doctors/{doctor_id}/fees", response_model=List[DoctorConsultationFeeResponse], summary="获取医生诊费配置列表")
async def get_doctor_fees(
    doctor_id: str,
    store_id: Optional[str] = Query(None, description="门店ID"),
    department_id: Optional[str] = Query(None, description="科室ID"),
    db: AsyncSession = Depends(get_db)
):
    """获取医生诊费配置列表"""
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
    _: None = Depends(require_permission("doctor:update"))
):
    """批量保存医生诊费配置"""
    if data.doctor_id != doctor_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="医生信息不匹配，请检查后重试")
    
    service = ConsultationFeeService(db)
    await service.batch_save_doctor_fees(data)
    
    return {"message": "保存成功"}


@router.post("/doctors/{doctor_id}/apply-template", summary="应用模板到医生")
async def apply_template_to_doctor(
    doctor_id: str,
    data: ApplyTemplateRequest,
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:update"))
):
    """
    一键带入模板：将门店模板的金额应用到医生诊费配置
    优先使用门店模板，如果门店未配置则使用全局模板
    """
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
    _: None = Depends(require_permission("doctor:update"))
):
    """删除医生在指定门店科室的所有诊费配置"""
    service = ConsultationFeeService(db)
    count = await service.delete_doctor_fees_by_store_department(doctor_id, store_id, department_id)
    
    return {"message": f"删除成功，共删除{count}条记录"}
