"""平台经营看板单元测试

覆盖范围：
- schemas.calc_no_show_rate 纯函数
- service._default_range 纯函数
- PlatformMetricsService 四个查询方法（mock db）
"""

import pytest
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

from app.modules.platform_metrics.schemas import (
    PlatformOverview,
    TenantCompareItem,
    StoreCompareItem,
    TrendPoint,
    calc_no_show_rate,
)
from app.modules.platform_metrics.service import _default_range, PlatformMetricsService


# ==================== 纯函数测试 ====================


class TestCalcNoShowRate:
    """calc_no_show_rate 边界测试。"""

    def test_normal_case(self):
        """有数据时正常计算，保留两位小数。"""
        assert calc_no_show_rate(80, 20) == 20.0
        assert calc_no_show_rate(70, 30) == 30.0

    def test_fractional_result(self):
        """结果含小数时四舍五入到两位。"""
        rate = calc_no_show_rate(66, 33)
        # 33 / 99 * 100 = 33.33...
        assert rate == 33.33

    def test_zero_denominator(self):
        """已到院+爽约均为 0 时返回 None。"""
        assert calc_no_show_rate(0, 0) is None

    def test_zero_visit_only(self):
        """已到院为 0、爽约 > 0 时正常计算（100%）。"""
        assert calc_no_show_rate(0, 5) == 100.0

    def test_zero_no_show_only(self):
        """爽约为 0、已到院 > 0 时返回 0。"""
        assert calc_no_show_rate(100, 0) == 0.0


class TestDefaultRange:
    """_default_range 默认日期范围测试。"""

    def test_default_30_days(self):
        """未传 end_date 时，end 为昨天，start 为 end-29 天。"""
        start, end = _default_range(None)
        expected_end = date.today() - timedelta(days=1)
        expected_start = expected_end - timedelta(days=29)
        assert end == expected_end
        assert start == expected_start

    def test_custom_end_date(self):
        """传入 end_date 时，start = end - 29 天。"""
        end = date(2026, 6, 14)
        start, result_end = _default_range(end)
        assert result_end == end
        assert start == date(2026, 5, 16)

    def test_custom_days(self):
        """自定义天数。"""
        end = date(2026, 6, 14)
        start, result_end = _default_range(end, days=7)
        assert result_end == end
        assert start == date(2026, 6, 8)


# ==================== Schema 构造测试 ====================


class TestSchemas:
    """Schema 字段别名和默认值测试。"""

    def test_platform_overview_alias(self):
        """PlatformOverview 序列化时使用 camelCase 别名。"""
        data = PlatformOverview(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            tenant_count=5,
            active_store_count=10,
            appointment_count=200,
            visit_count=150,
            completed_count=120,
            no_show_count=30,
            cancelled_count=20,
            new_patient_count=50,
            revenue=Decimal("12345.67"),
            no_show_rate=16.67,
        )
        dumped = data.model_dump(by_alias=True)
        assert dumped["startDate"] == date(2026, 6, 1)
        assert dumped["noShowRate"] == 16.67
        assert dumped["revenue"] == Decimal("12345.67")

    def test_tenant_compare_item_defaults(self):
        """TenantCompareItem 字段默认值。"""
        item = TenantCompareItem()
        assert item.appointment_count == 0
        assert item.revenue == Decimal("0")
        assert item.no_show_rate is None

    def test_store_compare_item_alias(self):
        """StoreCompareItem 别名正确。"""
        item = StoreCompareItem(
            store_id="s1",
            store_name="门店A",
            tenant_id="t1",
            tenant_name="租户A",
        )
        dumped = item.model_dump(by_alias=True)
        assert dumped["storeId"] == "s1"
        assert dumped["tenantName"] == "租户A"

    def test_trend_point_defaults(self):
        """TrendPoint 默认值正确。"""
        p = TrendPoint(date=date(2026, 6, 14))
        assert p.appointment_count == 0
        assert p.revenue == Decimal("0")


# ==================== Service 方法测试 (mock db) ====================


def _mock_row(**kwargs):
    """构造一个模拟的 SQLAlchemy Row 对象。"""
    row = MagicMock()
    for k, v in kwargs.items():
        setattr(row, k, v)
    return row


