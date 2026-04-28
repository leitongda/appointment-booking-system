"""统一通知分发器单元测试"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.notifications.dispatcher import NotificationDispatcher
from app.infrastructure.notifications.channels.base import BaseNotificationChannel
from app.schemas.notification import (
    NotificationEvent,
    NotificationContent,
    NotificationChannel,
    NotificationPriority,
)


# ==================== Mock 渠道用于测试 ====================

class MockSuccessChannel(BaseNotificationChannel):
    """模拟成功发送的渠道"""

    @property
    def channel_name(self) -> str:
        return "mock_success"

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        return True


class MockFailureChannel(BaseNotificationChannel):
    """模拟发送失败的渠道"""

    @property
    def channel_name(self) -> str:
        return "mock_failure"

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        raise Exception("模拟发送失败")


class MockValidateFailChannel(BaseNotificationChannel):
    """模拟验证失败的渠道"""

    @property
    def channel_name(self) -> str:
        return "mock_validate_fail"

    async def validate_recipient(self, event: NotificationEvent) -> tuple[bool, str | None]:
        return False, "缺少必要信息"

    async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
        return True


# ==================== 测试夹具 ====================

@pytest.fixture
def mock_db():
    """模拟数据库会话"""
    db = AsyncMock(spec=AsyncSession)
    db.execute = AsyncMock()
    db.commit = AsyncMock()
    db.flush = AsyncMock()
    db.add = MagicMock()
    db.refresh = AsyncMock()
    return db


@pytest.fixture
def sample_event():
    """示例通知事件"""
    return NotificationEvent(
        tenant_id="tenant123",
        recipient_id="user123",
        recipient_type="patient",
        recipient_phone="13800138000",
        template_code="appointment_success",
        variables={"patient_name": "张三", "doctor": "李医生", "time": "2024-01-01 09:00"},
        message_type="appointment_success",
        related_id="apt123",
        priority=NotificationPriority.NORMAL,
    )


# ==================== 单元测试 ====================

class TestNotificationDispatcher:
    """通知分发器测试"""

    @pytest.mark.asyncio
    async def test_dispatch_success(self, mock_db, sample_event):
        """测试成功发送通知"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis

            # 注册模拟渠道并清空内置渠道
            from app.infrastructure.notifications.registry import channel_registry
            original_channels = channel_registry._channels.copy()
            channel_registry._channels.clear()
            channel_registry.register(MockSuccessChannel)

            try:
                # 显式指定使用 mock_success 渠道
                sample_event.channels = ["mock_success"]

                dispatcher = NotificationDispatcher(mock_db)
                result = await dispatcher.dispatch(sample_event)

                assert result.total_channels == 1
                assert result.success_channels == 1
                assert result.failed_channels == 0
                assert "mock_success" in result.results
                assert result.results["mock_success"].success is True
            finally:
                # 恢复原始渠道
                channel_registry._channels.clear()
                for name, channel_class in original_channels.items():
                    channel_registry._channels[name] = channel_class

    @pytest.mark.asyncio
    async def test_dispatch_with_failure(self, mock_db, sample_event):
        """测试发送失败处理"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis

            from app.infrastructure.notifications.registry import channel_registry
            original_channels = channel_registry._channels.copy()
            channel_registry._channels.clear()
            channel_registry.register(MockSuccessChannel)
            channel_registry.register(MockFailureChannel)

            try:
                # 指定渠道
                sample_event.channels = ["mock_success", "mock_failure"]

                dispatcher = NotificationDispatcher(mock_db)
                result = await dispatcher.dispatch(sample_event)

                # 由于降级策略，mock_success 成功后不会再尝试 mock_failure
                assert result.success_channels >= 1
                assert "mock_success" in result.results
                assert result.results["mock_success"].success is True
            finally:
                # 恢复原始渠道
                channel_registry._channels.clear()
                for name, channel_class in original_channels.items():
                    channel_registry._channels[name] = channel_class

    @pytest.mark.asyncio
    async def test_dispatch_with_validation_failure(self, mock_db, sample_event):
        """测试验证失败处理"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis

            from app.infrastructure.notifications.registry import channel_registry
            original_channels = channel_registry._channels.copy()
            channel_registry._channels.clear()
            channel_registry.register(MockSuccessChannel)
            channel_registry.register(MockValidateFailChannel)

            try:
                sample_event.channels = ["mock_success", "mock_validate_fail"]

                dispatcher = NotificationDispatcher(mock_db)
                result = await dispatcher.dispatch(sample_event)

                # mock_validate_fail 验证失败会被跳过
                assert result.success_channels >= 1
                assert "mock_validate_fail" not in result.results
            finally:
                # 恢复原始渠道
                channel_registry._channels.clear()
                for name, channel_class in original_channels.items():
                    channel_registry._channels[name] = channel_class

    @pytest.mark.asyncio
    async def test_check_preference_default(self, mock_db, sample_event):
        """测试偏好检查默认行为（无偏好记录时默认允许）"""
        # 模拟数据库返回无偏好记录
        mock_db.execute.return_value.first.return_value = None

        dispatcher = NotificationDispatcher(mock_db)
        preference_allowed = await dispatcher._check_preference(sample_event, "in_app")

        assert preference_allowed is True

    @pytest.mark.asyncio
    async def test_check_preference_enabled(self, mock_db, sample_event):
        """测试偏好检查（用户启用通知）"""
        # 模拟数据库返回启用状态
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: True  # 两个字段都为 True
        mock_db.execute.return_value.first.return_value = mock_row

        dispatcher = NotificationDispatcher(mock_db)
        preference_allowed = await dispatcher._check_preference(sample_event, "in_app")

        assert preference_allowed is True

    @pytest.mark.asyncio
    async def test_check_preference_disabled(self, mock_db, sample_event):
        """测试偏好检查（用户禁用通知）"""
        # 模拟数据库返回禁用状态
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: False  # 某个字段为 False
        mock_db.execute.return_value.first.return_value = mock_row

        dispatcher = NotificationDispatcher(mock_db)
        preference_allowed = await dispatcher._check_preference(sample_event, "in_app")

        assert preference_allowed is False

    @pytest.mark.asyncio
    async def test_get_target_channels_explicit(self, mock_db, sample_event):
        """测试获取目标渠道（显式指定）"""
        sample_event.channels = ["sms", "email"]

        dispatcher = NotificationDispatcher(mock_db)
        channels = await dispatcher._get_target_channels(sample_event)

        assert channels == ["sms", "email"]

    @pytest.mark.asyncio
    async def test_get_target_channels_default(self, mock_db, sample_event):
        """测试获取目标渠道（默认策略）"""
        dispatcher = NotificationDispatcher(mock_db)
        channels = await dispatcher._get_target_channels(sample_event)

        # appointment_success 的默认渠道
        assert "in_app" in channels
        assert "wechat" in channels
        assert "sms" in channels

    @pytest.mark.asyncio
    async def test_render_content(self, mock_db, sample_event):
        """测试内容渲染"""
        sample_event.title = "测试标题"
        sample_event.content = "测试内容"

        dispatcher = NotificationDispatcher(mock_db)
        content = await dispatcher._render_content(sample_event)

        assert content.title == "测试标题"
        assert content.content == "测试内容"
        assert content.template_variables == sample_event.variables


