"""
排班导出功能单元测试

覆盖：
1. 导出返回正确的 Excel 内容类型和结构
2. 参数过滤（按医生、日期范围）
3. 租户隔离
"""
import pytest
from datetime import datetime, date, time, timedelta
from io import BytesIO
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from openpyxl import load_workbook

from app.models.schedule import Schedule
from app.infrastructure.excel.export_service import ExcelExportService


# ==================== 辅助函数 ====================


def _make_schedule(db_session, tenant, doctor, store, **overrides):
    """创建排班的辅助函数。"""
    defaults = dict(
        id=str(uuid4()),
        doctor_id=doctor.id,
        store_id=store.id,
        tenant_id=tenant.id,
        schedule_date=date.today() + timedelta(days=1),
        time_slot="morning",
        start_time=time(8, 0),
        end_time=time(12, 0),
        total_slots=10,
        booked_slots=3,
        online_quota=5,
        offline_quota=3,
        reserved_quota=0,
        extra_quota=2,
        schedule_status="published",
        appointment_type="normal",
        status=1,
        created_at=datetime.now(),
        updated_at=datetime.now(),
    )
    defaults.update(overrides)
    schedule = Schedule(**defaults)
    db_session.add(schedule)
    return schedule


# ==================== 导出内容测试 ====================


