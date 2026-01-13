---
name: Build Application
description: 构建应用生产版本
category: development
tags: [build, production]
parameters:
  - name: app
    type: choice
    required: true
    default: all
    description: 应用名称
    choices: [all, admin, doctor, patient-h5, patient-miniapp]
  - name: analyze
    type: boolean
    required: false
    default: false
    description: 分析构建产物
---

**用途**
构建应用的生产版本。

**前置条件**
- 依赖已安装
- 无 TypeScript 类型错误

**参数说明**
| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| --app | choice | 是 | all | 应用名称 |
| --analyze | boolean | 否 | false | 分析构建产物 |

**执行步骤**

1. 清理旧的构建产物

2. 构建共享包（优先）

3. 根据 app 参数构建：

   **all**: 构建所有前端应用
   ```bash
   pnpm build
   ```

   **admin**:
   ```bash
   cd apps/admin && pnpm build
   ```

   **doctor**:
   ```bash
   cd apps/doctor && pnpm build
   ```

   **patient-h5**:
   ```bash
   cd apps/patient-h5 && pnpm build
   ```

   **patient-miniapp**:
   ```bash
   cd apps/patient-miniapp && npm run build
   ```

4. 如果 analyze=true：
   - 显示构建产物大小
   - 显示各模块大小
   - 分析 Gzip 后大小

5. 显示构建结果摘要

**注意事项**
- 构建耗时约 2-5 分钟
- 确保有足够的磁盘空间
- 构建前建议先运行 lint 检查

**示例**
```bash
# 构建所有应用
/build --app all

# 构建单个应用
/build --app admin

# 构建并分析
/build --app admin --analyze true
```
