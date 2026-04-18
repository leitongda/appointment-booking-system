"""
排班定时任务单元测试
测试自动排班的租户级并行编排与单租户执行逻辑
"""
import logging
from datetime import date, time
from unittest.mock import MagicMock, patch

from app.tasks.schedule_task import (
    auto_generate_schedules_task,
    generate_schedules_for_template,
    generate_schedules_for_tenant_task,
    is_rest_day,
    summarize_auto_generate_schedules_task,
)
from app.models.schedule_template import ScheduleTemplate

logger = logging.getLogger(__name__)


def _make_tenant(tenant_id="tenant-1", tenant_code="hospital-a", name="测试医院"):
    tenant = MagicMock()
    tenant.id = tenant_id
    tenant.tenant_code = tenant_code
    tenant.name = name
    return tenant


def _make_template(
    template_id="template-1",
    name="测试模板",
    doctor_id="doctor-1",
    store_id="store-1",
    weekday_list=None,
    schedule_mode="weekly",
    start_time=time(9, 0),
    end_time=time(17, 0),
    slot_count=2,
    slot_capacity=10,
    break_times_list=None,
    appointment_type="normal",
    tenant_id="tenant-1",
):
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


class TestIsRestDay:
    def test_is_rest_day_no_rest_days_configured(self):
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = is_rest_day(mock_db, date.today())
        assert result is False

    def test_is_rest_day_with_store_filter(self):
        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = is_rest_day(mock_db, date.today(), store_id="store-1")
        assert result is False

    def test_is_rest_day_exception_handling(self):
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("数据库错误")

        result = is_rest_day(mock_db, date.today())
        assert result is False


class TestAutoGenerateSchedulesTask:
    @patch("app.tasks.schedule_task.chord")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_no_tenants(
        self,
        mock_get_sync_db,
        mock_settings,
        mock_chord,
    ):
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result
        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = auto_generate_schedules_task()

        assert result["status"] == "noop"
        assert result["dispatched_tenant_count"] == 0
        assert result["created_count"] == 0
        assert result["tenant_results"] == []
        mock_chord.assert_not_called()

    @patch("app.tasks.schedule_task.chord")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_auto_generate_schedules_task_dispatches_tenant_subtasks(
        self,
        mock_get_sync_db,
        mock_settings,
        mock_chord,
    ):
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        tenant1 = _make_tenant("tenant-1", "hospital-a", "医院A")
        tenant2 = _make_tenant("tenant-2", "hospital-b", "医院B")

        mock_db = MagicMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [tenant1, tenant2]
        mock_db.execute.return_value = mock_result
        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        captured = {}

        def fake_chord(header):
            captured["header"] = header

            def apply(callback):
                captured["callback"] = callback
                result = MagicMock()
                result.id = "chord-123"
                return result

            return apply

        mock_chord.side_effect = fake_chord

        result = auto_generate_schedules_task()

        assert result["status"] == "dispatched"
        assert result["dispatched_tenant_count"] == 2
        assert result["tenant_ids"] == ["tenant-1", "tenant-2"]
        assert result["chord_id"] == "chord-123"
        assert len(captured["header"]) == 2
        assert captured["header"][0].task == "app.tasks.schedule_task.generate_schedules_for_tenant_task"
        assert captured["header"][0].args == ("tenant-1", "hospital-a", "医院A", 7)
        assert captured["callback"].task == "app.tasks.schedule_task.summarize_auto_generate_schedules_task"
        assert captured["callback"].kwargs == {"dispatched_tenant_count": 2}


