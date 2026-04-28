"""单元测试：消息模板服务（Jinja2 渲染）"""

import pytest
from unittest.mock import MagicMock
from jinja2 import TemplateSyntaxError

from app.modules.messages.service_templates import MessageTemplateService
from app.models.message import MessageTemplate


class TestMessageTemplateService:
    """测试 MessageTemplateService 的模板渲染功能"""

    def test_simple_variable_rendering(self):
        """测试简单变量替换 {{ var }} 格式"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-1",
            code="test_simple",
            name="简单变量测试",
            message_type="test",
            title_template="你好，{{ name }}",
            content_template="预约时间：{{ date }} {{ time }}",
        )

        title, content = service.render_template(template, {"name": "张三", "date": "2024-01-15", "time": "09:00"})

        assert title == "你好，张三"
        assert content == "预约时间：2024-01-15 09:00"

    def test_conditional_logic(self):
        """测试条件逻辑 {% if %}"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-2",
            code="test_conditional",
            name="条件逻辑测试",
            message_type="test",
            title_template="预约通知",
            content_template="{% if openid %}点击查看详情{% else %}请先登录{% endif %}",
        )

        title, content = service.render_template(template, {"openid": "wx123"})
        assert title == "预约通知"
        assert "点击查看详情" in content

        title, content = service.render_template(template, {})
        assert "请先登录" in content

    def test_loop_rendering(self):
        """测试循环 {% for %}"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-3",
            code="test_loop",
            name="循环测试",
            message_type="test",
            title_template="医生列表",
            content_template="{% for doctor in doctors %}{{ doctor }}{% if not loop.last %}、{% endif %}{% endfor %}",
        )

        title, content = service.render_template(template, {"doctors": ["张医生", "李医生", "王医生"]})
        assert title == "医生列表"
        assert content == "张医生、李医生、王医生"

    def test_default_value_filter(self):
        """测试默认值过滤器 | default()"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-4",
            code="test_default",
            name="默认值测试",
            message_type="test",
            title_template="预约{{ department | default('全科') }}",
            content_template="医生：{{ doctor_name | default('医生') }}",
        )

        title, content = service.render_template(template, {})
        assert title == "预约全科"
        assert content == "医生：医生"

        title, content = service.render_template(template, {"department": "内科", "doctor_name": "李医生"})
        assert title == "预约内科"
        assert content == "医生：李医生"

    def test_backward_compatibility_old_format(self):
        """测试向后兼容：旧格式 {variable} 仍然工作"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-5",
            code="test_old_format",
            name="旧格式兼容测试",
            message_type="test",
            title_template="预约成功提醒",
            content_template="您已成功预约{doctor_name}医生，就诊时间：{date} {time_slot}",
        )

        title, content = service.render_template(
            template, {"doctor_name": "王医生", "date": "2024-01-15", "time_slot": "09:00-12:00"}
        )
        assert title == "预约成功提醒"
        assert content == "您已成功预约王医生医生，就诊时间：2024-01-15 09:00-12:00"

    def test_sandbox_security_restricted(self):
        """测试沙箱安全性：禁止执行危险操作"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-6",
            code="test_sandbox",
            name="沙箱安全测试",
            message_type="test",
            title_template="测试",
            content_template="{{ ''.__class__.__mro__[1].__subclasses__()[104] }}",
        )

        title, content = service.render_template(template, {})
        # 沙箱会抛出 SecurityError，被异常处理捕获，返回原始模板字符串
        # 重要的是没有执行危险代码
        assert "{{" in content or content == ""
        assert "__" not in content or "{{" in content  # 如果包含 __，说明是原始模板未渲染

    def test_mixed_jinja2_and_old_format(self):
        """测试混合格式：Jinja2 {{ var }} 和旧格式 {var} 都支持"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-7",
            code="test_mixed",
            name="混合格式测试",
            message_type="test",
            title_template="{% if urgent %}紧急{% endif %}{{ title }}",
            content_template="{{ content }} {extra}",
        )

        title, content = service.render_template(
            template, {"urgent": True, "title": "通知", "content": "主要内容", "extra": "备注"}
        )
        assert "紧急" in title
        assert "通知" in title
        assert "主要内容" in content
        # Jinja2 不处理单花括号，但我们的后处理会处理
        assert "备注" in content

    def test_missing_variable_handling(self):
        """测试缺失变量的处理（StrictUndefined 不会报错，返回空）"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-8",
            code="test_missing",
            name="缺失变量测试",
            message_type="test",
            title_template="{{ title }}",
            content_template="内容：{{ content }}",
        )

        title, content = service.render_template(template, {"title": "测试"})
        assert title == "测试"
        assert "内容：" in content

    def test_complex_template(self):
        """测试复杂模板：条件 + 循环 + 默认值"""
        db = MagicMock()
        service = MessageTemplateService(db)

        template = MessageTemplate(
            id="test-9",
            code="test_complex",
            name="复杂模板测试",
            message_type="test",
            title_template="预约成功 - {{ patient_name | default('患者') }}",
            content_template="""您已成功预约 {{ doctor_name | default('医生') }}。
就诊时间：{{ appointment_date }} {{ appointment_time }}
{% if department %}科室：{{ department }}{% endif %}
{% if notes %}备注：{{ notes }}{% endif %}""",
        )

        title, content = service.render_template(
            template,
            {
                "patient_name": "张三",
                "doctor_name": "李医生",
                "appointment_date": "2024-01-15",
                "appointment_time": "09:00",
                "department": "内科",
                "notes": "请提前10分钟到院",
            },
        )

        assert "张三" in title
        assert "李医生" in content
        assert "2024-01-15" in content
        assert "内科" in content
        assert "请提前10分钟到院" in content
