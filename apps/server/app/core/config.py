from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path
import os


def _get_env_file() -> str | None:
    """检查 .env 文件是否可访问，如果不可访问则返回 None"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        try:
            # 尝试读取文件来检查权限
            with open(env_path, 'r') as f:
                f.read(1)
            return str(env_path)
        except (PermissionError, OSError):
            # 文件存在但无法访问（macOS provenance 属性等）
            print(f"Warning: .env file exists but cannot be accessed: {env_path}")
            return None
    return None


class Settings(BaseSettings):
    PROJECT_NAME: str = "医院挂号系统"
    API_V1_STR: str = "/api/v1"
    
    # 环境
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # 数据库（异步，FastAPI 使用）
    DATABASE_URL: str = "postgresql+asyncpg://hospital:hospital123@localhost:5432/hospital_booking"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_TIMEOUT: int = 30
    DB_POOL_RECYCLE: int = 1800  # 30分钟回收连接
    
    # 数据库（同步，Celery 任务使用）
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """将异步数据库 URL 转换为同步 URL"""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Celery 配置
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL
    
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL
    
    # 微信配置（可选，也可从数据库读取）
    WECHAT_APP_ID: Optional[str] = None
    WECHAT_APP_SECRET: Optional[str] = None
    
    # 预约提醒配置
    APPOINTMENT_REMINDER_HOURS: int = 24  # 提前多少小时发送提醒
    
    # 排班自动生成配置
    SCHEDULE_AUTO_GENERATE_DAYS: int = 14  # 自动生成未来多少天的排班
    
    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # RSA 密钥（用于密码加密传输）
    # 生产环境请配置实际的密钥，开发环境会自动生成
    RSA_PRIVATE_KEY: Optional[str] = None
    RSA_PUBLIC_KEY: Optional[str] = None
    
    # CORS
    # 同时支持 localhost 和 127.0.0.1，因为浏览器将它们视为不同的域
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:8002", "http://localhost:8003", "http://localhost:8005",
        "http://127.0.0.1:8002", "http://127.0.0.1:8003", "http://127.0.0.1:8005"
    ]
    
    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    RATE_LIMIT_PER_SECOND: int = 10
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "logs"
    LOG_JSON_FORMAT: bool = False
    
    # 短信配置
    SMS_PROVIDER: str = "mock"  # mock, aliyun, tencent
    ALIYUN_ACCESS_KEY_ID: Optional[str] = None
    ALIYUN_ACCESS_KEY_SECRET: Optional[str] = None
    SMS_SIGN_NAME: Optional[str] = None
    SMS_TEMPLATE_CODE: Optional[str] = None
    
    # 存储配置
    STORAGE_TYPE: str = "minio"  # minio / cos
    
    # MinIO 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "hospital"
    MINIO_SECURE: bool = False  # 是否使用HTTPS
    MINIO_PUBLIC_URL: Optional[str] = None  # 公网访问URL（可选，如CDN域名）
    
    # 腾讯云 COS 配置（预留）
    COS_SECRET_ID: Optional[str] = None
    COS_SECRET_KEY: Optional[str] = None
    COS_REGION: str = "ap-guangzhou"
    COS_BUCKET: Optional[str] = None
    COS_CDN_DOMAIN: Optional[str] = None  # CDN加速域名（可选）
    
    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding='utf-8',
        case_sensitive=True,
    )


settings = Settings()
