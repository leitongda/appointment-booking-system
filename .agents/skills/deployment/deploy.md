---
name: Deploy
description: 执行应用部署（前端/后端/全量）
category: deployment
tags: [deployment, ssh, docker]
parameters:
  - name: env
    type: choice
    required: true
    default: production
    description: 部署环境
    choices: [production, staging]
  - name: app
    type: choice
    required: false
    default: all
    description: 部署目标
    choices: [all, frontend, server]
  - name: rebuild
    type: boolean
    required: false
    default: false
    description: 是否重新构建 Docker 镜像
---

**用途**
自动化部署应用到服务器，支持前端构建上传和后端 Docker 容器更新。

**前置条件**
- 已配置 `scripts/deploy.env` 文件（包含 SSH 主机、用户、路径等）
- SSH 密钥已配置并可连接到服务器
- 服务器网络可达
- Git 已提交当前更改

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --env | choice | 是 | production | 部署环境：production/staging |
| --app | choice | 否 | all | 部署目标：all/frontend/server |
| --rebuild | boolean | 否 | false | 是否重建 Docker 镜像 |

**执行步骤**

1. 加载 `scripts/deploy.env` 配置
2. 显示部署信息摘要（环境、目标、是否重建）
3. 用户确认（除非使用 --yes 标志）
4. 根据 app 参数执行：

   **当 app=all 时**：
   - 步骤 1/2: 前端构建并上传（调用 deploy-frontend.sh）
   - 步骤 2/2: 服务器部署（调用 deploy-server.sh）

   **当 app=frontend 时**：
   - 执行 `pnpm build` 构建所有前端应用
   - 打包构建产物
   - 上传到服务器指定目录

   **当 app=server 时**：
   - SSH 到服务器
   - 拉取最新代码
   - 如果 rebuild=true，执行 docker-compose build
   - 执行 docker-compose up -d 重启服务

5. 运行健康检查验证部署结果
6. 显示部署摘要

**注意事项**
- 部署前确认 git 已提交当前更改
- 建议在非高峰时段执行
- 前端构建耗时约 3-5 分钟
- 后端重启会导致短暂服务中断（约 10-30 秒）
- 确保服务器有足够的磁盘空间

**示例**
```bash
# 全量部署到生产环境
/deploy --env production --app all

# 仅部署前端
/deploy --env production --app frontend

# 仅部署后端
/deploy --env production --app server

# 部署并重建 Docker 镜像
/deploy --env staging --app server --rebuild true
```
