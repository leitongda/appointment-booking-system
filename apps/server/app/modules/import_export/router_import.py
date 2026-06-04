"""导入相关端点"""
from datetime import date, datetime, time
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_admin, get_store_filter, require_permission
from app.core.config import settings
from app.core.security import get_password_hash
from app.db.session import get_db
from app.modules.import_export.service_import import ImportService
from app.infrastructure.excel.import_service import ExcelImportService
from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.schedule_status import ScheduleStatus
from app.models.store import Store
from app.models.user import Patient, User
from app.middleware.tenant_context import get_current_tenant_id
from app.utils.audit import set_create_audit

router = APIRouter()

SUPPORTED_EXCEL_EXTENSIONS = (".xlsx", ".xls")


def validate_excel_upload(file: UploadFile) -> None:
    filename = (file.filename or "").lower()
    if not filename.endswith(SUPPORTED_EXCEL_EXTENSIONS):
        raise HTTPException(status_code=400, detail="请上传 .xlsx 或 .xls 格式的 Excel 文件")


@router.post("/doctors", summary="导入医生数据")
async def import_doctors(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:create")),
):
    validate_excel_upload(file)

    # 获取租户上下文
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

    content = await file.read()

    headers = ["姓名", "性别", "手机号", "门店名称", "科室名称", "职称", "擅长", "标签"]
    required_fields = ["姓名", "门店名称", "科室名称"]

    # 预加载门店和科室映射（添加租户过滤）
    stores_result = await db.execute(
        select(Store).where(Store.tenant_id == tenant_id)
    )
    stores = {s.name: s for s in stores_result.scalars().all()}

    depts_result = await db.execute(
        select(Department).where(Department.tenant_id == tenant_id)
    )
    depts = {d.name: d for d in depts_result.scalars().all()}

    gender_map = {"未知": 0, "男": 1, "女": 2}

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
            gender=gender_map.get(row_data.get("性别"), 0),
            phone=row_data.get("手机号"),
            store_id=store.id,
            department_id=dept.id,
            title=row_data.get("职称"),
            specialty=row_data.get("擅长"),
            tags=row_data.get("标签"),
            status=1,
            tenant_id=tenant_id,
        )
        db.add(doctor)

    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, file.filename, headers, required_fields, process_row
    )

    return result


@router.post("/patients", summary="导入患者数据")
async def import_patients(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:create")),
):
    validate_excel_upload(file)

    # 获取租户上下文
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

    content = await file.read()

    headers = ["姓名", "手机号", "身份证号", "性别", "出生日期", "与本人关系", "省", "市", "区", "详细地址"]
    required_fields = ["姓名", "手机号"]

    gender_map = {"男": 1, "女": 2, "未知": 0}

    async def process_row(row_data):
        phone = row_data.get("手机号")

        user_result = await db.execute(
            select(User).where(User.phone == phone, User.tenant_id == tenant_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(
                id=str(uuid4()),
                phone=phone,
                password_hash=get_password_hash(settings.DEFAULT_USER_PASSWORD),
                nickname=row_data.get("姓名"),
                status=1,
                tenant_id=tenant_id,
            )
            db.add(user)
            await db.flush()

        birthday = row_data.get("出生日期")
        if birthday and isinstance(birthday, str):
            try:
                birthday = datetime.strptime(birthday, "%Y-%m-%d").date()
            except:
                birthday = None

        patient = Patient(
            user_id=user.id,
            name=row_data.get("姓名"),
            phone=phone,
            id_card=row_data.get("身份证号"),
            gender=gender_map.get(row_data.get("性别"), 0),
            birthday=birthday,
            relationship=row_data.get("与本人关系") or "本人",
            province=row_data.get("省"),
            city=row_data.get("市"),
            district=row_data.get("区"),
            address=row_data.get("详细地址"),
            source=2,  # 管理员添加
            tenant_id=tenant_id,
        )
        db.add(patient)

    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, file.filename, headers, required_fields, process_row
    )

    return result


@router.post("/departments", summary="导入科室数据")
async def import_departments(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:create")),
):
    validate_excel_upload(file)

    # 获取租户上下文
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

    content = await file.read()

    headers = ["科室名称", "门店名称", "科室标签", "排序", "是否终极科室", "是否推荐", "是否热门"]
    required_fields = ["科室名称", "门店名称"]

    # 预加载门店映射（添加租户过滤）
    stores_result = await db.execute(
        select(Store).where(Store.tenant_id == tenant_id)
    )
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
            tag=row_data.get("科室标签"),
            sort_order=int(row_data.get("排序") or 0),
            is_final=parse_bool(row_data.get("是否终极科室")),
            is_recommended=parse_bool(row_data.get("是否推荐")),
            is_hot=parse_bool(row_data.get("是否热门")),
            status=1,
            tenant_id=tenant_id,
        )
        db.add(dept)

    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, file.filename, headers, required_fields, process_row
    )

    return result