class TestChannelRegistry:
    """渠道注册表测试"""

    def test_register_channel(self):
        """测试渠道注册"""
        from app.infrastructure.notifications.registry import ChannelRegistry

        registry = ChannelRegistry()
        registry.register(MockSuccessChannel)

        assert "mock_success" in registry.list_channels()
        assert registry.is_available("mock_success") is True
        assert registry.is_available("nonexistent") is False

    def test_get_channel(self):
        """测试获取渠道类"""
        from app.infrastructure.notifications.registry import ChannelRegistry

        registry = ChannelRegistry()
        registry.register(MockSuccessChannel)

        channel_class = registry.get("mock_success")
        assert channel_class is MockSuccessChannel

        channel_class = registry.get("nonexistent")
        assert channel_class is None


class TestNotificationDispatcherDedup:
    """消息去重测试"""

    @pytest.mark.asyncio
    async def test_check_and_mark_dedup_first_time(self, mock_db, sample_event):
        """测试首次发送通过去重检查"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)  # 首次设置成功
            mock_get_redis.return_value = mock_redis

            dispatcher = NotificationDispatcher(mock_db)
            is_duplicate = await dispatcher._check_and_mark_dedup(sample_event)

            assert is_duplicate is False  # 首次发送，不重复
            mock_redis.set.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_and_mark_dedup_duplicate(self, mock_db, sample_event):
        """测试重复发送被拦截"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=None)  # key 已存在，设置失败
            mock_get_redis.return_value = mock_redis

            dispatcher = NotificationDispatcher(mock_db)
            is_duplicate = await dispatcher._check_and_mark_dedup(sample_event)

            assert is_duplicate is True  # 重复发送

    @pytest.mark.asyncio
    async def test_dispatch_skip_duplicate(self, mock_db, sample_event):
        """测试 dispatch 跳过重复消息"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=None)  # 模拟已存在
            mock_get_redis.return_value = mock_redis

            from app.infrastructure.notifications.registry import channel_registry
            original_channels = channel_registry._channels.copy()
            channel_registry._channels.clear()
            channel_registry.register(MockSuccessChannel)

            try:
                sample_event.channels = ["mock_success"]

                dispatcher = NotificationDispatcher(mock_db)
                result = await dispatcher.dispatch(sample_event)

                assert result.total_channels == 0  # 去重拦截，没有尝试发送
                assert result.skipped_channels == 1
            finally:
                channel_registry._channels.clear()
                for name, channel_class in original_channels.items():
                    channel_registry._channels[name] = channel_class


class TestNotificationDispatcherDegradation:
    """渠道降级策略测试"""

    @pytest.mark.asyncio
    async def test_channel_degradation_on_failure(self, mock_db, sample_event):
        """测试渠道降级：首选失败后尝试降级渠道"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis

            from app.infrastructure.notifications.registry import channel_registry
            original_channels = channel_registry._channels.copy()
            channel_registry._channels.clear()
            channel_registry.register(MockFailureChannel)
            channel_registry.register(MockSuccessChannel)

            try:
                # 指定渠道顺序：失败渠道在前，成功渠道在后
                sample_event.channels = ["mock_failure", "mock_success"]

                dispatcher = NotificationDispatcher(mock_db)
                result = await dispatcher.dispatch(sample_event)

                # mock_failure 发送失败后，会尝试 mock_success
                # mock_success 成功后停止降级
                assert result.success_channels == 1
                assert "mock_success" in result.results
                assert result.results["mock_success"].success is True
            finally:
                channel_registry._channels.clear()
                for name, channel_class in original_channels.items():
                    channel_registry._channels[name] = channel_class

    @pytest.mark.asyncio
    async def test_channel_degradation_stop_on_success(self, mock_db, sample_event):
        """测试渠道降级：首选成功后不再尝试降级渠道"""
        with patch("app.infrastructure.notifications.dispatcher.get_redis") as mock_get_redis:
            mock_redis = AsyncMock()
            mock_redis.set = AsyncMock(return_value=True)
            mock_get_redis.return_value = mock_redis

            from app.infrastructure.notifications.registry import channel_registry
            original_channels = channel_registry._channels.copy()
            channel_registry._channels.clear()

            # 创建一个记录调用次数的渠道
            call_count = {"count": 0}

            class MockCountChannel(BaseNotificationChannel):
                @property
                def channel_name(self) -> str:
                    return "mock_count"

                async def send(self, event: NotificationEvent, content: NotificationContent) -> bool:
                    call_count["count"] += 1
                    return True

            channel_registry.register(MockSuccessChannel)
            channel_registry.register(MockCountChannel)

            try:
                sample_event.channels = ["mock_success", "mock_count"]

                dispatcher = NotificationDispatcher(mock_db)
                result = await dispatcher.dispatch(sample_event)

                assert result.success_channels == 1
                assert call_count["count"] == 0  # 降级渠道未被调用
                assert "mock_count" not in result.results
            finally:
                channel_registry._channels.clear()
                for name, channel_class in original_channels.items():
                    channel_registry._channels[name] = channel_class


