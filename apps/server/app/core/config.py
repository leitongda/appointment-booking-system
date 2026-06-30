from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


def _get_env_file() -> str | None:
    """检查 .env 文件是否可访问，如果不可访问则返回 None"""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if env_path.exists():
        try:
            # 尝试读取文件来检查权限
            with open(env_path) as f:
                f.read(1)
            return str(env_path)
        except (PermissionError, OSError):
            # 文件存在但无法访问（macOS provenance 属性等）
            print(f"Warning: .env file exists but cannot be accessed: {env_path}")
            return None
    return None


class Settings(BaseSettings):
    PROJECT_NAME: str = "医院挂号系统"
    
    # API 路径配置（支持动态版本和前缀）
    API_PREFIX: str = "/api"    # API 基础前缀
    API_VERSION: str = "v1"     # API 版本号
    
    @property
    def API_V1_STR(self) -> str:
        """完整 API v1 路径（保持向后兼容）"""
        return f"{self.API_PREFIX}/{self.API_VERSION}"

    @property
    def API_V2_STR(self) -> str:
        """API v2 路径（预留，当前为空路由）"""
        return f"{self.API_PREFIX}/v2"

    # OpenAPI 版本
    OPENAPI_VERSION: str = "1.0.0"

    # 环境
    DEBUG: bool = False
    ENVIRONMENT: str = "development"  # development, staging, production
    
    # 数据库（异步，FastAPI 使用）
    # 必需配置，请在 .env 文件中设置
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10         # 保持的连接数（高并发排班场景需要更大连接池）
    DB_MAX_OVERFLOW: int = 20      # 最大溢出连接数（最大总连接数 = 10+20 = 30）
    DB_POOL_TIMEOUT: int = 30       # 获取连接超时
    DB_POOL_RECYCLE: int = 300      # 5分钟回收连接（避免服务器端超时关闭）
    
    # 数据库（同步，Celery 任务使用）
    @property
    def SYNC_DATABASE_URL(self) -> str:
        """将异步数据库 URL 转换为同步 URL"""
        return self.DATABASE_URL.replace("postgresql+asyncpg", "postgresql+psycopg2")
    
    # Redis
    # 必需配置，请在 .env 文件中设置
    REDIS_URL: str
    
    # Celery 配置
    @property
    def CELERY_BROKER_URL(self) -> str:
        return self.REDIS_URL
    
    @property
    def CELERY_RESULT_BACKEND(self) -> str:
        return self.REDIS_URL
    
    # 微信配置（可选，也可从数据库读取）
    WECHAT_APP_ID: str | None = None
    WECHAT_APP_SECRET: str | None = None
    # 微信回调 Token（用于验证回调签名，与微信后台配置一致）
    WECHAT_CALLBACK_TOKEN: str | None = None

    # 第三方集成默认凭证（钉钉/企业微信/飞书）
    # 注：租户级凭证存于 integrations 表，此处为全局默认值/自部署兜底。
    # 敏感 Secret 仅放环境变量，DB 以 env: 引用。
    # 钉钉
    DINGTALK_APP_KEY: str | None = None
    DINGTALK_APP_SECRET: str | None = None
    DINGTALK_AGENT_ID: str | None = None
    # 企业微信
    WECOM_CORP_ID: str | None = None
    WECOM_APP_SECRET: str | None = None
    WECOM_AGENT_ID: str | None = None
    # 飞书
    FEISHU_APP_ID: str | None = None
    FEISHU_APP_SECRET: str | None = None
    
    # 预约提醒配置
    APPOINTMENT_REMINDER_HOURS: int = 24  # 提前多少小时发送提醒
    
    # 排班自动生成配置
    SCHEDULE_AUTO_GENERATE_DAYS: int = 14  # 自动生成未来多少天的排班
    
    # JWT
    # 必需配置，请在 .env 文件中设置
    # 生成方法: openssl rand -hex 32
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # RSA 密钥（用于密码加密传输）
    # 生产环境请配置实际的密钥，开发环境会自动生成
    RSA_PRIVATE_KEY: str | None = None
    RSA_PUBLIC_KEY: str | None = None

    # SMTP 密码加密密钥（Fernet 对称加密）
    # 必需配置：未设置时每次重启会生成新密钥，导致已加密密码不可解密
    # 生成方法: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
    SMTP_ENCRYPTION_KEY: str = ""
    
    # CORS
    # 同时支持 localhost 和 127.0.0.1，因为浏览器将它们视为不同的域
    BACKEND_CORS_ORIGINS: list[str] = [
        "http://localhost:8002", "http://localhost:8003", "http://localhost:8005", "http://localhost:9102",
        "http://127.0.0.1:8002", "http://127.0.0.1:8003", "http://127.0.0.1:8005", "http://127.0.0.1:9102"
    ]
    
    # 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 300  # 每分钟最大请求数（前端页面加载可能同时发起多个请求）
    RATE_LIMIT_PER_SECOND: int = 50   # 每秒最大请求数
    
    # 日志配置
    RUNTIME_DATA_DIR: str = "var/server"
    LOG_LEVEL: str = "INFO"
    LOG_DIR: str = "var/server/logs"
    LOG_JSON_FORMAT: bool = False

    # 分页配置
    DEFAULT_PAGE_SIZE: int = 10        # 默认每页数量
    MAX_PAGE_SIZE: int = 500           # 通用最大每页数量
    APPOINTMENTS_MAX_PAGE_SIZE: int = 500  # 预约列表专用最大每页数量（需管理员权限+日期范围才能超过100）

    # API 超时配置
    API_TIMEOUT: int = 30              # API 调用超时（秒）
    DB_QUERY_TIMEOUT: int = 10         # 数据库查询超时（秒）

    # 规则引擎性能监控配置
    RULE_PERFORMANCE_MONITORING_ENABLED: bool = True  # 是否启用性能监控
    RULE_SLOW_QUERY_THRESHOLD: int = 100              # 慢查询阈值（毫秒）
    RULE_METRICS_TTL: int = 86400 * 7                 # 指标保留时间（秒，默认7天）
    RULE_SLOW_QUERY_TTL: int = 86400 * 30             # 慢查询保留时间（秒，默认30天）

    # 短信配置
    SMS_PROVIDER: str = "mock"  # mock, aliyun, tencent
    ALIYUN_ACCESS_KEY_ID: str | None = None
    ALIYUN_ACCESS_KEY_SECRET: str | None = None
    SMS_SIGN_NAME: str | None = None
    SMS_TEMPLATE_CODE: str | None = None
    # 腾讯云短信配置
    TENCENT_SECRET_ID: str | None = None
    TENCENT_SECRET_KEY: str | None = None
    TENCENT_SMS_APP_ID: str | None = None
    TENCENT_SMS_SIGN_NAME: str | None = None
    TENCENT_SMS_REGION: str = "ap-guangzhou"

    # KMS 密钥管理配置
    KMS_PROVIDER: str = "local"  # local / aliyun / tencent
    KMS_KEY_ID: str | None = None  # KMS 密钥 ID（阿里云/腾讯云）
    ENCRYPTION_KEY: str | None = None  # 本地加密密钥（base64 编码的 32 字节，仅 local 模式）
    ENCRYPTION_KEY_PREVIOUS: str | None = None  # 旧密钥（密钥轮换期间用于解密历史数据）

    # 存储配置
    STORAGE_TYPE: str = "local"  # local / minio / cos
    
    # 本地存储配置
    LOCAL_UPLOAD_DIR: str = "var/server/uploads"  # 上传文件目录
    LOCAL_PUBLIC_URL: str | None = None  # 公网访问URL（可选，如CDN域名）
    
    # MinIO 配置
    MINIO_ENDPOINT: str = "localhost:9000"
    # 敏感配置，请在 .env 文件中设置
    MINIO_ACCESS_KEY: str = ""
    MINIO_SECRET_KEY: str = ""
    MINIO_BUCKET: str = "hospital"
    MINIO_SECURE: bool = False  # 是否使用HTTPS
    MINIO_PUBLIC_URL: str | None = None  # 公网访问URL（可选，如CDN域名）
    
    # 腾讯云 COS 配置（预留）
    COS_SECRET_ID: str | None = None
    COS_SECRET_KEY: str | None = None
    COS_REGION: str = "ap-guangzhou"
    COS_BUCKET: str | None = None
    COS_CDN_DOMAIN: str | None = None  # CDN加速域名（可选）

    # Flower 监控配置
    FLOWER_PORT: int = 5555
    FLOWER_BASIC_AUTH: str | None = None  # 格式: username:password

    # 告警配置
    ALERT_WEBHOOK_URL: str | None = None  # 任务失败告警 Webhook URL

    # Sentry APM 配置
    SENTRY_DSN: str = ""  # Sentry DSN，为空则不启用
    SENTRY_TRACES_SAMPLE_RATE: float = 0.1  # 性能追踪采样率 (0.0 ~ 1.0)

    # 高德地图配置
    AMAP_KEY: str | None = None  # 高德地图 Web 服务 API Key
    AMAP_SERVICE_BASE_URL: str = "https://restapi.amap.com"  # 高德 API 基础地址

    # 安全 Header 配置
    SECURITY_HSTS_ENABLED: bool = False  # 生产环境设为 true，启用 HSTS

    # 双写过渡期开关（阶段 1：默认开启，用于验证数据一致性）
    ACCOUNT_DUAL_WRITE_ENABLED: bool = True  # 阶段 1 开启双写验证

    # 新用户默认密码（管理员代创建用户时使用）
    DEFAULT_USER_PASSWORD: str = "Hosp!t@l#2024$xQ"

    # 登录历史保留天数（超过此天数的记录将被定时清理）
    LOGIN_HISTORY_RETENTION_DAYS: int = 180

    # 考勤数据保留天数
    ATTENDANCE_RECORD_RETENTION_DAYS: int = 365   # 打卡记录保留天数
    ATTENDANCE_STAT_RETENTION_DAYS: int = 730     # 每日统计保留天数
    
    model_config = SettingsConfigDict(
        env_file=_get_env_file(),
        env_file_encoding='utf-8',
        case_sensitive=True,
    )


settings = Settings()
