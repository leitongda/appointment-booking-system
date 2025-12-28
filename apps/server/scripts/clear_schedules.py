"""
清空排班相关数据的脚本
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

from app.core.config import settings


async def clear_schedules():
    """清空排班相关数据"""
    print(f"连接数据库...")
    engine = create_async_engine(settings.DATABASE_URL)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        try:
            # 1. 先清空依赖于 schedules 的表
            print("清空预约记录 (appointments)...")
            await session.execute(text("DELETE FROM appointments"))
            
            # 2. 清空排班生成日志
            print("清空排班生成日志 (schedule_generation_logs)...")
            await session.execute(text("DELETE FROM schedule_generation_logs"))
            
            # 3. 清空停诊记录
            print("清空停诊记录 (schedule_suspensions)...")
            await session.execute(text("DELETE FROM schedule_suspensions"))
            
            # 4. 清空排班数据
            print("清空排班数据 (schedules)...")
            await session.execute(text("DELETE FROM schedules"))
            
            # 5. 清空排班规则模板
            print("清空排班规则模板 (schedule_templates)...")
            await session.execute(text("DELETE FROM schedule_templates"))
            
            await session.commit()
            print("\n✅ 所有排班相关数据已清空！")
            
        except Exception as e:
            await session.rollback()
            print(f"\n❌ 清空数据失败: {e}")
            raise
        finally:
            await engine.dispose()


if __name__ == "__main__":
    print("=" * 50)
    print("⚠️  警告：此操作将清空所有排班相关数据！")
    print("   包括：预约记录、排班、排班规则、停诊记录等")
    print("=" * 50)
    
    confirm = input("\n确认要清空吗？输入 'yes' 继续: ")
    if confirm.lower() == 'yes':
        asyncio.run(clear_schedules())
    else:
        print("操作已取消")

