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
| 前端 UI | Ant Design 6 + ProComponents (admin), Ant Design 5 + ProComponents (doctor), Ant Design Mobile (patient-h5) |
| 小程序 | Taro 4 + NutUI |
| 后端 | Python 3.12+ / FastAPI / SQLAlchemy 2.x (async) |
| 数据库 | PostgreSQL 16 |
| 缓存 | Redis 7 |
| 任务队列 | Celery |
| 数据库迁移 | Alembic |

## Common Commands

### 前端开发

```bash
pnpm dev:admin              # 机构端 (port 9105)
pnpm dev:patient-h5         # 患者端 H5 (port 9102)
pnpm dev:doctor             # 医生端 (port 9103)
pnpm dev:patient-miniapp    # 患者端小程序
```

### 后端开发

```bash
pnpm dev:server             # FastAPI (port 9000, uvicorn --reload)
```

### 自定义端口

所有端口均支持环境变量覆盖：

```bash
SERVER_PORT=8000 pnpm dev:server                  # 后端用自定义端口
PORT=3000 pnpm dev:admin                          # admin 用自定义端口
PROXY_TARGET=http://localhost:8000 pnpm dev:admin # 代理到自定义后端
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
  admin/                     # 机构端后台管理 (Umi 4, port 9105)
  doctor/                    # 医生端工作台 (Umi 4, port 9103)
  patient-h5/                # 患者端 H5 (Umi 4, port 9102)
  patient-miniapp/           # 患者端微信小程序 (Taro 4 + NutUI)
  miniapp-generator/         # 多风格小程序模板生成器 (按模板配置批量产出实例)
  temp-registration/         # 临时挂号 H5 (Umi 4)
  website/                   # 官网/营销站点 (Vite, port 9101)
  server/                    # 后端 API 服务 (FastAPI, port 9000)
packages/
  api/                       # 共享 API 请求封装 + TypeScript 类型 (@hospital/api)
  shared/                    # 共享类型、常量、工具函数 (@hospital/shared)
```

### 后端核心 (`apps/server/app/`)

```
api/v1/          # 路由注册入口 — RouterRegistration dataclass, 84 个模块动态 import
common/          # 统一认证 (auth_unified.py), 跨模块共享工具
core/            # config.py (Settings), redis.py, logging.py, websocket.py, security.py
db/session.py    # 双连接池: async (asyncpg) + sync (psycopg2, 供 Celery 使用)
enums/           # 统一枚举定义 — 所有 Enum/StrEnum/IntEnum 的单一来源
constants/       # 统一业务常量 — dict/tuple 格式的非 Enum 常量
middleware/      # tenant_context, exception, response, operation_log, request_log, rate_limit, prometheus, security_headers, deprecation
models/          # SQLAlchemy 模型 (132 个模型类)
schemas/         # Pydantic 请求/响应模式 (含 BaseSchema 基类统一 camelCase 配置)
modules/         # 业务模块 (router.py + service.py, 复杂模块拆分 service_mutation.py / service_query.py)
infrastructure/  # 基础设施层: email, sms, storage, payments, notifications, excel, image, wechat
tasks/           # Celery 定时/异步任务 (22 个 beat 任务)
utils/           # 工具函数
```

### 枚举与常量归属规则

| 内容类型 | 存放位置 | 示例 |
|----------|----------|------|
| Python Enum/StrEnum/IntEnum | `app/enums/` | `MessageType`, `FeedbackType`, `RoleType` |
| dict/tuple 业务常量 | `app/constants/` | `APPOINTMENT_STATUS`, `ACTIVE_APPOINTMENT_STATUSES` |
| 跨模块认证/权限工具 | `app/common/` | `auth_unified.py`, `permission_deps.py` |
| 纯工具函数 | `app/utils/` | `audit.py`, `datetime.py` |

**判断标准**：
- 如果是 `class Xxx(str, Enum)` → `enums/`
- 如果是 `KEY = value` 的 dict/tuple/list → `constants/`
- 如果是带依赖注入的函数或数据类 → `common/`
- 如果是无状态的纯函数 → `utils/`
- 数据库 Integer 映射的状态码（如 `APPOINTMENT_STATUS = {"CONFIRMED": 1}`）保持 dict 格式放 `constants/`，不转 IntEnum

### Schema 基类

