---
name: Health Check
description: 检查系统各服务健康状态
category: system
tags: [monitoring, health, diagnostics]
parameters:
  - name: services
    type: string
    required: false
    default: "all"
    description: 检查的服务（逗号分隔）
  - name: verbose
    type: boolean
    required: false
    default: false
    description: 显示详细信息
---

**用途**
检查数据库、Redis、后端 API、前端应用等服务的健康状态。

**前置条件**
- 无特殊要求

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --services | string | 否 | all | 服务列表：all/db,redis,backend,frontend,docker |
| --verbose | boolean | 否 | false | 显示详细信息 |

**执行步骤**

根据 services 参数执行相应检查：

1. **数据库检查 (db)**
   - 测试 PostgreSQL 连接
   - 查询数据库版本
   - 检查数据库大小
   - verbose 时显示连接池状态

2. **Redis 检查 (redis)**
   - 测试 Redis 连接
   - 执行 PING 命令
   - 显示内存使用情况
   - verbose 时显示键数量和过期键统计

3. **后端 API 检查 (backend)**
   - 检查端口 8000 是否开放
   - 访问 /health 或 /api/health 端点
   - 测量响应时间
   - verbose 时显示详细响应内容

4. **前端应用检查 (frontend)**
   - 检查静态文件是否存在
   - 验证构建产物完整性
   - 检查各应用端口（8002, 8003, 8005）

5. **Docker 容器检查 (docker)**
   - 检查 Docker 是否运行
   - 列出所有容器状态
   - 显示资源使用情况
   - verbose 时显示容器日志（最近 20 行）

6. 汇总显示各服务状态：
   - ✓ 正常运行
   - ✗ 服务异常
   - ⚠ 性能警告

**注意事项**
- 需要配置正确的服务端口
- API 健康检查需要后端运行
- 如果某些服务未运行，会显示为异常但不影响其他检查

**示例**
```bash
# 检查所有服务
/health-check

# 仅检查数据库和 Redis
/health-check --services db,redis

# 详细模式检查
/health-check --verbose true

# 仅检查 Docker 容器
/health-check --services docker

# 检查后端和前端
/health-check --services backend,frontend
```
