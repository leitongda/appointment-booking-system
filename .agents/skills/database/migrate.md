---
name: Database Migration
description: 执行数据库迁移操作（创建、升级、回滚）
category: database
tags: [database, migration, alembic]
parameters:
  - name: action
    type: choice
    required: true
    default: upgrade
    description: 迁移操作类型
    choices: [create, upgrade, downgrade, current, history]
  - name: message
    type: string
    required: false
    default: ""
    description: 迁移描述（仅 create 需要）
  - name: revision
    type: string
    required: false
    default: "head"
    description: 目标版本（upgrade/downgrade 时使用）
---

**用途**
管理数据库迁移，支持创建新迁移、升级到最新版本、回滚到指定版本等操作。基于 Alembic 迁移框架。

**前置条件**
- Python 虚拟环境已激活或 Python 3.12+ 已安装
- 已安装依赖 `pip install -r requirements.txt`
- 数据库服务正在运行
- 在项目根目录执行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --action | choice | 是 | upgrade | 操作类型：create/upgrade/downgrade/current/history |
| --message | string | 否 | - | 迁移描述（create 时必填） |
| --revision | string | 否 | head | 目标版本标识（如 -1 回滚一个版本） |

**执行步骤**

当 `action=create` 时：
1. 验证 message 参数已提供
2. 进入 `apps/server` 目录
3. 执行 `alembic revision --autogenerate -m "<message>"`
4. 显示生成的迁移文件路径

当 `action=upgrade` 时：
1. 检查数据库连接
2. 进入 `apps/server` 目录
3. 执行 `alembic upgrade <revision>`
4. 显示迁移结果

当 `action=downgrade` 时：
1. 确认操作（危险操作）
2. 进入 `apps/server` 目录
3. 执行 `alembic downgrade <revision>`
4. 显示回滚结果

当 `action=current` 时：
1. 进入 `apps/server` 目录
2. 执行 `alembic current`
3. 显示当前版本

当 `action=history` 时：
1. 进入 `apps/server` 目录
2. 执行 `alembic history`
3. 显示迁移历史

**注意事项**
- create 操作需要先修改 SQLAlchemy 模型
- downgrade 操作需谨慎，确保有备份
- 生产环境执行前先在测试环境验证
- 如果迁移失败，检查 alembic.ini 中的数据库连接配置

**示例**
```bash
# 创建新迁移
/migrate --action create --message "添加用户表字段"

# 升级到最新版本
/migrate --action upgrade

# 升级到指定版本
/migrate --action upgrade --revision 001

# 回滚一个版本
/migrate --action downgrade --revision -1

# 查看当前版本
/migrate --action current

# 查看迁移历史
/migrate --action history
```
