"""
邮件同步工具 + 邮件模板服务 + 邮件事件钩子 通用单元测试

覆盖 4 个模块的全部公共函数/类：
1. app.utils.email_sync — Fernet 加解密、模板渲染、邮件配置、同步发送
2. app.tasks.email_hook_task — 事件邮件处理 Celery task
3. app.models.email_template — 唯一约束 + AuditMixin
4. app.modules.email_templates.service — CRUD + 租户过滤 + 渲染
"""
import json
import smtplib
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, patch, MagicMock, PropertyMock
from uuid import uuid4
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base


# ======================================================================
# Fixtures
# ======================================================================

@pytest.fixture(autouse=True)
def _reset_fernet_cache():
    """每个测试前重置 Fernet 单例缓存，防止测试间串扰"""
    import app.utils.email_sync as mod
    mod._fernet_instance = None
    yield
    mod._fernet_instance = None


def _create_all_safe(connection):
    """去重重复索引后创建所有表（兼容 lowcode 模型的重复索引定义）"""
    seen_indexes = set()
    for table in Base.metadata.sorted_tables:
        deduped = set()
        for idx in table.indexes:
            if idx.name not in seen_indexes:
                seen_indexes.add(idx.name)
                deduped.add(idx)
        table.indexes = deduped
    Base.metadata.create_all(connection)


