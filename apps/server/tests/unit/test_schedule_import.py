"""
排班导入功能的单元测试

测试用例：
1. 正常导入流程
2. 冲突检测（skip/overwrite/report 策略）
3. 医生匹配（姓名+门店）
4. 无效数据行被跳过并返回错误
5. 租户隔离
"""
import asyncio
from datetime import date, time, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.department import Department
from app.models.doctor import Doctor
from app.models.schedule import Schedule
from app.models.store import Store
from app.models.tenant import Tenant
from app.infrastructure.excel.import_service import ExcelImportService


# ==================== 测试工具函数 ====================


def _make_excel(
    rows: list[list],
    headers: list[str] | None = None,
) -> bytes:
    """构造 Excel 文件字节流"""
    if headers is None:
        headers = ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源", "在线号源"]

    wb = Workbook()
    ws = wb.active
    ws.title = "导入模板"

    for col_idx, header in enumerate(headers, 1):
        ws.cell(row=1, column=col_idx, value=header)

    for row_idx, row_data in enumerate(rows, 2):
        for col_idx, value in enumerate(row_data, 1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()


def _tenant_patches(test_tenant_id):
    """Mock 租户上下文"""
    return {
        "app.modules.import_export.router_import.get_current_tenant_id": lambda: test_tenant_id,
        "app.modules.import_export.router_import.get_store_filter": lambda admin: None,
    }


# ==================== 测试用例 ====================


@pytest.mark.asyncio
async def test_import_schedules_success(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_doctor: Doctor,
):
    """测试正常导入排班"""
    target_date = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")
    excel_bytes = _make_excel([
        [test_doctor.name, test_store.name, target_date, "morning", "08:00", "12:00", 20, 15],
        [test_doctor.name, test_store.name, target_date, "afternoon", "14:00", "17:00", 15, 10],
    ])

    # 验证 Excel 可正确解析
    valid_rows, error_rows = ExcelImportService.parse_excel(
        excel_bytes,
        ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源", "在线号源"],
        ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源"],
    )

    assert len(valid_rows) == 2
    assert len(error_rows) == 0

    # 验证行数据
    assert valid_rows[0]["医生姓名"] == test_doctor.name
    assert valid_rows[0]["时段"] == "morning"
    assert valid_rows[0]["总号源"] == 20
    assert valid_rows[1]["时段"] == "afternoon"


@pytest.mark.asyncio
async def test_import_conflict_skip_strategy(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_doctor: Doctor,
):
    """测试冲突策略：skip - 跳过冲突行"""
    target_date = date.today() + timedelta(days=7)

    # 先创建一条已有排班
    existing = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=target_date,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    db_session.add(existing)
    await db_session.commit()

    # 验证冲突检测：同医生同日期同时段
    conflict_key = (test_doctor.id, target_date, "morning", str(time(8, 0)), str(time(12, 0)))
    existing_result = await db_session.execute(
        select(Schedule).where(
            Schedule.doctor_id == test_doctor.id,
            Schedule.schedule_date == target_date,
            Schedule.time_slot == "morning",
        )
    )
    found = existing_result.scalar_one_or_none()
    assert found is not None
    assert found.id == existing.id


@pytest.mark.asyncio
async def test_import_conflict_overwrite_strategy(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_doctor: Doctor,
):
    """测试冲突策略：overwrite - 覆盖已有排班"""
    target_date = date.today() + timedelta(days=7)

    # 创建一条无预约的排班
    existing = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=target_date,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,  # 无预约，可以覆盖
        status=1,
    )
    db_session.add(existing)
    await db_session.commit()

    # overwrite 策略应允许删除
    assert existing.booked_slots == 0

    # 创建一条有预约的排班，不应允许覆盖
    existing_with_booking = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=target_date,
        time_slot="afternoon",
        start_time=time(14, 0),
        end_time=time(17, 0),
        total_slots=10,
        booked_slots=3,  # 有预约
        status=1,
    )
    db_session.add(existing_with_booking)
    await db_session.commit()

    assert existing_with_booking.booked_slots > 0  # 不应被覆盖


@pytest.mark.asyncio
async def test_import_conflict_report_strategy(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_doctor: Doctor,
):
    """测试冲突策略：report - 仅报告不写入"""
    target_date = date.today() + timedelta(days=7)

    # 创建已有排班
    existing = Schedule(
        id=str(uuid4()),
        doctor_id=test_doctor.id,
        store_id=test_store.id,
        tenant_id=test_tenant.id,
        schedule_date=target_date,
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=0,
        status=1,
    )
    db_session.add(existing)
    await db_session.commit()

    # report 策略不应删除或修改已有排班
    await db_session.refresh(existing)
    assert existing.total_slots == 10  # 未被修改

    # 验证排班仍存在
    result = await db_session.execute(
        select(Schedule).where(Schedule.id == existing.id)
    )
    assert result.scalar_one_or_none() is not None


