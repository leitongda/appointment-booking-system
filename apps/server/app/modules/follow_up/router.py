"""随访路由"""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, and_, func, case
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user_or_admin
from app.common.auth_deps import get_current_admin
from app.core.config import settings
from app.db.session import get_db
from app.models.follow_up_task import FollowUpTask
from app.models.follow_up_record import FollowUpRecord
from app.models.follow_up_self_report import FollowUpSelfReport
from app.models.doctor import Doctor
from app.models.user import Patient
from app.middleware.tenant_context import get_current_tenant_id
from app.schemas.follow_up import (
    FollowUpPlanCreate, FollowUpPlanUpdate, FollowUpPlanStepsUpdate,
    FollowUpPlanResponse, FollowUpPlanListResponse,
    FollowUpTaskCreate, FollowUpTaskGenerateRequest, FollowUpTaskSkipRequest,
    FollowUpTaskResponse, FollowUpTaskListResponse,
    FollowUpRecordCreate, FollowUpRecordUpdate,
    FollowUpRecordResponse, FollowUpRecordListResponse,
    SelfReportCreate, SelfReportResponse, SelfReportListResponse,
)
from app.schemas.response import PageResponse
from app.modules.follow_up.service import FollowUpPlanService, FollowUpTaskService, FollowUpRecordService, SelfReportService

router = APIRouter()