class TestGenerateSchedulesForTenantTask:
    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task._get_enabled_templates_for_tenant")
    def test_generate_schedules_for_tenant_task_no_templates(
        self,
        mock_get_templates,
        mock_settings,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_get_templates.return_value = []

        result = generate_schedules_for_tenant_task(
            "tenant-1", "hospital-a", "医院A"
        )

        assert result["tenant_id"] == "tenant-1"
        assert result["template_count"] == 0
        assert result["created_count"] == 0
        assert result["error"] is None
        mock_set_tenant_ctx.assert_called_once_with("tenant-1", "hospital-a")
        mock_clear_tenant_ctx.assert_called_once()

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task._generate_template_schedules")
    @patch("app.tasks.schedule_task._get_enabled_templates_for_tenant")
    def test_generate_schedules_for_tenant_task_success(
        self,
        mock_get_templates,
        mock_generate_template,
        mock_settings,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_get_templates.return_value = [
            _make_template(template_id="template-1"),
            _make_template(template_id="template-2", doctor_id="doctor-2"),
        ]
        mock_generate_template.side_effect = [
            {
                "template_id": "template-1",
                "template_name": "模板1",
                "doctor_id": "doctor-1",
                "created_count": 2,
                "skipped_count": 1,
                "error": None,
            },
            {
                "template_id": "template-2",
                "template_name": "模板2",
                "doctor_id": "doctor-2",
                "created_count": 1,
                "skipped_count": 0,
                "error": None,
            },
        ]

        result = generate_schedules_for_tenant_task(
            "tenant-1", "hospital-a", "医院A"
        )

        assert result["template_count"] == 2
        assert result["success_count"] == 2
        assert result["failed_count"] == 0
        assert result["created_count"] == 3
        assert result["skipped_count"] == 1
        assert result["error"] is None
        mock_set_tenant_ctx.assert_called_once_with("tenant-1", "hospital-a")
        mock_clear_tenant_ctx.assert_called_once()

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.settings")
    @patch("app.tasks.schedule_task._get_enabled_templates_for_tenant")
    def test_generate_schedules_for_tenant_task_failure_returns_error_summary(
        self,
        mock_get_templates,
        mock_settings,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
        mock_settings.SCHEDULE_AUTO_GENERATE_DAYS = 7
        mock_get_templates.side_effect = Exception("租户模板查询失败")

        result = generate_schedules_for_tenant_task(
            "tenant-1", "hospital-a", "医院A"
        )

        assert result["tenant_id"] == "tenant-1"
        assert result["template_count"] == 0
        assert result["error"] == "租户模板查询失败"
        mock_set_tenant_ctx.assert_called_once_with("tenant-1", "hospital-a")
        mock_clear_tenant_ctx.assert_called_once()


class TestSummarizeAutoGenerateSchedulesTask:
    def test_summarize_auto_generate_schedules_task(self):
        tenant_results = [
            {
                "tenant_id": "tenant-1",
                "created_count": 3,
                "skipped_count": 1,
                "template_count": 2,
                "success_count": 2,
                "failed_count": 0,
                "error": None,
            },
            {
                "tenant_id": "tenant-2",
                "created_count": 0,
                "skipped_count": 0,
                "template_count": 0,
                "success_count": 0,
                "failed_count": 0,
                "error": "数据库异常",
            },
        ]

        result = summarize_auto_generate_schedules_task(
            tenant_results,
            dispatched_tenant_count=2,
        )

        assert result["status"] == "completed"
        assert result["dispatched_tenant_count"] == 2
        assert result["completed_tenant_count"] == 2
        assert result["successful_tenant_count"] == 1
        assert result["failed_tenant_count"] == 1
        assert result["created_count"] == 3
        assert result["template_count"] == 2


class TestGenerateSchedulesForTemplate:
    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_generate_schedules_for_template_not_found(
        self,
        mock_get_sync_db,
        mock_is_rest_day,
        mock_should_generate,
        mock_split,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
        mock_db = MagicMock()
        mock_db.get.return_value = None

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "non-existent-template",
            "2024-01-01",
            "2024-01-07",
        )

        assert result["created_count"] == 0
        assert "reason" in result
        mock_set_tenant_ctx.assert_called_once_with(None, None)
        mock_clear_tenant_ctx.assert_called_once()

    @patch("app.tasks.schedule_task.clear_tenant_context")
    @patch("app.tasks.schedule_task.set_tenant_context")
    @patch("app.tasks.schedule_task.split_time_range_with_breaks")
    @patch("app.tasks.schedule_task.should_generate_schedule")
    @patch("app.tasks.schedule_task.is_rest_day")
    @patch("app.tasks.schedule_task.get_sync_db")
    def test_generate_schedules_for_template_disabled(
        self,
        mock_get_sync_db,
        mock_is_rest_day,
        mock_should_generate,
        mock_split,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
        mock_template = MagicMock()
        mock_template.status = 0

        mock_db = MagicMock()
        mock_db.get.return_value = mock_template

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "template-1",
            "2024-01-01",
            "2024-01-07",
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
        self,
        mock_get_sync_db,
        mock_is_rest_day,
        mock_should_generate,
        mock_split,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
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
            tenant_code="hospital-a",
        )

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
        self,
        mock_get_sync_db,
        mock_is_rest_day,
        mock_should_generate,
        mock_split,
        mock_set_tenant_ctx,
        mock_clear_tenant_ctx,
    ):
        mock_template = MagicMock()
        mock_template.status = 1
        mock_template.tenant_id = "tenant-2"

        mock_db = MagicMock()
        mock_db.get.return_value = mock_template

        mock_get_sync_db.return_value.__enter__ = MagicMock(return_value=mock_db)
        mock_get_sync_db.return_value.__exit__ = MagicMock(return_value=False)

        result = generate_schedules_for_template(
            "template-1",
            "2024-01-01",
            "2024-01-07",
            tenant_id="tenant-1",
        )

        assert result["created_count"] == 0
        assert result["reason"] == "模板不属于指定租户"
