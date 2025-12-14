from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import logging

from app.api.v1 import api_router
from app.core.config import settings
from app.middleware.response import UnifiedResponseMiddleware
from app.db.session import AsyncSessionLocal
from app.tasks.blacklist_task import auto_release_blacklist

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
    # 启动后台任务
    task = asyncio.create_task(blacklist_auto_release_task())
    _background_tasks.append(task)
    logger.info("后台定时任务已启动")
    
    yield
    
    # 停止后台任务
    for task in _background_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("后台定时任务已停止")

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
    
    # 统一响应格式中间件（必须在 CORS 之前添加）
    app.add_middleware(UnifiedResponseMiddleware)
    
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 路由
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    @app.get("/health")
    async def health_check():
        return {"status": "ok"}
    
    return app

app = create_app()

