from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import PlainTextResponse
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
    # OpenAPI Tag 分组描述
    openapi_tags = [
        # 认证与用户
        {
            "name": "认证",
            "description": "用户登录、注册、Token 刷新、微信授权等认证相关接口",
        },
        {
            "name": "用户",
            "description": "用户个人信息、密码修改、头像上传、就诊人管理",
        },
        {
            "name": "权限管理",
            "description": "管理员账号、角色、权限、操作日志等后台权限管理",
        },
        # 核心业务
        {
            "name": "预约",
            "description": "预约挂号、签到、叫号、取消、完成等预约全流程接口",
        },
        {
            "name": "排班",
            "description": "医生排班查询、批量创建、停诊、恢复等排班管理接口",
        },
        {
            "name": "排班模板",
            "description": "排班规则模板管理，支持按模板批量生成排班",
        },
        {
            "name": "自定义排班",
            "description": "不依赖模板的自定义排班管理",
        },
        {
            "name": "医生",
            "description": "医生信息查询、创建、更新、排序等管理接口",
        },
        {
            "name": "科室",
            "description": "科室信息查询、树形结构、医生绑定等管理接口",
        },
        {
            "name": "门店管理",
            "description": "多门店管理、门店配置、科室绑定、微信配置",
        },
        # 患者相关
        {
            "name": "就诊卡管理",
            "description": "患者就诊卡（家庭成员）的增删改查",
        },
        {
            "name": "患者管理",
            "description": "后台患者管理、黑名单、积分调整等",
        },
        {
            "name": "病历",
            "description": "病历记录的创建、查询、更新",
        },
        # 排班辅助
        {
            "name": "休息日设置",
            "description": "门店/医生休息日配置，休息日期间不可预约",
        },
        {
            "name": "停诊管理",
            "description": "临时停诊管理",
        },
        {
            "name": "停诊调班",
            "description": "医生停诊申请、调班申请的审核流程",
        },
        # 配置与设置
        {
            "name": "系统设置",
            "description": "预约规则、医院信息、微信/短信/邮件配置、时段配置等",
        },
        {
            "name": "诊费管理",
            "description": "诊费类型、全局模板、门店模板、医生诊费配置",
        },
        {
            "name": "医生预约设置",
            "description": "医生个性化预约限制配置",
        },
        {
            "name": "复诊规则配置",
            "description": "门店复诊判定规则配置（时间范围、判定范围）",
        },
        {
            "name": "规则管理",
            "description": "预约/签到/取消时间窗规则组管理",
        },
        {
            "name": "班次类型",
            "description": "班次类型定义（普通号、专家号等）",
        },
        # 内容与消息
        {
            "name": "内容管理",
            "description": "新闻公告、轮播图等内容管理",
        },
        {
            "name": "消息中心",
            "description": "站内消息发送、模板管理、已读状态",
        },
        {
            "name": "邮件模板",
            "description": "邮件通知模板管理",
        },
        {
            "name": "预约须知",
            "description": "预约须知内容配置",
        },
        {
            "name": "用户反馈",
            "description": "用户反馈、投诉建议的处理",
        },
        # 数据与统计
        {
            "name": "数据统计",
            "description": "预约统计、收入趋势、科室/医生排行等数据看板",
        },
        {
            "name": "用户行为分析",
            "description": "用户行为日志分析",
        },
        {
            "name": "审计日志",
            "description": "系统操作审计日志查询",
        },
        {
            "name": "数据导出",
            "description": "预约记录、统计数据导出",
        },
        {
            "name": "数据导入导出",
            "description": "批量数据导入导出",
        },
        # 其他
        {
            "name": "黑名单管理",
            "description": "患者黑名单管理，黑名单用户无法预约",
        },
        {
            "name": "用户收藏",
            "description": "用户收藏的医生",
        },
        {
            "name": "文件上传",
            "description": "图片上传、URL 转存",
        },
        {
            "name": "医生端",
            "description": "医生专属接口：今日预约、叫号队列、就诊操作",
        },
        {
            "name": "WebSocket",
            "description": "实时消息推送（叫号通知、签到通知等）",
        },
    ]

    app = FastAPI(
        title=settings.PROJECT_NAME,
        description="""
## 医院预约挂号系统 API

一套完整的医院预约挂号解决方案，支持多门店、多科室、多医生的排班预约管理。

### 主要功能

| 模块 | 功能 |
|------|------|
| **预约管理** | 在线预约、签到、叫号、取消、爽约处理 |
| **排班管理** | 模板排班、自定义排班、停诊、休息日 |
| **患者管理** | 就诊卡、病历、积分、黑名单 |
| **权限管理** | 多角色、细粒度权限、操作日志 |
| **数据统计** | 预约趋势、收入统计、科室/医生排行 |

### 认证方式

- **JWT Token 认证**: 大部分接口需要在 Header 中携带 `Authorization: Bearer <token>`
- **微信登录**: 支持微信小程序授权登录
- **手机号登录**: 支持短信验证码登录

### 响应格式

所有接口返回统一格式：
```json
{
  "code": 0,
  "message": "success",
  "data": { ... }
}
```

### 错误码说明

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 400 | 请求参数错误 |
| 401 | 未认证或 Token 过期 |
| 403 | 无权限 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
        """,
        version="1.0.0",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
        openapi_tags=openapi_tags,
        swagger_ui_parameters={"docExpansion": "none"},
        contact={
            "name": "技术支持",
        },
        license_info={
            "name": "私有协议",
        },
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
    
    # ==================== LLMs.txt 支持 ====================
    # llms.txt 是一个标准格式，帮助 LLM 理解 API 结构
    # 参考: https://llmstxt.org/
    
    @app.get("/llms.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_txt():
        """提供 llms.txt 文件 - API 概览版"""
        static_dir = Path(__file__).parent / "static"
        llms_txt_path = static_dir / "llms.txt"
        
        if llms_txt_path.exists():
            return llms_txt_path.read_text(encoding="utf-8")
        
        # 如果文件不存在，返回基础信息
        return f"""# {settings.PROJECT_NAME}

> 医院挂号系统 API

- API 版本: 1.0.0
- 基础路径: {settings.API_V1_STR}
- Swagger 文档: /docs
- ReDoc 文档: /redoc
- OpenAPI JSON: {settings.API_V1_STR}/openapi.json

请运行 `python scripts/generate_llms_txt.py` 生成完整的 llms.txt 文件。
"""
    
    @app.get("/llms-full.txt", response_class=PlainTextResponse, include_in_schema=False)
    async def get_llms_full_txt():
        """提供 llms-full.txt 文件 - 包含完整端点详情"""
        static_dir = Path(__file__).parent / "static"
        llms_full_path = static_dir / "llms-full.txt"
        
        if llms_full_path.exists():
            return llms_full_path.read_text(encoding="utf-8")
        
        # 如果文件不存在，返回提示
        return f"""# {settings.PROJECT_NAME}

> 医院挂号系统 API - 完整版

请运行 `python scripts/generate_llms_txt.py` 生成完整的 llms-full.txt 文件。

或者访问 OpenAPI 规范获取完整 API 定义:
- {settings.API_V1_STR}/openapi.json
"""
    
    return app


app = create_app()