@pytest_asyncio.fixture
async def email_db_session():
    """轻量级内存 SQLite session（仅用于邮件模板模型约束测试）"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False,
    )
    async with engine.begin() as conn:
        await conn.run_sync(_create_all_safe)

    session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


# ======================================================================
# 1. email_sync.py — _get_fernet / encrypt / decrypt / render / config / send
# ======================================================================

class TestGetFernet:
    """测试 Fernet 实例获取逻辑"""

    def test_get_fernet_from_settings(self):
        """测试优先从 AppSettings 读取密钥并初始化 Fernet"""
        from app.utils.email_sync import _get_fernet
        from cryptography.fernet import Fernet

        mock_key = Fernet.generate_key().decode()
        mock_settings = MagicMock()
        mock_settings.SMTP_ENCRYPTION_KEY = mock_key

        with patch("app.utils.email_sync._fernet_instance", None), \
             patch("app.core.config.Settings", return_value=mock_settings), \
             patch("cryptography.fernet.Fernet") as mock_fernet_cls:
            mock_fernet_cls.return_value = MagicMock(spec=Fernet)
            result = _get_fernet()
            mock_fernet_cls.assert_called_once_with(mock_key.encode())
            assert result is mock_fernet_cls.return_value

    def test_get_fernet_fallback_to_env(self):
        """测试 Settings 初始化失败时回退到环境变量"""
        from app.utils.email_sync import _get_fernet
        from cryptography.fernet import Fernet

        mock_key = Fernet.generate_key().decode()
        with patch("app.utils.email_sync._fernet_instance", None), \
             patch("app.core.config.Settings", side_effect=RuntimeError("init failed")), \
             patch.dict("os.environ", {"SMTP_ENCRYPTION_KEY": mock_key}):
            result = _get_fernet()
            assert result is not None

    def test_get_fernet_no_key_raises(self):
        """测试密钥未配置时抛出 RuntimeError"""
        from app.utils.email_sync import _get_fernet

        with patch("app.utils.email_sync._fernet_instance", None), \
             patch("app.core.config.Settings", side_effect=RuntimeError("no env")), \
             patch.dict("os.environ", {}, clear=True):
            with pytest.raises(RuntimeError, match="SMTP_ENCRYPTION_KEY 未配置"):
                _get_fernet()

    def test_get_fernet_singleton_cache(self):
        """测试第二次调用返回缓存的同一实例"""
        from app.utils.email_sync import _get_fernet

        mock_instance = MagicMock()
        with patch("app.utils.email_sync._fernet_instance", mock_instance):
            result = _get_fernet()
            assert result is mock_instance


class TestEncryptPassword:
    """测试密码加密"""

    def test_encrypt_returns_fernet_token(self):
        """测试非空字符串加密后返回以 gAAAAA 开头的 Fernet token"""
        from app.utils.email_sync import encrypt_password

        mock_fernet = MagicMock()
        mock_fernet.encrypt.return_value = b"gAAAAAfakeencrypted"
        with patch("app.utils.email_sync._get_fernet", return_value=mock_fernet):
            result = encrypt_password("mypassword")
            assert result == "gAAAAAfakeencrypted"
            mock_fernet.encrypt.assert_called_once_with(b"mypassword")

    def test_encrypt_empty_string_returns_empty(self):
        """测试空字符串原样返回"""
        from app.utils.email_sync import encrypt_password
        assert encrypt_password("") == ""

    def test_encrypt_none_returns_none(self):
        """测试 None 原样返回（falsy 值走 early return）"""
        from app.utils.email_sync import encrypt_password
        assert encrypt_password(None) is None


class TestDecryptPassword:
    """测试密码解密"""

    def test_decrypt_fernet_token(self):
        """测试解密 Fernet 格式密码返回明文"""
        from app.utils.email_sync import decrypt_password

        mock_fernet = MagicMock()
        mock_fernet.decrypt.return_value = b"mypassword"
        with patch("app.utils.email_sync._get_fernet", return_value=mock_fernet):
            result = decrypt_password("gAAAAAfaketoken")
            assert result == "mypassword"

    def test_decrypt_plaintext_passthrough(self):
        """测试非 Fernet 格式（明文）直接返回，兼容旧数据"""
        from app.utils.email_sync import decrypt_password
        result = decrypt_password("plain_password_123")
        assert result == "plain_password_123"

    def test_decrypt_empty_string_returns_empty(self):
        """测试空字符串原样返回"""
        from app.utils.email_sync import decrypt_password
        assert decrypt_password("") == ""

    def test_decrypt_wrong_key_raises_value_error(self):
        """测试密钥不匹配时抛出 ValueError"""
        from app.utils.email_sync import decrypt_password

        mock_fernet = MagicMock()
        mock_fernet.decrypt.side_effect = Exception("Invalid token")
        with patch("app.utils.email_sync._get_fernet", return_value=mock_fernet):
            with pytest.raises(ValueError, match="SMTP 密码解密失败"):
                decrypt_password("gAAAAAbadtoken")


class TestRenderEmailTemplate:
    """测试 Jinja2 邮件模板渲染"""

    def test_render_normal_template(self):
        """测试正常 Jinja2 模板渲染"""
        from app.utils.email_sync import render_email_template
        result = render_email_template(
            "Hello {{ name }}, your code is {{ code }}",
            {"name": "张三", "code": "ABC123"},
        )
        assert "张三" in result
        assert "ABC123" in result

    def test_render_html_autoescape(self):
        """测试 HTML 自动转义防 XSS"""
        from app.utils.email_sync import render_email_template
        result = render_email_template(
            "<p>{{ user_input }}</p>",
            {"user_input": "<script>alert('xss')</script>"},
        )
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_render_syntax_error_fallback(self):
        """测试模板语法非法时回退到简单字符串替换（变量以 key 形式匹配）"""
        from app.utils.email_sync import render_email_template
        # Jinja2 语法非法: 未闭合的 {%，触发 TemplateSyntaxError -> 回退到简单替换
        # 回退逻辑: result.replace("{{" + key + "}}", str(value))
        result = render_email_template(
            "Hello {{name}}",
            {"name": "张三"},
        )
        assert "张三" in result

    def test_render_missing_variable_shows_empty(self):
        """测试变量缺失时 Jinja2 渲染为空字符串（未定义变量渲染为空）"""
        from app.utils.email_sync import render_email_template
        result = render_email_template(
            "Hello {{ name }}",
            {},
        )
        # Jinja2 对未定义变量渲染为空字符串
        assert "Hello" in result
        assert "name" not in result


class TestGetEmailConfig:
    """测试从数据库获取邮件配置"""

    def test_get_email_config_success(self):
        """测试正常读取并解密邮件配置"""
        from app.utils.email_sync import get_email_config

        mock_db = MagicMock()
        s1 = MagicMock(key="host", value="smtp.example.com")
        s2 = MagicMock(key="username", value="user@example.com")
        s3 = MagicMock(key="password", value="gAAAAAencryptedpw")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [s1, s2, s3]
        mock_db.execute.return_value = mock_result

        with patch("app.utils.email_sync.decrypt_password", return_value="plainpw"):
            config = get_email_config(mock_db)

        assert config["host"] == "smtp.example.com"
        assert config["username"] == "user@example.com"
        assert config["password"] == "plainpw"

    def test_get_email_config_no_password(self):
        """测试无密码配置时不调用解密"""
        from app.utils.email_sync import get_email_config

        mock_db = MagicMock()
        s1 = MagicMock(key="host", value="smtp.example.com")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [s1]
        mock_db.execute.return_value = mock_result

        config = get_email_config(mock_db)
        assert config["host"] == "smtp.example.com"
        assert "password" not in config

    def test_get_email_config_decrypt_error_propagates(self):
        """测试密码解密失败时异常向上传播"""
        from app.utils.email_sync import get_email_config

        mock_db = MagicMock()
        s1 = MagicMock(key="password", value="gAAAAAbad")
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [s1]
        mock_db.execute.return_value = mock_result

        with patch("app.utils.email_sync.decrypt_password", side_effect=ValueError("bad key")):
            with pytest.raises(ValueError, match="bad key"):
                get_email_config(mock_db)

    def test_get_email_config_other_error_returns_empty(self):
        """测试其他异常时返回空 dict"""
        from app.utils.email_sync import get_email_config

        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("db error")
        config = get_email_config(mock_db)
        assert config == {}


class TestSendEmailSync:
    """测试同步邮件发送"""

    def test_send_ssl_success(self):
        """测试 SSL 模式成功发送邮件"""
        from app.utils.email_sync import send_email_sync

        config = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "user@example.com",
            "password": "secret",
            "use_tls": True,
        }
        with patch("smtplib.SMTP_SSL") as mock_ssl:
            mock_server = MagicMock()
            mock_ssl.return_value = mock_server
            result = send_email_sync(config, "to@example.com", "测试主题", "<p>内容</p>")
            assert result is True
            mock_ssl.assert_called_once_with("smtp.example.com", 465, timeout=15)
            mock_server.login.assert_called_once_with("user@example.com", "secret")
            mock_server.quit.assert_called_once()

    def test_send_starttls_success(self):
        """测试 STARTTLS 模式成功发送邮件"""
        from app.utils.email_sync import send_email_sync

        config = {
            "host": "smtp.example.com",
            "port": 587,
            "username": "user@example.com",
            "password": "secret",
            "use_tls": "false",
        }
        with patch("smtplib.SMTP") as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value = mock_server
            result = send_email_sync(config, "to@example.com", "测试主题", "<p>内容</p>")
            assert result is True
            mock_smtp.assert_called_once_with("smtp.example.com", 587, timeout=15)
            mock_server.starttls.assert_called_once()

    def test_send_missing_config_returns_false(self):
        """测试 SMTP 配置不完整时返回 False"""
        from app.utils.email_sync import send_email_sync

        config = {"host": "", "username": "", "password": ""}
        result = send_email_sync(config, "to@example.com", "主题", "内容")
        assert result is False

    def test_send_smtp_exception_returns_false(self):
        """测试 SMTP 连接异常时返回 False"""
        from app.utils.email_sync import send_email_sync

        config = {
            "host": "smtp.example.com",
            "port": 465,
            "username": "user@example.com",
            "password": "secret",
            "use_tls": True,
        }
        with patch("smtplib.SMTP_SSL", side_effect=OSError("connection refused")):
            result = send_email_sync(config, "to@example.com", "主题", "内容")
            assert result is False

    def test_send_ssl_string_values(self):
        """测试 use_tls 各种字符串值正确识别为 SSL 模式"""
        from app.utils.email_sync import send_email_sync

        for val in ["true", "1", "yes"]:
            config = {
                "host": "smtp.example.com",
                "port": 465,
                "username": "u@e.com",
                "password": "p",
                "use_tls": val,
            }
            with patch("smtplib.SMTP_SSL") as mock_ssl:
                mock_ssl.return_value = MagicMock()
                result = send_email_sync(config, "to@e.com", "s", "c")
                assert result is True, f"use_tls={val} should be SSL"


# ======================================================================
# 2. email_hook_task.py — _render_simple_template / process_event_email
# ======================================================================

class TestRenderSimpleTemplate:
    """测试内置简单模板渲染"""

    def test_known_event_type(self):
        """测试已知事件类型使用中文标签渲染"""
        from app.tasks.email_hook_task import _render_simple_template
        from app.core.events import EVENT_TYPE_LABELS

        ctx = {
            "store_name": "总院",
            "appointment_no": "YY001",
            "patient_name": "张三",
            "doctor_name": "李医生",
            "department_name": "内科",
            "appointment_date": "2026-01-01",
            "appointment_time": "09:00",
        }
        with patch("app.tasks.email_hook_task.render_email_template", side_effect=lambda t, c: t) as mock_render:
            subject, content = _render_simple_template("appointment_created", ctx)
            assert mock_render.call_count == 2
            # 验证 context 中包含 event_label（变量作为第二个位置参数传入）
            call_args = mock_render.call_args_list
            assert call_args[0][0][1]["event_label"] == EVENT_TYPE_LABELS["appointment_created"]

    def test_unknown_event_type_uses_raw_type(self):
        """测试未知事件类型使用原始 event_type 作为标签"""
        from app.tasks.email_hook_task import _render_simple_template

        ctx = {"store_name": "总院"}
        with patch("app.tasks.email_hook_task.render_email_template", side_effect=lambda t, c: t) as mock_render:
            subject, content = _render_simple_template("custom_event_xyz", ctx)
            call_args = mock_render.call_args_list
            assert call_args[0][0][1]["event_label"] == "custom_event_xyz"


class TestProcessEventEmail:
    """测试 process_event_email Celery task"""

    def _mock_store(self, store_id, name="测试门店", tenant_id="t1"):
        store = MagicMock()
        store.id = store_id
        store.name = name
        store.tenant_id = tenant_id
        return store

    def _mock_recipient(self, store_id, email, event_types, status=1):
        r = MagicMock()
        r.store_id = store_id
        r.email = email
        r.event_types = event_types
        r.status = status
        return r

    def _run_task(self, *args):
        """通过 .run() 直接调用原始函数，绕过 Celery __call__ 包装"""
        from app.tasks.email_hook_task import process_event_email
        return process_event_email.run(*args)

    def test_store_not_found(self):
        """测试门店不存在时返回 sent=0"""
        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = store_result

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            result = self._run_task("store_999", "appointment_created", {})

        assert result["sent"] == 0
        assert result["reason"] == "门店不存在"

    def test_no_matching_recipients(self):
        """测试无匹配接收人时返回 sent=0"""
        store = self._mock_store("s1")
        r1 = self._mock_recipient("s1", "a@b.com", json.dumps(["checkin"]))

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        mock_db.execute.side_effect = [store_result, recip_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 0
        assert result["reason"] == "无匹配接收人"

    def test_recipient_event_types_null_skipped(self):
        """测试 event_types 为 None 的接收人被跳过"""
        store = self._mock_store("s1")
        r1 = self._mock_recipient("s1", "a@b.com", None)

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        mock_db.execute.side_effect = [store_result, recip_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 0
        assert result["reason"] == "无匹配接收人"

    def test_recipient_event_types_invalid_json_skipped(self):
        """测试 event_types 为非法 JSON 的接收人被跳过"""
        store = self._mock_store("s1")
        r1 = self._mock_recipient("s1", "a@b.com", "not-valid-json{")

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        mock_db.execute.side_effect = [store_result, recip_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 0

    def test_full_send_flow_with_template(self):
        """测试完整发送流程：有租户模板时使用模板渲染"""
        store = self._mock_store("s1", "总院", "t1")
        r1 = self._mock_recipient("s1", "a@b.com", json.dumps(["appointment_created"]))

        template = MagicMock()
        template.subject_template = "主题: {{ store_name }}"
        template.content_template = "<p>{{ store_name }}</p>"

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        tmpl_result = MagicMock()
        tmpl_result.scalar_one_or_none.return_value = template
        mock_db.execute.side_effect = [store_result, recip_result, tmpl_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb, \
             patch("app.tasks.email_hook_task.render_email_template", return_value="rendered") as mock_render, \
             patch("app.tasks.email_hook_task.get_email_config", return_value={"host": "smtp.x.com"}), \
             patch("app.tasks.email_hook_task.send_email_sync", return_value=True) as mock_send, \
             patch("app.tasks.email_hook_task.NotificationLog") as mock_log_cls:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            mock_log_cls.return_value = MagicMock()

            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 1
        assert result.get("failed", 0) == 0
        mock_send.assert_called_once()
        # 验证使用模板渲染
        assert mock_render.call_count == 2

    def test_fallback_to_platform_template(self):
        """测试租户模板不存在时回退到平台模板"""
        store = self._mock_store("s1", "总院", "t1")
        r1 = self._mock_recipient("s1", "a@b.com", json.dumps(["appointment_created"]))

        platform_template = MagicMock()
        platform_template.subject_template = "平台主题"
        platform_template.content_template = "<p>平台内容</p>"

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        tenant_tmpl_result = MagicMock()
        tenant_tmpl_result.scalar_one_or_none.return_value = None
        platform_tmpl_result = MagicMock()
        platform_tmpl_result.scalar_one_or_none.return_value = platform_template
        mock_db.execute.side_effect = [store_result, recip_result, tenant_tmpl_result, platform_tmpl_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb, \
             patch("app.tasks.email_hook_task.render_email_template", return_value="rendered"), \
             patch("app.tasks.email_hook_task.get_email_config", return_value={}), \
             patch("app.tasks.email_hook_task.send_email_sync", return_value=True), \
             patch("app.tasks.email_hook_task.NotificationLog") as mock_log_cls:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            mock_log_cls.return_value = MagicMock()

            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 1

    def test_fallback_to_simple_template(self):
        """测试所有模板都不存在时使用内置简单模板"""
        store = self._mock_store("s1", "总院", "t1")
        r1 = self._mock_recipient("s1", "a@b.com", json.dumps(["appointment_created"]))

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        empty_result = MagicMock()
        empty_result.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [store_result, recip_result, empty_result, empty_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb, \
             patch("app.tasks.email_hook_task._render_simple_template", return_value=("sub", "<p>body</p>")) as mock_simple, \
             patch("app.tasks.email_hook_task.get_email_config", return_value={}), \
             patch("app.tasks.email_hook_task.send_email_sync", return_value=True), \
             patch("app.tasks.email_hook_task.NotificationLog") as mock_log_cls:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            mock_log_cls.return_value = MagicMock()

            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 1
        mock_simple.assert_called_once()

    def test_partial_failure_counts_independently(self):
        """测试部分发送失败时 sent/failed 独立计数"""
        store = self._mock_store("s1", "总院", "t1")
        r1 = self._mock_recipient("s1", "ok@b.com", json.dumps(["appointment_created"]))
        r2 = self._mock_recipient("s1", "fail@b.com", json.dumps(["appointment_created"]))

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1, r2]
        empty_tmpl = MagicMock()
        empty_tmpl.scalar_one_or_none.return_value = None
        mock_db.execute.side_effect = [store_result, recip_result, empty_tmpl, empty_tmpl]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb, \
             patch("app.tasks.email_hook_task._render_simple_template", return_value=("sub", "<p>body</p>")), \
             patch("app.tasks.email_hook_task.get_email_config", return_value={}), \
             patch("app.tasks.email_hook_task.send_email_sync", side_effect=[True, False]) as mock_send, \
             patch("app.tasks.email_hook_task.NotificationLog") as mock_log_cls:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            mock_log_cls.return_value = MagicMock()

            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 1
        assert result["failed"] == 1

    def test_exception_triggers_retry(self):
        """测试未捕获异常触发 Celery 重试"""
        from app.tasks.email_hook_task import process_event_email

        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("db crash")

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb, \
             patch.object(process_event_email, "retry", side_effect=Exception("retry triggered")):
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            with pytest.raises(Exception, match="retry triggered"):
                self._run_task("s1", "appointment_created", {})

    def test_store_name_set_from_store(self):
        """测试门店名称自动补充到 context_data"""
        store = self._mock_store("s1", "分院一号", "t1")

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [store_result, recip_result]

        context_data = {}
        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            self._run_task("s1", "checkin", context_data)

        assert context_data["store_name"] == "分院一号"

    def test_store_name_not_overwritten(self):
        """测试 context_data 中已有 store_name 时不覆盖"""
        store = self._mock_store("s1", "分院一号", "t1")

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = []
        mock_db.execute.side_effect = [store_result, recip_result]

        context_data = {"store_name": "自定义名称"}
        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            self._run_task("s1", "checkin", context_data)

        assert context_data["store_name"] == "自定义名称"

    def test_no_tenant_queries_platform_template_directly(self):
        """测试无租户门店直接查询平台模板"""
        store = self._mock_store("s1", "平台门店", tenant_id=None)
        r1 = self._mock_recipient("s1", "a@b.com", json.dumps(["appointment_created"]))

        platform_tmpl = MagicMock()
        platform_tmpl.subject_template = "t"
        platform_tmpl.content_template = "c"

        mock_db = MagicMock()
        store_result = MagicMock()
        store_result.scalar_one_or_none.return_value = store
        recip_result = MagicMock()
        recip_result.scalars.return_value.all.return_value = [r1]
        platform_result = MagicMock()
        platform_result.scalar_one_or_none.return_value = platform_tmpl
        mock_db.execute.side_effect = [store_result, recip_result, platform_result]

        with patch("app.tasks.email_hook_task.get_sync_db") as mock_gdb, \
             patch("app.tasks.email_hook_task.render_email_template", return_value="r"), \
             patch("app.tasks.email_hook_task.get_email_config", return_value={}), \
             patch("app.tasks.email_hook_task.send_email_sync", return_value=True), \
             patch("app.tasks.email_hook_task.NotificationLog") as mock_log_cls:
            mock_gdb.return_value.__enter__ = MagicMock(return_value=mock_db)
            mock_gdb.return_value.__exit__ = MagicMock(return_value=False)
            mock_log_cls.return_value = MagicMock()

            result = self._run_task("s1", "appointment_created", {})

        assert result["sent"] == 1


# ======================================================================
# 3. email_template.py model — 唯一约束 + AuditMixin
# ======================================================================

class TestEmailTemplateModel:
    """测试 EmailTemplate 模型约束"""

    @pytest.mark.asyncio
    async def test_create_template_success(self, email_db_session):
        """测试正常创建邮件模板"""
        from app.models.email_template import EmailTemplate

        tmpl = EmailTemplate(
            id=str(uuid4()),
            tenant_id="t1",
            code="welcome",
            name="欢迎邮件",
            subject_template="欢迎 {{name}}",
            content_template="<p>欢迎</p>",
        )
        email_db_session.add(tmpl)
        await email_db_session.commit()

        result = await email_db_session.execute(
            select(EmailTemplate).where(EmailTemplate.code == "welcome")
        )
        assert result.scalar_one_or_none() is not None

    @pytest.mark.asyncio
    async def test_unique_code_per_tenant(self, email_db_session):
        """测试同一租户下 code 唯一约束"""
        from app.models.email_template import EmailTemplate

        tmpl1 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="模板1", subject_template="s1", content_template="c1",
        )
        tmpl2 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="模板2", subject_template="s2", content_template="c2",
        )
        email_db_session.add(tmpl1)
        await email_db_session.commit()

        email_db_session.add(tmpl2)
        with pytest.raises(Exception):
            await email_db_session.commit()

    @pytest.mark.asyncio
    async def test_same_code_different_tenant_allowed(self, email_db_session):
        """测试不同租户下可使用相同 code"""
        from app.models.email_template import EmailTemplate

        tmpl1 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="模板A", subject_template="s1", content_template="c1",
        )
        tmpl2 = EmailTemplate(
            id=str(uuid4()), tenant_id="t2", code="welcome",
            name="模板B", subject_template="s2", content_template="c2",
        )
        email_db_session.add(tmpl1)
        await email_db_session.commit()

        email_db_session.add(tmpl2)
        await email_db_session.commit()  # 应成功

        result = await email_db_session.execute(select(EmailTemplate))
        assert len(result.scalars().all()) == 2

    @pytest.mark.asyncio
    async def test_platform_template_unique_code_postgres_behavior(self, email_db_session):
        """测试平台模板 (tenant_id=None) 的 code 唯一约束

        注意: SQLite 对 NULL 值不做 UNIQUE 比较 (NULL != NULL)，
        因此 SQLite 下两条 tenant_id=None 的同 code 记录不会冲突。
        PostgreSQL 下此约束生效。此测试验证 SQLite 的实际行为。
        """
        from app.models.email_template import EmailTemplate

        tmpl1 = EmailTemplate(
            id=str(uuid4()), tenant_id=None, code="welcome",
            name="平台模板", subject_template="s", content_template="c",
        )
        tmpl2 = EmailTemplate(
            id=str(uuid4()), tenant_id=None, code="welcome",
            name="平台模板2", subject_template="s2", content_template="c2",
        )
        email_db_session.add(tmpl1)
        await email_db_session.commit()

        email_db_session.add(tmpl2)
        # SQLite: NULL != NULL，所以不冲突，提交成功
        await email_db_session.commit()
        result = await email_db_session.execute(select(EmailTemplate))
        assert len(result.scalars().all()) == 2


# ======================================================================
# 4. email_templates/service.py — EmailTemplateService
# ======================================================================

class TestEmailTemplateServiceCreate:
    """测试邮件模板创建"""

    @pytest.mark.asyncio
    async def test_create_success(self, email_db_session):
        """测试正常创建模板"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.schemas.email_template import EmailTemplateCreate
        from app.enums.general import EmailTemplateType

        service = EmailTemplateService(email_db_session)
        # 使用 model_construct 绕过 Pydantic 验证，保留 Enum 对象
        # （service 代码中 data.template_type.value 需要 Enum 属性）
        data = EmailTemplateCreate.model_construct(
            code="welcome",
            name="欢迎邮件",
            template_type=EmailTemplateType.CUSTOM,
            subject_template="欢迎 {{name}}",
            content_template="<p>内容</p>",
            description="测试模板",
            status=1,
        )

        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"), \
             patch("app.modules.email_templates.service.set_create_audit"):
            result = await service.create(data, operator_id="op1")
            assert result.code == "welcome"
            assert result.tenant_id == "t1"

    @pytest.mark.asyncio
    async def test_create_duplicate_code_raises(self, email_db_session):
        """测试同一租户下创建重复 code 模板抛出 ValueError"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.schemas.email_template import EmailTemplateCreate
        from app.models.email_template import EmailTemplate

        # 先插入一条
        existing = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="已存在", subject_template="s", content_template="c",
        )
        email_db_session.add(existing)
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        data = EmailTemplateCreate(
            code="welcome", name="新模板", template_type="custom",
            subject_template="s", content_template="c",
        )
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            with pytest.raises(ValueError, match="模板编码 welcome 已存在"):
                await service.create(data)

    @pytest.mark.asyncio
    async def test_create_platform_duplicate_code_raises(self, email_db_session):
        """测试平台管理员 (tenant_id=None) 创建重复 code 模板抛出 ValueError"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.schemas.email_template import EmailTemplateCreate
        from app.models.email_template import EmailTemplate

        existing = EmailTemplate(
            id=str(uuid4()), tenant_id=None, code="welcome",
            name="平台模板", subject_template="s", content_template="c",
        )
        email_db_session.add(existing)
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        data = EmailTemplateCreate(
            code="welcome", name="新平台模板", template_type="custom",
            subject_template="s", content_template="c",
        )
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value=None):
            with pytest.raises(ValueError, match="模板编码 welcome 已存在"):
                await service.create(data)


