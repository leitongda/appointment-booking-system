---
name: Development Server
description: 启动开发服务器
category: development
tags: [dev, server, local]
parameters:
  - name: app
    type: choice
    required: true
    default: admin
    description: 应用名称
    choices: [admin, doctor, patient-h5, patient-miniapp, server]
  - name: env
    type: choice
    required: false
    default: local
    description: 环境配置
    choices: [local, remote, prod]
---

**用途**
启动指定应用的开发服务器。

**前置条件**
- 依赖已安装 `pnpm install`
- 端口未被占用
- 后端服务需要 Python 环境

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --app | choice | 是 | admin | 应用名称 |
| --env | choice | 否 | local | 环境配置 |

**执行步骤**

1. 检查端口占用情况
   - admin: 8005
   - doctor: 8003
   - patient-h5: 8002
   - server: 8000

2. 如果端口被占用，提示用户选择：
   - 终止占用进程
   - 更换端口
   - 取消操作

3. 根据应用启动对应服务：

   **admin**:
   ```bash
   cd apps/admin && pnpm dev
   ```

   **doctor**:
   ```bash
   cd apps/doctor && pnpm dev
   ```

   **patient-h5**:
   ```bash
   cd apps/patient-h5 && pnpm dev
   ```

   **patient-miniapp**:
   ```bash
   # 小程序需要使用微信开发者工具打开
   cd apps/patient-miniapp && npm run dev
   # 提示用户使用微信开发者工具打开项目
   ```

   **server**:
   ```bash
   cd apps/server && uvicorn app.main:app --reload --port 8000
   ```

4. 显示访问地址

**注意事项**
- 小程序开发需要微信开发者工具
- 多个应用可同时启动（不同端口）
- 按 Ctrl+C 停止服务
- 前端服务支持热更新

**示例**
```bash
# 启动 admin
/dev --app admin

# 启动后端
/dev --app server

# 启动患者 H5
/dev --app patient-h5

# 启动医生端
/dev --app doctor
```
