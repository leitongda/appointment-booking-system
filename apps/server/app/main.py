from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
import asyncio
import logging
from pathlib import Path

from app.api.v1 import api_router
from app.core.config import settings
from app.core.logging import setup_logging
from app.core.redis import close_redis
from app.middleware.response import UnifiedResponseMiddleware
from app.middleware.exception import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_log import RequestLogMiddleware
from app.middleware.operation_log import OperationLogMiddleware
from app.db.session import AsyncSessionLocal
from app.tasks.blacklist_task import auto_release_blacklist

# 初始化日志系统
setup_logging(
    log_level=settings.LOG_LEVEL,
    log_dir=settings.LOG_DIR,
    app_name="hospital",
    json_format=settings.LOG_JSON_FORMAT,
    console_output=True,
    file_output=True
)

logger = logging.getLogger(__name__)

# 后台任务控制
_background_tasks = []


async def blacklist_auto_release_task():
    """黑名单自动解禁定时任务（每小时执行一次）"""
    while True:
        try:
            await asyncio.sleep(3600)  # 每小时执行一次
            async with AsyncSessionLocal() as db:
                released = await auto_release_blacklist(db)
                if released:
                    logger.info(f"自动解禁黑名单用户 {len(released)} 人")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"黑名单自动解禁任务出错: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("="*50)
    logger.info(f"🚀 {settings.PROJECT_NAME} 启动中...")
    logger.info(f"   环境: {settings.ENVIRONMENT}")
    logger.info(f"   调试模式: {settings.DEBUG}")
    logger.info("="*50)
    
    # 启动后台任务
    task = asyncio.create_task(blacklist_auto_release_task())
    _background_tasks.append(task)
    logger.info("后台定时任务已启动")
    
    yield
    
    # 停止后台任务
    logger.info("正在关闭后台任务...")
    for task in _background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # 关闭 Redis 连接
    await close_redis()
    logger.info("Redis 连接已关闭")
    
    logger.info(f"👋 {settings.PROJECT_NAME} 已停止")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="医院挂号系统 API",
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # ==================== 注册中间件 ====================
    # 注意：中间件的执行顺序是后注册的先执行（洋葱模型）
    # 所以 CORS 放在最后注册，确保它最先处理请求（尤其是 OPTIONS 预检）
    
    # 1. 统一响应格式中间件（最内层）
    app.add_middleware(UnifiedResponseMiddleware)
    
    # 2. 操作日志中间件（记录管理员的写操作到数据库）
    app.add_middleware(OperationLogMiddleware)
    
    # 3. 请求日志中间件
    app.add_middleware(RequestLogMiddleware)
    
    # 4. 限流中间件
    app.add_middleware(
        RateLimitMiddleware,
        requests_per_minute=settings.RATE_LIMIT_PER_MINUTE,
        requests_per_second=settings.RATE_LIMIT_PER_SECOND,
        enabled=settings.RATE_LIMIT_ENABLED
    )
    
    # 5. CORS 中间件（最外层，最先处理请求，确保 OPTIONS 预检能正确响应）
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # ==================== 注册异常处理器 ====================
    register_exception_handlers(app)
    
    # ==================== 注册路由 ====================
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # ==================== 静态文件服务（本地存储模式） ====================
    if settings.STORAGE_TYPE.lower() == "local":
        upload_dir = Path(settings.LOCAL_UPLOAD_DIR)
        upload_dir.mkdir(parents=True, exist_ok=True)
        app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")
        logger.info(f"静态文件服务已挂载: /uploads -> {upload_dir}")
    
    # ==================== 健康检查 ====================
    @app.get("/health")
    async def health_check():
        """健康检查"""
        return {"status": "ok"}
    
    @app.get("/health/detailed")
    async def detailed_health_check():
        """详细健康检查"""
        from app.core.redis import get_redis
        from sqlalchemy import text
        from app.db.session import async_session_maker
        
        checks = {
            "status": "ok",
            "database": "ok",
            "redis": "ok",
            "environment": settings.ENVIRONMENT,
        }
        
        # 检查数据库
        try:
            async with async_session_maker() as db:
                await db.execute(text("SELECT 1"))
        except Exception as e:
            checks["database"] = f"error: {str(e)}"
            checks["status"] = "degraded"
        
        # 检查 Redis
        try:
            redis = await get_redis()
            await redis.ping()
        except Exception as e:
            checks["redis"] = f"error: {str(e)}"
            checks["status"] = "degraded"
        
        return checks
    
    return app


app = create_app()
