"""初始化权限数据和内置角色"""
import asyncio
import sys
import os
import json

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.services.admin_service import PermissionService, RoleService

# 权限数据定义
# type: menu - 菜单权限, button - 按钮/操作权限
PERMISSIONS = [
    # ========== 仪表盘 ==========
    {"code": "dashboard", "name": "仪表盘", "type": "menu", "parent_code": None, "icon": "dashboard", "sort": 1},
    {"code": "dashboard:view", "name": "查看仪表盘", "type": "button", "parent_code": "dashboard", "sort": 1},
    
    # ========== 门店管理 ==========
    {"code": "store", "name": "门店管理", "type": "menu", "parent_code": None, "icon": "shop", "sort": 2},
    {"code": "store:list", "name": "查看门店列表", "type": "button", "parent_code": "store", "sort": 1},
    {"code": "store:create", "name": "新增门店", "type": "button", "parent_code": "store", "sort": 2},
    {"code": "store:update", "name": "编辑门店", "type": "button", "parent_code": "store", "sort": 3},
    {"code": "store:delete", "name": "删除门店", "type": "button", "parent_code": "store", "sort": 4},
    
    # ========== 科室管理 ==========
    {"code": "department", "name": "科室管理", "type": "menu", "parent_code": None, "icon": "apartment", "sort": 3},
    {"code": "department:list", "name": "查看科室列表", "type": "button", "parent_code": "department", "sort": 1},
    {"code": "department:create", "name": "新增科室", "type": "button", "parent_code": "department", "sort": 2},
    {"code": "department:update", "name": "编辑科室", "type": "button", "parent_code": "department", "sort": 3},
    {"code": "department:delete", "name": "删除科室", "type": "button", "parent_code": "department", "sort": 4},
    
    # ========== 医生管理 ==========
    {"code": "doctor", "name": "医生管理", "type": "menu", "parent_code": None, "icon": "user", "sort": 4},
    {"code": "doctor:list", "name": "查看医生列表", "type": "button", "parent_code": "doctor", "sort": 1},
    {"code": "doctor:detail", "name": "查看医生详情", "type": "button", "parent_code": "doctor", "sort": 2},
    {"code": "doctor:create", "name": "新增医生", "type": "button", "parent_code": "doctor", "sort": 3},
    {"code": "doctor:update", "name": "编辑医生", "type": "button", "parent_code": "doctor", "sort": 4},
    {"code": "doctor:delete", "name": "删除医生", "type": "button", "parent_code": "doctor", "sort": 5},
    {"code": "doctor:booking-setting", "name": "预约设置", "type": "button", "parent_code": "doctor", "sort": 6},
    
    # ========== 排班管理 ==========
    {"code": "schedule", "name": "排班管理", "type": "menu", "parent_code": None, "icon": "calendar", "sort": 5},
    {"code": "schedule:list", "name": "查看排班列表", "type": "button", "parent_code": "schedule", "sort": 1},
    {"code": "schedule:create", "name": "新增排班", "type": "button", "parent_code": "schedule", "sort": 2},
    {"code": "schedule:update", "name": "编辑排班", "type": "button", "parent_code": "schedule", "sort": 3},
    {"code": "schedule:delete", "name": "删除排班", "type": "button", "parent_code": "schedule", "sort": 4},
    {"code": "schedule:template", "name": "排班模板", "type": "button", "parent_code": "schedule", "sort": 5},
    {"code": "schedule:custom", "name": "自定义排班", "type": "button", "parent_code": "schedule", "sort": 6},
    {"code": "schedule:rest-day", "name": "休息日设置", "type": "button", "parent_code": "schedule", "sort": 7},
    {"code": "schedule:suspension", "name": "停诊管理", "type": "button", "parent_code": "schedule", "sort": 8},
    {"code": "schedule:statistics", "name": "排班统计", "type": "button", "parent_code": "schedule", "sort": 9},
    
    # ========== 预约管理 ==========
    {"code": "appointment", "name": "预约管理", "type": "menu", "parent_code": None, "icon": "schedule", "sort": 6},
    {"code": "appointment:list", "name": "查看预约列表", "type": "button", "parent_code": "appointment", "sort": 1},
    {"code": "appointment:detail", "name": "查看预约详情", "type": "button", "parent_code": "appointment", "sort": 2},
    {"code": "appointment:update", "name": "更新预约状态", "type": "button", "parent_code": "appointment", "sort": 3},
    {"code": "appointment:cancel", "name": "取消预约", "type": "button", "parent_code": "appointment", "sort": 4},
    {"code": "appointment:statistics", "name": "预约统计", "type": "button", "parent_code": "appointment", "sort": 5},
    
    # ========== 患者管理 ==========
    {"code": "patient", "name": "患者管理", "type": "menu", "parent_code": None, "icon": "team", "sort": 7},
    {"code": "patient:list", "name": "查看患者列表", "type": "button", "parent_code": "patient", "sort": 1},
    {"code": "patient:detail", "name": "查看患者详情", "type": "button", "parent_code": "patient", "sort": 2},
    {"code": "patient:update", "name": "编辑患者", "type": "button", "parent_code": "patient", "sort": 3},
    {"code": "patient:create", "name": "新增患者", "type": "button", "parent_code": "patient", "sort": 4},
    
    # ========== 停诊审核 ==========
    {"code": "leave-request", "name": "停诊审核", "type": "menu", "parent_code": None, "icon": "exception", "sort": 8},
    {"code": "leave-request:list", "name": "查看停诊申请", "type": "button", "parent_code": "leave-request", "sort": 1},
    {"code": "leave-request:approve", "name": "审批停诊申请", "type": "button", "parent_code": "leave-request", "sort": 2},
    
    # ========== 用户反馈 ==========
    {"code": "feedback", "name": "用户反馈", "type": "menu", "parent_code": None, "icon": "comment", "sort": 9},
    {"code": "feedback:list", "name": "查看反馈列表", "type": "button", "parent_code": "feedback", "sort": 1},
    {"code": "feedback:reply", "name": "回复反馈", "type": "button", "parent_code": "feedback", "sort": 2},
    {"code": "feedback:delete", "name": "删除反馈", "type": "button", "parent_code": "feedback", "sort": 3},
    
    # ========== 消息管理 ==========
    {"code": "message", "name": "消息管理", "type": "menu", "parent_code": None, "icon": "bell", "sort": 10},
    {"code": "message:list", "name": "查看消息列表", "type": "button", "parent_code": "message", "sort": 1},
    {"code": "message:send", "name": "发送消息", "type": "button", "parent_code": "message", "sort": 2},
    {"code": "message:delete", "name": "删除消息", "type": "button", "parent_code": "message", "sort": 3},
    
    # ========== 内容管理 ==========
    {"code": "content", "name": "内容管理", "type": "menu", "parent_code": None, "icon": "fileText", "sort": 11},
    {"code": "content:news", "name": "新闻管理", "type": "button", "parent_code": "content", "sort": 1},
    {"code": "content:news:create", "name": "新增新闻", "type": "button", "parent_code": "content:news", "sort": 1},
    {"code": "content:news:update", "name": "编辑新闻", "type": "button", "parent_code": "content:news", "sort": 2},
    {"code": "content:news:delete", "name": "删除新闻", "type": "button", "parent_code": "content:news", "sort": 3},
    {"code": "content:notice", "name": "公告管理", "type": "button", "parent_code": "content", "sort": 2},
    {"code": "content:notice:create", "name": "新增公告", "type": "button", "parent_code": "content:notice", "sort": 1},
    {"code": "content:notice:update", "name": "编辑公告", "type": "button", "parent_code": "content:notice", "sort": 2},
    {"code": "content:notice:delete", "name": "删除公告", "type": "button", "parent_code": "content:notice", "sort": 3},
    {"code": "content:banner", "name": "轮播图管理", "type": "button", "parent_code": "content", "sort": 3},
    {"code": "content:banner:create", "name": "新增轮播图", "type": "button", "parent_code": "content:banner", "sort": 1},
    {"code": "content:banner:update", "name": "编辑轮播图", "type": "button", "parent_code": "content:banner", "sort": 2},
    {"code": "content:banner:delete", "name": "删除轮播图", "type": "button", "parent_code": "content:banner", "sort": 3},
    
    # ========== 统计分析 ==========
    {"code": "statistics", "name": "统计分析", "type": "menu", "parent_code": None, "icon": "barChart", "sort": 12},
    {"code": "statistics:view", "name": "查看统计分析", "type": "button", "parent_code": "statistics", "sort": 1},
    
    # ========== 系统设置 ==========
    {"code": "system", "name": "系统设置", "type": "menu", "parent_code": None, "icon": "setting", "sort": 13},
    {"code": "system:role", "name": "角色管理", "type": "button", "parent_code": "system", "sort": 1},
    {"code": "system:role:create", "name": "新增角色", "type": "button", "parent_code": "system:role", "sort": 1},
    {"code": "system:role:update", "name": "编辑角色", "type": "button", "parent_code": "system:role", "sort": 2},
    {"code": "system:role:delete", "name": "删除角色", "type": "button", "parent_code": "system:role", "sort": 3},
    {"code": "system:role:permission", "name": "分配权限", "type": "button", "parent_code": "system:role", "sort": 4},
    # 用户管理（原管理员管理）
    {"code": "system:user", "name": "用户管理", "type": "button", "parent_code": "system", "sort": 2},
    {"code": "system:user:create", "name": "新增用户", "type": "button", "parent_code": "system:user", "sort": 1},
    {"code": "system:user:update", "name": "编辑用户", "type": "button", "parent_code": "system:user", "sort": 2},
    {"code": "system:user:delete", "name": "删除用户", "type": "button", "parent_code": "system:user", "sort": 3},
    {"code": "system:user:reset-password", "name": "重置密码", "type": "button", "parent_code": "system:user", "sort": 4},
    {"code": "system:settings", "name": "系统配置", "type": "button", "parent_code": "system", "sort": 3},
    {"code": "system:consultation-fee", "name": "诊费管理", "type": "button", "parent_code": "system", "sort": 4},
    {"code": "system:log", "name": "操作日志", "type": "button", "parent_code": "system", "sort": 5},
]