async def _resolve_patient(
    db: AsyncSession,
    user_id: str,
    tenant_id: Optional[str],
    patient_id: Optional[str] = None,
) -> Optional[Patient]:
    """从 token 解析就诊人。若指定 patient_id 则校验归属，否则取默认就诊人。"""
    stmt = select(Patient).where(Patient.user_id == user_id)
    if tenant_id:
        stmt = stmt.where(Patient.tenant_id == tenant_id)
    if patient_id:
        # 指定就诊人：校验是否属于当前用户
        stmt = stmt.where(Patient.id == patient_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()
    else:
        # 默认就诊人
        stmt = stmt.where(Patient.is_default == True)
        result = await db.execute(stmt)
        return result.scalar_one_or_none()


# ========== 响应构建 ==========

def build_plan_response(plan) -> FollowUpPlanResponse:
    from app.schemas.follow_up import FollowUpPlanStepResponse
    return FollowUpPlanResponse(
        id=plan.id,
        name=plan.name,
        description=plan.description,
        department_id=plan.department_id,
        department_name=plan.department.name if plan.department else None,
        diagnosis_code=plan.diagnosis_code,
        diagnosis_name=plan.diagnosis_name,
        status=plan.status,
        steps=[FollowUpPlanStepResponse.model_validate(s) for s in (plan.steps or [])],
        created_at=plan.created_at,
        updated_at=plan.updated_at,
    )


def build_plan_list_response(plan) -> FollowUpPlanListResponse:
    return FollowUpPlanListResponse(
        id=plan.id,
        name=plan.name,
        department_name=plan.department.name if hasattr(plan, 'department') and plan.department else None,
        diagnosis_name=plan.diagnosis_name,
        status=plan.status,
        step_count=len(plan.steps) if plan.steps else 0,
        created_at=plan.created_at,
    )


def build_task_response(task) -> FollowUpTaskResponse:
    return FollowUpTaskResponse(
        id=task.id,
        task_no=task.task_no,
        patient_id=task.patient_id,
        patient_name=task.patient.name if task.patient else None,
        doctor_id=task.doctor_id,
        doctor_name=task.doctor.name if task.doctor else None,
        department_id=task.department_id,
        department_name=task.department.name if task.department else None,
        appointment_id=task.appointment_id,
        medical_record_id=task.medical_record_id,
        plan_id=task.plan_id,
        plan_name=task.plan.name if task.plan else None,
        step_order=task.step_order,
        scheduled_date=task.scheduled_date,
        status=task.status,
        completed_at=task.completed_at,
        completed_by=task.completed_by,
        skip_reason=task.skip_reason,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def build_task_list_response(task) -> FollowUpTaskListResponse:
    return FollowUpTaskListResponse(
        id=task.id,
        task_no=task.task_no,
        patient_name=task.patient.name if task.patient else None,
        doctor_name=task.doctor.name if task.doctor else None,
        department_name=task.department.name if task.department else None,
        scheduled_date=task.scheduled_date,
        status=task.status,
        plan_name=task.plan.name if task.plan else None,
        step_order=task.step_order,
        created_at=task.created_at,
    )


def build_record_response(record) -> FollowUpRecordResponse:
    import json
    attachments = None
    if record.attachments:
        try:
            attachments = json.loads(record.attachments)
        except (json.JSONDecodeError, TypeError):
            pass

    return FollowUpRecordResponse(
        id=record.id,
        task_id=record.task_id,
        patient_id=record.patient_id,
        patient_name=record.patient.name if record.patient else None,
        doctor_id=record.doctor_id,
        doctor_name=record.doctor.name if record.doctor else None,
        appointment_id=record.appointment_id,
        medical_record_id=record.medical_record_id,
        follow_up_date=record.follow_up_date,
        content=record.content,
        patient_condition=record.patient_condition,
        next_action=record.next_action,
        next_follow_up_date=record.next_follow_up_date,
        attachments=attachments,
        created_at=record.created_at,
        updated_at=record.updated_at,
    )


def build_record_list_response(record) -> FollowUpRecordListResponse:
    return FollowUpRecordListResponse(
        id=record.id,
        patient_name=record.patient.name if record.patient else None,
        doctor_name=record.doctor.name if record.doctor else None,
        follow_up_date=record.follow_up_date,
        content=record.content,
        patient_condition=record.patient_condition,
        task_id=record.task_id,
        created_at=record.created_at,
    )


# ========== 随访计划端点 ==========

@router.get("/plans", response_model=PageResponse[FollowUpPlanListResponse], summary="获取计划列表")
async def list_plans(
    department_id: Optional[str] = None,
    diagnosis_code: Optional[str] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpPlanService(db)
    plans, total = await service.get_list(
        department_id=department_id,
        diagnosis_code=diagnosis_code,
        status=status,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=[build_plan_list_response(p) for p in plans], total=total, page=page, page_size=page_size)


@router.get("/plans/{plan_id}", response_model=FollowUpPlanResponse, summary="获取计划详情")
async def get_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpPlanService(db)
    plan = await service.get_by_id(plan_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访计划不存在")
    return build_plan_response(plan)


@router.post("/plans", response_model=FollowUpPlanResponse, summary="创建计划")
async def create_plan(
    data: FollowUpPlanCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpPlanService(db)
    plan = await service.create(data, operator_id=operator_id)
    plan = await service.get_by_id(plan.id)
    return build_plan_response(plan)


@router.put("/plans/{plan_id}", response_model=FollowUpPlanResponse, summary="更新计划")
async def update_plan(
    plan_id: str,
    data: FollowUpPlanUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpPlanService(db)
    plan = await service.update(plan_id, data, operator_id=operator_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访计划不存在")
    plan = await service.get_by_id(plan_id)
    return build_plan_response(plan)


@router.put("/plans/{plan_id}/steps", response_model=FollowUpPlanResponse, summary="替换计划步骤")
async def update_plan_steps(
    plan_id: str,
    data: FollowUpPlanStepsUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpPlanService(db)
    plan = await service.update_steps(plan_id, data.steps, operator_id=operator_id)
    if not plan:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访计划不存在")
    return build_plan_response(plan)


@router.delete("/plans/{plan_id}", summary="删除计划")
async def delete_plan(
    plan_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpPlanService(db)
    success = await service.delete(plan_id, operator_id=operator_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访计划不存在")
    return {"message": "删除成功"}


# ========== 随访任务端点 ==========

@router.get("/tasks", response_model=PageResponse[FollowUpTaskListResponse], summary="获取任务列表")
async def list_tasks(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpTaskService(db)
    tasks, total = await service.get_list(
        doctor_id=doctor_id,
        patient_id=patient_id,
        department_id=department_id,
        status=status,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=[build_task_list_response(t) for t in tasks], total=total, page=page, page_size=page_size)


@router.get("/tasks/my", response_model=PageResponse[FollowUpTaskListResponse], summary="获取我的任务")
async def get_my_tasks(
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    doctor_id = current_user.get("doctor_id")
    if not doctor_id:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)
    service = FollowUpTaskService(db)
    tasks, total = await service.get_list(doctor_id=doctor_id, status=status, page=page, page_size=page_size)
    return PageResponse(data=[build_task_list_response(t) for t in tasks], total=total, page=page, page_size=page_size)


@router.get("/tasks/my-patient", response_model=PageResponse[FollowUpTaskListResponse], summary="获取当前患者的随访任务")
async def get_my_patient_tasks(
    patient_id: Optional[str] = Query(None, description="就诊人 ID，不传则取默认就诊人"),
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    """患者端专用：从 token 解析就诊人，查询随访任务。支持传入 patient_id 查看家庭成员数据。"""
    user_id = current_user.get("id")
    tenant_id = get_current_tenant_id()
    if not user_id:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)

    patient = await _resolve_patient(db, user_id, tenant_id, patient_id)
    if not patient:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)

    service = FollowUpTaskService(db)
    tasks, total = await service.get_list(patient_id=patient.id, status=status, page=page, page_size=page_size)
    return PageResponse(data=[build_task_list_response(t) for t in tasks], total=total, page=page, page_size=page_size)


@router.get("/tasks/overdue", response_model=PageResponse[FollowUpTaskListResponse], summary="获取逾期任务（管理员专用）")
async def get_overdue_tasks(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_admin),
):
    service = FollowUpTaskService(db)
    tasks, total = await service.get_list(status="overdue", page=page, page_size=page_size)
    return PageResponse(data=[build_task_list_response(t) for t in tasks], total=total, page=page, page_size=page_size)


@router.get("/tasks/patient/{patient_id}", response_model=PageResponse[FollowUpTaskListResponse], summary="获取患者任务")
async def get_patient_tasks(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpTaskService(db)
    tasks, total = await service.get_list(patient_id=patient_id, page=page, page_size=page_size)
    return PageResponse(data=[build_task_list_response(t) for t in tasks], total=total, page=page, page_size=page_size)


@router.get("/tasks/{task_id}", response_model=FollowUpTaskResponse, summary="获取任务详情")
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpTaskService(db)
    task = await service.get_by_id(task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访任务不存在")
    return build_task_response(task)


@router.post("/tasks", response_model=FollowUpTaskResponse, summary="手动创建任务")
async def create_task(
    data: FollowUpTaskCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpTaskService(db)
    task = await service.create(data, operator_id=operator_id)
    task = await service.get_by_id(task.id)
    return build_task_response(task)


@router.post("/tasks/generate", response_model=list[FollowUpTaskResponse], summary="从计划生成任务")
async def generate_tasks(
    data: FollowUpTaskGenerateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpTaskService(db)
    try:
        tasks = await service.generate_from_plan(
            patient_id=data.patient_id,
            doctor_id=data.doctor_id,
            department_id=data.department_id,
            plan_id=data.plan_id,
            appointment_id=data.appointment_id,
            medical_record_id=data.medical_record_id,
            base_date=data.base_date,
            operator_id=operator_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    return [build_task_response(t) for t in tasks]


@router.patch("/tasks/{task_id}/complete", response_model=FollowUpTaskResponse, summary="完成任务")
async def complete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpTaskService(db)
    try:
        task = await service.complete_task(task_id, operator_id=operator_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访任务不存在")
    return build_task_response(task)


@router.patch("/tasks/{task_id}/skip", response_model=FollowUpTaskResponse, summary="跳过任务")
async def skip_task(
    task_id: str,
    data: FollowUpTaskSkipRequest,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpTaskService(db)
    try:
        task = await service.skip_task(task_id, reason=data.reason, operator_id=operator_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访任务不存在")
    return build_task_response(task)


@router.delete("/tasks/{task_id}", summary="删除任务")
async def delete_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpTaskService(db)
    success = await service.delete(task_id, operator_id=operator_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访任务不存在")
    return {"message": "删除成功"}


# ========== 随访记录端点 ==========

@router.get("/records", response_model=PageResponse[FollowUpRecordListResponse], summary="获取记录列表")
async def list_records(
    doctor_id: Optional[str] = None,
    patient_id: Optional[str] = None,
    task_id: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    keyword: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpRecordService(db)
    records, total = await service.get_list(
        doctor_id=doctor_id,
        patient_id=patient_id,
        task_id=task_id,
        start_date=start_date,
        end_date=end_date,
        keyword=keyword,
        page=page,
        page_size=page_size,
    )
    return PageResponse(data=[build_record_list_response(r) for r in records], total=total, page=page, page_size=page_size)


@router.get("/records/patient/{patient_id}", response_model=PageResponse[FollowUpRecordListResponse], summary="获取患者记录")
async def get_patient_records(
    patient_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpRecordService(db)
    records, total = await service.get_list(patient_id=patient_id, page=page, page_size=page_size)
    return PageResponse(data=[build_record_list_response(r) for r in records], total=total, page=page, page_size=page_size)


@router.get("/records/my-patient", response_model=PageResponse[FollowUpRecordListResponse], summary="获取当前患者的随访记录")
async def get_my_patient_records(
    patient_id: Optional[str] = Query(None, description="就诊人 ID，不传则取默认就诊人"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    """患者端专用：从 token 解析就诊人，查询随访记录。支持传入 patient_id 查看家庭成员数据。"""
    user_id = current_user.get("id")
    tenant_id = get_current_tenant_id()
    if not user_id:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)

    patient = await _resolve_patient(db, user_id, tenant_id, patient_id)
    if not patient:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)

    service = FollowUpRecordService(db)
    records, total = await service.get_list(patient_id=patient.id, page=page, page_size=page_size)
    return PageResponse(data=[build_record_list_response(r) for r in records], total=total, page=page, page_size=page_size)


@router.get("/records/task/{task_id}", response_model=list[FollowUpRecordResponse], summary="获取任务记录")
async def get_task_records(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpRecordService(db)
    records, _ = await service.get_list(task_id=task_id, page=1, page_size=100)
    return [build_record_response(r) for r in records]


@router.get("/records/{record_id}", response_model=FollowUpRecordResponse, summary="获取记录详情")
async def get_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = FollowUpRecordService(db)
    record = await service.get_by_id(record_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访记录不存在")
    return build_record_response(record)


@router.post("/records", response_model=FollowUpRecordResponse, summary="创建记录")
async def create_record(
    data: FollowUpRecordCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpRecordService(db)
    record = await service.create(data, operator_id=operator_id)
    record = await service.get_by_id(record.id)
    return build_record_response(record)


@router.put("/records/{record_id}", response_model=FollowUpRecordResponse, summary="更新记录")
async def update_record(
    record_id: str,
    data: FollowUpRecordUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpRecordService(db)
    record = await service.update(record_id, data, operator_id=operator_id)
    if not record:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访记录不存在")
    record = await service.get_by_id(record_id)
    return build_record_response(record)


@router.delete("/records/{record_id}", summary="删除记录")
async def delete_record(
    record_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    operator_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = FollowUpRecordService(db)
    success = await service.delete(record_id, operator_id=operator_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="随访记录不存在")
    return {"message": "删除成功"}


# ========== 统计端点 ==========

@router.get("/statistics", summary="随访统计概览")
async def get_statistics(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    conditions = [FollowUpTask.deleted_at.is_(None)]
    tenant_id = get_current_tenant_id()
    if tenant_id:
        conditions.append(FollowUpTask.tenant_id == tenant_id)
    if start_date:
        conditions.append(FollowUpTask.scheduled_date >= start_date)
    if end_date:
        conditions.append(FollowUpTask.scheduled_date <= end_date)

    # 按状态统计
    status_query = (
        select(
            FollowUpTask.status,
            func.count(FollowUpTask.id).label("count"),
        )
        .where(and_(*conditions))
        .group_by(FollowUpTask.status)
    )
    status_result = await db.execute(status_query)
    status_stats = {row.status: row.count for row in status_result}

    total = sum(status_stats.values())
    completed = status_stats.get("completed", 0)
    overdue = status_stats.get("overdue", 0)
    skipped = status_stats.get("skipped", 0)
    pending = status_stats.get("pending", 0)

    # 医生工作量排行 Top 10
    doctor_query = (
        select(
            FollowUpTask.doctor_id,
            Doctor.name.label("doctor_name"),
            func.count(FollowUpTask.id).label("total"),
            func.sum(case((FollowUpTask.status == "completed", 1), else_=0)).label("completed"),
        )
        .join(Doctor, FollowUpTask.doctor_id == Doctor.id)
        .where(and_(*conditions))
        .group_by(FollowUpTask.doctor_id, Doctor.name)
        .order_by(func.count(FollowUpTask.id).desc())
        .limit(10)
    )
    doctor_result = await db.execute(doctor_query)
    doctor_ranking = [
        {
            "doctorId": row.doctor_id,
            "doctorName": row.doctor_name,
            "total": row.total,
            "completed": row.completed or 0,
            "rate": round((row.completed or 0) / row.total * 100, 1) if row.total > 0 else 0,
        }
        for row in doctor_result
    ]

    return {
        "total": total,
        "completed": completed,
        "overdue": overdue,
        "skipped": skipped,
        "pending": pending,
        "completionRate": round(completed / total * 100, 1) if total > 0 else 0,
        "overdueRate": round(overdue / total * 100, 1) if total > 0 else 0,
        "doctorRanking": doctor_ranking,
    }


# ========== 患者自报告端点 ==========

def _build_self_report_response(report: FollowUpSelfReport) -> dict:
    """构建自报告响应，手动解析 attachments JSON"""
    import json
    attachments = None
    if report.attachments:
        try:
            attachments = json.loads(report.attachments)
        except (json.JSONDecodeError, TypeError):
            attachments = None
    return {
        "id": report.id,
        "task_id": report.task_id,
        "patient_id": report.patient_id,
        "patient_name": getattr(report, "patient_name", None),
        "report_date": report.report_date,
        "systolic_bp": report.systolic_bp,
        "diastolic_bp": report.diastolic_bp,
        "blood_glucose": float(report.blood_glucose) if report.blood_glucose is not None else None,
        "heart_rate": report.heart_rate,
        "temperature": float(report.temperature) if report.temperature is not None else None,
        "symptoms": report.symptoms,
        "patient_condition": report.patient_condition,
        "notes": report.notes,
        "attachments": attachments,
        "status": report.status,
        "reviewed_at": report.reviewed_at,
        "reviewed_by": report.reviewed_by,
        "created_at": report.created_at,
    }


@router.post("/self-reports", response_model=SelfReportResponse, summary="创建自报告")
async def create_self_report(
    data: SelfReportCreate,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    """患者端专用：从 token 解析就诊人，创建自报告"""
    user_id = current_user.get("id")
    tenant_id = get_current_tenant_id()
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    patient = await _resolve_patient(db, user_id, tenant_id)
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未找到就诊人信息")

    service = SelfReportService(db)
    report = await service.create(data, patient_id=patient.id, operator_id=user_id)
    report.patient_name = patient.name
    return _build_self_report_response(report)


@router.get("/self-reports/my", response_model=PageResponse[SelfReportListResponse], summary="获取当前患者的自报告列表")
async def get_my_self_reports(
    task_id: Optional[str] = Query(None, description="按任务ID筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    """患者端专用：获取当前患者的自报告列表"""
    user_id = current_user.get("id")
    tenant_id = get_current_tenant_id()
    if not user_id:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)

    patient = await _resolve_patient(db, user_id, tenant_id)
    if not patient:
        return PageResponse(data=[], total=0, page=page, page_size=page_size)

    service = SelfReportService(db)
    reports, total = await service.get_list(
        patient_id=patient.id,
        task_id=task_id,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_build_self_report_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/self-reports/task/{task_id}", response_model=list[SelfReportListResponse], summary="获取任务关联的自报告")
async def get_task_self_reports(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = SelfReportService(db)
    reports, _ = await service.get_list(task_id=task_id, page=1, page_size=100)
    return [_build_self_report_response(r) for r in reports]


@router.get("/self-reports", response_model=PageResponse[SelfReportListResponse], summary="自报告列表（管理端）")
async def get_self_reports(
    patient_id: Optional[str] = Query(None, description="按患者ID筛选"),
    task_id: Optional[str] = Query(None, description="按任务ID筛选"),
    status_filter: Optional[str] = Query(None, alias="status", description="按状态筛选"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=settings.MAX_PAGE_SIZE),
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = SelfReportService(db)
    reports, total = await service.get_list(
        patient_id=patient_id,
        task_id=task_id,
        status=status_filter,
        page=page,
        page_size=page_size,
    )
    return PageResponse(
        data=[_build_self_report_response(r) for r in reports],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/self-reports/{report_id}", response_model=SelfReportResponse, summary="获取自报告详情")
async def get_self_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    service = SelfReportService(db)
    report = await service.get_by_id(report_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="自报告不存在")
    return _build_self_report_response(report)


@router.patch("/self-reports/{report_id}/review", response_model=SelfReportResponse, summary="审核自报告")
async def review_self_report(
    report_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user_or_admin),
):
    reviewer_id = current_user.get("doctor_id") or current_user.get("admin_id") or current_user.get("sub")
    service = SelfReportService(db)
    report = await service.review(report_id, reviewer_id)
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="自报告不存在")
    return _build_self_report_response(report)