def _make_service(rows=None, row=None):
    """构造带 mock db 的 PlatformMetricsService。

    - row: 单行结果（供 .one() 使用）
    - rows: 多行结果（供 .all() 使用）
    """
    db = AsyncMock()
    mock_result = MagicMock()
    mock_result.one.return_value = row or MagicMock()
    mock_result.all.return_value = rows or []
    db.execute.return_value = mock_result
    return PlatformMetricsService(db), db


class TestOverview:
    """PlatformMetricsService.overview 测试。"""

    @pytest.mark.asyncio
    async def test_overview_with_data(self):
        """有数据时正确映射所有字段。"""
        row = _mock_row(
            active_stores=3,
            tenant_count=2,
            appointments=100,
            visits=80,
            completed=60,
            no_show=15,
            cancelled=5,
            new_patients=20,
            revenue=Decimal("5000.00"),
        )
        service, db = _make_service(row=row)

        result = await service.overview(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 14)
        )

        assert isinstance(result, PlatformOverview)
        assert result.active_store_count == 3
        assert result.tenant_count == 2
        assert result.appointment_count == 100
        assert result.visit_count == 80
        assert result.completed_count == 60
        assert result.no_show_count == 15
        assert result.cancelled_count == 5
        assert result.new_patient_count == 20
        assert result.revenue == Decimal("5000.00")
        # 15 / (80+15) * 100 = 15.79
        assert result.no_show_rate == 15.79

    @pytest.mark.asyncio
    async def test_overview_empty_data(self):
        """空数据时返回全零，noShowRate 为 None。"""
        row = _mock_row(
            active_stores=None,
            tenant_count=None,
            appointments=None,
            visits=None,
            completed=None,
            no_show=None,
            cancelled=None,
            new_patients=None,
            revenue=None,
        )
        service, _ = _make_service(row=row)

        result = await service.overview(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 14)
        )

        assert result.active_store_count == 0
        assert result.appointment_count == 0
        assert result.revenue == Decimal("0")
        assert result.no_show_rate is None

    @pytest.mark.asyncio
    async def test_overview_default_range(self):
        """不传日期时使用默认 30 天范围。"""
        row = _mock_row(
            active_stores=1, tenant_count=1, appointments=10,
            visits=8, completed=6, no_show=2, cancelled=0,
            new_patients=3, revenue=Decimal("500"),
        )
        service, db = _make_service(row=row)

        result = await service.overview()

        expected_end = date.today() - timedelta(days=1)
        expected_start = expected_end - timedelta(days=29)
        assert result.start_date == expected_start
        assert result.end_date == expected_end

    @pytest.mark.asyncio
    async def test_overview_only_start_date(self):
        """仅传 start_date 时，end_date 应为 today。"""
        row = _mock_row(
            active_stores=1, tenant_count=1, appointments=5,
            visits=4, completed=3, no_show=1, cancelled=0,
            new_patients=2, revenue=Decimal("200"),
        )
        service, _ = _make_service(row=row)

        result = await service.overview(start_date=date(2026, 6, 1))

        assert result.start_date == date(2026, 6, 1)
        assert result.end_date == date.today()


