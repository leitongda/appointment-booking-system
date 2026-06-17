---
name: Initialize System
description: 初始化系统数据（角色、权限、基础数据）
category: system
tags: [initialization, database, setup]
parameters:
  - name: components
    type: string
    required: false
    default: "all"
    description: 初始化组件（逗号分隔）
  - name: skip-confirm
    type: boolean
    required: false
    default: false
    description: 跳过确认提示
---

**用途**
一键初始化系统所需的基础数据，包括角色、权限、管理员账号等。

**前置条件**
- 数据库已创建并运行
- 已执行数据库迁移（或使用空数据库）
- Python 环境已就绪
- 在项目根目录执行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --components | string | 否 | all | 组件列表：all/roles,permissions,admin,demo |
| --skip-confirm | boolean | 否 | false | 跳过确认直接执行 |

**执行步骤**

1. 解析 components 参数，确定要执行的初始化脚本
2. 显示即将执行的操作
3. 用户确认（除非 skip-confirm=true）
4. 按顺序执行：

   **当 components 包含 roles 时**：
   - 执行 `apps/server/scripts/init_roles.py`
   - 初始化三级角色体系（超级管理员、管理员、普通用户）
   - 显示创建的角色数量

   **当 components 包含 permissions 时**：
   - 执行 `apps/server/scripts/init_permissions.py`
   - 初始化所有权限（菜单权限和按钮权限）
   - 显示创建的权限数量和列表

   **当 components 包含 admin 时**：
   - 执行 `apps/server/scripts/init_data.py`
   - 创建默认管理员账号
   - 显示账号信息

   **当 components 包含 demo 时**：
   - 执行 `apps/server/scripts/init_demo_data.py`
   - 加载演示数据（门店、科室、医生等）
   - 显示创建的数据统计

5. 显示执行结果摘要和错误信息（如有）

**注意事项**
- 所有脚本都是幂等的，重复执行不会重复创建已存在数据
- demo 数据仅用于开发测试，生产环境不要使用
- 默认管理员账号：admin / admin123（首次部署后请修改）
- 如果某个组件初始化失败，其他组件仍会继续执行

**示例**
```bash
# 完整初始化（所有组件）
/init-system

# 仅初始化角色和权限
/init-system --components roles,permissions

# 初始化包含演示数据
/init-system --components all

# 跳过确认直接执行
/init-system --components all --skip-confirm true

# 仅初始化管理员账号
/init-system --components admin
```
