"""
数据库会话管理
- 异步连接池：FastAPI 使用
- 同步连接池：Celery 任务使用
"""
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from contextlib import contextmanager

from app.core.config import settings


# ==================== 异步连接池（FastAPI 使用）====================
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.DB_POOL_SIZE,
    max_overflow=settings.DB_MAX_OVERFLOW,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
)

async_session_maker = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 兼容旧代码的别名
AsyncSessionLocal = async_session_maker


async def get_db():
    """FastAPI 依赖注入：获取异步数据库会话"""
    async with async_session_maker() as session:
        try:
            yield session
        finally:
            await session.close()


# ==================== 同步连接池（Celery 任务使用）====================
sync_engine = create_engine(
    settings.SYNC_DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_timeout=settings.DB_POOL_TIMEOUT,
    pool_recycle=settings.DB_POOL_RECYCLE,
    pool_pre_ping=True,
    echo=settings.DEBUG,
)

SessionLocal = sessionmaker(
    bind=sync_engine,
    class_=Session,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


@contextmanager
def get_sync_db():
    """上下文管理器：获取同步数据库会话（用于 Celery 任务）"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_sync_db_session() -> Session:
    """获取同步数据库会话（需要手动关闭）"""
    return SessionLocal()


async def get_async_db_context():
    """异步生成器：获取异步数据库会话（用于同步上下文中调用异步代码）"""
    async with async_session_maker() as session:
        yield session