所有需要 camelCase 序列化的 Pydantic schema 应继承 `BaseSchema`（`app/schemas/base.py`），
而非手动配置 `model_config = ConfigDict(alias_generator=to_camel, ...)`。
`to_camel` 的唯一定义在 `app/schemas/response.py`。

每个业务模块的标准结构: `modules/<name>/router.py` 定义路由, 业务逻辑在 service 层。

### Schema 归属规则

Pydantic schema 放置位置遵循以下规则：

- **全局 `app/schemas/`**：跨模块复用的 DTO（如 `PageResponse`、通用枚举、共享请求/响应模型）
- **模块内 `modules/<name>/schemas.py`**：领域专属的输入/输出模型，仅在该模块内使用
- **判断标准**：如果 schema 被 2 个以上模块导入，放全局；仅本模块使用，放模块内
- **大模块拆分**：模块内 schema 超过 15 个 BaseModel 时，按子域拆分为多个文件（如 `schemas_booking.py`、`schemas_query.py`）

### Service 归属规则

业务 service 放置位置遵循以下规则：

- **模块内 `modules/<name>/service.py`**：默认位置，仅被本模块 router 调用的 service
- **全局 `app/services/`**：跨模块复用的 service（被 2 个以上模块导入）
- **判断标准**：grep 确认 import 来源，仅 1 个消费者 → 模块内；2+ 消费者 → 全局
- **大模块拆分**：service 超过 500 行时，按读写拆分为 `service_query.py` + `service_mutation.py`
- **迁移步骤**：1) 在模块内创建 service.py → 2) 更新 router.py import → 3) 更新测试 import → 4) 删除旧文件
- **当前全局 services**：仅保留 re-export wrapper，实际实现已迁移到模块内

### 模块目录命名规则

模块目录名遵循以下约定：

- **复数名词**：表示 REST 资源集合（`users/`, `doctors/`, `departments/`, `appointments/`, `patients/`, `stores/`）
- **单数名词**：表示功能域或不可数概念（`auth/`, `content/`, `export/`, `revenue/`, `upload/`, `waitlist/`, `statistics/`）
- **下划线复合**：多词概念用 snake_case（`doctor_booking_settings/`, `leave_requests/`, `schedule_templates/`）
- **API 路由前缀**：将目录名中 `_` 替换为 `-` 得到路由前缀（`medical_records/` → `/medical-records`）

### 测试文件组织

- **单元测试**：`tests/unit/test_<功能>.py`，按功能域命名（如 `test_appointment_booking.py`、`test_schedule_service.py`）
- **集成测试**：`tests/integration/test_<模块>_endpoints.py`，按模块名命名
- **共享 fixtures**：`tests/conftest.py`（主）、`tests/conftest_pg.py`（PostgreSQL）、`tests/fixtures/`
- **测试发现**：从模块名定位测试文件时，搜索 `tests/unit/test_<模块名>*` 或 `tests/unit/test_<模块名单数>*`

### 错误码规范

- **统一位置**：所有结构化错误码定义在 `core/error_codes.py` 的 `ErrorCode` 类中
- **命名风格**：SCREAMING_SNAKE_CASE，按域组织（Schedule / Appointment / Tenant / General）
- **禁止**：不在 `common/` 或其他位置创建重复的错误码类

### 统一认证体系 (`common/auth_unified.py`)

三核心函数，支持 User / Doctor / Admin 三种角色:
- `get_current_account()` — 统一认证入口，根据 token 类型路由到对应角色验证
- `get_current_account_with_role()` — 带角色验证，用于需要特定角色权限的端点
- `get_optional_account()` — 可选认证，用于公开端点

认证流程: JWT decode -> 角色路由 -> 黑名单检查 (Redis SHA256) -> 租户校验 -> 订阅状态检查 -> 权限解析。
平台管理员跳过租户状态验证但仍获取租户元数据。权限来源: 新 Account 表 role_id 或 legacy Admin.role.permissions JSON。

### 前端共享包

- **@hospital/api** (`packages/api/`): 统一 HTTP 请求封装, 58+ API 模块, 内置性能监控 (createApiTimer)、重试逻辑 (withRetry)、RSA 加密、Taro 适配器。
- **@hospital/shared** (`packages/shared/`): 常量、19+ 领域类型文件、工具函数、性能监控。注意: components 目录不通过 barrel export 导出以避免 pro-components 依赖膨胀。