class TestTenantsCompare:
    """PlatformMetricsService.tenants_compare 测试。"""

    @pytest.mark.asyncio
    async def test_tenants_compare_returns_list(self):
        """返回 TenantCompareItem 列表。"""
        rows = [
            _mock_row(
                tenant_id="t1",
                tenant_name="租户A",
                store_count=3,
                appointments=50,
                visits=40,
                completed=35,
                no_show=5,
                new_patients=10,
                revenue=Decimal("3000.00"),
            ),
            _mock_row(
                tenant_id="t2",
                tenant_name=None,  # 模拟 NULL -> "平台级门店"
                store_count=1,
                appointments=20,
                visits=15,
                completed=10,
                no_show=3,
                new_patients=5,
                revenue=Decimal("1000.00"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.tenants_compare(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 14)
        )

        assert len(result) == 2
        assert isinstance(result[0], TenantCompareItem)
        assert result[0].tenant_id == "t1"
        assert result[0].tenant_name == "租户A"
        assert result[0].store_count == 3
        assert result[0].no_show_rate == 11.11  # 5/(40+5)*100
        # tenant_name 为 None 时降级为 "平台级门店"
        assert result[1].tenant_name == "平台级门店"

    @pytest.mark.asyncio
    async def test_tenants_compare_empty(self):
        """无数据时返回空列表。"""
        service, _ = _make_service(rows=[])
        result = await service.tenants_compare()
        assert result == []

    @pytest.mark.asyncio
    async def test_tenants_compare_sort_by_appointment(self):
        """sort_by=appointment 时按预约数排序。"""
        rows = [
            _mock_row(
                tenant_id="t1", tenant_name="租户A", store_count=1,
                appointments=100, visits=80, completed=60, no_show=10,
                new_patients=20, revenue=Decimal("1000"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.tenants_compare(sort_by="appointment")
        assert len(result) == 1
        assert result[0].appointment_count == 100

    @pytest.mark.asyncio
    async def test_tenants_compare_sort_by_visit(self):
        """sort_by=visit 时按到院数排序。"""
        rows = [
            _mock_row(
                tenant_id="t1", tenant_name="租户A", store_count=1,
                appointments=50, visits=45, completed=40, no_show=3,
                new_patients=10, revenue=Decimal("2000"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.tenants_compare(sort_by="visit")
        assert len(result) == 1
        assert result[0].visit_count == 45

    @pytest.mark.asyncio
    async def test_tenants_compare_sort_by_new_patient(self):
        """sort_by=new_patient 时按新患者数排序。"""
        rows = [
            _mock_row(
                tenant_id="t1", tenant_name="租户A", store_count=1,
                appointments=30, visits=25, completed=20, no_show=5,
                new_patients=15, revenue=Decimal("800"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.tenants_compare(sort_by="new_patient")
        assert len(result) == 1
        assert result[0].new_patient_count == 15

    @pytest.mark.asyncio
    async def test_tenants_compare_invalid_sort_by_fallback(self):
        """无效 sort_by 回退到 revenue 排序。"""
        rows = [
            _mock_row(
                tenant_id="t1", tenant_name="租户A", store_count=1,
                appointments=10, visits=8, completed=6, no_show=2,
                new_patients=3, revenue=Decimal("500"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        # sort_by 传无效值，应回退到 revenue 不报错
        result = await service.tenants_compare(sort_by="invalid_field")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_tenants_compare_default_range(self):
        """不传日期时使用默认范围。"""
        rows = [
            _mock_row(
                tenant_id="t1", tenant_name="租户A", store_count=1,
                appointments=10, visits=8, completed=6, no_show=2,
                new_patients=3, revenue=Decimal("500"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.tenants_compare()
        assert len(result) == 1


class TestStoresCompare:
    """PlatformMetricsService.stores_compare 测试。"""

    @pytest.mark.asyncio
    async def test_stores_compare_returns_list(self):
        """返回 StoreCompareItem 列表。"""
        rows = [
            _mock_row(
                store_id="s1",
                store_name="门店A",
                tenant_id="t1",
                tenant_name="租户A",
                appointments=30,
                visits=25,
                completed=20,
                no_show=5,
                new_patients=8,
                revenue=Decimal("2000.00"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.stores_compare(
            start_date=date(2026, 6, 1),
            end_date=date(2026, 6, 14),
            tenant_id="t1",
            sort_by="revenue",
            limit=10,
        )

        assert len(result) == 1
        assert isinstance(result[0], StoreCompareItem)
        assert result[0].store_id == "s1"
        assert result[0].store_name == "门店A"
        assert result[0].tenant_name == "租户A"

    @pytest.mark.asyncio
    async def test_stores_compare_unknown_store(self):
        """store_name 为 None 时降级为 '未知门店'。"""
        rows = [
            _mock_row(
                store_id="s1",
                store_name=None,
                tenant_id=None,
                tenant_name=None,
                appointments=0,
                visits=0,
                completed=0,
                no_show=0,
                new_patients=0,
                revenue=None,
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.stores_compare()
        assert result[0].store_name == "未知门店"
        assert result[0].revenue == Decimal("0")

    @pytest.mark.asyncio
    async def test_stores_compare_no_tenant_filter(self):
        """不传 tenant_id 时不过滤租户。"""
        rows = [
            _mock_row(
                store_id="s1", store_name="门店A", tenant_id="t1",
                tenant_name="租户A", appointments=10, visits=8,
                completed=6, no_show=2, new_patients=3,
                revenue=Decimal("500"),
            ),
            _mock_row(
                store_id="s2", store_name="门店B", tenant_id="t2",
                tenant_name="租户B", appointments=20, visits=15,
                completed=12, no_show=3, new_patients=5,
                revenue=Decimal("800"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.stores_compare()  # 不传 tenant_id
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_stores_compare_sort_by_appointment(self):
        """sort_by=appointment 时按预约数排序。"""
        rows = [
            _mock_row(
                store_id="s1", store_name="门店A", tenant_id="t1",
                tenant_name="租户A", appointments=50, visits=40,
                completed=30, no_show=10, new_patients=15,
                revenue=Decimal("3000"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.stores_compare(sort_by="appointment")
        assert result[0].appointment_count == 50

    @pytest.mark.asyncio
    async def test_stores_compare_default_range(self):
        """不传日期时使用默认范围。"""
        rows = [
            _mock_row(
                store_id="s1", store_name="门店A", tenant_id="t1",
                tenant_name="租户A", appointments=10, visits=8,
                completed=6, no_show=2, new_patients=3,
                revenue=Decimal("500"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.stores_compare()
        assert len(result) == 1


class TestTrend:
    """PlatformMetricsService.trend 测试。"""

    @pytest.mark.asyncio
    async def test_trend_fills_missing_dates(self):
        """无数据的日期用零值补齐，保证趋势连续。"""
        # 仅 6/1 和 6/3 有数据
        rows = [
            _mock_row(
                d=date(2026, 6, 1),
                appointments=10,
                visits=8,
                completed=6,
                new_patients=3,
                revenue=Decimal("500"),
            ),
            _mock_row(
                d=date(2026, 6, 3),
                appointments=15,
                visits=12,
                completed=10,
                new_patients=5,
                revenue=Decimal("800"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.trend(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 5)
        )

        # 6/1 ~ 6/5 共 5 天
        assert len(result) == 5
        assert all(isinstance(p, TrendPoint) for p in result)

        # 6/1 有数据
        assert result[0].appointment_count == 10
        assert result[0].revenue == Decimal("500")
        # 6/2 无数据 -> 零值
        assert result[1].appointment_count == 0
        assert result[1].revenue == Decimal("0")
        # 6/3 有数据
        assert result[2].appointment_count == 15
        # 6/4, 6/5 无数据
        assert result[3].appointment_count == 0
        assert result[4].appointment_count == 0

    @pytest.mark.asyncio
    async def test_trend_empty(self):
        """全部无数据时返回全零。"""
        service, _ = _make_service(rows=[])

        result = await service.trend(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
        )

        assert len(result) == 3
        assert all(p.appointment_count == 0 for p in result)
        assert all(p.revenue == Decimal("0") for p in result)

    @pytest.mark.asyncio
    async def test_trend_default_range(self):
        """不传日期时使用默认 30 天范围。"""
        service, _ = _make_service(rows=[])

        result = await service.trend()

        expected_end = date.today() - timedelta(days=1)
        expected_start = expected_end - timedelta(days=29)
        expected_days = (expected_end - expected_start).days + 1
        assert len(result) == expected_days
        assert result[0].date == expected_start
        assert result[-1].date == expected_end

    @pytest.mark.asyncio
    async def test_trend_single_day(self):
        """单日范围返回一条数据。"""
        rows = [
            _mock_row(
                d=date(2026, 6, 14),
                appointments=10,
                visits=8,
                completed=6,
                new_patients=3,
                revenue=Decimal("500"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.trend(
            start_date=date(2026, 6, 14), end_date=date(2026, 6, 14)
        )

        assert len(result) == 1
        assert result[0].date == date(2026, 6, 14)
        assert result[0].appointment_count == 10

    @pytest.mark.asyncio
    async def test_trend_consecutive_days(self):
        """连续日期全部有数据时无空洞。"""
        rows = [
            _mock_row(
                d=date(2026, 6, 1), appointments=10, visits=8,
                completed=6, new_patients=3, revenue=Decimal("500"),
            ),
            _mock_row(
                d=date(2026, 6, 2), appointments=12, visits=10,
                completed=8, new_patients=4, revenue=Decimal("600"),
            ),
            _mock_row(
                d=date(2026, 6, 3), appointments=15, visits=12,
                completed=10, new_patients=5, revenue=Decimal("700"),
            ),
        ]
        service, _ = _make_service(rows=rows)

        result = await service.trend(
            start_date=date(2026, 6, 1), end_date=date(2026, 6, 3)
        )

        assert len(result) == 3
        assert result[0].appointment_count == 10
        assert result[1].appointment_count == 12
        assert result[2].appointment_count == 15
        # 全部有数据，不存在零值补齐
        assert all(p.appointment_count > 0 for p in result)
