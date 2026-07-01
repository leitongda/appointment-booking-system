"""
候补自动递补异步任务单元测试

验证 ``app.tasks.waitlist_promotion_task.handle_appointment_cancelled``:
- 正确解析 payload 并调用 WaitlistService.auto_promote
- 设置租户上下文（ContextVar）
- payload 缺少 schedule_id 时安全跳过
- auto_promote 抛异常时指数退避重试 3 次；用尽后才吞掉、返回 ok=False
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from celery.exceptions import Retry

from app.tasks.waitlist_promotion_task import handle_appointment_cancelled


def _make_task_module():
    """返回待测任务模块，便于 patch 其内部懒加载的依赖。"""
    import app.tasks.waitlist_promotion_task as m
    return m


class TestHandleAppointmentCancelled:
    """处理预约取消事件 —— 候补递补任务"""

    def test_promotes_and_sets_tenant_context(self):
        """正常路径：设置租户上下文 + 调用 auto_promote + 返回成功摘要"""
        fake_session = MagicMock()
        fake_service = MagicMock()
        fake_service.auto_promote = AsyncMock(return_value=[MagicMock(), MagicMock()])

        with patch(
            "app.middleware.tenant_context.set_tenant_context"
        ) as mock_set_tenant, patch(
            "app.db.session.async_session_maker"
        ) as mock_session_maker, patch(
            "app.modules.waitlist.service.WaitlistService"
        ) as mock_waitlist_cls:
            # async session_maker 作为 async context manager
            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(return_value=fake_session)
            session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = session_cm
            mock_waitlist_cls.return_value = fake_service

            result = handle_appointment_cancelled(
                {
                    "tenant_id": "tenant-1",
                    "schedule_id": "sched-1",
                    "appointment_id": "appt-1",
                    "reason": "APPOINTMENT_CANCELLED",
                }
            )

        # 还原了租户上下文
        mock_set_tenant.assert_called_once_with("tenant-1")
        # 用同步 session（async_session_maker 产出的）实例化 service 并调用 auto_promote
        mock_waitlist_cls.assert_called_once_with(fake_session)
        fake_service.auto_promote.assert_awaited_once_with(
            schedule_id="sched-1", reason="APPOINTMENT_CANCELLED"
        )
        assert result["ok"] is True
        assert result["promoted_count"] == 2
        assert result["tenant_id"] == "tenant-1"
        assert result["schedule_id"] == "sched-1"
        assert result["appointment_id"] == "appt-1"

    def test_missing_schedule_id_skips(self):
        """payload 缺少 schedule_id 时安全跳过，不实例化 service"""
        with patch(
            "app.modules.waitlist.service.WaitlistService"
        ) as mock_waitlist_cls, patch(
            "app.db.session.async_session_maker"
        ) as mock_session_maker:
            result = handle_appointment_cancelled(
                {"tenant_id": "tenant-1", "schedule_id": None, "appointment_id": "a1"}
            )

        mock_waitlist_cls.assert_not_called()
        mock_session_maker.assert_not_called()
        assert result["ok"] is False
        assert result["reason"] == "missing_schedule_id"

    def test_reason_defaults_when_absent(self):
        """payload 未带 reason 时默认 APPOINTMENT_CANCELLED"""
        fake_session = MagicMock()
        fake_service = MagicMock()
        fake_service.auto_promote = AsyncMock(return_value=[])

        with patch(
            "app.db.session.async_session_maker"
        ) as mock_session_maker, patch(
            "app.modules.waitlist.service.WaitlistService"
        ) as mock_waitlist_cls:
            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(return_value=fake_session)
            session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = session_cm
            mock_waitlist_cls.return_value = fake_service

            result = handle_appointment_cancelled(
                {
                    "tenant_id": None,
                    "schedule_id": "sched-2",
                    "appointment_id": "appt-2",
                    # reason 故意缺失
                }
            )

        fake_service.auto_promote.assert_awaited_once_with(
            schedule_id="sched-2", reason="APPOINTMENT_CANCELLED"
        )
        assert result["ok"] is True
        assert result["promoted_count"] == 0

    def test_exception_retries_when_under_limit(self):
        """未用尽重试次数时，auto_promote 抛异常触发指数退避重试（countdown=2^retries）"""
        fake_session = MagicMock()
        fake_service = MagicMock()
        fake_service.auto_promote = AsyncMock(side_effect=RuntimeError("boom"))

        with patch(
            "app.db.session.async_session_maker"
        ) as mock_session_maker, patch(
            "app.modules.waitlist.service.WaitlistService"
        ) as mock_waitlist_cls:
            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(return_value=fake_session)
            session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = session_cm
            mock_waitlist_cls.return_value = fake_service

            # 模拟 Celery worker 拦截 retry 信号（self.retry 实际抛 Retry）
            with patch.object(
                handle_appointment_cancelled, "retry"
            ) as mock_retry:
                mock_retry.side_effect = Retry()
                with pytest.raises(Retry):
                    handle_appointment_cancelled(
                        {
                            "tenant_id": "tenant-9",
                            "schedule_id": "sched-9",
                            "appointment_id": "appt-9",
                            "reason": "APPOINTMENT_CANCELLED",
                        }
                    )

        mock_retry.assert_called_once()
        # 首次（retries=0）：countdown = 2^0 = 1
        assert mock_retry.call_args.kwargs["countdown"] == 1
        assert isinstance(mock_retry.call_args.kwargs["exc"], RuntimeError)

    def test_exception_swallowed_after_retries_exhausted(self):
        """重试次数用尽后，auto_promote 抛异常被吞掉，返回 ok=False（取消已成功，号源空转由 reconcile 告警）"""
        fake_session = MagicMock()
        fake_service = MagicMock()
        fake_service.auto_promote = AsyncMock(side_effect=RuntimeError("boom"))

        with patch(
            "app.db.session.async_session_maker"
        ) as mock_session_maker, patch(
            "app.modules.waitlist.service.WaitlistService"
        ) as mock_waitlist_cls:
            session_cm = MagicMock()
            session_cm.__aenter__ = AsyncMock(return_value=fake_session)
            session_cm.__aexit__ = AsyncMock(return_value=None)
            mock_session_maker.return_value = session_cm
            mock_waitlist_cls.return_value = fake_service

            # 模拟已用尽重试次数
            handle_appointment_cancelled.push_request(
                retries=handle_appointment_cancelled.max_retries
            )
            try:
                result = handle_appointment_cancelled(
                    {
                        "tenant_id": "tenant-9",
                        "schedule_id": "sched-9",
                        "appointment_id": "appt-9",
                        "reason": "APPOINTMENT_CANCELLED",
                    }
                )
            finally:
                handle_appointment_cancelled.pop_request()

        assert result["ok"] is False
        assert "boom" in result["error"]
        assert result["schedule_id"] == "sched-9"
        assert result["exhausted_retries"] is True
