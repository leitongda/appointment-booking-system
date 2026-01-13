# Claude Skills

医院挂号系统的自定义 Claude Skills 集合，用于提升开发和运维效率。

## 目录结构

```
.claude/skills/
├── _shared/           # 共享工具脚本
├── database/          # 数据库相关
├── deployment/        # 部署相关
├── development/       # 开发环境
├── system/           # 系统管理
└── data/             # 数据管理
```

## 可用 Skills

### 数据库 (database)

| Skill | 描述 | 用法 |
|-------|------|------|
| `/migrate` | 数据库迁移 | `/migrate --action upgrade` |
| `/db-backup` | 数据库备份 | `/db-backup --output ./backups` |
| `/db-restore` | 数据库恢复 | `/db-restore --input ./backup.sql` |

### 部署 (deployment)

| Skill | 描述 | 用法 |
|-------|------|------|
| `/deploy` | 应用部署 | `/deploy --env production --app all` |
| `/docker-restart` | Docker重启 | `/docker-restart --rebuild false` |

### 开发 (development)

| Skill | 描述 | 用法 |
|-------|------|------|
| `/dev` | 启动开发环境 | `/dev --app admin` |
| `/build` | 构建应用 | `/build --app all` |
| `/test` | 运行测试 | `/test --type unit --coverage true` |

### 系统 (system)

| Skill | 描述 | 用法 |
|-------|------|------|
| `/init-system` | 系统初始化 | `/init-system --components all` |
| `/health-check` | 健康检查 | `/health-check --verbose true` |
| `/logs` | 查看日志 | `/logs --service backend --follow true` |
| `/cache-clear` | 清空缓存 | `/cache-clear --pattern "*"` |
| `/secrets-generate` | 密钥生成 | `/secrets-generate --type jwt` |

### 数据 (data)

| Skill | 描述 | 用法 |
|-------|------|------|
| `/init-permissions` | 权限初始化 | `/init-permissions` |
| `/init-roles` | 角色初始化 | `/init-roles` |
| `/init-demo-data` | 演示数据 | `/init-demo-data` |
| `/stats` | 数据统计 | `/stats --type all` |

## 常见工作流

### 新功能开发

```bash
# 1. 启动开发环境
/dev --app server

# 2. 创建数据库迁移
/migrate --action create --message "添加订单状态字段"

# 3. 执行迁移
/migrate --action upgrade

# 4. 运行测试
/test --type unit

# 5. 构建前端
/build --app admin

# 6. 部署到测试环境
/deploy --env staging --app frontend
```

### 部署到生产

```bash
# 1. 备份数据库
/db-backup

# 2. 健康检查
/health-check

# 3. 全量部署
/deploy --env production --app all

# 4. 验证部署
/health-check --verbose true
```

### 系统初始化

```bash
# 1. 数据库迁移
/migrate --action upgrade

# 2. 初始化系统
/init-system --components all

# 3. 健康检查
/health-check

# 4. 启动服务
/docker-restart
```

## 添加新 Skill

1. 在对应分类目录下创建 `.md` 文件
2. 使用 frontmatter 定义元数据
3. 遵循现有格式编写内容

### Skill 模板

```markdown
---
name: Skill Name
description: 简短描述
category: 分类
tags: [标签]
parameters:
  - name: param1
    type: choice
    required: true
    default: value1
    choices: [a, b]
---

**用途**
详细说明...

**前置条件**
- 条件1

**执行步骤**
1. 步骤1
2. 步骤2

**示例**
```
/skill-name --param value
```
```