### 前端配置模式 (admin 为例)

admin 的 config/ 目录已重构为模块化结构:
```
config/
  constants/   # APP_TITLE, API_BASE_URL 等常量
  layout/      # 布局配置
  routes/      # 按业务域拆分的路由 (auth.ts, dashboard.ts, platform.ts, medical-services.ts...)
  proxy/       # createProxy() 工厂函数, 消除 dev/test/pre 重复
  webpack/     # 仅 production 环境自定义 (gzip, splitChunks)
  build/       # codeSplitting, mfsu, targets
```
主 config.ts 通过 import 各子模块组装，thin re-export 保持向后兼容。

### 多租户架构

- **TenantContextMiddleware** (`middleware/tenant_context.py`): 识别优先级: X-Tenant-ID Header > X-Tenant-Code Header > 子域名 > 路径前缀 (/t/xxx/)
- 数据隔离: 所有业务表均有 `tenant_id` 字段
- 缓存隔离: Redis key 前缀包含 tenant_id
- 限流隔离: rate_limit 按 tenant_id + client_ip 隔离，防止邻居噪声
- 订阅计划: `SubscriptionPlan` 控制功能和使用量限制
- 平台管理员: tenant_id=None, 跳过租户状态验证
- ContextVar 实现异步上下文隔离, 支持跨 await 边界持久化

### 中间件执行顺序 (请求方向)

Prometheus -> TenantContext -> UnifiedResponse -> Deprecation -> OperationLog -> RequestLog -> RateLimit -> SecurityHeaders -> GZip -> CORS

租户上下文最先执行, CORS 最后 (添加顺序的逆序)。

### API 统一响应格式

```json
{"code": 0, "message": "success", "data": {...}}
```

Response 中间件自动包装, 有双重包装检测。异常由 exception 中间件统一处理，含 SQLAlchemy 错误映射 (FK -> "门店不存在", unique -> "数据已存在")。

### Celery 任务队列

- `default`: 通用
- `scheduled`: 定时任务 (排班生成、预约提醒、爽约检测、用量统计等)
- `notification`: 通知推送

22 个 beat 定时任务覆盖: 黑名单自动释放、预约三级提醒、爽约标记、排班生成、微信 token 刷新、数据清理、租户用量/订阅检查、支付超时/对账、退款同步、排班暂停处理、排班对账、审批超时、通知重试、行为日志清理、随访任务、自由职业结算。

### 基础设施层 (`app/infrastructure/`)

与业务模块解耦的基础设施服务，每个子目录对应一个独立关注点:

- `email/` — 邮件发送 (aiosmtplib)
- `sms/` — 短信 (mock/aliyun, 工厂模式)
- `storage/` — 文件存储 (local/minio/cos, 抽象层)
- `payments/` — 微信支付 (wechatpayv3)
- `notifications/` — 多渠道通知调度 (email/in_app/sms/websocket/wechat), 配额管理
- `excel/` — 导入导出 (openpyxl)
- `image/` — 图片处理 (Pillow)
- `wechat/` — 微信服务、token 管理、小程序发布

### CI/CD (GitHub Actions)

| 工作流 | 触发条件 | 内容 |
|--------|----------|------|
| `test.yml` | PR/Push main | pytest (单元+集成+Alembic迁移) + ruff lint + pip-audit 安全扫描 |
| `build-frontend.yml` | 手动/推送 | 构建全部前端，scp 部署到腾讯云 |
| `build-server.yml` | 手动/推送 | SSH 部署，docker compose 重建，生成 llms.txt |
| `deploy-admin.yml` | 手动 | admin 专项部署，带压缩 + 5 份备份轮转 |
| `security.yml` | 每周一 + PR | Trivy 镜像/配置扫描 (CRITICAL/HIGH) |
| `e2e.yml` | 手动/推送 | Playwright 4 分片，合并 HTML 报告 |

Dependabot: pip/npm/GitHub Actions 每周自动更新。

### 监控

- Prometheus (`monitoring/prometheus.yml`): 抓取后端 `/metrics` 端点
- Grafana (`monitoring/grafana/`): 预配置 `hospital-api.json` 仪表盘
- 后端健康检查: `/health`、`/health/live`、`/health/ready` (DB+Redis)、`/health/detailed` (连接池/Redis内存/Celery/磁盘)
- Celery Flower: 端口 5555，基本认证