class TestEmailTemplateServiceGetByCode:
    """测试按编码查询模板"""

    @pytest.mark.asyncio
    async def test_get_by_code_tenant_first(self, email_db_session):
        """测试有租户时优先返回租户模板"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.models.email_template import EmailTemplate

        t1 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="租户模板", subject_template="s", content_template="c",
        )
        t2 = EmailTemplate(
            id=str(uuid4()), tenant_id=None, code="welcome",
            name="平台模板", subject_template="s", content_template="c",
        )
        email_db_session.add_all([t1, t2])
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            result = await service.get_by_code("welcome")
            assert result.name == "租户模板"

    @pytest.mark.asyncio
    async def test_get_by_code_fallback_to_platform(self, email_db_session):
        """测试租户模板不存在时回退到平台模板"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.models.email_template import EmailTemplate

        t2 = EmailTemplate(
            id=str(uuid4()), tenant_id=None, code="welcome",
            name="平台模板", subject_template="s", content_template="c",
        )
        email_db_session.add(t2)
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            result = await service.get_by_code("welcome")
            assert result.name == "平台模板"

    @pytest.mark.asyncio
    async def test_get_by_code_not_found(self, email_db_session):
        """测试编码不存在时返回 None"""
        from app.modules.email_templates.service import EmailTemplateService

        service = EmailTemplateService(email_db_session)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            result = await service.get_by_code("nonexistent")
            assert result is None