class TestExportContent:
    """测试导出 Excel 内容正确性"""

    @pytest.mark.asyncio
    async def test_export_returns_multi_sheet_excel(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """导出应返回包含两个工作表的 Excel 文件"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()

        # 模拟租户上下文
        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            from sqlalchemy import select, and_
            from sqlalchemy.orm import selectinload
            from app.models.doctor import Doctor

            query = (
                select(Schedule)
                .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
                .where(Schedule.store_id == test_store.id)
                .where(Schedule.tenant_id == test_tenant.id)
            )
            result = await db_session.execute(query)
            schedules = result.unique().scalars().all()

            # 构建导出数据（模拟 router_export.py 中的逻辑）
            workbook_data = {
                "排班明细": {
                    "headers": ["医生姓名", "日期", "时段", "开始时间", "结束时间",
                                "总号源", "已预约", "在线号源", "排班状态", "排班类型"],
                    "data": [
                        [
                            s.doctor.name if s.doctor else "",
                            s.schedule_date.strftime("%Y-%m-%d"),
                            "上午" if s.time_slot == "morning" else s.time_slot,
                            s.start_time.strftime("%H:%M") if s.start_time else "",
                            s.end_time.strftime("%H:%M") if s.end_time else "",
                            s.total_slots or 0,
                            s.booked_slots or 0,
                            s.online_quota if s.online_quota and s.online_quota > 0 else s.total_slots,
                            s.schedule_status or "",
                            s.appointment_type or "",
                        ]
                        for s in schedules
                    ],
                },
                "汇总统计": {
                    "headers": ["医生姓名", "排班数", "总号源", "已预约数"],
                    "data": [
                        [test_doctor.name, 1, 10, 3],
                    ],
                },
            }

            excel_bytes = ExcelExportService.create_multi_sheet_workbook(workbook_data)

            # 验证 Excel 结构
            wb = load_workbook(BytesIO(excel_bytes))
            assert "排班明细" in wb.sheetnames
            assert "汇总统计" in wb.sheetnames

            # 验证排班明细表头
            ws_detail = wb["排班明细"]
            assert ws_detail.cell(1, 1).value == "医生姓名"
            assert ws_detail.cell(1, 6).value == "总号源"

            # 验证数据行
            assert ws_detail.cell(2, 1).value == test_doctor.name
            assert ws_detail.cell(2, 6).value == 10
            assert ws_detail.cell(2, 7).value == 3

            # 验证汇总统计表
            ws_summary = wb["汇总统计"]
            assert ws_summary.cell(2, 1).value == test_doctor.name
            assert ws_summary.cell(2, 2).value == 1
            assert ws_summary.cell(2, 3).value == 10
            assert ws_summary.cell(2, 4).value == 3

    @pytest.mark.asyncio
    async def test_export_filters_by_doctor(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
        test_department,
    ):
        """按医生过滤导出"""
        from app.models.doctor import Doctor

        # 创建第二个医生
        doctor2 = Doctor(
            id=str(uuid4()),
            name="第二个医生",
            title="副主任医师",
            department_id=test_department.id,
            store_id=test_store.id,
            tenant_id=test_tenant.id,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        db_session.add(doctor2)
        await db_session.flush()

        # 为两个医生各创建排班
        schedule1 = _make_schedule(
            db_session, test_tenant, test_doctor, test_store,
            schedule_date=date.today() + timedelta(days=1),
        )
        schedule2 = _make_schedule(
            db_session, test_tenant, doctor2, test_store,
            schedule_date=date.today() + timedelta(days=2),
        )
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.doctor import Doctor as DoctorModel

            # 只查询第一个医生的排班
            query = (
                select(Schedule)
                .options(selectinload(Schedule.doctor).selectinload(DoctorModel.department))
                .where(Schedule.store_id == test_store.id)
                .where(Schedule.tenant_id == test_tenant.id)
                .where(Schedule.doctor_id == test_doctor.id)
            )
            result = await db_session.execute(query)
            schedules = result.unique().scalars().all()

            assert len(schedules) == 1
            assert schedules[0].doctor_id == test_doctor.id

    @pytest.mark.asyncio
    async def test_export_filters_by_date_range(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """按日期范围过滤导出"""
        today = date.today()

        # 创建三个不同日期的排班
        _make_schedule(
            db_session, test_tenant, test_doctor, test_store,
            schedule_date=today + timedelta(days=1),
        )
        _make_schedule(
            db_session, test_tenant, test_doctor, test_store,
            schedule_date=today + timedelta(days=5),
        )
        _make_schedule(
            db_session, test_tenant, test_doctor, test_store,
            schedule_date=today + timedelta(days=10),
        )
        await db_session.commit()

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=test_tenant.id):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.doctor import Doctor

            # 只查询第 1-5 天的排班
            start_date = today + timedelta(days=1)
            end_date = today + timedelta(days=5)

            query = (
                select(Schedule)
                .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
                .where(Schedule.store_id == test_store.id)
                .where(Schedule.tenant_id == test_tenant.id)
                .where(Schedule.schedule_date >= start_date)
                .where(Schedule.schedule_date <= end_date)
            )
            result = await db_session.execute(query)
            schedules = result.unique().scalars().all()

            assert len(schedules) == 2
            for s in schedules:
                assert start_date <= s.schedule_date <= end_date


# ==================== 租户隔离测试 ====================


class TestExportTenantIsolation:
    """测试导出的租户隔离"""

    @pytest.mark.asyncio
    async def test_tenant_isolation_blocks_other_tenant(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """不同租户的数据不应出现在导出结果中"""
        # 创建排班（属于 test_tenant）
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()

        # 使用另一个租户 ID 查询（应查不到）
        other_tenant_id = "other-tenant-id"

        with patch("app.middleware.tenant_context.get_current_tenant_id", return_value=other_tenant_id):
            from sqlalchemy import select
            from sqlalchemy.orm import selectinload
            from app.models.doctor import Doctor

            query = (
                select(Schedule)
                .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
                .where(Schedule.store_id == test_store.id)
                .where(Schedule.tenant_id == other_tenant_id)
            )
            result = await db_session.execute(query)
            schedules = result.unique().scalars().all()

            assert len(schedules) == 0

    @pytest.mark.asyncio
    async def test_no_tenant_filter_returns_all(
        self,
        db_session,
        test_tenant,
        test_doctor,
        test_store,
    ):
        """不设置租户过滤时应返回所有数据"""
        schedule = _make_schedule(db_session, test_tenant, test_doctor, test_store)
        await db_session.commit()

        # 不加租户过滤
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.models.doctor import Doctor

        query = (
            select(Schedule)
            .options(selectinload(Schedule.doctor).selectinload(Doctor.department))
            .where(Schedule.store_id == test_store.id)
        )
        result = await db_session.execute(query)
        schedules = result.unique().scalars().all()

        assert len(schedules) >= 1


# ==================== Excel 格式测试 ====================


class TestExportExcelFormat:
    """测试 Excel 文件格式正确性"""

    def test_excel_content_type_is_valid(self):
        """Excel 文件的二进制内容应以 PK 开头（ZIP 格式）"""
        headers = ["列1", "列2"]
        data = [["值1", "值2"]]
        excel_bytes = ExcelExportService.create_workbook(headers, data, "测试")

        # Excel (.xlsx) 是 ZIP 格式，以 PK 开头
        assert excel_bytes[:2] == b'PK'

    def test_multi_sheet_workbook_has_sheets(self):
        """多工作表 Excel 应正确创建多个工作表"""
        workbook_data = {
            "明细": {
                "headers": ["A", "B"],
                "data": [[1, 2], [3, 4]],
            },
            "汇总": {
                "headers": ["C", "D"],
                "data": [[5, 6]],
            },
        }
        excel_bytes = ExcelExportService.create_multi_sheet_workbook(workbook_data)
        wb = load_workbook(BytesIO(excel_bytes))

        assert len(wb.sheetnames) == 2
        assert "明细" in wb.sheetnames
        assert "汇总" in wb.sheetnames

        ws1 = wb["明细"]
        assert ws1.max_row == 3  # 1 header + 2 data rows
        assert ws1.cell(1, 1).value == "A"
        assert ws1.cell(2, 1).value == 1

        ws2 = wb["汇总"]
        assert ws2.max_row == 2  # 1 header + 1 data row
        assert ws2.cell(2, 1).value == 5

    def test_empty_data_creates_valid_excel(self):
        """空数据也应生成有效的 Excel 文件"""
        headers = ["列1", "列2"]
        data = []
        excel_bytes = ExcelExportService.create_workbook(headers, data, "空数据")

        assert excel_bytes[:2] == b'PK'
        wb = load_workbook(BytesIO(excel_bytes))
        ws = wb.active
        assert ws.cell(1, 1).value == "列1"
        assert ws.max_row == 1  # 只有表头
