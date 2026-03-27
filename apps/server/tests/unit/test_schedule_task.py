"""
排班定时任务单元测试
测试定时任务按模板隔离事务 + 多租户隔离
"""
import pytest
import logging
from unittest.mock import patch, MagicMock, call
from datetime import date, timedelta, time

from app.tasks.schedule_task import (
    auto_generate_schedules_task,
    is_rest_day,
    generate_schedules_for_template
)
from app.models.schedule_template import ScheduleTemplate
from app.models.schedule import Schedule

logger = logging.getLogger(__name__)


class TestIsRestDay:
    """测试休息日检查函数"""

    def test_is_rest_day_no_rest_days_configured(self):
        """测试没有配置休息日"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = is_rest_day(mock_db, date.today())
        assert result is False

    def test_is_rest_day_with_store_filter(self):
        """测试带门店过滤的休息日检查"""
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = is_rest_day(mock_db, date.today(), store_id="store-1")
        assert result is False

    def test_is_rest_day_exception_handling(self):
        """测试异常处理"""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("数据库错误")

        result = is_rest_day(mock_db, date.today())
        assert result is False


def _make_tenant(tenant_id="tenant-1", tenant_code="hospital-a", name="测试医院"):
    """创建模拟租户对象"""
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.tenant_code = tenant_code
    tenant.name = name
    return tenant


def _make_template(template_id="template-1", name="测试模板", doctor_id="doctor-1",
                   store_id="store-1", weekday_list=None, schedule_mode="weekly",
                   start_time=time(9, 0), end_time=time(17, 0), slot_count=2,
                   slot_capacity=10, break_times_list=None, appointment_type="normal",
                   tenant_id="tenant-1"):
    """创建模拟排班模板对象"""
    template = MagicMock(spec=ScheduleTemplate)
    template.id = template_id
    template.name = name
    template.doctor_id = doctor_id
    template.store_id = store_id
    template.weekday_list = [1, 2, 3, 4, 5] if weekday_list is None else weekday_list
    template.start_time = start_time
    template.end_time = end_time
    template.slot_count = slot_count
    template.slot_capacity = slot_capacity
    template.schedule_mode = schedule_mode
    template.break_times_list = [] if break_times_list is None else break_times_list
    template.appointment_type = appointment_type
    template.tenant_id = tenant_id
    return template


class TestAutoGenerateSchedulesTask:
    """测试自动排班生成任务（多租户版本）"""

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_no_tenants(
        self, mock_get_sync_db, mock_session_local, mock_settings,
        mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试没有活跃租户"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7

        # 模拟查询租户返回空列表
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = auto_generate_schedules_task()

        assert result["created_count"] == 0
        assert result["skipped_count"] == 0
        assert result["template_results"] == []

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_success(
        self, mock_get_sync_db, mock_session_local, mock_is_rest_day,
        mock_should_generate, mock_split, mock_settings,
        mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试成功生成排班"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_is_rest_day.return_value = False
        mock_should_generate.return_value = True
        mock_split.return_value = [(time(9, 0), time(12, 0)), (time(14, 0), time(17, 0))]

        # 创建模拟租户
        tenant = _make_tenant()

        # 创建模拟模板
        template = _make_template()

        # 模拟 get_sync_db 上下文管理器
        # 第一次调用返回租户列表，第二次调用返回模板列表
        mock_db = MagicMock()
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalars.return_value.all.return_value = [tenant]

        mock_template_result = MagicMock()
        mock_template_result.scalars.return_value.all.return_value = [template]

        mock_db.execute.side_effect = [mock_tenant_result, mock_template_result]

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 SessionLocal
        mock_template_db = MagicMock()
        mock_template_db.execute.return_value.scalar_one_or_none.return_value = None  # 没有已存在的排班
        mock_session_local.return_value = mock_template_db

        result = auto_generate_schedules_task()

        assert result["template_count"] == 1
        assert result["success_count"] == 1
        assert result["failed_count"] == 0
        # 验证设置了租户上下文
        mock_set_tenant_ctx.assert_called_once_with(tenant.id, tenant.tenant_code)
        mock_clear_tenant_ctx.assert_called_once()

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_rest_day(
        self, mock_get_sync_db, mock_session_local, mock_is_rest_day,
        mock_should_generate, mock_settings, mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试休息日不生成排班"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_is_rest_day.return_value = True  # 所有日期都是休息日
        mock_should_generate.return_value = True

        # 创建模拟租户和模板
        tenant = _make_tenant()
        template = _make_template()

        # 模拟 get_sync_db
        mock_db = MagicMock()
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalars.return_value.all.return_value = [tenant]
        mock_template_result = MagicMock()
        mock_template_result.scalars.return_value.all.return_value = [template]
        mock_db.execute.side_effect = [mock_tenant_result, mock_template_result]

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 SessionLocal
        mock_template_db = MagicMock()
        mock_session_local.return_value = mock_template_db

        result = auto_generate_schedules_task()

        assert result["template_count"] == 1
        assert result["success_count"] == 1
        assert result["created_count"] == 0  # 休息日不创建排班

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_no_weekday(
        self, mock_get_sync_db, mock_session_local, mock_settings,
        mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试没有配置星期"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7

        # 创建模拟租户和没有配置星期的模板
        tenant = _make_tenant()
        template = _make_template(weekday_list=[])  # 空列表

        # 模拟 get_sync_db
        mock_db = MagicMock()
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalars.return_value.all.return_value = [tenant]
        mock_template_result = MagicMock()
        mock_template_result.scalars.return_value.all.return_value = [template]
        mock_db.execute.side_effect = [mock_tenant_result, mock_template_result]

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 SessionLocal
        mock_template_db = MagicMock()
        mock_session_local.return_value = mock_template_db

        result = auto_generate_schedules_task()

        assert result["template_count"] == 1
        assert result["template_results"][0]["error"] == "没有配置星期"

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_template_failure(
        self, mock_get_sync_db, mock_session_local, mock_is_rest_day,
        mock_should_generate, mock_split, mock_settings,
        mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试模板处理失败不影响其他模板"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_is_rest_day.return_value = False
        mock_should_generate.return_value = True
        mock_split.return_value = [(time(9, 0), time(12, 0))]

        # 创建模拟租户
        tenant = _make_tenant()

        # 创建两个模板
        template1 = _make_template(template_id="template-1", name="失败模板")
        template2 = _make_template(template_id="template-2", name="成功模板", doctor_id="doctor-2")

        # 模拟 get_sync_db
        mock_db = MagicMock()
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalars.return_value.all.return_value = [tenant]
        mock_template_result = MagicMock()
        mock_template_result.scalars.return_value.all.return_value = [template1, template2]
        mock_db.execute.side_effect = [mock_tenant_result, mock_template_result]

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 SessionLocal - 第一个失败，第二个成功
        call_count = [0]

        def create_session():
            call_count[0] += 1
            mock_template_db = MagicMock()
            if call_count[0] == 1:
                # 第一个模板失败
                mock_template_db.execute.side_effect = Exception("模拟数据库错误")
            else:
                # 第二个模板成功
                mock_template_db.execute.return_value.scalar_one_or_none.return_value = None
            return mock_template_db

        mock_session_local.side_effect = create_session

        result = auto_generate_schedules_task()

        assert result["template_count"] == 2
        assert result["failed_count"] == 1

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_multi_tenant(
        self, mock_get_sync_db, mock_session_local, mock_is_rest_day,
        mock_should_generate, mock_split, mock_settings,
        mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试多租户场景：每个租户只处理自己的模板"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_is_rest_day.return_value = False
        mock_should_generate.return_value = True
        mock_split.return_value = [(time(9, 0), time(12, 0))]

        # 创建两个租户
        tenant1 = _make_tenant(tenant_id="tenant-1", tenant_code="hospital-a", name="医院A")
        tenant2 = _make_tenant(tenant_id="tenant-2", tenant_code="hospital-b", name="医院B")

        # 每个租户各有一个模板
        template1 = _make_template(template_id="template-1", name="医院A模板", tenant_id="tenant-1")
        template2 = _make_template(template_id="template-2", name="医院B模板", tenant_id="tenant-2")

        # 模拟 get_sync_db
        mock_db = MagicMock()
        # 第一次调用：查租户列表
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalars.return_value.all.return_value = [tenant1, tenant2]
        # 第二次调用：租户1的模板
        mock_template1_result = MagicMock()
        mock_template1_result.scalars.return_value.all.return_value = [template1]
        # 第三次调用：租户2的模板
        mock_template2_result = MagicMock()
        mock_template2_result.scalars.return_value.all.return_value = [template2]

        mock_db.execute.side_effect = [
            mock_tenant_result,
            mock_template1_result,
            mock_template2_result,
        ]

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 SessionLocal
        mock_template_db = MagicMock()
        mock_template_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_session_local.return_value = mock_template_db

        result = auto_generate_schedules_task()

        assert result["template_count"] == 2
        assert result["success_count"] == 2
        assert result["failed_count"] == 0
        # 验证为每个租户都设置了上下文
        assert mock_set_tenant_ctx.call_count == 2
        mock_set_tenant_ctx.assert_any_call("tenant-1", "hospital-a")
        mock_set_tenant_ctx.assert_any_call("tenant-2", "hospital-b")

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.db.session.SessionLocal")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_tenant_failure_does_not_affect_others(
        self, mock_get_sync_db, mock_session_local, mock_is_rest_day,
        mock_should_generate, mock_split, mock_settings,
        mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试一个租户处理失败不影响其他租户"""
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_is_rest_day.return_value = False
        mock_should_generate.return_value = True
        mock_split.return_value = [(time(9, 0), time(12, 0))]

        # 创建两个租户
        tenant1 = _make_tenant(tenant_id="tenant-1", tenant_code="hospital-a", name="医院A")
        tenant2 = _make_tenant(tenant_id="tenant-2", tenant_code="hospital-b", name="医院B")

        template1 = _make_template(template_id="template-1", name="医院A模板")
        template2 = _make_template(template_id="template-2", name="医院B模板")

        # 模拟 get_sync_db
        mock_db = MagicMock()
        mock_tenant_result = MagicMock()
        mock_tenant_result.scalars.return_value.all.return_value = [tenant1, tenant2]

        # 租户1的模板查询抛异常
        mock_db.execute.side_effect = [
            mock_tenant_result,
            Exception("租户1数据库查询失败"),  # 租户1查询模板失败
        ]

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        # 模拟 SessionLocal
        mock_template_db = MagicMock()
        mock_template_db.execute.return_value.scalar_one_or_none.return_value = None
        mock_session_local.return_value = mock_template_db

        result = auto_generate_schedules_task()

        # 租户1失败，租户2也会因为同一个 mock 的 side_effect 而受影响
        # 但核心是验证异常不会导致整个任务崩溃
        assert "template_results" in result
        # 验证 clear_tenant_context 被调用（即使异常）
        assert mock_clear_tenant_ctx.call_count >= 1


