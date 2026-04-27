"""常见服务和健康提醒默认种子数据"""
import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy import select
from app.models.common_service import CommonService, HealthReminder
from app.core.config import settings
from app.middleware.tenant_context import TenantContext


# 常见服务默认配置
COMMON_SERVICES_DEFAULT = [
    {
        "name": "预约挂号",
        "code": "appointment_booking",
        "icon": "calendar",
        "variant": "blue",
        "link_type": 1,
        "link_url": "/pages/appointment/index",
        "sort_order": 1,
        "description": "在线预约医生，选择合适的时间段",
    },
    {
        "name": "在线咨询",
        "code": "online_consult",
        "icon": "message",
        "variant": "green",
        "link_type": 1,
        "link_url": "/pages/consult/index",
        "sort_order": 2,
        "description": "与医生在线沟通，获得专业建议",
    },
    {
        "name": "体检服务",
        "code": "health_checkup",
        "icon": "heart",
        "variant": "pink",
        "link_type": 1,
        "link_url": "/pages/checkup/index",
        "sort_order": 3,
        "description": "全面体检套餐，关爱身体健康",
    },
    {
        "name": "报告查询",
        "code": "report_query",
        "icon": "file-text",
        "variant": "orange",
        "link_type": 1,
        "link_url": "/pages/report/index",
        "sort_order": 4,
        "description": "查看检查检验报告结果",
    },
    {
        "name": "我的医生",
        "code": "my_doctors",
        "icon": "user",
        "variant": "purple",
        "link_type": 1,
        "link_url": "/pages/doctor/my",
        "sort_order": 5,
        "description": "收藏和关注的医生列表",
    },
    {
        "name": "就医指南",
        "code": "medical_guide",
        "icon": "book",
        "variant": "cyan",
        "link_type": 1,
        "link_url": "/pages/guide/index",
        "sort_order": 6,
        "description": "医院就诊流程和注意事项",
    },
]


# 健康提醒默认配置
HEALTH_REMINDERS_DEFAULT = [
    {
        "reminder_type": "checkup",
        "name": "常规体检",
        "title": "年度体检提醒",
        "content": "定期体检可以及早发现健康问题，建议每年进行一次全面体检。",
        "tips": '["体检前一天晚上10点后避免进食", "体检前三天保持清淡饮食", "体检当天穿着宽松衣物"]',
        "recommended_interval": 365,
        "sort_order": 1,
    },
    {
        "reminder_type": "gynecological",
        "name": "妇科检查",
        "title": "女性健康检查",
        "content": "建议成年女性每年进行一次妇科检查，关注乳腺和宫颈健康。",
        "tips": '["检查时间应避开月经期", "检查前24小时避免性生活", "检查前不要进行阴道冲洗"]',
        "recommended_interval": 365,
        "sort_order": 2,
    },
    {
        "reminder_type": "dental",
        "name": "口腔检查",
        "title": "口腔健康检查",
        "content": "建议每半年进行一次口腔检查，预防龋齿和牙周疾病。",
        "tips": '["每天刷牙两次", "使用牙线清洁牙缝", "减少糖分摄入"]',
        "recommended_interval": 180,
        "sort_order": 3,
    },
    {
        "reminder_type": "blood_pressure",
        "name": "血压监测",
        "title": "定期血压检测",
        "content": "高血压被称为"沉默的杀手"，建议定期监测血压。",
        "tips": '["保持健康体重", "减少盐分摄入", "适量运动"]',
        "recommended_interval": 90,
        "sort_order": 4,
    },
    {
        "reminder_type": "vision",
        "name": "视力检查",
        "title": "眼健康检查",
        "content": "建议每年进行一次视力检查，关注眼部健康。",
        "tips": '["用眼一小时休息十分钟", "保持正确坐姿", "增加户外活动时间"]',
        "recommended_interval": 365,
        "sort_order": 5,
    },
]


async def seed_common_services_for_tenant(
    session: AsyncSession,
    tenant_id: str,
    store_id: str = None,
) -> None:
    """为指定租户创建常见服务种子数据

    Args:
        session: 数据库会话
        tenant_id: 租户ID
        store_id: 门店ID，None表示租户级全局服务
    """
    # 使用 upsert 逻辑：先检查是否存在，不存在则创建
    for service_data in COMMON_SERVICES_DEFAULT:
        existing = await session.execute(
            select(CommonService).where(
                CommonService.tenant_id == tenant_id,
                CommonService.code == service_data["code"],
                CommonService.store_id == store_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        service = CommonService(
            id=str(uuid4()),
            tenant_id=tenant_id,
            store_id=store_id,
            **service_data,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(service)


async def seed_health_reminders_for_tenant(
    session: AsyncSession,
    tenant_id: str,
    store_id: str = None,
) -> None:
    """为指定租户创建健康提醒种子数据

    Args:
        session: 数据库会话
        tenant_id: 租户ID
        store_id: 门店ID，None表示租户级全局提醒
    """
    for reminder_data in HEALTH_REMINDERS_DEFAULT:
        existing = await session.execute(
            select(HealthReminder).where(
                HealthReminder.tenant_id == tenant_id,
                HealthReminder.reminder_type == reminder_data["reminder_type"],
                HealthReminder.store_id == store_id,
            )
        )
        if existing.scalar_one_or_none():
            continue

        reminder = HealthReminder(
            id=str(uuid4()),
            tenant_id=tenant_id,
            store_id=store_id,
            **reminder_data,
            status=1,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        session.add(reminder)


async def seed_all_common_data(
    session: AsyncSession,
    tenant_id: str,
    store_id: str = None,
) -> None:
    """为指定租户创建所有常见服务和健康提醒数据

    Args:
        session: 数据库会话
        tenant_id: 租户ID
        store_id: 门店ID，None表示租户级全局数据
    """
    await seed_common_services_for_tenant(session, tenant_id, store_id)
    await seed_health_reminders_for_tenant(session, tenant_id, store_id)
    await session.commit()
    print(f"租户 {tenant_id} 的常见服务和健康提醒种子数据创建完成")


async def seed_from_tenant_table():
    """从租户表读取所有租户，为每个租户创建种子数据"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    from app.models.tenant import Tenant

    async with async_session_maker() as session:
        # 获取所有启用的租户
        result = await session.execute(
            select(Tenant).where(Tenant.status == 1)
        )
        tenants = result.scalars().all()

        if not tenants:
            print("没有找到启用的租户")
            return

        for tenant in tenants:
            async with TenantContext(tenant_id=tenant.id, tenant_code=tenant.tenant_code):
                await seed_all_common_data(session, tenant.id)
                print(f"已为租户 {tenant.name} ({tenant.tenant_code}) 创建种子数据")

    await engine.dispose()


async def main():
    """主函数：为所有租户创建种子数据"""
    print("开始创建常见服务和健康提醒种子数据...")
    await seed_from_tenant_table()
    print("种子数据创建完成!")


if __name__ == "__main__":
    asyncio.run(main())
