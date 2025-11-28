"""初始化数据库表结构"""
import asyncio
import sys
sys.path.insert(0, '/Users/leijiadashao/leitond/appointment-booking-system/apps/server')

from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings as app_settings
from app.db.base import Base

# 导入所有模型以确保它们被注册
from app.models import *


async def init_db():
    """创建所有数据库表"""
    print(f"连接数据库: {app_settings.DATABASE_URL}")
    
    engine = create_async_engine(app_settings.DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        print("开始创建表...")
        await conn.run_sync(Base.metadata.create_all)
        print("表创建完成!")
    
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(init_db())
