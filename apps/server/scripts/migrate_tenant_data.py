"""迁移现有数据到多租户架构

此脚本用于将现有数据迁移到多租户架构：
1. 创建默认订阅计划（如果不存在）
2. 创建默认租户
3. 将现有门店关联到默认租户
4. 将现有管理员关联到默认租户

运行方式:
    python scripts/migrate_tenant_data.py

注意：此脚本应该在运行数据库迁移后执行。
"""
import asyncio
import sys
import os
from datetime import datetime, timedelta

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, func
from app.db.session import AsyncSessionLocal
from app.models.tenant import Tenant, SubscriptionPlan
from app.models.store import Store
from app.models.admin import Admin, Role


async def get_or_create_default_plan(db) -> SubscriptionPlan:
    """获取或创建默认订阅计划"""
    result = await db.execute(
        select(SubscriptionPlan).where(SubscriptionPlan.plan_code == "basic")
    )
    plan = result.scalar_one_or_none()

    if plan:
        print(f"  使用现有订阅计划: {plan.name}")
        return plan

    # 创建默认计划
    plan = SubscriptionPlan(
        plan_code="basic",
        name="基础版",
        description="默认订阅计划（迁移创建）",
        price_monthly=0,
        price_yearly=0,
        max_stores=10,
        max_admins=50,
        max_doctors=200,
        max_appointments_per_month=10000,
        max_storage_mb=5120,
        status=1,
        is_default=True,
        sort_order=1,
    )
    db.add(plan)
    await db.flush()
    print(f"  创建订阅计划: {plan.name}")
    return plan


async def get_or_create_default_tenant(db, plan: SubscriptionPlan) -> Tenant:
    """获取或创建默认租户"""
    result = await db.execute(
        select(Tenant).where(Tenant.tenant_code == "default")
    )
    tenant = result.scalar_one_or_none()

    if tenant:
        print(f"  使用现有租户: {tenant.name}")
        return tenant

    # 创建默认租户
    now = datetime.utcnow()
    tenant = Tenant(
        tenant_code="default",
        name="默认租户",
        status=1,
        subscription_plan_id=plan.id,
        subscription_start_at=now,
        subscription_end_at=now + timedelta(days=36500),  # 100年后
        billing_cycle="yearly",
        contact_name="系统管理员",
        contact_email="admin@example.com",
    )
    db.add(tenant)
    await db.flush()
    print(f"  创建租户: {tenant.name} (ID: {tenant.id})")
    return tenant


async def migrate_stores(db, tenant_id: str):
    """迁移门店数据"""
    # 统计未关联租户的门店数量
    result = await db.execute(
        select(func.count(Store.id)).where(Store.tenant_id == None)
    )
    count = result.scalar() or 0

    if count == 0:
        print("  所有门店已关联租户，无需迁移")
        return

    # 更新门店的 tenant_id
    from sqlalchemy import update as sql_update
    await db.execute(
        sql_update(Store).where(Store.tenant_id == None).values(tenant_id=tenant_id)
    )
    print(f"  已将 {count} 个门店关联到默认租户")


async def migrate_admins(db, tenant_id: str):
    """迁移管理员数据"""
    # 获取超级管理员角色
    result = await db.execute(
        select(Role).where(Role.code == "SUPER_ADMIN")
    )
    super_role = result.scalar_one_or_none()

    # 统计未关联租户的非超级管理员数量
    query = select(func.count(Admin.id)).where(Admin.tenant_id == None)
    if super_role:
        query = query.where(Admin.role_id != super_role.id)

    result = await db.execute(query)
    count = result.scalar() or 0

    if count == 0:
        print("  所有管理员已关联租户或为平台管理员，无需迁移")
        return

    # 更新非超级管理员的 tenant_id
    from sqlalchemy import update as sql_update
    update_query = sql_update(Admin).where(Admin.tenant_id == None)
    if super_role:
        update_query = update_query.where(Admin.role_id != super_role.id)

    await db.execute(update_query.values(tenant_id=tenant_id))
    print(f"  已将 {count} 个管理员关联到默认租户")


async def create_tenant_admin_role(db):
    """创建租户管理员角色（如果不存在）"""
    result = await db.execute(
        select(Role).where(Role.code == "TENANT_ADMIN")
    )
    role = result.scalar_one_or_none()

    if role:
        print("  租户管理员角色已存在")
        return

    role = Role(
        name="租户管理员",
        code="TENANT_ADMIN",
        description="租户管理员，可以管理本租户的所有数据",
        status=1,
        permissions='["*"]',
    )
    db.add(role)
    print("  创建租户管理员角色")


async def create_platform_admin_role(db):
    """创建平台管理员角色（如果不存在）"""
    result = await db.execute(
        select(Role).where(Role.code == "PLATFORM_ADMIN")
    )
    role = result.scalar_one_or_none()

    if role:
        print("  平台管理员角色已存在")
        return

    role = Role(
        name="平台管理员",
        code="PLATFORM_ADMIN",
        description="平台管理员，可以管理所有租户",
        status=1,
        permissions='["*"]',
    )
    db.add(role)
    print("  创建平台管理员角色")


async def main():
    print("=" * 50)
    print("迁移数据到多租户架构")
    print("=" * 50)
    print()

    async with AsyncSessionLocal() as db:
        try:
            print("步骤 1: 创建默认订阅计划")
            plan = await get_or_create_default_plan(db)
            print()

            print("步骤 2: 创建默认租户")
            tenant = await get_or_create_default_tenant(db, plan)
            print()

            print("步骤 3: 迁移门店数据")
            await migrate_stores(db, tenant.id)
            print()

            print("步骤 4: 迁移管理员数据")
            await migrate_admins(db, tenant.id)
            print()

            print("步骤 5: 创建新角色")
            await create_tenant_admin_role(db)
            await create_platform_admin_role(db)
            print()

            await db.commit()
            print("迁移完成!")

        except Exception as e:
            await db.rollback()
            print(f"迁移失败: {e}")
            raise


if __name__ == "__main__":
    asyncio.run(main())
