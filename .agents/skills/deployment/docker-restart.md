---
name: Docker Restart
description: 重启 Docker 服务（后端、Celery）
category: deployment
tags: [docker, restart, service]
parameters:
  - name: rebuild
    type: boolean
    required: false
    default: false
    description: 重新构建镜像
  - name: service
    type: string
    required: false
    default: "all"
    description: 重启的服务
---

**用途**
重启 Docker 容器，可选择是否重新构建镜像。

**前置条件**
- Docker 已安装并运行
- docker-compose.yml 文件存在
- 在项目根目录或 scripts/server 目录执行

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --rebuild | boolean | 否 | false | 是否重建镜像 |
| --service | string | 否 | all | 服务名：all/backend/celery_worker/celery_beat |

**执行步骤**

1. 检查 Docker 是否运行
2. 进入 scripts/server 目录
3. 执行 `restart-docker.sh` 脚本
4. 根据 rebuild 和 service 参数执行：

   **当 rebuild=true 时**：
   - 停止所有容器 `docker-compose down`
   - 重新构建镜像 `docker-compose build`
   - 启动容器 `docker-compose up -d`

   **当 rebuild=false 时**：
   - 快速重启 `docker-compose restart`

   **当 service=all 时**：
   - 重启所有服务

   **当 service=特定服务时**：
   - 仅重启指定服务 `docker-compose restart <service>`

5. 等待服务启动
6. 显示容器状态
7. 可选：运行健康检查

**注意事项**
- 重启会导致短暂服务中断（约 10-30 秒）
- rebuild 会重新构建镜像，耗时较长（2-5 分钟）
- 建议在低峰时段执行
- 重启前建议先执行 `/db-backup` 备份数据

**示例**
```bash
# 简单重启所有服务
/docker-restart

# 重建并重启
/docker-restart --rebuild true

# 仅重启后端服务
/docker-restart --service backend

# 仅重启 Celery Worker
/docker-restart --service celery_worker

# 重建并重启特定服务
/docker-restart --service backend --rebuild true
```
