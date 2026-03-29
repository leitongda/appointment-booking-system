# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Defaults

- Reply in **Chinese** unless I explicitly ask for English.
- No emojis.
- Do not truncate important outputs (logs, diffs, stack traces, commands,
  or critical reasoning that affects safety/correctness).

## Project Overview

全栈医院预约挂号系统，SaaS 多租户架构。支持多门店/分院、多科室、多医生排班预约。

## Tech Stack

| 层 | 技术 |
|---|---|
| Monorepo | pnpm 10 + Turbo 2 |
| 前端 (admin/doctor/patient-h5) | React 18 + TypeScript + Umi 4 |
| 前端 UI | Ant Design 5 + ProComponents (admin/doctor), Ant Design Mobile (patient-h5) |
| 小程序 | Taro 3 + NutUI |
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy 2.x (async) |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 任务队列 | Celery |
| 数据库迁移 | Alembic |

## Common Commands

### 前端开发

```bash
pnpm dev:admin              # 机构端 (port 8005)
pnpm dev:patient-h5         # 患者端 H5 (port 8002)
pnpm dev:doctor             # 医生端 (port 8003)
pnpm dev:patient-miniapp    # 患者端小程序
```

### 后端开发

```bash
pnpm dev:server             # FastAPI (port 8000, uvicorn --reload)
```

后端依赖安装: `cd apps/server && pip install -r requirements.txt`

### 构建

```bash
pnpm build                  # 全部构建
pnpm build:admin            # 仅机构端
```

### 测试

后端测试 (pytest + pytest-asyncio, 内存 SQLite):

```bash
cd apps/server
pytest                              # 全部测试
pytest tests/unit/                  # 仅单元测试
pytest tests/unit/test_family_member.py -v   # 单个文件
pytest -k "test_create" -v          # 按名称匹配
pytest -m unit                      # 按 marker 过滤
```

测试标记: `unit` (无外部依赖), `integration` (需 DB/Redis), `slow`

前端测试: `pnpm test` (Vitest, admin 端)

### Lint

```bash
pnpm lint                  # Turbo 驱动的全项目 lint
```

### 基础设施

```bash
docker-compose up -d postgres redis   # 启动数据库和缓存
```

## Architecture

### Monorepo 结构

```
apps/
  admin/                # 机构端后台管理 (Umi 4)
  patient-h5/           # 患者端 H5 (Umi 4)
  patient-miniapp/      # 患者端微信小程序 (Taro 3)
  doctor/               # 医生端工作台 (Umi 4)
  mini-appointment-miniapp/  # 临时挂号小程序 (独立 Taro 项目)
  temp-registration/    # 临时挂号 H5 (Umi 4)
  server/               # 后端 API 服务 (FastAPI)
packages/
  api/                  # 共享 API 请求封装 + TypeScript 类型定义
  shared/               # 共享组件、常量、工具函数
```

### 后端核心 (`apps/server/app/`)

```
api/v1/          # 路由注册入口，按模块 include 子路由
core/            # config.py (Settings), redis.py, logging.py, websocket.py
db/session.py    # 异步/同步 SQLAlchemy session 工厂
middleware/      # tenant_context, rate_limit, operation_log, request_log, response, exception
models/          # SQLAlchemy 模型 (40+ 表)
schemas/         # Pydantic 请求/响应模式
modules/         # 业务模块 (每个模块通常含 router.py, service.py, 有时含 service_mutation.py, service_query.py)
tasks/           # Celery 定时/异步任务
utils/           # 工具函数
```

每个业务模块的标准结构: `modules/<name>/router.py` 定义路由, 业务逻辑在 service 层。

### 前端共享包 (`packages/api/`)

统一的 HTTP 请求封装，导出 40+ API 模块和 TypeScript 类型。前端项目通过 `@hospital/api` 引用。

### 多租户架构

- **TenantContextMiddleware** (`middleware/tenant_context.py`): 通过 `X-Tenant-ID`/`X-Tenant-Code` Header 或子域名/路径前缀识别租户，使用 `ContextVar` 实现异步上下文隔离
- 数据隔离: 所有业务表均有 `tenant_id` 字段
- 缓存隔离: Redis key 前缀包含 tenant_id
- 订阅计划: `SubscriptionPlan` 控制功能和使用量限制

### 中间件执行顺序 (FastAPI, 添加顺序 = 执行顺序的逆)

CORS -> RateLimit -> RequestLog -> OperationLog -> UnifiedResponse -> TenantContext

### API 统一响应格式

```json
{"code": 0, "message": "success", "data": {...}}
```

### Celery 任务队列

- `default`: 通用
- `scheduled`: 定时任务 (排班生成、预约提醒、爽约检测、用量统计等)
- `notification`: 通知推送

## Key Files

