"""初始化默认订阅计划

运行方式:
    python scripts/init_subscription_plans.py
"""
import asyncio
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from app.db.session import AsyncSessionLocal
from app.models.tenant import SubscriptionPlan


DEFAULT_PLANS = [
    {
        "plan_code": "basic",
        "name": "基础版",
        "description": "适合小型诊所和单体门店，包含基础的预约管理功能。",
        "price_monthly": 299,
        "price_yearly": 2990,
        "max_stores": 1,
        "max_admins": 3,
        "max_doctors": 10,
        "max_appointments_per_month": 500,
        "max_storage_mb": 512,
        "features": '{"basic_appointment": true, "basic_schedule": true, "basic_statistics": true}',
        "is_default": True,
        "sort_order": 1,
    },
    {
        "plan_code": "pro",
        "name": "专业版",
        "description": "适合中型诊所和连锁门店，包含完整的预约管理和数据分析功能。",
        "price_monthly": 699,
        "price_yearly": 6990,
        "max_stores": 5,
        "max_admins": 10,
        "max_doctors": 50,
        "max_appointments_per_month": 3000,
        "max_storage_mb": 2048,
        "features": '{"basic_appointment": true, "basic_schedule": true, "basic_statistics": true, "advanced_statistics": true, "wechat_integration": true, "sms_notification": true, "export_data": true}',
        "is_default": False,
        "sort_order": 2,
    },
    {
        "plan_code": "enterprise",
        "name": "企业版",
        "description": "适合大型医疗集团和医院，包含所有功能和无限制的配额。",
        "price_monthly": 1999,
        "price_yearly": 19990,
        "max_stores": 50,
        "max_admins": 100,
        "max_doctors": 500,
        "max_appointments_per_month": 50000,
        "max_storage_mb": 10240,
        "features": '{"basic_appointment": true, "basic_schedule": true, "basic_statistics": true, "advanced_statistics": true, "wechat_integration": true, "sms_notification": true, "export_data": true, "api_access": true, "custom_branding": true, "priority_support": true, "sso": true}',
        "is_default": False,
        "sort_order": 3,
    },
]


async def init_subscription_plans():
    """初始化默认订阅计划"""
    async with AsyncSessionLocal() as db:
        created_count = 0
        updated_count = 0

        for plan_data in DEFAULT_PLANS:
            # 检查计划是否已存在
            result = await db.execute(
                select(SubscriptionPlan).where(SubscriptionPlan.plan_code == plan_data["plan_code"])
            )
            existing = result.scalar_one_or_none()

            if existing:
                # 更新现有计划
                for key, value in plan_data.items():
                    setattr(existing, key, value)
                updated_count += 1
                print(f"  更新计划: {plan_data['name']} ({plan_data['plan_code']})")
            else:
                # 创建新计划
                plan = SubscriptionPlan(**plan_data)
                db.add(plan)
                created_count += 1
                print(f"  创建计划: {plan_data['name']} ({plan_data['plan_code']})")

        await db.commit()

        print()
        print(f"完成: 创建 {created_count} 个计划, 更新 {updated_count} 个计划")


async def main():
    print("=" * 50)
    print("初始化默认订阅计划")
    print("=" * 50)
    print()

    await init_subscription_plans()


if __name__ == "__main__":
    asyncio.run(main())
