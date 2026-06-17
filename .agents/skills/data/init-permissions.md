---
name: Initialize Permissions
description: 初始化权限数据
category: data
tags: [permissions, initialization]
parameters: []
---

**用途**
执行 `apps/server/scripts/init_permissions.py` 初始化系统权限。

**前置条件**
- 数据库已创建并运行
- 角色已初始化（建议先执行 init-roles）

**参数说明**
无参数

**执行步骤**

1. 进入 `apps/server` 目录

2. 执行权限初始化脚本：
   ```bash
   python scripts/init_permissions.py
   ```

3. 显示创建的权限数量

4. 显示权限树结构：
   - 菜单权限（一级）
   - 按钮权限（二级，属于菜单权限）

5. 显示执行结果摘要

**注意事项**
- 脚本是幂等的，重复执行不会重复创建已存在的权限
- 权限定义在脚本中的 PERMISSIONS 数组
- 约 80+ 条权限记录
- 如果需要添加新权限，修改脚本中的 PERMISSIONS 数组后重新执行

**示例**
```bash
# 初始化权限
/init-permissions
```