- `apps/server/app/main.py` — FastAPI 应用入口，中间件配置，生命周期
- `apps/server/app/core/config.py` — Settings (环境变量映射)
- `apps/server/app/api/v1/__init__.py` — 路由注册
- `apps/server/app/middleware/tenant_context.py` — 多租户核心
- `packages/api/src/index.ts` — 前端 API 包入口
- `apps/server/tests/conftest.py` — 测试 fixtures (内存 SQLite + mock Redis)

## Environment

必需环境变量 (见 `apps/server/.env.example`):
- `DATABASE_URL` — PostgreSQL 异步连接 (postgresql+asyncpg://...)
- `REDIS_URL` — Redis 连接
- `SECRET_KEY` — JWT 签名密钥

可选: `WECHAT_APP_ID`, `WECHAT_APP_SECRET`, `STORAGE_TYPE` (local/minio/cos)

## Refactor policy (legacy code)

- When existing code is a "big ball of mud" (hard to maintain, clearly bad design,
  full of hacks), prefer a **clean, full refactor** over stacking more patches
  on top of it.
- A refactor may completely replace internal structure
  (functions, modules, classes, data flow).
- By default, try to preserve externally observable behaviour.
  If you intentionally change behaviour or protocols, you MUST:
  - Call out clearly that this is a **behaviour/protocol change**.
  - Explain why the change is necessary and which code paths/consumers are affected.
  - Update or add tests to cover the new behaviour.

## Before touching code (mandatory)

Find reuse opportunities + Trace the call/dependency chain and impact radius:

- Use semantic code search first via `codebase-retrieval` tool.
- Confirm understanding with LSP: `goToDefinition`, `findReferences`.
- Use Grep/Glob for verifying and understanding additional code snippets.

## Red lines

- No copy-paste duplication.
- Do not break existing externally observable behaviour **unless**:
  - It is part of a deliberate refactor as described in the refactor policy, and
  - You clearly document the behavioural change and its impact.
- Do not proceed with a known-wrong approach.
- Critical paths must have explicit error handling.
- Never implement "blindly": always confirm understanding via code reading + references.

## Web research (no guessing)

If something is unfamiliar or likely version-sensitive, you MUST search the web instead of guessing:

- Use Exa: `mcp__exa__web_search_exa`.

Source priority:

1. Official docs / API reference.
2. Official changelog / release notes.
3. Upstream GitHub repository docs (README, `/docs`).
4. Community posts only if necessary to fill gaps.

Version rule:

- When behaviour may differ across versions, first identify the project's version (lockfile/config),
  then search docs specifically for that version.

## Task sizing

- **Simple**
- Criteria — single file, clear requirement, < 20 lines changed,
  clearly local impact.
- Handling — after doing the "Before touching code" steps
  (research + impact analysis + internal three-question checklist),
  you may execute directly with minimal explanation.
- A very short context line is enough;
  a full breakdown of the checklist is not required.

- **Medium**
  - Criteria — 2–5 files, or requires some research, or impact is not obviously local.
  - Handling — write a short plan (bullet points) → then implement.
  - Briefly surface the checklist result in the reply
    (1–3 short lines describing real issue, key reuse, and main impact).

- **Complex**
  - Criteria — architecture changes, multiple modules, high uncertainty or risk.
  - Handling — follow this workflow:
    1. **RESEARCH**: inspect code and facts only (no proposals yet).
    2. **PLAN**: present options + tradeoffs + recommendation;
       use `AskUserQuestion` actively to align with the user;
       wait for user's confirmation.
    3. **EXECUTE**: implement exactly the approved plan.
    4. **REVIEW**: self-check (tests, edge cases, cleanup).

## Git

- Do not commit unless I explicitly ask.
- Do not push unless I explicitly ask.
- Before writing a commit message, glance at a few recent commits and match the repo's style:
  - `git log -n 5 --oneline`
- If there is no obvious existing style, use this default format:
  - `<type>(<scope>): <description>`
- Before any commit: run `git diff` and confirm the exact scope of changes.
- Never force-push to `main` / `master` unless the user approves.
- Do not add attribution lines in commit messages.

## Security

- Never hardcode secrets (keys/passwords/tokens).
- Never commit `.env` files or any credentials.
- Validate user input at trust boundaries (APIs, CLIs, external data sources).

## Quality & cleanup

- Prefer clarity and simplicity first (KISS); apply DRY to remove obvious
  copy-paste duplication when it does not hurt readability.
- If you change a function signature, update **all** call sites.
- After changes:
  - Remove temporary files.
  - Remove dead/commented-out code.
  - Remove unused imports.
  - Remove debug logging that is no longer needed.
- Run the smallest meaningful verification (lint/test/build) for the parts you touched.

## Windows / PowerShell (if used)

- PowerShell does not support `&&`; use `;` to chain commands.
- Quote paths that contain spaces or non-ASCII characters.

## Baisc Infos

Unless directly relevant to the user's current question, you should avoid proactively mentioning, illustrating, or trailing off into the following information in 99% of cases:

- the user's github id: xxxx
