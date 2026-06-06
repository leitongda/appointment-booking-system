"""
邮件事件钩子任务单元测试

测试 process_event_email Celery task 的核心逻辑：
1. 门店不存在 -> 提前返回
2. 无匹配接收人 -> 提前返回
3. 正常发送流程（租户模板 / 平台模板 / 简单模板三级回退）
4. 接收人 event_types 为 null / 非法 JSON -> 跳过
5. 部分发送失败 -> sent/failed 独立计数
6. NotificationLog 创建异常 -> 不中断发送
7. 未捕获异常 -> 触发 Celery 重试
"""
import json
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch, PropertyMock
from uuid import uuid4

from app.models.store import Store
from app.models.store_email_recipient import StoreEmailRecipient
from app.models.email_template import EmailTemplate
from app.models.notification_log import NotificationLog


# ---------------------------------------------------------------------------
# 获取原始函数（绕过 Celery proxy 和 autoretry 包装）
# ---------------------------------------------------------------------------

def _get_raw_task():
    """获取 Celery task 的原始函数（self 已绑定，直接传 keyword 参数即可）"""
    from app.tasks.email_hook_task import process_event_email
    return process_event_email._orig_run


def _get_task_instance():
    """获取 Celery task 实例（用于 mock self.retry 等方法）"""
    from app.celery_app import celery_app
    return celery_app.tasks["app.tasks.email_hook_task.process_event_email"]


# ---------------------------------------------------------------------------
# Mock 辅助函数
# ---------------------------------------------------------------------------

def _make_store(store_id: str = None, tenant_id: str = "t1", name: str = "测试门店") -> MagicMock:
    """构造 mock Store 对象"""
    store = MagicMock(spec=Store)
    store.id = store_id or str(uuid4())
    store.tenant_id = tenant_id
    store.name = name
    return store


def _make_recipient(
    email: str = "test@example.com",
    event_types: str = None,
    status: int = 1,
    store_id: str = "s1",
) -> MagicMock:
    """构造 mock StoreEmailRecipient 对象"""
    r = MagicMock(spec=StoreEmailRecipient)
    r.id = str(uuid4())
    r.email = email
    r.event_types = event_types
    r.status = status
    r.store_id = store_id
    return r


def _make_template(
    template_id: str = None,
    tenant_id: str = None,
    template_type: str = "appointment_created",
    subject_template: str = "[{{ store_name }}] 测试主题",
    content_template: str = "<p>{{ event_label }}通知</p>",
) -> MagicMock:
    """构造 mock EmailTemplate 对象"""
    t = MagicMock(spec=EmailTemplate)
    t.id = template_id or str(uuid4())
    t.tenant_id = tenant_id
    t.template_type = template_type
    t.subject_template = subject_template
    t.content_template = content_template
    t.status = 1
    return t


def _make_db_with_queries(query_results: list):
    """构造 mock db，按顺序返回 query_results 中的值。

    每个 query_results 元素可以是:
    - MagicMock 对象 -> scalar_one_or_none 返回该对象, scalars().all() 返回 [该对象]
    - None -> scalar_one_or_none 返回 None, scalars().all() 返回 []
    - list -> scalar_one_or_none 返回第一个元素, scalars().all() 返回整个列表
    """
    call_index = [0]

    def execute_side_effect(stmt):
        idx = call_index[0]
        call_index[0] += 1
        if idx >= len(query_results):
            result = MagicMock()
            result.scalar_one_or_none.return_value = None
            result.scalars.return_value.all.return_value = []
            return result

        val = query_results[idx]
        mock_result = MagicMock()
        if val is None:
            mock_result.scalar_one_or_none.return_value = None
            mock_result.scalars.return_value.all.return_value = []
        elif isinstance(val, list):
            mock_result.scalar_one_or_none.return_value = val[0] if val else None
            mock_result.scalars.return_value.all.return_value = val
        else:
            mock_result.scalar_one_or_none.return_value = val
            mock_result.scalars.return_value.all.return_value = [val]
        return mock_result

    return MagicMock(execute=MagicMock(side_effect=execute_side_effect))


def _make_sync_db_context(db):
    """构造 get_sync_db 上下文管理器 mock"""
    ctx = MagicMock()
    ctx.__enter__ = MagicMock(return_value=db)
    ctx.__exit__ = MagicMock(return_value=False)
    return ctx


# ===========================================================================
# 测试类
# ===========================================================================

