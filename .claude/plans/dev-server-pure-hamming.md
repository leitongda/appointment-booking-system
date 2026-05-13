# 计划：将各服务默认端口改为 9xxx 系列，并支持环境变量自定义

## Context

当前各 dev 服务的端口（8000/8002/8003/8005）太常用，容易与其他服务冲突。将默认端口全部改为 9xxx 系列，同时确保所有引用旧端口的地方同步更新，并支持环境变量覆盖。

## 新端口映射

| 服务 | 旧端口 | 新端口 |
|------|-------|-------|
| server (FastAPI) | 8000 | **9000** |
| admin | 8005 | **9105** |
| patient-h5 | 8002 | **9102** |
| doctor | 8003 | **9103** |
| temp-registration | 8003 | **9104** (原与 doctor 冲突，现在分开) |

## 需要修改的文件

### 1. 各服务启动端口（5 个文件）

| 文件 | 修改 |
|------|------|
| `package.json` 第28行 | `--port 8000` → `--port ${SERVER_PORT:-9000}` |
| `apps/admin/package.json` 第7-8行 | `PORT=8005` → `PORT=${PORT:-9105}` |
| `apps/patient-h5/package.json` 第7行 | `PORT=8002` → `PORT=${PORT:-9102}` |
| `apps/doctor/package.json` 第7行 | `PORT=8003` → `PORT=${PORT:-9103}` |
| `apps/temp-registration/package.json` 第7行 | `PORT=8003` → `PORT=${PORT:-9104}` |

### 2. 前端 proxy 默认目标：8000 → 9000（5 个文件）

| 文件 | 行号 |
|------|------|
| `apps/admin/config/proxy.ts` | 第7行 |
| `apps/patient-h5/.umirc.ts` | 第13行 |
| `apps/doctor/.umirc.ts` | 第25行 |
| `apps/temp-registration/.umirc.ts` | 第37行 |
| `apps/admin-v2/vite.config.ts` | 第18、22行 |

### 3. 环境示例文件（3 个文件）

| 文件 | 修改 |
|------|------|
| `apps/admin/.env.example` | 第21行注释中 8000 → 9000 |
| `apps/patient-miniapp/.env.example` | 第21、28行 8000 → 9000 |
| `apps/miniapp-instance/.env.example` | 第2行 8000 → 9000 |

### 4. 工具函数中的 fallback URL（2 个文件）

| 文件 | 行号 |
|------|------|
| `apps/patient-miniapp/src/utils/url.ts` | 第10、17、29行 |
| `apps/miniapp-instance/src/utils/url.ts` | 第10、17、29行 |

### 5. E2E 测试配置（1 个文件）

| 文件 | 行号 |
|------|------|
| `playwright.config.ts` | 第8行注释 |

### 6. Turbo 配置（1 个文件）

`turbo.json` — 4 处 `env` 数组添加 `"SERVER_PORT"`

### 7. 文档更新（1 个文件）

`CLAUDE.md` — Common Commands 部分的端口说明

## 修改详情

### `package.json` (根目录)

```diff
- "dev:server": "cd apps/server && uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
+ "dev:server": "cd apps/server && uvicorn app.main:app --reload --host 0.0.0.0 --port ${SERVER_PORT:-9000}"
```

### `apps/admin/package.json`

```diff
- "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=8005 max dev",
- "dev:local": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=8005 max dev",
+ "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=${PORT:-9105} max dev",
+ "dev:local": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=${PORT:-9105} max dev",
```

### `apps/patient-h5/package.json`

```diff
- "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=8002 umi dev",
+ "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=${PORT:-9102} umi dev",
```

### `apps/doctor/package.json`

```diff
- "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=8003 umi dev",
+ "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=${PORT:-9103} umi dev",
```

### `apps/temp-registration/package.json`

```diff
- "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=8003 umi dev",
+ "dev": "NODE_OPTIONS='--require ./scripts/fix-network.js' HOST=127.0.0.1 PORT=${PORT:-9104} umi dev",
```

### `turbo.json`

4 处 `env` 数组统一添加：
```diff
- "env": ["PROXY_TARGET", "HOST", "PORT"]
+ "env": ["PROXY_TARGET", "HOST", "PORT", "SERVER_PORT"]
```

### proxy 配置 — 默认值 8000 → 9000

各文件中的 `'http://localhost:8000'` 和 `'http://127.0.0.1:8000'` 统一替换为对应新端口。

### `CLAUDE.md` Common Commands 部分

更新端口注释：
- `pnpm dev:admin` — port 9105
- `pnpm dev:patient-h5` — port 9102
- `pnpm dev:doctor` — port 9103
- `pnpm dev:server` — port 9000

补充端口自定义说明：
```
自定义端口:
SERVER_PORT=8000 pnpm dev:server     # 后端用自定义端口
PORT=3000 pnpm dev:admin             # admin 用自定义端口
PROXY_TARGET=http://localhost:8000 pnpm dev:admin  # 代理到自定义后端
```

## 验证

1. 不设环境变量，运行 `pnpm dev:server`，确认监听 9000
2. 不设环境变量，运行 `pnpm dev:admin`，确认监听 9105
3. 设置 `SERVER_PORT=8000` 运行 `pnpm dev:server`，确认监听 8000（向后兼容）
4. 运行 `pnpm dev:server` + `pnpm dev:admin`，确认 admin 页面 API 请求正常代理到 9000
5. `grep -rn "8000" apps/ --include="*.ts" --include="*.tsx"` 确认无遗漏（排除电话号码 13800138000）
