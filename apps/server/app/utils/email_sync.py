"""同步邮件发送工具（供 Celery worker 使用）"""
import logging
import os

from jinja2.sandbox import SandboxedEnvironment
from jinja2 import TemplateSyntaxError
from sqlalchemy import select

from app.models.settings import SystemSetting as Settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# SMTP 密码加密/解密（Fernet 对称加密）
# ---------------------------------------------------------------------------

_fernet_instance = None


def _get_fernet():
    """获取 Fernet 加密实例

    优先从 app.core.config.Settings 读取 SMTP_ENCRYPTION_KEY，
    回退到环境变量（兼容 Celery worker 等无法访问 Settings 的场景）。

    Raises:
        RuntimeError: 密钥未配置时抛出，防止静默使用临时密钥导致数据丢失
    """
    global _fernet_instance
    if _fernet_instance is not None:
        return _fernet_instance
    from cryptography.fernet import Fernet

    # 优先从 Settings 读取（FastAPI 进程）
    key = ""
    try:
        from app.core.config import Settings
        settings = Settings()
        key = settings.SMTP_ENCRYPTION_KEY
    except Exception:
        pass

    # 回退到环境变量（Celery worker 等场景）
    if not key:
        key = os.environ.get("SMTP_ENCRYPTION_KEY", "")

    if not key:
        raise RuntimeError(
            "SMTP_ENCRYPTION_KEY 未配置。每次重启会生成新密钥，"
            "导致已加密的 SMTP 密码不可解密。"
            "请在 .env 中设置: SMTP_ENCRYPTION_KEY=<your-key>"
        )

    _fernet_instance = Fernet(key.encode() if isinstance(key, str) else key)
    return _fernet_instance


def encrypt_password(plaintext: str) -> str:
    """加密 SMTP 密码"""
    if not plaintext:
        return plaintext
    return _get_fernet().encrypt(plaintext.encode()).decode()


def decrypt_password(ciphertext: str) -> str:
    """解密 SMTP 密码，兼容明文（非 Fernet 格式则原样返回）

    Raises:
        RuntimeError: 密钥未配置
        ValueError: 密码解密失败（密钥不匹配或数据损坏）
    """
    if not ciphertext:
        return ciphertext
    # Fernet token 以 'gAAAAA' 开头，以此判断是否已加密
    if not ciphertext.startswith("gAAAAA"):
        return ciphertext
    try:
        return _get_fernet().decrypt(ciphertext.encode()).decode()
    except Exception as e:
        logger.error("SMTP 密码解密失败: %s", e)
        raise ValueError(
            "SMTP 密码解密失败，可能是 SMTP_ENCRYPTION_KEY 与加密时使用的密钥不匹配。"
            "请检查 .env 中的 SMTP_ENCRYPTION_KEY 是否正确。"
        ) from e

# 共享的沙箱环境，启用 autoescape 防止 XSS
_jinja_env = SandboxedEnvironment(autoescape=True)


def render_email_template(template_str: str, variables: dict) -> str:
    """使用 Jinja2 沙箱环境渲染邮件模板

    SandboxedEnvironment 阻止访问不安全属性，autoescape 自动转义 HTML。
    """
    try:
        tpl = _jinja_env.from_string(template_str)
        return tpl.render(**variables)
    except TemplateSyntaxError:
        # 模板语法非法，回退到简单替换（兼容旧模板）
        result = template_str
        for key, value in variables.items():
            result = result.replace("{{" + key + "}}", str(value))
        return result


def get_email_config(db) -> dict:
    """从数据库获取 SMTP 邮件配置（同步版本），密码自动解密"""
    try:
        result = db.execute(
            select(Settings).where(Settings.category == "email")
        )
        settings_list = result.scalars().all()
        config = {}
        for s in settings_list:
            config[s.key] = s.value
        # 解密密码
        if config.get("password"):
            config["password"] = decrypt_password(config["password"])
        return config
    except Exception as e:
        logger.error(f"获取邮件配置失败: {e}")
        return {}


def send_email_sync(config: dict, to_email: str, subject: str, content: str) -> bool:
    """同步发送邮件（Celery worker 环境）"""
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart
    from email.utils import formataddr

    smtp_host = config.get("host", "")
    smtp_port = int(config.get("port", 587))
    smtp_user = config.get("username", "")
    smtp_password = config.get("password", "")
    smtp_ssl = config.get("use_tls", "true") in (True, "true", "1", "yes")
    sender_name = config.get("from_name", "")
    sender_email = config.get("from_email", smtp_user)

    if not smtp_host or not smtp_user or not smtp_password:
        logger.warning("[EmailSync] SMTP 配置不完整，跳过发送")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = formataddr((sender_name, sender_email))
    msg["To"] = to_email
    msg.attach(MIMEText(content, "html", "utf-8"))

    try:
        if smtp_ssl:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=15)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=15)
            server.starttls()

        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"[EmailSync] 发送邮件失败: to={to_email}, error={e}")
        return False
