"""初始化权限数据

注意：角色初始化请使用 init_roles.py 脚本
"""
import asyncio
import sys
import os

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.session import AsyncSessionLocal
from app.modules.admin.permission_metadata import infer_permission_control_type_for_seed
from app.modules.admin.service_permissions import PermissionService

# 权限数据定义
# type: menu - 菜单权限, button - 按钮/操作权限
PERMISSIONS = [
    # ========== 仪表盘 ==========
    {"code": "dashboard", "name": "仪表盘", "type": "menu", "parent_code": None, "icon": "dashboard", "sort": 1},
    {"code": "dashboard:view", "name": "查看仪表盘", "type": "button", "parent_code": "dashboard", "sort": 1},
    
    # ========== 门店管理 ==========
    {"code": "store", "name": "门店管理", "type": "menu", "parent_code": None, "icon": "shop", "sort": 2},
    {"code": "store:list", "name": "查看门店列表", "type": "button", "parent_code": "store", "sort": 1},
    {"code": "store:export", "name": "导出门店", "type": "button", "parent_code": "store", "sort": 2},
    {"code": "store:create", "name": "新增门店", "type": "button", "parent_code": "store", "sort": 2},
    {"code": "store:update", "name": "编辑门店", "type": "button", "parent_code": "store", "sort": 3},
    {"code": "store:delete", "name": "删除门店", "type": "button", "parent_code": "store", "sort": 4},
    
    # ========== 科室管理 ==========
    {"code": "department", "name": "科室管理", "type": "menu", "parent_code": None, "icon": "apartment", "sort": 3},
    {"code": "department:list", "name": "查看科室列表", "type": "button", "parent_code": "department", "sort": 1},
    {"code": "department:export", "name": "导出科室", "type": "button", "parent_code": "department", "sort": 2},
    {"code": "department:create", "name": "新增科室", "type": "button", "parent_code": "department", "sort": 2},
    {"code": "department:update", "name": "编辑科室", "type": "button", "parent_code": "department", "sort": 3},
    {"code": "department:delete", "name": "删除科室", "type": "button", "parent_code": "department", "sort": 4},
    
    # ========== 医生管理 ==========
    {"code": "doctor", "name": "医生管理", "type": "menu", "parent_code": None, "icon": "user", "sort": 4},
    {"code": "doctor:list", "name": "查看医生列表", "type": "button", "parent_code": "doctor", "sort": 1},
    {"code": "doctor:detail", "name": "查看医生详情", "type": "button", "parent_code": "doctor", "sort": 2},
    {"code": "doctor:export", "name": "导出医生", "type": "button", "parent_code": "doctor", "sort": 3},
    {"code": "doctor:create", "name": "新增医生", "type": "button", "parent_code": "doctor", "sort": 3},
    {"code": "doctor:update", "name": "编辑医生", "type": "button", "parent_code": "doctor", "sort": 4},
    {"code": "doctor:delete", "name": "删除医生", "type": "button", "parent_code": "doctor", "sort": 5},
    {"code": "doctor:booking-setting", "name": "预约设置", "type": "button", "parent_code": "doctor", "sort": 6},
    
    # ========== 排班管理 ==========
    {"code": "schedule", "name": "排班管理", "type": "menu", "parent_code": None, "icon": "calendar", "sort": 5},
    {"code": "schedule:list", "name": "查看排班列表", "type": "button", "parent_code": "schedule", "sort": 1},
    {"code": "schedule:export", "name": "导出排班", "type": "button", "parent_code": "schedule", "sort": 2},
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
    {"code": "appointment:export", "name": "导出预约", "type": "button", "parent_code": "appointment", "sort": 3},
    {"code": "appointment:refund", "name": "预约退款", "type": "button", "parent_code": "appointment", "sort": 4},
    {"code": "appointment:manage", "name": "预约流转操作", "type": "button", "parent_code": "appointment", "sort": 5},
    {"code": "appointment:update", "name": "更新预约状态", "type": "button", "parent_code": "appointment", "sort": 3},
    {"code": "appointment:cancel", "name": "取消预约", "type": "button", "parent_code": "appointment", "sort": 4},
    {"code": "appointment:statistics", "name": "预约统计", "type": "button", "parent_code": "appointment", "sort": 5},
    
    # ========== 患者管理 ==========
    {"code": "patient", "name": "患者管理", "type": "menu", "parent_code": None, "icon": "team", "sort": 7},
    {"code": "patient:list", "name": "查看患者列表", "type": "button", "parent_code": "patient", "sort": 1},
    {"code": "patient:detail", "name": "查看患者详情", "type": "button", "parent_code": "patient", "sort": 2},
    {"code": "patient:export", "name": "导出患者", "type": "button", "parent_code": "patient", "sort": 3},
    {"code": "patient:create", "name": "新增患者", "type": "button", "parent_code": "patient", "sort": 3},
    {"code": "patient:update", "name": "编辑患者", "type": "button", "parent_code": "patient", "sort": 4},
    {"code": "patient:delete", "name": "删除患者", "type": "button", "parent_code": "patient", "sort": 5},
    
    # ========== 停诊审核 ==========
    {"code": "leave-request", "name": "停诊审核", "type": "menu", "parent_code": None, "icon": "exception", "sort": 8},
    {"code": "leave-request:list", "name": "查看停诊申请", "type": "button", "parent_code": "leave-request", "sort": 1},
    {"code": "leave-request:approve", "name": "审批停诊申请", "type": "button", "parent_code": "leave-request", "sort": 2},
    
    # ========== 用户反馈 ==========
    {"code": "feedback", "name": "用户反馈", "type": "menu", "parent_code": None, "icon": "comment", "sort": 9},
    {"code": "feedback:list", "name": "查看反馈列表", "type": "button", "parent_code": "feedback", "sort": 1},
    {"code": "feedback:export", "name": "导出反馈", "type": "button", "parent_code": "feedback", "sort": 2},
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

    # ========== 内容站点 CMS ==========
    {"code": "cms", "name": "内容站点", "type": "menu", "parent_code": None, "icon": "global", "sort": 15},
    {"code": "cms:site", "name": "站点管理", "type": "button", "parent_code": "cms", "sort": 1},
    {"code": "cms:site:create", "name": "新增站点", "type": "button", "parent_code": "cms:site", "sort": 1},
    {"code": "cms:site:update", "name": "编辑站点", "type": "button", "parent_code": "cms:site", "sort": 2},
    {"code": "cms:site:delete", "name": "删除站点", "type": "button", "parent_code": "cms:site", "sort": 3},
    {"code": "cms:category", "name": "栏目管理", "type": "button", "parent_code": "cms", "sort": 2},
    {"code": "cms:category:create", "name": "新增栏目", "type": "button", "parent_code": "cms:category", "sort": 1},
    {"code": "cms:category:update", "name": "编辑栏目", "type": "button", "parent_code": "cms:category", "sort": 2},
    {"code": "cms:category:delete", "name": "删除栏目", "type": "button", "parent_code": "cms:category", "sort": 3},
    {"code": "cms:article", "name": "文章管理", "type": "button", "parent_code": "cms", "sort": 3},
    {"code": "cms:article:create", "name": "新增文章", "type": "button", "parent_code": "cms:article", "sort": 1},
    {"code": "cms:article:update", "name": "编辑文章", "type": "button", "parent_code": "cms:article", "sort": 2},
    {"code": "cms:article:delete", "name": "删除文章", "type": "button", "parent_code": "cms:article", "sort": 3},

    # ========== 统计分析 ==========
    {"code": "statistics", "name": "统计分析", "type": "menu", "parent_code": None, "icon": "barChart", "sort": 12},
    {"code": "statistics:view", "name": "查看统计分析", "type": "button", "parent_code": "statistics", "sort": 1},

    # ========== 页面搭建（低代码） ==========
    {"code": "lowcode", "name": "页面搭建", "type": "menu", "parent_code": None, "icon": "appstore", "sort": 13},
    {"code": "lowcode:page", "name": "页面管理", "type": "button", "parent_code": "lowcode", "sort": 1},
    {"code": "lowcode:page:list", "name": "查看页面列表", "type": "button", "parent_code": "lowcode:page", "sort": 1},
    {"code": "lowcode:page:create", "name": "新增页面", "type": "button", "parent_code": "lowcode:page", "sort": 2},
    {"code": "lowcode:page:update", "name": "编辑页面", "type": "button", "parent_code": "lowcode:page", "sort": 3},
    {"code": "lowcode:page:delete", "name": "删除页面", "type": "button", "parent_code": "lowcode:page", "sort": 4},
    {"code": "lowcode:page:publish", "name": "发布页面", "type": "button", "parent_code": "lowcode:page", "sort": 5},
    {"code": "lowcode:marketplace", "name": "模板市场", "type": "button", "parent_code": "lowcode", "sort": 2},
    {"code": "lowcode:marketplace:view", "name": "查看模板市场", "type": "button", "parent_code": "lowcode:marketplace", "sort": 1},
    {"code": "lowcode:marketplace:publish", "name": "发布模板", "type": "button", "parent_code": "lowcode:marketplace", "sort": 2},

    # ========== 系统设置 ==========
    {"code": "system", "name": "系统设置", "type": "menu", "parent_code": None, "icon": "setting", "sort": 14},
    {"code": "system:role", "name": "角色管理", "type": "button", "parent_code": "system", "sort": 1},
    {"code": "system:role:list", "name": "查看角色列表", "type": "button", "parent_code": "system:role", "sort": 0},
    {"code": "system:role:create", "name": "新增角色", "type": "button", "parent_code": "system:role", "sort": 1},
    {"code": "system:role:update", "name": "编辑角色", "type": "button", "parent_code": "system:role", "sort": 2},
    {"code": "system:role:delete", "name": "删除角色", "type": "button", "parent_code": "system:role", "sort": 3},
    {"code": "system:role:permission", "name": "分配权限", "type": "button", "parent_code": "system:role", "sort": 4},
    # 用户管理（原管理员管理）
    {"code": "system:user", "name": "用户管理", "type": "button", "parent_code": "system", "sort": 2},
    {"code": "system:user:list", "name": "查看用户列表", "type": "button", "parent_code": "system:user", "sort": 0},
    {"code": "system:user:create", "name": "新增用户", "type": "button", "parent_code": "system:user", "sort": 1},
    {"code": "system:user:update", "name": "编辑用户", "type": "button", "parent_code": "system:user", "sort": 2},
    {"code": "system:user:delete", "name": "删除用户", "type": "button", "parent_code": "system:user", "sort": 3},
    {"code": "system:user:reset-password", "name": "重置密码", "type": "button", "parent_code": "system:user", "sort": 4},
    {"code": "system:settings", "name": "系统配置", "type": "button", "parent_code": "system", "sort": 3},
    {"code": "settings:edit", "name": "编辑系统设置", "type": "button", "parent_code": "system:settings", "sort": 1},
    {"code": "settings:wechat", "name": "编辑微信配置", "type": "button", "parent_code": "system:settings", "sort": 2},
    {"code": "settings:sms", "name": "编辑短信配置", "type": "button", "parent_code": "system:settings", "sort": 3},
    {"code": "settings:email", "name": "编辑邮件配置", "type": "button", "parent_code": "system:settings", "sort": 4},
    {"code": "blacklist:list", "name": "查看黑名单列表", "type": "button", "parent_code": "system:settings", "sort": 5},
    {"code": "blacklist:create", "name": "新增黑名单", "type": "button", "parent_code": "system:settings", "sort": 6},
    {"code": "blacklist:delete", "name": "移除黑名单", "type": "button", "parent_code": "system:settings", "sort": 7},
    {"code": "system:consultation-fee", "name": "诊费管理", "type": "button", "parent_code": "system", "sort": 4},
    {"code": "system:log", "name": "操作日志", "type": "button", "parent_code": "system", "sort": 5},
    {"code": "log:list", "name": "查看操作日志明细", "type": "button", "parent_code": "system:log", "sort": 1},
    {"code": "log:export", "name": "导出操作日志", "type": "button", "parent_code": "system:log", "sort": 2},
    {"code": "admin:list", "name": "查看系统用户列表", "type": "button", "parent_code": "system:user", "sort": 5},
    {"code": "admin:export", "name": "导出系统用户", "type": "button", "parent_code": "system:user", "sort": 6},
    {"code": "schedule_template:list", "name": "查看排班模板列表", "type": "button", "parent_code": "schedule", "sort": 10},
    {"code": "schedule_template:export", "name": "导出排班模板", "type": "button", "parent_code": "schedule", "sort": 11},
    {"code": "rule_set:list", "name": "查看规则组列表", "type": "button", "parent_code": "system", "sort": 6},
    {"code": "rule_set:export", "name": "导出规则组", "type": "button", "parent_code": "system", "sort": 7},
    {"code": "rule_set:create", "name": "导入规则组", "type": "button", "parent_code": "system", "sort": 8},
    {"code": "system:config", "name": "系统配置", "type": "button", "parent_code": "system", "sort": 9},
    {"code": "system:monitoring", "name": "在线监控", "type": "button", "parent_code": "system", "sort": 10},

    # ========== 2026-10-24 目录补齐：后端守卫既有码（48 个，此前无法授权） ==========
    # 审批中心
    {"code": "approval", "name": "审批中心", "type": "menu", "parent_code": None, "icon": "audit", "sort": 15},
    {"code": "approval:read", "name": "查看审批", "type": "button", "parent_code": "approval", "sort": 1},
    {"code": "approval:approve", "name": "审批操作", "type": "button", "parent_code": "approval", "sort": 2},
    {"code": "approval-instance:manage", "name": "处理审批实例", "type": "button", "parent_code": "approval", "sort": 3},
    {"code": "approval-flow:list", "name": "查看审批流程", "type": "button", "parent_code": "approval", "sort": 4},
    {"code": "approval-flow:create", "name": "新增审批流程", "type": "button", "parent_code": "approval", "sort": 5},
    {"code": "approval-flow:update", "name": "编辑审批流程", "type": "button", "parent_code": "approval", "sort": 6},
    {"code": "approval-flow:delete", "name": "删除审批流程", "type": "button", "parent_code": "approval", "sort": 7},
    {"code": "approval-flow:manage", "name": "发布/停用审批流程", "type": "button", "parent_code": "approval", "sort": 8},
    # 联系人管理
    {"code": "contact", "name": "联系人管理", "type": "menu", "parent_code": None, "icon": "team", "sort": 16},
    {"code": "contact:view", "name": "查看联系人", "type": "button", "parent_code": "contact", "sort": 1},
    {"code": "contact:create", "name": "新增联系人", "type": "button", "parent_code": "contact", "sort": 2},
    {"code": "contact:edit", "name": "编辑联系人", "type": "button", "parent_code": "contact", "sort": 3},
    {"code": "contact:delete", "name": "删除联系人", "type": "button", "parent_code": "contact", "sort": 4},
    {"code": "contact:export", "name": "导出联系人", "type": "button", "parent_code": "contact", "sort": 5},
    # 兼职结算
    {"code": "freelance", "name": "兼职结算", "type": "menu", "parent_code": None, "icon": "money-collect", "sort": 17},
    {"code": "freelance:list", "name": "查看兼职数据", "type": "button", "parent_code": "freelance", "sort": 1},
    {"code": "freelance:create", "name": "新增兼职数据", "type": "button", "parent_code": "freelance", "sort": 2},
    {"code": "freelance:update", "name": "编辑兼职数据", "type": "button", "parent_code": "freelance", "sort": 3},
    {"code": "freelance:delete", "name": "删除兼职数据", "type": "button", "parent_code": "freelance", "sort": 4},
    {"code": "freelance:settle", "name": "结算操作", "type": "button", "parent_code": "freelance", "sort": 5},
    # 积分管理
    {"code": "points", "name": "积分管理", "type": "menu", "parent_code": None, "icon": "gift", "sort": 18},
    {"code": "points:list", "name": "查看积分", "type": "button", "parent_code": "points", "sort": 1},
    {"code": "points:update", "name": "调整积分", "type": "button", "parent_code": "points", "sort": 2},
    # 服务工单
    {"code": "support_ticket", "name": "服务工单", "type": "menu", "parent_code": None, "icon": "customer-service", "sort": 19},
    {"code": "support_ticket:view", "name": "查看工单", "type": "button", "parent_code": "support_ticket", "sort": 1},
    {"code": "support_ticket:list", "name": "查看工单列表", "type": "button", "parent_code": "support_ticket", "sort": 2},
    {"code": "support_ticket:update", "name": "处理工单", "type": "button", "parent_code": "support_ticket", "sort": 3},
    {"code": "support_ticket:manage", "name": "工单管理", "type": "button", "parent_code": "support_ticket", "sort": 4},
    # 候补管理
    {"code": "waitlist", "name": "候补管理", "type": "menu", "parent_code": None, "icon": "clock-circle", "sort": 20},
    {"code": "waitlist:read", "name": "查看候补", "type": "button", "parent_code": "waitlist", "sort": 1},
    {"code": "waitlist:cancel", "name": "取消候补", "type": "button", "parent_code": "waitlist", "sort": 2},
    {"code": "waitlist:promote", "name": "候补递补", "type": "button", "parent_code": "waitlist", "sort": 3},
    # 考勤管理
    {"code": "attendance", "name": "考勤管理", "type": "menu", "parent_code": None, "icon": "calendar", "sort": 21},
    {"code": "attendance:record", "name": "考勤打卡记录", "type": "button", "parent_code": "attendance", "sort": 1},
    {"code": "record:export", "name": "导出考勤记录", "type": "button", "parent_code": "attendance", "sort": 2},
    # 医生评价（挂医生管理）
    {"code": "doctor:review", "name": "医生评价管理", "type": "button", "parent_code": "doctor", "sort": 90},
    # 排班补充（挂排班管理）
    {"code": "schedule:read", "name": "查看排班", "type": "button", "parent_code": "schedule", "sort": 90},
    {"code": "schedule:suspend", "name": "停排管理", "type": "button", "parent_code": "schedule", "sort": 91},
    {"code": "schedule:room", "name": "诊室管理", "type": "button", "parent_code": "schedule", "sort": 92},
    {"code": "schedule:extra-quota", "name": "排班加额管理", "type": "button", "parent_code": "schedule", "sort": 93},
    {"code": "schedule:extra-quota:approve", "name": "加额审批", "type": "button", "parent_code": "schedule:extra-quota", "sort": 1},
    # 低代码补充（挂既有 lowcode:page / lowcode 分组）
    {"code": "lowcode:page:read", "name": "查看页面详情", "type": "button", "parent_code": "lowcode:page", "sort": 6},
    {"code": "lowcode:page:codegen", "name": "生成页面代码", "type": "button", "parent_code": "lowcode:page", "sort": 7},
    {"code": "lowcode:page:deploy", "name": "部署页面", "type": "button", "parent_code": "lowcode:page", "sort": 8},
    {"code": "lowcode:template", "name": "模板管理", "type": "button", "parent_code": "lowcode", "sort": 3},
    {"code": "lowcode:template:list", "name": "查看模板列表", "type": "button", "parent_code": "lowcode:template", "sort": 1},
    {"code": "lowcode:template:read", "name": "查看模板", "type": "button", "parent_code": "lowcode:template", "sort": 2},
    {"code": "lowcode:template:create", "name": "新增模板", "type": "button", "parent_code": "lowcode:template", "sort": 3},
    {"code": "lowcode:template:update", "name": "编辑模板", "type": "button", "parent_code": "lowcode:template", "sort": 4},
    {"code": "lowcode:template:delete", "name": "删除模板", "type": "button", "parent_code": "lowcode:template", "sort": 5},
    {"code": "lowcode:template:fork", "name": "复制模板", "type": "button", "parent_code": "lowcode:template", "sort": 6},
]

for permission in PERMISSIONS:
    permission["control_type"] = infer_permission_control_type_for_seed(permission, PERMISSIONS)

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


async def main():
    """主函数：仅初始化权限数据，角色初始化请使用 init_roles.py"""
    await init_permissions()


if __name__ == "__main__":
    asyncio.run(main())
