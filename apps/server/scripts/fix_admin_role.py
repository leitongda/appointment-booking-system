"""修复 admin 用户的角色关联"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, update
from app.db.session import AsyncSessionLocal
from app.models.admin import Admin, Role


async def fix_admin_role():
    """修复 admin 用户的角色"""
    async with AsyncSessionLocal() as db:
        print("=" * 50)
        print("修复 admin 用户角色")
        print("=" * 50)
        
        # 1. 查找 SUPER_ADMIN 角色
        result = await db.execute(select(Role).where(Role.code == "SUPER_ADMIN"))
        super_role = result.scalar_one_or_none()
        
        if not super_role:
            print("❌ 未找到 SUPER_ADMIN 角色，请先运行 init_roles.py")
            return
        
        print(f"✓ 找到 SUPER_ADMIN 角色: {super_role.id}")
        
        # 2. 查找 admin 用户
        result = await db.execute(select(Admin).where(Admin.username == "admin"))
        admin = result.scalar_one_or_none()
        
        if not admin:
            print("❌ 未找到 admin 用户")
            return
        
        print(f"✓ 找到 admin 用户: {admin.id}")
        print(f"  当前 role_id: {admin.role_id}")
        
        # 3. 更新 role_id
        if admin.role_id == super_role.id:
            print("✓ admin 用户已经是 SUPER_ADMIN 角色，无需修复")
        else:
            admin.role_id = super_role.id
            await db.commit()
            print(f"✓ 已将 admin 用户的角色更新为 SUPER_ADMIN")
        
        # 4. 验证
        await db.refresh(admin)
        result = await db.execute(
            select(Admin)
            .options(
                __import__('sqlalchemy.orm', fromlist=['selectinload']).selectinload(Admin.role)
            )
            .where(Admin.id == admin.id)
        )
        admin = result.scalar_one()
        
        print("\n" + "=" * 50)
        print("验证结果：")
        print(f"  用户名: {admin.username}")
        print(f"  role_id: {admin.role_id}")
        print(f"  角色名称: {admin.role.name if admin.role else 'None'}")
        print(f"  角色编码: {admin.role.code if admin.role else 'None'}")
        print("=" * 50)
        
        print("\n✅ 修复完成！请重新登录测试。")


if __name__ == "__main__":
    asyncio.run(fix_admin_role())

