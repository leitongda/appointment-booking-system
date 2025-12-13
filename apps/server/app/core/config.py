from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    PROJECT_NAME: str = "医院挂号系统"
    API_V1_STR: str = "/api/v1"
    
    # 数据库
    DATABASE_URL: str = "postgresql+asyncpg://hospital:hospital123@localhost:5432/hospital_booking"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    
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
    BACKEND_CORS_ORIGINS: List[str] = ["http://localhost:8002", "http://localhost:8003", "http://localhost:8005"]
    
    class Config:
        env_file = ".env"
        case_sensitive = True

settings = Settings()

