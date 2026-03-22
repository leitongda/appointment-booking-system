"""导出相关端点"""
from datetime import datetime
from io import BytesIO

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
from typing import Optional, Union, List

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.common.deps import get_store_filter, check_store_access
from app.services.excel_service import ExcelExportService
from app.models.doctor import Doctor
from app.models.user import Patient
from app.models.department import Department
from app.models.store import Store


router = APIRouter()


def _apply_store_filter(
    query,
    model_store_field,
    store_ids: Optional[Union[str, List[str]]]
):
    """应用门店过滤条件

    Args:
        store_ids:
            - None 或空字符串: 不过滤（超管或未绑定门店）
            - str: 单个门店ID
            - List[str]: 多个门店ID列表（空列表不过滤）
    """
    # None 或空字符串不过滤
    if not store_ids:
        return query
    if isinstance(store_ids, list):
        # 空列表不过滤
        if not store_ids:
            return query
        return query.where(model_store_field.in_(store_ids))
    return query.where(model_store_field == store_ids)


@router.get("/doctors", summary="导出医生列表")
async def export_doctors(
    store_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出医生列表"""
    # 获取门店过滤条件
    filter_store_ids = get_store_filter(current_admin)

    # 如果用户传了 store_id，验证权限
    if store_id and not current_admin.get("is_super_admin"):
        if not check_store_access(current_admin, store_id):
            store_id = None  # 无权限访问该门店，忽略该参数

    # 确定最终的门店过滤条件
    # 优先使用用户传入的 store_id（已验证权限），否则使用自动过滤
    final_store_ids = store_id if store_id else filter_store_ids

    query = select(Doctor).options(
        selectinload(Doctor.store),
        selectinload(Doctor.department),
    )

    # 应用门店过滤
    query = _apply_store_filter(query, Doctor.store_id, final_store_ids)

    if department_id:
        query = query.where(Doctor.department_id == department_id)
    if status is not None:
        query = query.where(Doctor.status == status)

    query = query.order_by(Doctor.created_at.desc())
    result = await db.execute(query)
    doctors = result.unique().scalars().all()

    headers = ["姓名", "性别", "手机号", "所属门店", "所属科室", "职称", "擅长", "标签", "状态"]
    data = []

    gender_map = {0: "未知", 1: "男", 2: "女"}
    status_map = {0: "离职", 1: "在职"}

    for d in doctors:
        data.append([
            d.name,
            gender_map.get(d.gender, ""),
            d.phone or "",
            d.store.name if d.store else "",
            d.department.name if d.department else "",
            d.title or "",
            d.specialty or "",
            d.tags or "",
            status_map.get(d.status, ""),
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "医生列表")
    filename = f"doctors_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/patients", summary="导出患者列表")
async def export_patients(
    keyword: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出患者列表"""
    query = select(Patient)
    if keyword:
        from sqlalchemy import or_
        query = query.where(
            or_(
                Patient.name.ilike(f"%{keyword}%"),
                Patient.phone.ilike(f"%{keyword}%")
            )
        )
    query = query.order_by(Patient.created_at.desc())
    result = await db.execute(query)
    patients = result.scalars().all()
    headers = ["就诊卡编号", "姓名", "手机号", "身份证号", "性别", "出生日期", "与本人关系", "省", "市", "区", "详细地址", "创建时间"]
    data = []
    gender_map = {0: "未知", 1: "男", 2: "女"}
    for p in patients:
        data.append([
            p.card_no or "",
            p.name,
            p.phone,
            p.id_card or "",
            gender_map.get(p.gender, ""),
            str(p.birthday) if p.birthday else "",
            p.relationship or "",
            p.province or "",
            p.city or "",
            p.district or "",
            p.address or "",
            p.created_at.strftime("%Y-%m-%d %H:%M:%S") if p.created_at else "",
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "患者列表")
    filename = f"patients_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/departments", summary="导出科室列表")
async def export_departments(
    store_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出科室列表"""
    # 获取门店过滤条件
    filter_store_ids = get_store_filter(current_admin)

    # 如果用户传了 store_id，验证权限
    if store_id and not current_admin.get("is_super_admin"):
        if not check_store_access(current_admin, store_id):
            store_id = None

    final_store_ids = store_id if store_id else filter_store_ids

    query = select(Department).options(selectinload(Department.store))

    # 应用门店过滤
    query = _apply_store_filter(query, Department.store_id, final_store_ids)

    if status is not None:
        query = query.where(Department.status == status)
    query = query.order_by(Department.sort_order)
    result = await db.execute(query)
    departments = result.unique().scalars().all()
    headers = ["科室名称", "所属门店", "科室标签", "排序", "是否终极科室", "是否推荐", "是否热门", "状态"]
    data = []
    for d in departments:
        data.append([
            d.name,
            d.store.name if d.store else "",
            d.tag or "",
            d.sort_order,
            "是" if d.is_final else "否",
            "是" if d.is_recommended else "否",
            "是" if d.is_hot else "否",
            "启用" if d.status == 1 else "禁用",
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "科室列表")
    filename = f"departments_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/stores", summary="导出门店列表")
async def export_stores(
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出门店列表"""
    # 获取门店过滤条件
    filter_store_ids = get_store_filter(current_admin)

    query = select(Store)

    # 应用门店过滤（非超管只能导出自己绑定的门店）
    query = _apply_store_filter(query, Store.id, filter_store_ids)

    if status is not None:
        query = query.where(Store.status == status)
    query = query.order_by(Store.created_at.desc())
    result = await db.execute(query)
    stores = result.scalars().all()
    headers = ["门店名称", "门店编码", "城市", "地址", "联系电话", "营业时间", "状态"]
    data = []
    for s in stores:
        data.append([
            s.name,
            s.code or "",
            s.city or "",
            s.address or "",
            s.phone or "",
            s.business_hours or "",
            "营业" if s.status == 1 else "停业",
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "门店列表")
    filename = f"stores_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 排班模板导出 ====================

@router.get("/schedule-templates", summary="导出排班模板列表")
async def export_schedule_templates(
    store_id: Optional[str] = None,
    doctor_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出排班模板列表"""
    from app.models.schedule_template import ScheduleTemplate
    from sqlalchemy.orm import selectinload

    # 获取门店过滤条件
    filter_store_ids = get_store_filter(current_admin)

    # 如果用户传了 store_id，验证权限
    if store_id and not current_admin.get("is_super_admin"):
        if not check_store_access(current_admin, store_id):
            store_id = None

    final_store_ids = store_id if store_id else filter_store_ids

    query = select(ScheduleTemplate).options(
        selectinload(ScheduleTemplate.store),
        selectinload(ScheduleTemplate.doctor),
        selectinload(ScheduleTemplate.department),
    )

    # 应用门店过滤
    query = _apply_store_filter(query, ScheduleTemplate.store_id, final_store_ids)

    if doctor_id:
        query = query.where(ScheduleTemplate.doctor_id == doctor_id)
    if status is not None:
        query = query.where(ScheduleTemplate.status == status)
    query = query.order_by(ScheduleTemplate.created_at.desc())
    result = await db.execute(query)
    templates = result.unique().scalars().all()
    headers = ["模板名称", "门店", "医生", "科室", "星期", "预约类型", "开始时间", "结束时间", "预约人数", "排班方式", "状态"]
    data = []

    weekday_map = {0: "周日", 1: "周一", 2: "周二", 3: "周三", 4: "周四", 5: "周五", 6: "周六"}
    type_map = {"normal": "普通", "expert": "专家", "urgent": "急诊"}
    mode_map = {"weekly": "每周", "biweekly_odd": "双周奇", "biweekly_even": "双周偶", "monthly": "每月"}
    status_map = {0: "禁用", 1: "启用"}
    for t in templates:
        # 格式化星期列表
        weekdays_str = ",".join([weekday_map.get(w, str(w)) for w in t.weekday_list]) if t.weekday_list else ""
        # 格式化时间
        start_time_str = t.start_time.strftime("%H:%M") if t.start_time else ""
        end_time_str = t.end_time.strftime("%H:%M") if t.end_time else ""
        data.append([
            t.name or "",
            t.store.name if t.store else "",
            t.doctor.name if t.doctor else "",
            t.department.name if t.department else "",
            weekdays_str,
            type_map.get(t.appointment_type, t.appointment_type or ""),
            start_time_str,
            end_time_str,
            t.slot_capacity or 0,
            mode_map.get(t.schedule_mode, t.schedule_mode or ""),
            status_map.get(t.status, ""),
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "排班模板")
    filename = f"schedule_templates_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 系统用户导出 ====================

@router.get("/users", summary="导出系统用户列表")
async def export_users(
    store_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出系统用户列表"""
    from app.models.admin import Admin, admin_stores
    from sqlalchemy.orm import selectinload

    # 获取门店过滤条件
    filter_store_ids = get_store_filter(current_admin)

    # 如果用户传了 store_id，验证权限
    if store_id and not current_admin.get("is_super_admin"):
        if not check_store_access(current_admin, store_id):
            store_id = None

    final_store_ids = store_id if store_id else filter_store_ids

    query = select(Admin).options(
        selectinload(Admin.role),
        selectinload(Admin.stores),
    )

    # 应用门店过滤（多对多关系）
    if final_store_ids is not None:
        if isinstance(final_store_ids, list):
            query = query.join(admin_stores).where(admin_stores.c.store_id.in_(final_store_ids))
        else:
            query = query.join(admin_stores).where(admin_stores.c.store_id == final_store_ids)

    if status is not None:
        query = query.where(Admin.status == status)
    query = query.order_by(Admin.created_at.desc())
    result = await db.execute(query)
    users = result.unique().scalars().all()
    headers = ["账号", "用户名", "手机号", "角色", "所属门店", "状态", "最后登录时间"]
    data = []

    status_map = {0: "禁用", 1: "启用"}
    for u in users:
        # 获取角色名称
        role_name = u.role.name if u.role else ""
        # 获取所属门店名称
        store_names = ",".join([s.name for s in u.stores]) if u.stores else "全局"

        data.append([
            u.username or "",
            u.name or "",
            u.phone or "",
            role_name,
            store_names,
            status_map.get(u.status, ""),
            u.last_login_at.strftime("%Y-%m-%d %H:%M:%S") if u.last_login_at else "",
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "系统用户")
    filename = f"users_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 操作日志导出 ====================

@router.get("/logs", summary="导出操作日志")
async def export_logs(
    module: Optional[str] = None,
    log_result: Optional[str] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出操作日志"""
    from app.models.admin import OperationLog
    from sqlalchemy import and_

    query = select(OperationLog)
    conditions = []
    if module:
        conditions.append(OperationLog.module == module)
    if log_result:
        conditions.append(OperationLog.result == log_result)
    if start_time:
        conditions.append(OperationLog.created_at >= start_time)
    if end_time:
        conditions.append(OperationLog.created_at <= end_time)
    if conditions:
        query = query.where(and_(*conditions))
    query = query.order_by(OperationLog.created_at.desc()).limit(10000)
    result_db = await db.execute(query)
    logs = result_db.scalars().all()
    headers = ["操作人", "模块", "操作", "方法", "路径", "结果", "IP", "耗时(ms)", "时间"]
    data = []

    for log in logs:
        data.append([
            log.admin_name or "",
            log.module or "",
            log.action or "",
            log.method or "",
            log.path or "",
            log.result or "",
            log.ip or "",
            log.duration or 0,
            log.created_at.strftime("%Y-%m-%d %H:%M:%S") if log.created_at else "",
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "操作日志")
    filename = f"logs_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 用户反馈导出 ====================

@router.get("/feedbacks", summary="导出用户反馈")
async def export_feedbacks(
    status: Optional[str] = None,
    feedback_type: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出用户反馈"""
    from app.models.feedback import Feedback

    query = select(Feedback)
    if status:
        query = query.where(Feedback.status == status)
    if feedback_type:
        query = query.where(Feedback.feedback_type == feedback_type)
    query = query.order_by(Feedback.created_at.desc())
    result_db = await db.execute(query)
    feedbacks = result_db.scalars().all()
    headers = ["标题", "类型", "内容", "联系方式", "状态", "提交时间", "回复内容", "回复时间"]
    data = []

    type_map = {"suggestion": "建议", "complaint": "投诉", "bug": "故障", "other": "其他"}
    status_map = {"pending": "待处理", "processing": "处理中", "resolved": "已解决", "closed": "已关闭"}
    for f in feedbacks:
        data.append([
            f.title or "",
            type_map.get(f.feedback_type, f.feedback_type or ""),
            f.content or "",
            f.contact or "",
            status_map.get(f.status, f.status or ""),
            f.created_at.strftime("%Y-%m-%d %H:%M:%S") if f.created_at else "",
            f.reply or "",
            f.handled_at.strftime("%Y-%m-%d %H:%M:%S") if f.handled_at else "",
        ])
    excel_bytes = ExcelExportService.create_workbook(headers, data, "用户反馈")
    filename = f"feedbacks_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


# ==================== 规则组导出 ====================

@router.get("/rule-sets", summary="导出规则组列表")
async def export_rule_sets(
    enabled: Optional[bool] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出规则组列表（多工作表）"""
    from app.models.rule_set import RuleSet
    from sqlalchemy.orm import selectinload

    # 查询所有规则组及其关联数据
    query = select(RuleSet).options(
        selectinload(RuleSet.windows),
        selectinload(RuleSet.booking_policy),
        selectinload(RuleSet.checkin_policy),
        selectinload(RuleSet.capacity_policy),
    )

    if enabled is not None:
        query = query.where(RuleSet.enabled == enabled)

    query = query.order_by(RuleSet.priority, RuleSet.created_at.desc())
    result = await db.execute(query)
    rule_sets = result.unique().scalars().all()

    # 准备多工作表数据
    workbook_data = {}

    # 工作表1: 规则组基础信息
    headers1 = ["规则组名称", "优先级", "是否启用", "时间来源", "时区来源", "比较精度",
                "开放边界包含", "截止边界包含", "取整模式", "时钟偏差容忍度(秒)", "描述"]
    data1 = []

    for rs in rule_sets:
        data1.append([
            rs.name,
            rs.priority,
            "是" if rs.enabled else "否",
            rs.time_source,
            rs.timezone_source,
            rs.compare_precision,
            "是" if rs.default_open_inclusive else "否",
            "是" if rs.default_close_inclusive else "否",
            rs.rounding_mode,
            rs.clock_skew_tolerance_sec,
            rs.description or "",
        ])

    workbook_data["规则组"] = {"headers": headers1, "data": data1}

    # 工作表2: 时间窗配置
    headers2 = ["规则组名称", "动作类型", "参考点", "开放偏移(秒)", "截止偏移(秒)",
                "开放边界包含", "截止边界包含", "失败策略", "失败标签", "是否启用", "描述"]
    data2 = []

    for rs in rule_sets:
        for window in rs.windows:
            data2.append([
                rs.name,
                window.action,
                window.reference_point,
                window.open_offset_sec,
                window.close_offset_sec,
                "是" if window.open_inclusive else "否" if window.open_inclusive is not None else "",
                "是" if window.close_inclusive else "否" if window.close_inclusive is not None else "",
                window.fail_policy,
                window.fail_tag or "",
                "是" if window.enabled else "否",
                window.description or "",
            ])

    workbook_data["时间窗"] = {"headers": headers2, "data": data2}

    # 工作表3: 预约策略
    headers3 = ["规则组名称", "要求登录", "要求档案完整", "每用户每班次", "每用户每天", "每用户每周",
                "同班次冲突策略", "时间重叠策略", "同类型同日策略"]
    data3 = []

    for rs in rule_sets:
        bp = rs.booking_policy
        if bp:
            data3.append([
                rs.name,
                "是" if bp.require_auth else "否",
                "是" if bp.require_patient_profile_complete else "否",
                bp.per_user_per_shift,
                bp.per_user_per_day or "",
                bp.per_user_per_week or "",
                bp.conflict_same_shift,
                bp.conflict_overlap_time,
                bp.conflict_same_type_same_day,
            ])
    workbook_data["预约策略"] = {"headers": headers3, "data": data3}

    # 工作表4: 签到策略
    headers4 = ["规则组名称", "必须预约", "允许现场补约", "允许签到次数", "记录审计日志",
                "宽限期(秒)", "宽限后状态", "截止后未签到处理"]
    data4 = []

    for rs in rule_sets:
        cp = rs.checkin_policy
        if cp:
            data4.append([
                rs.name,
                "是" if cp.require_booking else "否",
                "是" if cp.allow_onsite_booking else "否",
                cp.max_times,
                "是" if cp.audit_log else "否",
                cp.grace_period_sec,
                cp.after_grace_status or "",
                cp.no_checkin_after_close,
            ])
    workbook_data["签到策略"] = {"headers": headers4, "data": data4}

    # 工作表5: 容量策略
    headers5 = ["规则组名称", "总容量", "每用户容量", "启用候补", "候补队列最大长度",
                "候补递补策略", "允许超额", "超额最大数量"]
    data5 = []

    for rs in rule_sets:
        cap = rs.capacity_policy
        if cap:
            data5.append([
                rs.name,
                cap.total_capacity,
                cap.per_user_capacity,
                "是" if cap.waitlist_enabled else "否",
                cap.waitlist_max_size,
                cap.waitlist_promote_policy,
                "是" if cap.overbooking_enabled else "否",
                cap.overbooking_max,
            ])
    workbook_data["容量策略"] = {"headers": headers5, "data": data5}

    # 创建多工作表Excel
    excel_bytes = ExcelExportService.create_multi_sheet_workbook(workbook_data)
    filename = f"rule_sets_{datetime.now().strftime('%Y%m%d%H%M%S')}.xlsx"
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
