"""邮件发送服务"""
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.service import SettingsService
from app.modules.email_templates.service import EmailTemplateService


class EmailService:
    """邮件发送服务"""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.settings_service = SettingsService(db)
        self.template_service = EmailTemplateService(db)

    async def get_email_config(self) -> dict:
        """获取邮件配置"""
        return await self.settings_service.get_email_config()

    async def send_email(
        self,
        to_email: str,
        subject: str,
        content: str,
        is_html: bool = True
    ) -> bool:
        """
        发送邮件

        Args:
            to_email: 收件人邮箱
            subject: 邮件主题
            content: 邮件内容
            is_html: 是否为HTML格式

        Returns:
            是否发送成功
        """
        config = await self.get_email_config()

        smtp_host = config.get('host', '')
        smtp_port = config.get('port', 587)
        smtp_user = config.get('username', '')
        smtp_password = config.get('password', '')
        smtp_ssl = config.get('use_tls', True)
        sender_name = config.get('from_name', '')
        sender_email = config.get('from_email', smtp_user)

        if not smtp_host or not smtp_user or not smtp_password:
            raise ValueError("邮件配置不完整，请先配置SMTP服务器信息")

        # 创建邮件
        msg = MIMEMultipart('alternative')
        msg['Subject'] = subject
        msg['From'] = formataddr((sender_name, sender_email))
        msg['To'] = to_email

        # 添加邮件内容
        content_type = 'html' if is_html else 'plain'
        part = MIMEText(content, content_type, 'utf-8')
        msg.attach(part)

        try:
            # 发送邮件
            if smtp_ssl:
                smtp = aiosmtplib.SMTP(
                    hostname=smtp_host,
                    port=smtp_port,
                    use_tls=True
                )
            else:
                smtp = aiosmtplib.SMTP(
                    hostname=smtp_host,
                    port=smtp_port,
                    start_tls=True
                )

            await smtp.connect()
            await smtp.login(smtp_user, smtp_password)
            await smtp.send_message(msg)
            await smtp.quit()

            return True
        except Exception as e:
            print(f"[Email] 发送邮件失败: {to_email} - {str(e)}")
            raise Exception(f"发送邮件失败: {str(e)}")

    async def send_by_template(
        self,
        template_code: str,
        to_email: str,
        variables: dict
    ) -> bool:
        """
        使用模板发送邮件

        Args:
            template_code: 模板编码
            to_email: 收件人邮箱
            variables: 模板变量

        Returns:
            是否发送成功
        """
        template = await self.template_service.get_by_code(template_code)
        if not template:
            raise ValueError(f"邮件模板 {template_code} 不存在")

        if template.status != 1:
            raise ValueError(f"邮件模板 {template_code} 已禁用")

        subject, content = self.template_service.render_template(template, variables)

        return await self.send_email(to_email, subject, content, is_html=True)

    async def send_verification_code_email(
        self,
        to_email: str,
        code: str,
        code_type: str = "login",
    ) -> bool:
        """
        发送邮箱验证码

        Args:
            to_email: 收件人邮箱
            code: 验证码
            code_type: 验证码类型（login/register/reset）

        Returns:
            是否发送成功
        """
        type_labels = {
            "login": "登录",
            "admin_login": "管理员登录",
            "register": "注册",
            "reset": "重置密码",
            "bind": "绑定",
            "admin_bind": "管理员邮箱绑定",
        }
        label = type_labels.get(code_type, "验证")

        subject = f"【预约挂号系统】{label}验证码"
        content = f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: 'Microsoft YaHei', Arial, sans-serif; background: #f5f5f5; padding: 20px;">
  <div style="max-width: 480px; margin: 0 auto; background: #fff; border-radius: 8px; padding: 30px; box-shadow: 0 2px 8px rgba(0,0,0,0.08);">
    <h2 style="color: #333; margin-bottom: 20px;">{label}验证码</h2>
    <p style="color: #666; font-size: 14px; line-height: 1.6;">
      您正在进行<span style="font-weight: bold; color: #1890ff;">{label}</span>操作，验证码如下：
    </p>
    <div style="background: #f0f7ff; border-radius: 6px; padding: 16px; text-align: center; margin: 20px 0;">
      <span style="font-size: 28px; font-weight: bold; color: #1890ff; letter-spacing: 6px;">{code}</span>
    </div>
    <p style="color: #999; font-size: 12px; line-height: 1.6;">
      验证码 5 分钟内有效，请勿泄露给他人。<br>
      如非本人操作，请忽略此邮件。
    </p>
    <hr style="border: none; border-top: 1px solid #eee; margin: 20px 0;">
    <p style="color: #ccc; font-size: 11px; text-align: center;">预约挂号系统</p>
  </div>
</body>
</html>"""

        return await self.send_email(to_email, subject, content, is_html=True)

    async def send_test_email(
        self,
        template_id: str,
        to_email: str,
        variables: Optional[dict] = None
    ) -> bool:
        """
        发送测试邮件

        Args:
            template_id: 模板ID
            to_email: 收件人邮箱
            variables: 模板变量（可选，使用示例数据）

        Returns:
            是否发送成功
        """
        template = await self.template_service.get_by_id(template_id)
        if not template:
            raise ValueError("邮件模板不存在")

        # 使用提供的变量或默认测试数据
        test_variables = variables or {
            'patient_name': '张三',
            'doctor_name': '李医生',
            'department_name': '内科',
            'appointment_date': '2024-01-15',
            'appointment_time': '上午 09:00-12:00',
            'appointment_no': 'APT20240115001',
            'hospital_name': '示例医院',
            'hospital_phone': '400-123-4567',
        }

        subject, content = self.template_service.render_template(template, test_variables)

        return await self.send_email(to_email, subject, content, is_html=True)