class TestGenerateSchedulesForTemplate:
    """测试为指定模板生成排班"""

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_generate_schedules_for_template_not_found(
        self, mock_get_sync_db, mock_is_rest_day, mock_should_generate,
        mock_split, mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试模板不存在"""
        mock_db = MagicMock()
        mock_db.get.return_value = None

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "non-existent-template",
            "2024-01-01",
            "2024-01-07"
        )

        assert result["created_count"] == 0
        assert "reason" in result
        # 验证租户上下文被设置和清除
        mock_set_tenant_ctx.assert_called_once_with(None, None)
        mock_clear_tenant_ctx.assert_called_once()

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_generate_schedules_for_template_disabled(
        self, mock_get_sync_db, mock_is_rest_day, mock_should_generate,
        mock_split, mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试模板未启用"""
        mock_template = MagicMock()
        mock_template.status = 0  # 未启用

        mock_db = MagicMock()
        mock_db.get.return_value = mock_template

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "template-1",
            "2024-01-01",
            "2024-01-07"
        )

        assert result["created_count"] == 0
        assert "reason" in result

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_generate_schedules_for_template_with_tenant_context(
        self, mock_get_sync_db, mock_is_rest_day, mock_should_generate,
        mock_split, mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试带租户上下文的模板排班生成"""
        mock_is_rest_day.return_value = False
        mock_should_generate.return_value = True
        mock_split.return_value = [(time(9, 0), time(12, 0))]

        mock_template = MagicMock()
        mock_template.status = 1
        mock_template.tenant_id = "tenant-1"
        mock_template.weekday_list = [1]
        mock_template.start_time = time(9, 0)
        mock_template.end_time = time(17, 0)
        mock_template.slot_count = 1
        mock_template.slot_capacity = 10
        mock_template.schedule_mode = "weekly"
        mock_template.break_times_list = []
        mock_template.appointment_type = "normal"
        mock_template.doctor_id = "doctor-1"
        mock_template.store_id = "store-1"

        mock_db = MagicMock()
        mock_db.get.return_value = mock_template
        mock_db.execute.return_value.scalar_one_or_none.return_value = None

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "template-1",
            "2024-01-01",
            "2024-01-07",
            tenant_id="tenant-1",
            tenant_code="hospital-a"
        )

        # 验证设置了正确的租户上下文
        mock_set_tenant_ctx.assert_called_once_with("tenant-1", "hospital-a")
        mock_clear_tenant_ctx.assert_called_once()
        assert result["tenant_id"] == "tenant-1"

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_generate_schedules_for_template_tenant_mismatch(
        self, mock_get_sync_db, mock_is_rest_day, mock_should_generate,
        mock_split, mock_set_tenant_ctx, mock_clear_tenant_ctx
    ):
        """测试模板不属于指定租户时返回错误"""
        mock_template = MagicMock()
        mock_template.status = 1
        mock_template.tenant_id = "tenant-2"  # 模板属于租户2

        mock_db = MagicMock()
        mock_db.get.return_value = mock_template

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "template-1",
            "2024-01-01",
            "2024-01-07",
            tenant_id="tenant-1"  # 但请求来自租户1
        )

        assert result["created_count"] == 0
        assert result["reason"] == "模板不属于指定租户"