class TestNotificationDispatcherPreferenceFilter:
    """偏好过滤测试"""

    @pytest.mark.asyncio
    async def test_filter_by_preference_all_enabled(self, mock_db, sample_event):
        """测试偏好过滤：全部启用"""
        mock_row = MagicMock()
        mock_row.__getitem__ = lambda self, key: True
        mock_result = AsyncMock()
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result

        dispatcher = NotificationDispatcher(mock_db)
        filtered = await dispatcher._filter_by_preference_and_quiet_hours(
            sample_event, ["sms", "wechat", "in_app"]
        )

        assert filtered == ["sms", "wechat", "in_app"]

    @pytest.mark.asyncio
    async def test_filter_by_preference_channel_disabled(self, mock_db, sample_event):
        """测试偏好过滤：某渠道被禁用"""
        # 模拟 SQLAlchemy Row 对象，需要支持迭代和索引访问
        mock_row = (
            False,  # sms_enabled (禁用)
            True,   # email_enabled
            True,   # wechat_enabled
            True,   # in_app_enabled
            True,   # appointment_enabled
            True,   # reminder_enabled
            True,   # stop_clinic_enabled
            True,   # system_enabled
            True,   # consultation_enabled
            True,   # feedback_enabled
            None,   # quiet_hours_start
            None,   # quiet_hours_end
        )
        mock_result = AsyncMock()
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result

        dispatcher = NotificationDispatcher(mock_db)
        filtered = await dispatcher._filter_by_preference_and_quiet_hours(
            sample_event, ["sms", "wechat", "in_app"]
        )

        assert "sms" not in filtered
        assert "wechat" in filtered
        assert "in_app" in filtered

    @pytest.mark.asyncio
    async def test_filter_by_preference_message_type_disabled(self, mock_db, sample_event):
        """测试偏好过滤：消息类型被禁用"""
        # 模拟 SQLAlchemy Row 对象，appointment_enabled=False
        mock_row = (
            True,   # sms_enabled
            True,   # email_enabled
            True,   # wechat_enabled
            True,   # in_app_enabled
            False,  # appointment_enabled (禁用)
            True,   # reminder_enabled
            True,   # stop_clinic_enabled
            True,   # system_enabled
            True,   # consultation_enabled
            True,   # feedback_enabled
            None,   # quiet_hours_start
            None,   # quiet_hours_end
        )
        mock_result = AsyncMock()
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result

        dispatcher = NotificationDispatcher(mock_db)
        filtered = await dispatcher._filter_by_preference_and_quiet_hours(
            sample_event, ["sms", "wechat", "in_app"]
        )

        assert filtered == []  # 消息类型禁用，全部过滤


