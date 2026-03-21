"""导入相关端点"""
from datetime import datetime

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from io import BytesIO

from app.db.session import get_db
from app.api.deps import get_current_admin, require_permission
from app.services.excel_service import ExcelImportService
from app.services.import_service import ImportService
from app.models.doctor import Doctor
from app.models.user import Patient
from app.models.department import Department
from app.models.store import Store

router = APIRouter()


@router.post("/doctors", summary="导入医生数据")
async def import_doctors(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("doctor:create")),
):
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


@router.post("/patients", summary="导入患者数据")
async def import_patients(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("patient:create")),
):
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


@router.post("/departments", summary="导入科室数据")
async def import_departments(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("department:create")),
):
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


@router.post("/stores", summary="导入门店数据")
async def import_stores(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_admin: dict = Depends(get_current_admin),
    _: None = Depends(require_permission("store:create")),
):
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