@pytest.mark.unit
class TestProcessEventEmail:
    """测试 process_event_email Celery 任务"""

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_store_not_found_returns_early(self, mock_send, mock_get_config, mock_get_db):
        """门店不存在时应提前返回，不执行后续逻辑"""
        raw = _get_raw_task()

        db = _make_db_with_queries([None])  # 门店查询 -> None
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(store_id="nonexistent", event_type="appointment_created", context_data={})

        assert result == {"sent": 0, "reason": "门店不存在"}
        mock_send.assert_not_called()
        mock_get_config.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_no_matching_recipients_returns_early(self, mock_send, mock_get_config, mock_get_db):
        """无匹配接收人时应提前返回"""
        raw = _get_raw_task()

        store = _make_store()
        # store -> recipients(空)
        db = _make_db_with_queries([store, []])
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={},
        )

        assert result == {"sent": 0, "reason": "无匹配接收人"}
        mock_send.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_recipient_event_types_none_skipped(self, mock_send, mock_get_config, mock_get_db):
        """接收人 event_types 为 None 时应跳过，不发送"""
        raw = _get_raw_task()

        store = _make_store()
        recipient = _make_recipient(event_types=None)

        # store -> recipients([None event_types recipient])
        db = _make_db_with_queries([store, [recipient]])
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={},
        )

        assert result == {"sent": 0, "reason": "无匹配接收人"}
        mock_send.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_recipient_invalid_json_event_types_skipped(self, mock_send, mock_get_config, mock_get_db):
        """接收人 event_types 为非法 JSON 时应跳过该接收人"""
        raw = _get_raw_task()

        store = _make_store()
        recipient_bad = _make_recipient(email="bad@example.com", event_types="not-valid-json")

        # store -> recipients([bad recipient])
        db = _make_db_with_queries([store, [recipient_bad]])
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={},
        )

        assert result == {"sent": 0, "reason": "无匹配接收人"}
        mock_send.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_successful_send_with_tenant_template(self, mock_send, mock_get_config, mock_get_db):
        """使用租户模板成功发送邮件"""
        raw = _get_raw_task()

        store = _make_store(tenant_id="t1")
        recipient = _make_recipient(email="admin@test.com", event_types='["appointment_created"]')
        tenant_template = _make_template(tenant_id="t1")

        # store -> recipients([recipient]) -> 租户模板(命中)
        db = _make_db_with_queries([store, [recipient], tenant_template])
        mock_get_db.return_value = _make_sync_db_context(db)

        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={"store_name": "测试门店"},
        )

        assert result == {"sent": 1, "failed": 0}
        mock_send.assert_called_once()
        assert db.add_all.called
        assert db.commit.called

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_successful_send_with_platform_template_fallback(self, mock_send, mock_get_config, mock_get_db):
        """租户模板不存在时，回退到平台模板发送"""
        raw = _get_raw_task()

        store = _make_store(tenant_id="t1")
        recipient = _make_recipient(email="admin@test.com", event_types='["checkin"]')
        platform_template = _make_template(tenant_id=None, template_type="checkin")

        # store -> recipients -> 租户模板(None) -> 平台模板(命中)
        db = _make_db_with_queries([store, [recipient], None, platform_template])
        mock_get_db.return_value = _make_sync_db_context(db)

        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        result = raw(
            store_id=store.id,
            event_type="checkin",
            context_data={},
        )

        assert result == {"sent": 1, "failed": 0}
        mock_send.assert_called_once()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    @patch("app.tasks.email_hook_task.render_email_template")
    def test_successful_send_with_simple_template_fallback(self, mock_render, mock_send, mock_get_config, mock_get_db):
        """无模板时回退到内置简单模板发送"""
        raw = _get_raw_task()

        store = _make_store(tenant_id="t1")
        recipient = _make_recipient(email="admin@test.com", event_types='["appointment_created"]')

        # store -> recipients -> 租户模板(None) -> 平台模板(None)
        db = _make_db_with_queries([store, [recipient], None, None])
        mock_get_db.return_value = _make_sync_db_context(db)

        # 简单模板渲染: subject + content
        mock_render.side_effect = [
            "[测试门店] 新预约通知",
            "<div>新预约通知</div>",
        ]

        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={},
        )

        assert result == {"sent": 1, "failed": 0}
        # 简单模板调用 render_email_template 2 次（subject + content）
        assert mock_render.call_count == 2

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_partial_failure_counts_independently(self, mock_send, mock_get_config, mock_get_db):
        """多个接收人中部分成功部分失败，sent/failed 独立计数"""
        raw = _get_raw_task()

        store = _make_store()
        r1 = _make_recipient(email="ok@test.com", event_types='["checkin"]')
        r2 = _make_recipient(email="fail@test.com", event_types='["checkin"]')
        r3 = _make_recipient(email="ok2@test.com", event_types='["checkin"]')

        template = _make_template(tenant_id=None, template_type="checkin")

        # store -> recipients([r1,r2,r3]) -> 租户模板(None) -> 平台模板(命中)
        db = _make_db_with_queries([store, [r1, r2, r3], None, template])
        mock_get_db.return_value = _make_sync_db_context(db)

        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        # 第 1 和第 3 个成功，第 2 个失败
        mock_send.side_effect = [True, False, True]

        result = raw(
            store_id=store.id,
            event_type="checkin",
            context_data={},
        )

        assert result == {"sent": 2, "failed": 1}
        assert mock_send.call_count == 3

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    @patch("app.tasks.email_hook_task.render_email_template")
    def test_send_failure_records_failed_log(self, mock_render, mock_send, mock_get_config, mock_get_db):
        """发送失败时应记录 status=failed 的 NotificationLog"""
        raw = _get_raw_task()

        store = _make_store()
        recipient = _make_recipient(email="admin@test.com", event_types='["checkin"]')
        template = _make_template(tenant_id=None, template_type="checkin")

        # store -> recipients -> 平台模板(命中)
        db = _make_db_with_queries([store, [recipient], None, template])
        mock_get_db.return_value = _make_sync_db_context(db)

        mock_render.side_effect = lambda tpl, ctx: "rendered"
        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = False  # 发送失败

        result = raw(
            store_id=store.id,
            event_type="checkin",
            context_data={},
        )

        assert result == {"sent": 0, "failed": 1}
        # 验证创建了 failed 日志
        assert db.add_all.called
        logs = db.add_all.call_args[0][0]
        assert len(logs) == 1
        assert logs[0].status == "failed"
        assert logs[0].error_message == "SMTP发送失败"

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    @patch("app.tasks.email_hook_task.render_email_template")
    @patch("app.tasks.email_hook_task.NotificationLog")
    def test_notification_log_creation_failure_does_not_interrupt(
        self, MockLog, mock_render, mock_send, mock_get_config, mock_get_db
    ):
        """NotificationLog 构造异常不应中断发送流程"""
        raw = _get_raw_task()

        store = _make_store()
        recipient = _make_recipient(email="admin@test.com", event_types='["checkin"]')
        template = _make_template(tenant_id=None, template_type="checkin")

        # store -> recipients -> 平台模板(命中)
        db = _make_db_with_queries([store, [recipient], None, template])
        mock_get_db.return_value = _make_sync_db_context(db)

        mock_render.side_effect = lambda tpl, ctx: "rendered"
        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        # NotificationLog 构造抛出异常
        MockLog.side_effect = RuntimeError("NotificationLog 构造失败")

        result = raw(
            store_id=store.id,
            event_type="checkin",
            context_data={},
        )

        # 即使日志创建失败，发送本身仍成功
        assert result["sent"] == 1
        assert result["failed"] == 0

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    @patch("app.tasks.email_hook_task.render_email_template")
    def test_context_data_store_name_auto_populated(self, mock_render, mock_send, mock_get_config, mock_get_db):
        """门店名称应自动补充到 context_data 中"""
        raw = _get_raw_task()

        store = _make_store(name="和平门诊")
        recipient = _make_recipient(email="admin@test.com", event_types='["checkin"]')
        template = _make_template(tenant_id=None, template_type="checkin")

        # store -> recipients -> 平台模板(命中)
        db = _make_db_with_queries([store, [recipient], None, template])
        mock_get_db.return_value = _make_sync_db_context(db)

        # 捕获传入 render_email_template 的变量
        render_calls = []

        def capture_render(tpl_str, variables):
            render_calls.append(dict(variables))
            return "rendered"

        mock_render.side_effect = capture_render
        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        ctx = {}  # 初始 context_data 中没有 store_name
        result = raw(
            store_id=store.id,
            event_type="checkin",
            context_data=ctx,
        )

        assert result["sent"] == 1
        # 验证 store_name 已自动补充
        assert ctx.get("store_name") == "和平门诊"
        # 验证模板渲染时也收到了 store_name
        assert render_calls[0]["store_name"] == "和平门诊"

    @patch("app.tasks.email_hook_task.get_sync_db")
    def test_uncaught_exception_triggers_retry(self, mock_get_db):
        """未捕获异常应触发 Celery self.retry 重试"""
        from celery.exceptions import Retry

        task_instance = _get_task_instance()

        db = MagicMock()
        mock_get_db.return_value = _make_sync_db_context(db)

        # 查询门店时抛出异常（模拟 DB 连接中断等）
        db.execute.side_effect = RuntimeError("数据库连接中断")

        # Mock self.retry 抛出 Celery Retry 异常（模拟重试机制）
        with patch.object(task_instance, "retry", side_effect=Retry("Task can be retried")):
            with pytest.raises(Retry):
                task_instance.run(
                    store_id="s1",
                    event_type="appointment_created",
                    context_data={},
                )

            task_instance.retry.assert_called_once()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_recipient_mismatched_event_type_not_sent(self, mock_send, mock_get_config, mock_get_db):
        """接收人订阅的事件类型不匹配时不应发送"""
        raw = _get_raw_task()

        store = _make_store()
        # 接收人订阅了 checkin，但触发事件是 appointment_created
        recipient = _make_recipient(email="admin@test.com", event_types='["checkin", "visit_completed"]')

        # store -> recipients([recipient])
        db = _make_db_with_queries([store, [recipient]])
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(
            store_id=store.id,
            event_type="appointment_created",  # 不匹配
            context_data={},
        )

        assert result == {"sent": 0, "reason": "无匹配接收人"}
        mock_send.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    @patch("app.tasks.email_hook_task.render_email_template")
    def test_unknown_event_type_uses_raw_label(self, mock_render, mock_send, mock_get_config, mock_get_db):
        """未知事件类型使用原始 event_type 作为标签"""
        raw = _get_raw_task()

        store = _make_store()
        recipient = _make_recipient(email="admin@test.com", event_types='["custom_event"]')

        # store -> recipients -> 租户模板(None) -> 平台模板(None) -> 走简单模板
        db = _make_db_with_queries([store, [recipient], None, None])
        mock_get_db.return_value = _make_sync_db_context(db)

        render_calls = []

        def capture_render(tpl_str, variables):
            render_calls.append(dict(variables))
            return "rendered"

        mock_render.side_effect = capture_render
        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        result = raw(
            store_id=store.id,
            event_type="custom_event",
            context_data={},
        )

        assert result["sent"] == 1
        # event_label 应为原始 event_type（不在 EVENT_TYPE_LABELS 中）
        assert render_calls[0]["event_label"] == "custom_event"

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_disabled_recipient_not_in_query_result(self, mock_send, mock_get_config, mock_get_db):
        """禁用的接收人(status=0)不应出现在查询结果中（WHERE status=1 过滤）"""
        raw = _get_raw_task()

        store = _make_store()

        # 查询已过滤 status=1，返回空列表
        db = _make_db_with_queries([store, []])
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={},
        )

        assert result == {"sent": 0, "reason": "无匹配接收人"}
        mock_send.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    def test_empty_event_types_array_no_match(self, mock_send, mock_get_config, mock_get_db):
        """接收人 event_types 为空 JSON 数组时，事件不匹配，应跳过"""
        raw = _get_raw_task()

        store = _make_store()
        # event_types 是合法 JSON 但为空数组
        recipient = _make_recipient(email="admin@test.com", event_types="[]")

        # store -> recipients([recipient])
        db = _make_db_with_queries([store, [recipient]])
        mock_get_db.return_value = _make_sync_db_context(db)

        result = raw(
            store_id=store.id,
            event_type="appointment_created",
            context_data={},
        )

        assert result == {"sent": 0, "reason": "无匹配接收人"}
        mock_send.assert_not_called()

    @patch("app.tasks.email_hook_task.get_sync_db")
    @patch("app.tasks.email_hook_task.get_email_config")
    @patch("app.tasks.email_hook_task.send_email_sync")
    @patch("app.tasks.email_hook_task.render_email_template")
    def test_db_commit_failure_logged_not_raised(self, mock_render, mock_send, mock_get_config, mock_get_db):
        """db.add_all/commit 异常应被记录但不抛出"""
        raw = _get_raw_task()

        store = _make_store()
        recipient = _make_recipient(email="admin@test.com", event_types='["checkin"]')
        template = _make_template(tenant_id=None, template_type="checkin")

        db = _make_db_with_queries([store, [recipient], None, template])
        mock_get_db.return_value = _make_sync_db_context(db)

        mock_render.side_effect = lambda tpl, ctx: "rendered"
        mock_get_config.return_value = {"host": "smtp.test.com", "username": "u", "password": "p"}
        mock_send.return_value = True

        # db.add_all 正常，但 commit 抛出异常
        db.commit.side_effect = RuntimeError("commit 失败")

        # 不应抛出异常，发送仍然计数
        result = raw(
            store_id=store.id,
            event_type="checkin",
            context_data={},
        )

        assert result["sent"] == 1
        assert result["failed"] == 0
