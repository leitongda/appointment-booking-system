"""重置并初始化三级角色体系

三级角色：
1. SUPER_ADMIN - 超级管理员：所有权限，无门店限制
2. STORE_ADMIN - 门店管理员：可管理用户，仅限绑定门店
3. STORE_USER - 门店用户：自定义权限，仅限绑定门店
"""
import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select, delete
from app.db.session import AsyncSessionLocal
from app.models.admin import Role, Permission


# 三级角色定义
SYSTEM_ROLES = [
    {
        "code": "SUPER_ADMIN",
        "name": "超级管理员",
        "description": "系统超级管理员，拥有所有权限，可管理所有门店数据",
        "permissions": "*",  # 特殊标记，表示全部权限
    },
    {
        "code": "STORE_ADMIN",
        "name": "门店管理员",
        "description": "门店管理员，可管理绑定门店的数据和用户",
        "permissions": [
            # 仪表盘
            "dashboard", "dashboard:view",
            # 门店（只能查看和编辑自己的门店）
            "store", "store:list", "store:export", "store:update",
            # 科室管理
            "department", "department:list", "department:export", "department:create", "department:update", "department:delete",
            # 医生管理
            "doctor", "doctor:list", "doctor:detail", "doctor:export", "doctor:create", "doctor:update", "doctor:delete", "doctor:booking-setting",
            # 排班管理
            "schedule", "schedule:list", "schedule:export", "schedule:create", "schedule:update", "schedule:delete",
            "schedule:template", "schedule:custom", "schedule:rest-day", "schedule:suspension", "schedule:statistics",
            "schedule_template:list", "schedule_template:export",
            # 预约管理
            "appointment", "appointment:list", "appointment:detail", "appointment:export", "appointment:update", "appointment:cancel", "appointment:statistics", "appointment:refund", "appointment:manage",
            # 患者管理
            "patient", "patient:list", "patient:detail", "patient:export", "patient:update", "patient:create",
            # 停诊审核
            "leave-request", "leave-request:list", "leave-request:approve",
            # 用户反馈
            "feedback", "feedback:list", "feedback:export", "feedback:reply", "feedback:delete",
            # 消息管理
            "message", "message:list", "message:send", "message:delete",
            # 内容管理
            "content", "content:news", "content:news:create", "content:news:update", "content:news:delete",
            "content:notice", "content:notice:create", "content:notice:update", "content:notice:delete",
            "content:banner", "content:banner:create", "content:banner:update", "content:banner:delete",
            # 统计分析
            "statistics", "statistics:view",
            # 系统设置（只能管理用户，不能管理角色）
            "system", "system:user", "system:user:create", "system:user:update", "system:user:delete", "system:user:reset-password",
            "admin:list", "admin:export",
            "system:settings", "settings:edit", "settings:wechat", "settings:sms", "settings:email",
            "blacklist:list", "blacklist:create", "blacklist:delete", "system:consultation-fee",
            "system:log", "log:list", "log:export",
        ],
    },
    {
        "code": "STORE_USER",
        "name": "门店用户",
        "description": "门店普通用户，权限由管理员分配",
        "permissions": [
            # 基础权限：仪表盘
            "dashboard", "dashboard:view",
            # 基础权限：查看列表
            "department", "department:list",
            "doctor", "doctor:list", "doctor:detail",
            "schedule", "schedule:list",
            "appointment", "appointment:list", "appointment:detail",
            "patient", "patient:list", "patient:detail",
        ],
    },
    {
        "code": "OPERATOR",
        "name": "运营人员",
        "description": "运营人员，负责内容管理和数据查看",
        "role_type": "operator",
        "permissions": [
            # 内容管理
            "content:news", "content:notice", "content:banner",
            # 统计分析
            "statistics:read",
            # 排班查看
            "schedule:read",
            # 预约查看
            "appointment:read",
            # 医生查看
            "doctor:read",
            # 患者查看
            "patient:read",
        ],
    },
]


async def reset_roles(force: bool = False):
    """重置角色数据，重新初始化三级角色体系
    
    Args:
        force: 是否强制重置（会删除所有现有角色）
    """
    async with AsyncSessionLocal() as db:
        print("=" * 50)
        print("角色体系初始化")
        print("=" * 50)
        
        # 获取所有权限码
        result = await db.execute(select(Permission))
        all_permissions = result.scalars().all()
        all_perm_codes = [p.code for p in all_permissions]
        print(f"\n当前系统有 {len(all_perm_codes)} 条权限记录")
        
        if force:
            # 强制模式：删除所有非系统角色
            print("\n⚠️  强制模式：将清除所有现有角色...")
            
            # 查询现有角色
            result = await db.execute(select(Role))
            existing_roles = result.scalars().all()
            
            # 删除所有角色（系统角色会重新创建）
            for role in existing_roles:
                print(f"  删除角色: {role.code} - {role.name}")
                await db.delete(role)
            
            await db.commit()
            print("  已清除所有角色")
        
        # 创建/更新系统角色
        print("\n开始创建系统角色...")
        
        for role_data in SYSTEM_ROLES:
            code = role_data["code"]
            
            # 检查是否已存在
            result = await db.execute(select(Role).where(Role.code == code))
            existing = result.scalar_one_or_none()
            
            # 处理权限
            if role_data["permissions"] == "*":
                permissions = all_perm_codes
            else:
                permissions = role_data["permissions"]
            
            permissions_json = json.dumps(permissions, ensure_ascii=False)
            
            if existing:
                print(f"  ✓ 更新角色: {code} - {role_data['name']}")
                existing.name = role_data["name"]
                existing.description = role_data["description"]
                existing.permissions = permissions_json
                existing.status = 1
            else:
                print(f"  + 创建角色: {code} - {role_data['name']}")
                import uuid
                new_role = Role(
                    id=str(uuid.uuid4()),
                    code=code,
                    name=role_data["name"],
                    description=role_data["description"],
                    permissions=permissions_json,
                    status=1,
                )
                db.add(new_role)
            
            await db.commit()
        
        print("\n" + "=" * 50)
        print("角色初始化完成！")
        print("=" * 50)
        
        # 打印角色信息
        result = await db.execute(select(Role).order_by(Role.code))
        roles = result.scalars().all()
        
        print("\n当前系统角色：")
        for role in roles:
            perm_count = len(json.loads(role.permissions)) if role.permissions else 0
            print(f"  - {role.code}: {role.name} ({perm_count} 个权限)")


async def main():
    """主函数"""
    import argparse
    parser = argparse.ArgumentParser(description="初始化三级角色体系")
    parser.add_argument("--force", action="store_true", help="强制重置所有角色")
    args = parser.parse_args()
    
    await reset_roles(force=args.force)


if __name__ == "__main__":
    asyncio.run(main())