# 内置角色定义
BUILTIN_ROLES = [
    {
        "code": "SUPER_ADMIN",
        "name": "超级管理员",
        "description": "系统超级管理员，拥有所有权限，可管理所有门店",
        "permissions": "*",  # 特殊标记，表示全部权限
    },
    {
        "code": "STORE_ADMIN",
        "name": "门店管理员",
        "description": "门店管理员，管理本门店数据",
        "permissions": [
            "dashboard", "dashboard:view",
            "store", "store:list", "store:update",  # 只能查看和编辑自己的门店
            "department", "department:list", "department:create", "department:update", "department:delete",
            "doctor", "doctor:list", "doctor:detail", "doctor:create", "doctor:update", "doctor:delete", "doctor:booking-setting",
            "schedule", "schedule:list", "schedule:create", "schedule:update", "schedule:delete", 
            "schedule:template", "schedule:custom", "schedule:rest-day", "schedule:suspension", "schedule:statistics",
            "appointment", "appointment:list", "appointment:detail", "appointment:update", "appointment:cancel", "appointment:statistics",
            "patient", "patient:list", "patient:detail", "patient:update", "patient:create",
            "leave-request", "leave-request:list", "leave-request:approve",
            "feedback", "feedback:list", "feedback:reply", "feedback:delete",
            "message", "message:list", "message:send", "message:delete",
            "content", "content:news", "content:news:create", "content:news:update", "content:news:delete",
            "content:notice", "content:notice:create", "content:notice:update", "content:notice:delete",
            "content:banner", "content:banner:create", "content:banner:update", "content:banner:delete",
            "statistics", "statistics:view",
            "system", "system:user", "system:user:create", "system:user:update", "system:user:delete", "system:user:reset-password",
        ],
    },
]


