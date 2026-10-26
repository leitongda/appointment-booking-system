"""PostgreSQL 集成测试 fixtures

使用环境变量 TEST_DATABASE_URL 连接真实 PostgreSQL 实例。
运行: TEST_DATABASE_URL="postgresql+asyncpg://test:test@localhost:5433/test_db" pytest tests/integration/ -m integration -v
"""
import os
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker


TEST_PG_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://test:test@localhost:5433/test_db"
)


def pytest_configure(config):
    """注册自定义 marker"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires PostgreSQL)"
    )


@pytest_asyncio.fixture(scope="session")
def pg_engine():
    """创建 PostgreSQL 测试引擎"""
    engine = create_async_engine(
        TEST_PG_URL,
        echo=False,
        pool_size=5,
        max_overflow=10,
    )
    yield engine
    engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def pg_session(pg_engine):
    """创建 PostgreSQL 测试会话"""
    from app.db.base import Base

    # 创建所有表
    async with pg_engine.begin() as conn:
        # 知识库 knowledge_chunks.embedding 依赖 pgvector 扩展
        from sqlalchemy import text as _sa_text

        await conn.execute(_sa_text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        pg_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with session_factory() as session:
        yield session

    # 清理所有数据
    async with pg_engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())

    # 删除所有表
    async with pg_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