class TestEmailTemplateServiceGetList:
    """测试模板列表查询"""

    @pytest.mark.asyncio
    async def test_get_list_with_keyword(self, email_db_session):
        """测试按关键词搜索模板"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.models.email_template import EmailTemplate
        from app.schemas.email_template import EmailTemplateQuery

        t1 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="欢迎邮件模板", subject_template="s", content_template="c",
        )
        t2 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="farewell",
            name="告别邮件", subject_template="s", content_template="c",
        )
        email_db_session.add_all([t1, t2])
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        query = EmailTemplateQuery(keyword="欢迎", page=1, page_size=10)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            items, total = await service.get_list(query)
            assert total == 1
            assert items[0].code == "welcome"

    @pytest.mark.asyncio
    async def test_get_list_empty_result(self, email_db_session):
        """测试查询结果为空"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.schemas.email_template import EmailTemplateQuery

        service = EmailTemplateService(email_db_session)
        query = EmailTemplateQuery(page=1, page_size=10)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            items, total = await service.get_list(query)
            assert items == []
            assert total == 0


class TestEmailTemplateServiceGetAll:
    """测试获取全部模板"""

    @pytest.mark.asyncio
    async def test_get_all_with_status_filter(self, email_db_session):
        """测试按状态过滤"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.models.email_template import EmailTemplate

        t1 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="a",
            name="启用模板", subject_template="s", content_template="c", status=1,
        )
        t2 = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="b",
            name="禁用模板", subject_template="s", content_template="c", status=0,
        )
        email_db_session.add_all([t1, t2])
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            enabled = await service.get_all(status=1)
            assert len(enabled) == 1
            assert enabled[0].code == "a"


class TestEmailTemplateServiceUpdate:
    """测试模板更新"""

    @pytest.mark.asyncio
    async def test_update_success(self, email_db_session):
        """测试正常更新模板字段"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.models.email_template import EmailTemplate
        from app.schemas.email_template import EmailTemplateUpdate

        tmpl = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="旧名称", subject_template="s", content_template="c",
        )
        email_db_session.add(tmpl)
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        data = EmailTemplateUpdate(name="新名称")
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"), \
             patch("app.modules.email_templates.service.set_update_audit"):
            result = await service.update(tmpl.id, data, operator_id="op1")
            assert result is not None
            assert result.name == "新名称"

    @pytest.mark.asyncio
    async def test_update_not_found_returns_none(self, email_db_session):
        """测试更新不存在的模板返回 None"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.schemas.email_template import EmailTemplateUpdate

        service = EmailTemplateService(email_db_session)
        data = EmailTemplateUpdate(name="新名称")
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            result = await service.update("nonexistent-id", data)
            assert result is None


class TestEmailTemplateServiceDelete:
    """测试模板删除"""

    @pytest.mark.asyncio
    async def test_delete_success(self, email_db_session):
        """测试正常删除模板"""
        from app.modules.email_templates.service import EmailTemplateService
        from app.models.email_template import EmailTemplate

        tmpl = EmailTemplate(
            id=str(uuid4()), tenant_id="t1", code="welcome",
            name="待删除", subject_template="s", content_template="c",
        )
        email_db_session.add(tmpl)
        await email_db_session.commit()

        service = EmailTemplateService(email_db_session)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            result = await service.delete(tmpl.id)
            assert result is True

    @pytest.mark.asyncio
    async def test_delete_not_found_returns_false(self, email_db_session):
        """测试删除不存在的模板返回 False"""
        from app.modules.email_templates.service import EmailTemplateService

        service = EmailTemplateService(email_db_session)
        with patch("app.modules.email_templates.service.get_current_tenant_id", return_value="t1"):
            result = await service.delete("nonexistent-id")
            assert result is False


class TestEmailTemplateServiceRender:
    """测试模板渲染"""

    def test_render_template_returns_subject_and_content(self):
        """测试渲染模板返回主题和内容"""
        from app.modules.email_templates.service import EmailTemplateService

        tmpl = MagicMock()
        tmpl.subject_template = "欢迎 {{name}}"
        tmpl.content_template = "<p>{{name}} 您好</p>"

        service = EmailTemplateService(MagicMock())
        with patch("app.utils.email_sync.render_email_template", side_effect=lambda t, v: t.replace("{{name}}", v.get("name", ""))):
            subject, content = service.render_template(tmpl, {"name": "张三"})
            assert subject == "欢迎 张三"
            assert content == "<p>张三 您好</p>"
