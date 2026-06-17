---
name: View Logs
description: 查看服务日志
category: system
tags: [logs, monitoring]
parameters:
  - name: service
    type: choice
    required: true
    default: backend
    description: 服务名称
    choices: [backend, celery_worker, celery_beat, all]
  - name: lines
    type: number
    required: false
    default: 100
    description: 显示行数
  - name: follow
    type: boolean
    required: false
    default: false
    description: 实时跟踪
---

**用途**
查看 Docker 容器日志。

**前置条件**
- Docker 正在运行
- 容器正在运行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --service | choice | 是 | backend | 服务名称 |
| --lines | number | 否 | 100 | 显示行数 |
| --follow | boolean | 否 | false | 实时跟踪 |

**执行步骤**

1. 确定目标容器名称

2. 根据参数执行：

   **查看最近日志**：
   ```bash
   docker-compose logs --tail <lines> <service>
   ```

   **实时跟踪日志**：
   ```bash
   docker-compose logs --tail <lines> --follow <service>
   ```

3. 高亮显示错误和警告信息

4. 显示日志统计（错误数、警告数）

**注意事项**
- follow 模式按 Ctrl+C 退出
- 日志文件可能很大，建议指定行数
- 可以使用 grep 过滤日志内容

**示例**
```bash
# 查看后端日志
/logs --service backend

# 实时跟踪
/logs --service backend --follow true

# 查看更多行
/logs --service backend --lines 500

# 查看所有服务日志
/logs --service all
```