@router.post("/stores", summary="导入门店数据")
async def import_stores(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("store:create")),
):
    validate_excel_upload(file)

    # 获取租户上下文
    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

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
            tenant_id=tenant_id,
        )
        db.add(store)

    import_service = ImportService(db)
    result = await import_service.validate_and_import(
        content, file.filename, headers, required_fields, process_row
    )

    return result


@router.post("/rule-sets", summary="导入规则组数据")
async def import_rule_sets(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("rule_set:create")),
):
    """导入规则组数据（多工作表 Excel：规则组、时间窗、预约策略、签到策略、容量策略）"""
    validate_excel_upload(file)

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

    content = await file.read()

    from app.modules.import_export.service_rule_set_import import RuleSetImportService
    service = RuleSetImportService(db)
    result = await service.import_rule_sets(content, tenant_id=tenant_id)

    return result


# ==================== 排班导入 ====================


VALID_TIME_SLOTS = {"morning", "afternoon", "evening"}
VALID_CONFLICT_STRATEGIES = {"skip", "overwrite", "report"}

SCHEDULE_HEADERS = ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源", "在线号源"]
SCHEDULE_REQUIRED_FIELDS = ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源"]


def _parse_time(value) -> Optional[time]:
    """将各种格式的时间值解析为 time 对象"""
    if value is None:
        return None
    if isinstance(value, time):
        return value
    if isinstance(value, datetime):
        return value.time()
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%H:%M:%S", "%H:%M"):
            try:
                return datetime.strptime(value, fmt).time()
            except ValueError:
                continue
    return None


def _parse_date(value) -> Optional[date]:
    """将各种格式的日期值解析为 date 对象"""
    if value is None:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str):
        value = value.strip()
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y%m%d"):
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue
    return None


def _time_slot_display(slot: str) -> str:
    return {"morning": "上午", "afternoon": "下午", "evening": "晚间"}.get(slot, slot)