class TestNotificationDispatcherQuietHours:
    """免打扰时段测试"""

    @pytest.mark.asyncio
    async def test_in_quiet_hours_same_day(self, mock_db):
        """测试免打扰时段判断（同一天内）"""
        from datetime import time
        from unittest.mock import patch

        # 模拟当前时间为 22:30
        with patch("app.infrastructure.notifications.dispatcher.datetime") as mock_datetime:
            mock_now = MagicMock()
            mock_now.time.return_value = time(22, 30)
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw)

            dispatcher = NotificationDispatcher(mock_db)

            # 22:00 - 06:00（跨天）
            assert dispatcher._in_quiet_hours("22:00", "06:00") is True
            # 08:00 - 18:00（当前不在）
            assert dispatcher._in_quiet_hours("08:00", "18:00") is False

    @pytest.mark.asyncio
    async def test_filter_by_quiet_hours(self, mock_db, sample_event):
        """测试免打扰时段过滤：仅保留 in_app"""
        # 模拟 SQLAlchemy Row 对象，设置免打扰时段
        mock_row = (
            True,    # sms_enabled
            True,    # email_enabled
            True,    # wechat_enabled
            True,    # in_app_enabled
            True,    # appointment_enabled
            True,    # reminder_enabled
            True,    # stop_clinic_enabled
            True,    # system_enabled
            True,    # consultation_enabled
            True,    # feedback_enabled
            "22:00", # quiet_hours_start
            "06:00", # quiet_hours_end
        )
        mock_result = AsyncMock()
        mock_result.first.return_value = mock_row
        mock_db.execute.return_value = mock_result

        with patch("app.infrastructure.notifications.dispatcher.datetime") as mock_datetime:
            from datetime import time
            # 模拟当前时间为 23:00（免打扰时段内）
            mock_now = MagicMock()
            mock_now.time.return_value = time(23, 0)
            from datetime import datetime as real_datetime
            mock_datetime.now.return_value = mock_now
            mock_datetime.side_effect = real_datetime

            dispatcher = NotificationDispatcher(mock_db)
            filtered = await dispatcher._filter_by_preference_and_quiet_hours(
                sample_event, ["wechat", "sms", "in_app"]
            )

            # 免打扰时段只保留 in_app
            assert filtered == ["in_app"]