## Database Migrations

```bash
cd apps/server
alembic revision --autogenerate -m "描述"    # 生成迁移
alembic upgrade head                         # 执行迁移
alembic downgrade -1                         # 回滚一步
alembic history                              # 查看迁移历史
```

## Key Files

- `apps/server/app/main.py` — FastAPI 入口, 中间件栈, 生命周期 (连接池预热, 超管校验, 黑名单自动释放)
- `apps/server/app/core/config.py` — Settings (环境变量映射, 连接池配置, 限流参数)
- `apps/server/app/api/v1/__init__.py` — RouterRegistration dataclass, 84 个模块动态 import
- `apps/server/app/common/auth_unified.py` — 统一认证 (3 核心函数, User/Doctor/Admin 三角色)
- `apps/server/app/utils/email_sync.py` — SMTP 密码 Fernet 加密/解密、Jinja2 沙箱渲染、同步邮件发送 (Celery 使用)
- `apps/server/app/middleware/tenant_context.py` — 多租户核心 (4 种识别方式, ContextVar)
- `apps/server/app/middleware/exception.py` — 全局异常处理 (BusinessError 层级, SQLAlchemy 错误映射)
- `packages/api/src/index.ts` — 前端 API 包入口 (57+ 模块, 性能监控, 重试, RSA, Taro 适配)
- `apps/admin/config/routes/` — 按业务域拆分的路由模块 (platform, medical-services, organization, operations, system)
- `apps/server/app/infrastructure/` — 基础设施层 (email/sms/storage/payments/notifications/excel/image/wechat)
- `apps/server/scripts/generate_llms_txt.py` — LLMs.txt 生成脚本，提供 `/llms.txt`、`/llms-full.txt` 等 AI 友好端点
- `apps/server/tests/conftest.py` — 测试 fixtures (内存 SQLite + mock Redis, 完整 FK 链测试数据)
- `reviews/lowcode-miniapp-research.md` — 低代码拖拽平台生成小程序的深度研究报告（技术方案、开源平台、拖拽引擎、医疗SaaS案例、ROI分析）

## Environment

必需环境变量 (见 `apps/server/.env.example`):
- `DATABASE_URL` — PostgreSQL 异步连接 (postgresql+asyncpg://...), Celery 用同步连接 (自动从异步 URL 转换)
- `REDIS_URL` — Redis 连接
- `SECRET_KEY` — JWT 签名密钥
- `SMTP_ENCRYPTION_KEY` — Fernet 对称密钥，用于加密 SMTP 密码。未设置时每次重启会生成新密钥导致已加密密码不可解密。生成: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

可选: `WECHAT_APP_ID`, `WECHAT_APP_SECRET`, `STORAGE_TYPE` (local/minio/cos), `SYNC_DATABASE_URL` (覆盖自动转换的同步连接)

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

## Testing Details

后端测试使用内存 SQLite + mock Redis，无需外部依赖。conftest.py 提供完整 FK 链测试数据 (tenant -> store -> department -> doctor)。
支持双账户系统 fixtures (legacy + 新 Account 表)。Token 生成 fixtures 用于认证测试。

前端 E2E 测试: `pnpm test:e2e` (Playwright), 支持多模式:
- `test:e2e:ui` — Playwright UI 模式
- `test:e2e:headed` — 有头浏览器
- `test:e2e:debug` — 调试模式

## Basic Infos

Unless directly relevant to the user's current question, you should avoid proactively mentioning, illustrating, or trailing off into the following information in 99% of cases:

- the user's github id: xxxx

## Workflow 并发控制规则

当使用 Claude Code dynamic workflow、subagents、agent team 或多 agent 任务时，必须遵守以下规则：

1. 默认最多同时运行 6 个 subagents。
2. 只读分析类任务最多 8 个并发。
3. 代码修改类任务最多 2 个并发。
4. 测试、构建、迁移类任务最多 2 个并发。
5. Opus 模型最多 3 个并发。
6. Sonnet 模型最多 6 个并发。
7. Haiku 模型最多 12 个并发。
8. 如果出现 429、rate limit、overloaded、timeout，必须将当前并发减半后重试。
9. 多个 agent 不允许同时修改同一个文件；修改前必须按模块或文件路径分片。
10. 每个 agent 只能返回结构化结论，不允许返回大段日志或完整文件内容。