@router.post("/schedules", summary="导入排班数据")
async def import_schedules(
    file: UploadFile = File(...),
    conflict_strategy: str = Form("skip"),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("schedule:create")),
):
    """从 Excel 文件导入排班数据。

    Excel 列: 医生姓名, 门店名称, 日期, 时段(morning/afternoon/evening), 开始时间, 结束时间, 总号源, 在线号源

    conflict_strategy:
      - skip: 跳过冲突行
      - overwrite: 删除旧排班并创建新排班（需分布式锁保护）
      - report: 不写入，仅返回冲突报告
    """
    validate_excel_upload(file)

    if conflict_strategy not in VALID_CONFLICT_STRATEGIES:
        raise HTTPException(status_code=400, detail=f"无效的冲突策略，可选值: skip/overwrite/report")

    tenant_id = get_current_tenant_id()
    if not tenant_id:
        raise HTTPException(status_code=400, detail="导入操作需要租户上下文")

    store_filter = get_store_filter(current_admin)

    content = await file.read()

    # 解析 Excel
    try:
        valid_rows, error_rows = ExcelImportService.parse_excel(
            content, SCHEDULE_HEADERS, SCHEDULE_REQUIRED_FIELDS, filename=file.filename
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    total_count = len(valid_rows) + len(error_rows)
    if total_count == 0:
        return {
            "total_count": 0, "success_count": 0, "skipped_count": 0,
            "conflict_count": 0, "errors": [],
        }

    # 预加载当前租户下的医生（按名字+门店映射）
    doctor_conditions = [
        Doctor.tenant_id == tenant_id,
        Doctor.status == 1,
        Doctor.deleted_at.is_(None),
    ]
    if store_filter:
        doctor_conditions.append(Doctor.store_id == store_filter)

    doctors_result = await db.execute(select(Doctor).where(and_(*doctor_conditions)))
    doctors = doctors_result.scalars().all()

    # 构建 (医生名, 门店名) -> doctor 的映射
    # 需要加载门店名称
    store_ids = {d.store_id for d in doctors if d.store_id}
    store_map = {}
    if store_ids:
        stores_result = await db.execute(select(Store).where(Store.id.in_(store_ids)))
        store_map = {s.id: s for s in stores_result.scalars().all()}

    doctor_lookup = {}  # (name, store_name) -> doctor
    for d in doctors:
        store_name = store_map[d.store_id].name if d.store_id in store_map else ""
        key = (d.name.strip(), store_name.strip())
        doctor_lookup[key] = d

    # 预加载已有排班（用于冲突检测）
    all_dates = set()
    for row in valid_rows:
        d = _parse_date(row.get("日期"))
        if d:
            all_dates.add(d)

    existing_schedules = []
    if all_dates and conflict_strategy != "report":
        exist_result = await db.execute(
            select(Schedule).where(
                and_(
                    Schedule.tenant_id == tenant_id,
                    Schedule.schedule_date >= min(all_dates),
                    Schedule.schedule_date <= max(all_dates),
                )
            )
        )
        existing_schedules = exist_result.scalars().all()

    # 构建已有排班索引: (doctor_id, date, time_slot, start_time, end_time) -> schedule
    existing_index = {}
    for s in existing_schedules:
        key = (s.doctor_id, s.schedule_date, s.time_slot, str(s.start_time), str(s.end_time))
        existing_index[key] = s

    success_count = 0
    skipped_count = 0
    conflict_count = 0

    # 冲突策略 = report 时收集冲突
    conflict_items = []

    # overwrite 需要收集待删除的旧排班
    to_delete_ids = set()
    to_create = []

    for row in valid_rows:
        row_id = row.get("_row", 0)
        row_errors = []

        # 医生匹配
        doctor_name = (row.get("医生姓名") or "").strip()
        store_name = (row.get("门店名称") or "").strip()
        doctor = doctor_lookup.get((doctor_name, store_name))

        if not doctor:
            row_errors.append(f"医生 '{doctor_name}' 在门店 '{store_name}' 中不存在")
            error_rows.append({"row": row_id, "data": {k: v for k, v in row.items() if not k.startswith("_")}, "errors": row_errors})
            continue

        # 解析日期
        schedule_date = _parse_date(row.get("日期"))
        if not schedule_date:
            row_errors.append("日期格式不正确，支持 YYYY-MM-DD / YYYY/MM/DD")
            error_rows.append({"row": row_id, "data": {k: v for k, v in row.items() if not k.startswith("_")}, "errors": row_errors})
            continue

        # 时段
        time_slot = (row.get("时段") or "").strip().lower()
        if time_slot not in VALID_TIME_SLOTS:
            row_errors.append(f"时段值不合法，可选值: morning/afternoon/evening")
            error_rows.append({"row": row_id, "data": {k: v for k, v in row.items() if not k.startswith("_")}, "errors": row_errors})
            continue

        # 时间
        start_time = _parse_time(row.get("开始时间"))
        end_time = _parse_time(row.get("结束时间"))
        if not start_time or not end_time:
            row_errors.append("开始时间或结束时间格式不正确，支持 HH:MM 或 HH:MM:SS")
            error_rows.append({"row": row_id, "data": {k: v for k, v in row.items() if not k.startswith("_")}, "errors": row_errors})
            continue

        # 号源
        total_slots_raw = row.get("总号源")
        try:
            total_slots = int(total_slots_raw) if total_slots_raw else 0
        except (ValueError, TypeError):
            total_slots = 0

        if total_slots <= 0:
            row_errors.append("总号源必须大于 0")
            error_rows.append({"row": row_id, "data": {k: v for k, v in row.items() if not k.startswith("_")}, "errors": row_errors})
            continue

        online_quota_raw = row.get("在线号源")
        try:
            online_quota = int(online_quota_raw) if online_quota_raw else total_slots
        except (ValueError, TypeError):
            online_quota = total_slots

        # 冲突检测
        conflict_key = (doctor.id, schedule_date, time_slot, str(start_time), str(end_time))
        existing = existing_index.get(conflict_key)

        if existing:
            conflict_count += 1
            if conflict_strategy == "report":
                conflict_items.append({
                    "row": row_id,
                    "doctor_name": doctor_name,
                    "schedule_date": str(schedule_date),
                    "time_slot": _time_slot_display(time_slot),
                    "message": f"医生 {doctor_name} 在 {schedule_date} {_time_slot_display(time_slot)} 已有排班",
                })
                skipped_count += 1
                continue
            elif conflict_strategy == "skip":
                skipped_count += 1
                continue
            elif conflict_strategy == "overwrite":
                if existing.booked_slots > 0:
                    error_rows.append({
                        "row": row_id,
                        "data": {k: v for k, v in row.items() if not k.startswith("_")},
                        "errors": [f"已有 {existing.booked_slots} 个预约，无法覆盖"],
                    })
                    skipped_count += 1
                    continue
                to_delete_ids.add(existing.id)

        to_create.append({
            "doctor": doctor,
            "schedule_date": schedule_date,
            "time_slot": time_slot,
            "start_time": start_time,
            "end_time": end_time,
            "total_slots": total_slots,
            "online_quota": online_quota,
        })

    # report 策略：只返回冲突报告，不执行写入
    if conflict_strategy == "report":
        return {
            "total_count": total_count,
            "success_count": 0,
            "skipped_count": skipped_count,
            "conflict_count": conflict_count,
            "conflicts": conflict_items,
            "errors": error_rows[:50],
        }

    # 执行写入
    from app.core.redis import RedisCache

    lock_name = f"schedule:import:{tenant_id}"

    try:
        async with RedisCache.tenant_distributed_lock(lock_name, tenant_id=tenant_id, timeout=60, retry_times=3):
            # overwrite：删除旧排班
            if to_delete_ids:
                for sid in to_delete_ids:
                    # 重新检查 booked_slots（锁内 double-check）
                    recheck = await db.execute(
                        select(Schedule).where(Schedule.id == sid, Schedule.booked_slots == 0)
                    )
                    s = recheck.scalar_one_or_none()
                    if s:
                        await db.delete(s)
                await db.flush()

            # 创建新排班
            for item in to_create:
                doctor = item["doctor"]
                schedule = Schedule(
                    id=str(uuid4()),
                    tenant_id=tenant_id,
                    doctor_id=doctor.id,
                    store_id=doctor.store_id,
                    schedule_date=item["schedule_date"],
                    time_slot=item["time_slot"],
                    start_time=item["start_time"],
                    end_time=item["end_time"],
                    total_slots=item["total_slots"],
                    booked_slots=0,
                    online_quota=item["online_quota"],
                    offline_quota=0,
                    reserved_quota=0,
                    extra_quota=0,
                    fee=0,
                    appointment_type="normal",
                    status=1,
                    schedule_status=ScheduleStatus.PUBLISHED,
                )
                set_create_audit(schedule, current_admin.get("id"))
                db.add(schedule)
                success_count += 1

            if success_count > 0:
                await db.commit()

    except RuntimeError:
        raise HTTPException(status_code=429, detail="操作频繁，请稍后重试")

    return {
        "total_count": total_count,
        "success_count": success_count,
        "skipped_count": skipped_count,
        "conflict_count": conflict_count,
        "errors": error_rows[:50],
    }
