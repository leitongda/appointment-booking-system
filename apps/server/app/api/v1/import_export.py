"""数据导入导出 API"""
from fastapi import APIRouter, Depends, Query, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from datetime import date, datetime
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_current_admin
from app.services.excel_service import ExcelExportService, ExcelImportService
from app.services.import_service import ImportService
from app.models.doctor import Doctor
from app.models.user import Patient
from app.models.department import Department
from app.models.store import Store
from sqlalchemy import select

router = APIRouter()


# ==================== 导出接口 ====================

@router.get("/export/doctors")
async def export_doctors(
    store_id: Optional[str] = None,
    department_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出医生列表"""
    from sqlalchemy.orm import selectinload
    
    query = select(Doctor).options(
        selectinload(Doctor.store),
        selectinload(Doctor.department),
    )
    
    if store_id:
        query = query.where(Doctor.store_id == store_id)
    if department_id:
        query = query.where(Doctor.department_id == department_id)
    if status is not None:
        query = query.where(Doctor.status == status)
    
    query = query.order_by(Doctor.created_at.desc())
    result = await db.execute(query)
    doctors = result.unique().scalars().all()
    
    headers = ["姓名", "性别", "手机号", "所属门店", "所属科室", "职称", "擅长", "标签", "状态"]
    data = []
    
    gender_map = {1: "男", 2: "女"}
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


@router.get("/export/patients")
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


@router.get("/export/departments")
async def export_departments(
    store_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出科室列表"""
    from sqlalchemy.orm import selectinload
    
    query = select(Department).options(selectinload(Department.store))
    
    if store_id:
        query = query.where(Department.store_id == store_id)
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


@router.get("/export/stores")
async def export_stores(
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出门店列表"""
    query = select(Store)
    
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


# ==================== 导入模板下载 ====================

@router.get("/template/doctors")
async def download_doctor_template(
    current_admin = Depends(get_current_admin),
):
    """下载医生导入模板"""
    headers = ["姓名", "性别", "手机号", "门店名称", "科室名称", "职称", "擅长", "标签"]
    required_fields = ["姓名", "门店名称", "科室名称"]
    sample_data = [
        ["张医生", "男", "13800138000", "总院", "内科", "主任医师", "心血管疾病", "专家,推荐"],
        ["李医生", "女", "13900139000", "分院", "外科", "副主任医师", "骨科手术", "骨科专家"],
    ]
    field_notes = {
        "姓名": "必填，医生姓名",
        "性别": "男/女",
        "手机号": "11位手机号",
        "门店名称": "必填，需与系统中门店名称一致",
        "科室名称": "必填，需与系统中科室名称一致",
        "职称": "如：主任医师、副主任医师、主治医师等",
        "擅长": "医生擅长的领域",
        "标签": "多个标签用逗号分隔",
    }
    
    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)
    
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=doctor_import_template.xlsx"}
    )


@router.get("/template/patients")
async def download_patient_template(
    current_admin = Depends(get_current_admin),
):
    """下载患者导入模板"""
    headers = ["姓名", "手机号", "身份证号", "性别", "出生日期", "与本人关系", "省", "市", "区", "详细地址"]
    required_fields = ["姓名", "手机号"]
    sample_data = [
        ["张三", "13800138000", "110101199001011234", "男", "1990-01-01", "本人", "北京市", "北京市", "朝阳区", "xx街道xx号"],
        ["李四", "13900139000", "110101199502021234", "女", "1995-02-02", "配偶", "北京市", "北京市", "海淀区", "xx路xx号"],
    ]
    field_notes = {
        "姓名": "必填，患者姓名",
        "手机号": "必填，11位手机号",
        "身份证号": "18位身份证号",
        "性别": "男/女",
        "出生日期": "格式：YYYY-MM-DD",
        "与本人关系": "本人/父亲/母亲/配偶/子女/其他",
        "省": "省份",
        "市": "城市",
        "区": "区县",
        "详细地址": "详细地址",
    }
    
    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)
    
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=patient_import_template.xlsx"}
    )


@router.get("/template/departments")
async def download_department_template(
    current_admin = Depends(get_current_admin),
):
    """下载科室导入模板"""
    headers = ["科室名称", "门店名称", "科室标签", "排序", "是否终极科室", "是否推荐", "是否热门"]
    required_fields = ["科室名称", "门店名称"]
    sample_data = [
        ["内科", "总院", "常见病", "1", "是", "是", "是"],
        ["外科", "总院", "手术", "2", "是", "否", "否"],
    ]
    field_notes = {
        "科室名称": "必填，科室名称",
        "门店名称": "必填，需与系统中门店名称一致",
        "科室标签": "科室标签",
        "排序": "数字，越小越靠前",
        "是否终极科室": "是/否，终极科室可绑定医生",
        "是否推荐": "是/否",
        "是否热门": "是/否",
    }
    
    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)
    
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=department_import_template.xlsx"}
    )


@router.get("/template/stores")
async def download_store_template(
    current_admin = Depends(get_current_admin),
):
    """下载门店导入模板"""
    headers = ["门店名称", "门店编码", "城市", "地址", "联系电话", "营业时间"]
    required_fields = ["门店名称", "城市"]
    sample_data = [
        ["总院", "STORE001", "北京", "北京市朝阳区xx路xx号", "010-12345678", "08:00-17:00"],
        ["分院", "STORE002", "上海", "上海市浦东新区xx路xx号", "021-12345678", "08:30-17:30"],
    ]
    field_notes = {
        "门店名称": "必填，门店名称",
        "门店编码": "门店唯一编码",
        "城市": "必填，所在城市",
        "地址": "详细地址",
        "联系电话": "联系电话",
        "营业时间": "如：08:00-17:00",
    }
    
    excel_bytes = ExcelImportService.create_template(headers, sample_data, required_fields, field_notes)
    
    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=store_import_template.xlsx"}
    )


# ==================== 导入接口 ====================

@router.post("/import/doctors")
async def import_doctors(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导入医生数据"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")
    
    content = await file.read()
    
    headers = ["姓名", "性别", "手机号", "门店名称", "科室名称", "职称", "擅长", "标签"]
    required_fields = ["姓名", "门店名称", "科室名称"]
    
    # 预加载门店和科室映射
    stores_result = await db.execute(select(Store))
    stores = {s.name: s for s in stores_result.scalars().all()}
    
    depts_result = await db.execute(select(Department))
    depts = {d.name: d for d in depts_result.scalars().all()}
    
    gender_map = {"男": 1, "女": 2}
    
    async def process_row(row_data):
        store_name = row_data.get("门店名称")
        dept_name = row_data.get("科室名称")
        
        store = stores.get(store_name)
        if not store:
            raise ValueError(f"门店 '{store_name}' 不存在")
        
        dept = depts.get(dept_name)
        if not dept:
            raise ValueError(f"科室 '{dept_name}' 不存在")
        
        doctor = Doctor(
            name=row_data.get("姓名"),
            gender=gender_map.get(row_data.get("性别"), 1),
            phone=row_data.get("手机号"),
            store_id=store.id,
            store_name=store.name,
            department_id=dept.id,
            department_name=dept.name,
            title=row_data.get("职称"),
            specialty=row_data.get("擅长"),
            tags=row_data.get("标签"),
            status=1,
        )
        db.add(doctor)
    
    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, headers, required_fields, process_row
    )
    
    return result


@router.post("/import/patients")
async def import_patients(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导入患者数据"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")
    
    content = await file.read()
    
    headers = ["姓名", "手机号", "身份证号", "性别", "出生日期", "与本人关系", "省", "市", "区", "详细地址"]
    required_fields = ["姓名", "手机号"]
    
    gender_map = {"男": 1, "女": 2, "未知": 0}
    
    async def process_row(row_data):
        birthday = row_data.get("出生日期")
        if birthday and isinstance(birthday, str):
            try:
                birthday = datetime.strptime(birthday, "%Y-%m-%d").date()
            except:
                birthday = None
        
        patient = Patient(
            name=row_data.get("姓名"),
            phone=row_data.get("手机号"),
            id_card=row_data.get("身份证号"),
            gender=gender_map.get(row_data.get("性别"), 0),
            birthday=birthday,
            relationship=row_data.get("与本人关系") or "本人",
            province=row_data.get("省"),
            city=row_data.get("市"),
            district=row_data.get("区"),
            address=row_data.get("详细地址"),
            source=2,  # 管理员添加
        )
        db.add(patient)
    
    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, headers, required_fields, process_row
    )
    
    return result


@router.post("/import/departments")
async def import_departments(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导入科室数据"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")
    
    content = await file.read()
    
    headers = ["科室名称", "门店名称", "科室标签", "排序", "是否终极科室", "是否推荐", "是否热门"]
    required_fields = ["科室名称", "门店名称"]
    
    # 预加载门店映射
    stores_result = await db.execute(select(Store))
    stores = {s.name: s for s in stores_result.scalars().all()}
    
    def parse_bool(val):
        if val in ["是", "1", 1, True, "true", "True"]:
            return 1
        return 0
    
    async def process_row(row_data):
        store_name = row_data.get("门店名称")
        store = stores.get(store_name)
        if not store:
            raise ValueError(f"门店 '{store_name}' 不存在")
        
        dept = Department(
            name=row_data.get("科室名称"),
            store_id=store.id,
            store_name=store.name,
            tag=row_data.get("科室标签"),
            sort_order=int(row_data.get("排序") or 0),
            is_final=parse_bool(row_data.get("是否终极科室")),
            is_recommended=parse_bool(row_data.get("是否推荐")),
            is_hot=parse_bool(row_data.get("是否热门")),
            status=1,
        )
        db.add(dept)
    
    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, headers, required_fields, process_row
    )
    
    return result


@router.post("/import/stores")
async def import_stores(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导入门店数据"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")
    
    content = await file.read()
    
    headers = ["门店名称", "门店编码", "城市", "地址", "联系电话", "营业时间"]
    required_fields = ["门店名称", "城市"]
    
    async def process_row(row_data):
        store = Store(
            name=row_data.get("门店名称"),
            code=row_data.get("门店编码"),
            city=row_data.get("城市"),
            address=row_data.get("地址"),
            phone=row_data.get("联系电话"),
            business_hours=row_data.get("营业时间"),
            status=1,
        )
        db.add(store)
    
    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, headers, required_fields, process_row
    )
    
    return result


# ==================== 排班模板导出 ====================

@router.get("/export/schedule-templates")
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
    
    query = select(ScheduleTemplate).options(
        selectinload(ScheduleTemplate.store),
        selectinload(ScheduleTemplate.doctor),
        selectinload(ScheduleTemplate.department),
    )
    
    if store_id:
        query = query.where(ScheduleTemplate.store_id == store_id)
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

@router.get("/export/users")
async def export_users(
    store_id: Optional[str] = None,
    status: Optional[int] = None,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导出系统用户列表"""
    from app.models.admin import Admin, admin_stores
    from sqlalchemy.orm import selectinload
    
    query = select(Admin).options(
        selectinload(Admin.role),
        selectinload(Admin.stores),
    )
    
    if store_id:
        # 多对多关系，需要联表查询
        query = query.join(admin_stores).where(admin_stores.c.store_id == store_id)
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

@router.get("/export/logs")
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

@router.get("/export/feedbacks")
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


# ==================== 规则组导入导出 ====================

@router.get("/export/rule-sets")
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


@router.get("/template/rule-sets")
async def download_rule_set_template(
    current_admin = Depends(get_current_admin),
):
    """下载规则组导入模板（多工作表）"""
    workbook_data = {}

    # 工作表1: 规则组基础信息
    headers1 = ["规则组名称", "优先级", "是否启用", "时间来源", "时区来源", "比较精度",
                "开放边界包含", "截止边界包含", "取整模式", "时钟偏差容忍度(秒)", "描述"]
    sample1 = [
        ["普通门诊规则", 100, "是", "SERVER", "HOSPITAL", "SECOND", "是", "是", "NONE", 5, "用于普通门诊"],
        ["专家门诊规则", 90, "是", "SERVER", "HOSPITAL", "SECOND", "是", "是", "NONE", 5, "用于专家门诊"],
    ]
    notes1 = {
        "规则组名称": "必填，唯一标识，用于关联其他工作表",
        "优先级": "数字，越小越优先",
        "是否启用": "是/否",
        "时间来源": "SERVER/CLIENT",
        "时区来源": "HOSPITAL/SHIFT/USER",
        "比较精度": "SECOND/MILLISECOND/MINUTE",
        "开放边界包含": "是/否",
        "截止边界包含": "是/否",
        "取整模式": "NONE/CEILING/FLOOR/ROUND",
        "时钟偏差容忍度(秒)": "秒数",
        "描述": "规则组描述",
    }
    workbook_data["规则组"] = {"headers": headers1, "data": sample1, "field_notes": notes1}

    # 工作表2: 时间窗配置
    headers2 = ["规则组名称", "动作类型", "参考点", "开放偏移(秒)", "截止偏移(秒)",
                "开放边界包含", "截止边界包含", "失败策略", "失败标签", "是否启用", "描述"]
    sample2 = [
        ["普通门诊规则", "BOOK", "SHIFT_START", -86400, 0, "是", "是", "REJECT", "", "是", "预约窗口"],
        ["普通门诊规则", "CHECKIN", "SHIFT_START", -1800, 300, "是", "是", "REJECT", "", "是", "签到窗口"],
        ["普通门诊规则", "CANCEL", "SHIFT_START", -86400, -3600, "是", "是", "REJECT", "", "是", "取消窗口"],
    ]
    notes2 = {
        '规则组名称': '必填，关联到"规则组"工作表的名称',
        "动作类型": "BOOK/CHECKIN/CANCEL/HOLD_RELEASE",
        "参考点": "SHIFT_START/SHIFT_END/BOOKING_CREATED_AT",
        "开放偏移(秒)": "秒数，可负可正",
        "截止偏移(秒)": "秒数，可负可正",
        "开放边界包含": "是/否，为空则使用规则组默认值",
        "截止边界包含": "是/否，为空则使用规则组默认值",
        "失败策略": "REJECT/ALLOW_WITH_TAG/AUTO_TO_WAITLIST",
        "失败标签": "失败时添加的标签",
        "是否启用": "是/否",
        "描述": "时间窗描述",
    }
    workbook_data["时间窗"] = {"headers": headers2, "data": sample2, "field_notes": notes2}

    # 工作表3: 预约策略
    headers3 = ["规则组名称", "要求登录", "要求档案完整", "每用户每班次", "每用户每天", "每用户每周",
                "同班次冲突策略", "时间重叠策略", "同类型同日策略"]
    sample3 = [
        ["普通门诊规则", "是", "否", 1, "", "", "REJECT", "REJECT", "ALLOW"],
        ["专家门诊规则", "是", "是", 1, 1, "", "REJECT", "REJECT", "ALLOW"],
    ]
    notes3 = {
        '规则组名称': '必填，关联到"规则组"工作表的名称',
        "要求登录": "是/否",
        "要求档案完整": "是/否",
        "每用户每班次": "数字",
        "每用户每天": "数字，为空表示不限制",
        "每用户每周": "数字，为空表示不限制",
        "同班次冲突策略": "REJECT/REPLACE",
        "时间重叠策略": "REJECT/ALLOW",
        "同类型同日策略": "REJECT/ALLOW",
    }
    workbook_data["预约策略"] = {"headers": headers3, "data": sample3, "field_notes": notes3}

    # 工作表4: 签到策略
    headers4 = ["规则组名称", "必须预约", "允许现场补约", "允许签到次数", "记录审计日志",
                "宽限期(秒)", "宽限后状态", "截止后未签到处理"]
    sample4 = [
        ["普通门诊规则", "是", "否", 1, "是", 300, "LATE", "KEEP_BOOKED"],
        ["专家门诊规则", "是", "否", 1, "是", 600, "LATE", "ABSENT"],
    ]
    notes4 = {
        '规则组名称': '必填，关联到"规则组"工作表的名称',
        "必须预约": "是/否",
        "允许现场补约": "是/否",
        "允许签到次数": "数字",
        "记录审计日志": "是/否",
        "宽限期(秒)": "秒数",
        "宽限后状态": "LATE/ON_TIME",
        "截止后未签到处理": "KEEP_BOOKED/AUTO_CANCEL/ABSENT",
    }
    workbook_data["签到策略"] = {"headers": headers4, "data": sample4, "field_notes": notes4}

    # 工作表5: 容量策略
    headers5 = ["规则组名称", "总容量", "每用户容量", "启用候补", "候补队列最大长度",
                "候补递补策略", "允许超额", "超额最大数量"]
    sample5 = [
        ["普通门诊规则", 50, 1, "是", 10, "MANUAL", "否", 0],
        ["专家门诊规则", 20, 1, "是", 5, "MANUAL", "否", 0],
    ]
    notes5 = {
        '规则组名称': '必填，关联到"规则组"工作表的名称',
        "总容量": "数字，0表示不限制",
        "每用户容量": "数字",
        "启用候补": "是/否",
        "候补队列最大长度": "数字",
        "候补递补策略": "MANUAL/AUTO",
        "允许超额": "是/否",
        "超额最大数量": "数字",
    }
    workbook_data["容量策略"] = {"headers": headers5, "data": sample5, "field_notes": notes5}

    # 创建多工作表Excel模板
    excel_bytes = ExcelImportService.create_multi_sheet_template(workbook_data)

    return StreamingResponse(
        BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=rule_set_import_template.xlsx"}
    )


@router.post("/import/rule-sets")
async def import_rule_sets(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin),
):
    """导入规则组数据（多工作表）"""
    if not file.filename.endswith(('.xlsx', '.xls')):
        raise HTTPException(status_code=400, detail="请上传 Excel 文件")

    content = await file.read()

    from app.services.rule_set_import_service import RuleSetImportService
    import_service = RuleSetImportService(db)
    result = await import_service.import_rule_sets(content)

    return result