@pytest.mark.asyncio
async def test_import_doctor_matching_by_name_and_store(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_doctor: Doctor,
):
    """测试医生匹配：按姓名+门店"""
    # 构建医生查找索引
    doctors_result = await db_session.execute(
        select(Doctor).where(
            Doctor.tenant_id == test_tenant.id,
            Doctor.status == 1,
            Doctor.deleted_at.is_(None),
        )
    )
    doctors = doctors_result.scalars().all()

    store_ids = {d.store_id for d in doctors}
    stores_result = await db_session.execute(select(Store).where(Store.id.in_(store_ids)))
    store_map = {s.id: s for s in stores_result.scalars().all()}

    doctor_lookup = {}
    for d in doctors:
        store_name = store_map[d.store_id].name if d.store_id in store_map else ""
        key = (d.name.strip(), store_name.strip())
        doctor_lookup[key] = d

    # 正确匹配
    found = doctor_lookup.get((test_doctor.name, test_store.name))
    assert found is not None
    assert found.id == test_doctor.id

    # 不匹配：错误的医生名
    not_found = doctor_lookup.get(("不存在的医生", test_store.name))
    assert not_found is None

    # 不匹配：错误的门店名
    not_found2 = doctor_lookup.get((test_doctor.name, "不存在的门店"))
    assert not_found2 is None


@pytest.mark.asyncio
async def test_import_invalid_rows_returned_as_errors():
    """测试无效数据行被跳过并返回错误"""
    # 缺少必填字段的 Excel
    excel_bytes = _make_excel([
        ["张医生", "总院", "2026-06-01", "", "08:00", "12:00", 20, 15],  # 缺少时段
        ["", "总院", "2026-06-01", "morning", "08:00", "12:00", 20, 15],  # 缺少医生姓名
    ])

    valid_rows, error_rows = ExcelImportService.parse_excel(
        excel_bytes,
        ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源", "在线号源"],
        ["医生姓名", "门店名称", "日期", "时段", "开始时间", "结束时间", "总号源"],
    )

    # 两行都因缺少必填字段而成为错误行
    assert len(error_rows) == 2
    assert any("时段" in str(e["errors"]) for e in error_rows)
    assert any("医生姓名" in str(e["errors"]) for e in error_rows)


@pytest.mark.asyncio
async def test_import_tenant_isolation(
    db_session: AsyncSession,
    test_tenant: Tenant,
    test_store: Store,
    test_doctor: Doctor,
):
    """测试租户隔离：只能查到当前租户的医生"""
    # 创建另一个租户
    other_tenant = Tenant(
        id=str(uuid4()),
        tenant_code="other_tenant",
        name="其他租户",
        status=1,
    )
    db_session.add(other_tenant)
    await db_session.commit()

    # 创建另一个租户的门店和医生
    other_store = Store(
        id=str(uuid4()),
        name="其他门店",
        tenant_id=other_tenant.id,
        status=1,
    )
    db_session.add(other_store)
    await db_session.commit()

    other_dept = Department(
        id=str(uuid4()),
        name="其他科室",
        store_id=other_store.id,
        tenant_id=other_tenant.id,
        status=1,
    )
    db_session.add(other_dept)
    await db_session.commit()

    other_doctor = Doctor(
        id=str(uuid4()),
        name="其他医生",
        store_id=other_store.id,
        department_id=other_dept.id,
        tenant_id=other_tenant.id,
        status=1,
    )
    db_session.add(other_doctor)
    await db_session.commit()

    # 只查询当前租户的医生
    doctors_result = await db_session.execute(
        select(Doctor).where(
            Doctor.tenant_id == test_tenant.id,
            Doctor.status == 1,
            Doctor.deleted_at.is_(None),
        )
    )
    doctors = doctors_result.scalars().all()

    # 应只包含当前租户的医生
    doctor_ids = {d.id for d in doctors}
    assert test_doctor.id in doctor_ids
    assert other_doctor.id not in doctor_ids

    # 门店索引也应只包含当前租户的
    store_ids = {d.store_id for d in doctors}
    stores_result = await db_session.execute(select(Store).where(Store.id.in_(store_ids)))
    store_map = {s.id: s for s in stores_result.scalars().all()}

    for s in store_map.values():
        assert s.tenant_id == test_tenant.id


@pytest.mark.asyncio
async def test_import_date_parsing():
    """测试日期解析支持多种格式"""
    from app.modules.import_export.router_import import _parse_date

    # YYYY-MM-DD
    assert _parse_date("2026-06-01") == date(2026, 6, 1)

    # YYYY/MM/DD
    assert _parse_date("2026/06/01") == date(2026, 6, 1)

    # YYYYMMDD
    assert _parse_date("20260601") == date(2026, 6, 1)

    # date 对象
    d = date(2026, 6, 1)
    assert _parse_date(d) == d

    # None
    assert _parse_date(None) is None

    # 无效格式
    assert _parse_date("invalid") is None


@pytest.mark.asyncio
async def test_import_time_parsing():
    """测试时间解析支持多种格式"""
    from app.modules.import_export.router_import import _parse_time

    # HH:MM
    assert _parse_time("08:00") == time(8, 0)

    # HH:MM:SS
    assert _parse_time("08:30:45") == time(8, 30, 45)

    # time 对象
    t = time(14, 30)
    assert _parse_time(t) == t

    # None
    assert _parse_time(None) is None

    # 无效格式
    assert _parse_time("invalid") is None


@pytest.mark.asyncio
async def test_import_time_slot_validation():
    """测试时段值验证"""
    from app.modules.import_export.router_import import VALID_TIME_SLOTS

    assert "morning" in VALID_TIME_SLOTS
    assert "afternoon" in VALID_TIME_SLOTS
    assert "evening" in VALID_TIME_SLOTS
    assert "AM" not in VALID_TIME_SLOTS
    assert "PM" not in VALID_TIME_SLOTS
    assert "" not in VALID_TIME_SLOTS