async def init_permissions():
    """初始化权限数据"""
    async with AsyncSessionLocal() as db:
        service = PermissionService(db)
        
        print("开始初始化权限数据...")
        created = await service.batch_create(PERMISSIONS)
        print(f"成功创建 {len(created)} 条权限记录")
        
        # 打印所有权限
        all_permissions = await service.get_all()
        print(f"\n当前系统共有 {len(all_permissions)} 条权限:")
        for p in all_permissions:
            prefix = "  " if p.parent_code else ""
            print(f"{prefix}- [{p.type}] {p.code}: {p.name}")


async def init_roles():
    """初始化内置角色"""
    async with AsyncSessionLocal() as db:
        role_service = RoleService(db)
        perm_service = PermissionService(db)
        
        print("\n开始初始化内置角色...")
        
        # 获取所有权限码（用于超级管理员）
        all_permissions = await perm_service.get_all()
        all_perm_codes = [p.code for p in all_permissions]
        
        for role_data in BUILTIN_ROLES:
            existing = await role_service.get_by_code(role_data["code"])
            
            if existing:
                print(f"  角色 {role_data['code']} 已存在，更新权限...")
                # 更新权限
                if role_data["permissions"] == "*":
                    permissions = all_perm_codes
                else:
                    permissions = role_data["permissions"]
                await role_service.update_permissions(existing.id, permissions)
            else:
                print(f"  创建角色 {role_data['code']}...")
                if role_data["permissions"] == "*":
                    permissions = all_perm_codes
                else:
                    permissions = role_data["permissions"]
                
                await role_service.create({
                    "code": role_data["code"],
                    "name": role_data["name"],
                    "description": role_data["description"],
                    "permissions": permissions,
                    "status": 1,
                })
        
        print("内置角色初始化完成！")


async def main():
    """主函数"""
    await init_permissions()
    await init_roles()


if __name__ == "__main__":
    asyncio.run(main())
