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
from app.core.redis import close_redis, get_redis
from app.core.websocket import ws_manager
from app.middleware.response import UnifiedResponseMiddleware
from app.middleware.exception import register_exception_handlers
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.request_log import RequestLogMiddleware
from app.middleware.operation_log import OperationLogMiddleware
from app.db.session import AsyncSessionLocal, engine
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


async def warmup_connections():
    """预热数据库和 Redis 连接池
    
    在应用启动时建立连接，避免首次请求时的连接延迟
    """
    try:
        # 预热 PostgreSQL 连接池
        logger.info("正在预热数据库连接池...")
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        logger.info("✅ 数据库连接池预热完成")
    except Exception as e:
        logger.error(f"❌ 数据库连接池预热失败: {e}")
    
    try:
        # 预热 Redis 连接
        logger.info("正在预热 Redis 连接...")
        redis = await get_redis()
        await redis.ping()
        logger.info("✅ Redis 连接预热完成")
    except Exception as e:
        logger.error(f"❌ Redis 连接预热失败: {e}")


async def ensure_super_admin_exists():
    """确保系统中存在超级管理员
    
    系统启动时检查，如果没有超级管理员则记录警告日志。
    生产环境中应通过初始化脚本创建超级管理员。
    """
    from sqlalchemy import select, func
    from app.models.admin import Admin, Role
    
    try:
        async with AsyncSessionLocal() as session:
            # 检查是否存在 SUPER_ADMIN 角色
            role_result = await session.execute(
                select(Role).where(Role.code == "SUPER_ADMIN")
            )
            super_role = role_result.scalar_one_or_none()
            
            if not super_role:
                logger.warning("⚠️  系统中不存在 SUPER_ADMIN 角色，请运行初始化脚本: python scripts/init_roles.py")
                return
            
            # 检查是否有超级管理员账号
            admin_count = await session.scalar(
                select(func.count(Admin.id))
                .join(Role)
                .where(Role.code == "SUPER_ADMIN", Admin.status == 1)
            )
            
            if not admin_count or admin_count == 0:
                logger.warning("⚠️  系统中不存在有效的超级管理员账号，请运行初始化脚本: python scripts/init_data.py")
            else:
                logger.info(f"✅ 超级管理员检查通过（共 {admin_count} 个有效超管账号）")
    except Exception as e:
        logger.error(f"❌ 超级管理员检查失败: {e}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    logger.info("="*50)
    logger.info(f"🚀 {settings.PROJECT_NAME} 启动中...")
    logger.info(f"   环境: {settings.ENVIRONMENT}")
    logger.info(f"   调试模式: {settings.DEBUG}")
    logger.info("="*50)
    
    # 预热连接池（消除冷启动延迟）
    await warmup_connections()
    
    # 检查超级管理员是否存在
    await ensure_super_admin_exists()
    
    # 启动后台任务
    task = asyncio.create_task(blacklist_auto_release_task())
    _background_tasks.append(task)
    logger.info("后台定时任务已启动")
    
    # 启动 WebSocket 管理器
    await ws_manager.start()
    logger.info("WebSocket 管理器已启动")
    
    yield
    
    # 停止后台任务
    logger.info("正在关闭后台任务...")
    for task in _background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    
    # 停止 WebSocket 管理器
    await ws_manager.stop()
    logger.info("WebSocket 管理器已停止")
    
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
