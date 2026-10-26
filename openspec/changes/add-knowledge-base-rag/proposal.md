# Change: 新增机构知识库（文档管理 + RAG 语义检索）

## Why
机构日常依赖大量非结构化资料——制度规范、SOP、药品说明、培训材料、医保政策——目前散落在个人电脑与聊天记录里，无法按目录沉淀、无法在同事间受控共享，更无法"按意思找"。本变更在现有 admin 端（web + Tauri 桌面壳同一套产物）内新增**机构知识库**能力：上传多类型文档 → 后台自动解析/切片/向量化（"学习"）→ 语义检索并给出可点开的引用来源；资料按目录管理，可受权限约束地分享给同事，处理失败可一键重新发起。

选型结论（2026-10-26 定案，详见 design.md）：**知识库本体放服务端**，桌面壳只是消费者。原因：分享/权限/学习状态/失败重试全是多用户服务端能力，本地知识库与这些需求天然矛盾。向量存储用 **PostgreSQL + pgvector**（生产 PG 18.0 已于 2026-10-26 安装 pgvector 0.8.7 并验证通过），解析/向量化走 **Celery 独立队列**，embedding 走**国内厂商 API**（生产机 3.6G 内存，已用 swap，自托管模型不可行）。不引入 Dify/RAGFlow 等平台：现有 PG/Redis/Celery/RBAC/多租户全部可直接复用，租户隔离握在自己手里。

## What Changes
- 新增后端模块 `apps/server/app/modules/knowledge/`（router + router_documents / service + service_documents + service_base + service_access + service_search / pipeline / chunker / schemas / exceptions），5 张表：`knowledge_bases`、`knowledge_folders`、`knowledge_documents`、`knowledge_chunks`（`vector(1024)` + HNSW 余弦索引）、`knowledge_shares`，全部挂 `TenantMixin`。
- 新增 Celery 任务 `app/tasks/knowledge_task.py`（`process_document`：解析 → 切片 → 向量化，状态机 pending→parsing→embedding→ready/failed，幂等可重试），新增队列 `knowledge` 与 compose 服务 `celery_knowledge_worker`（`-c 1`、磁盘 scratch 卷）。
- 新增 embedding 提供方抽象 `app/infrastructure/embedding/`（首个实现：智谱 `embedding-3`，1024 维；查询与文档共用同一模型/维度，库上记录模型指纹）。
- 新增文档解析器 `app/infrastructure/document_parser/`：PDF（pypdf）、DOCX（python-docx）、XLSX（openpyxl，已有依赖）、TXT/MD；无文本层 PDF 明确失败并给出原因。
- 新增权限码 6 个：`knowledge:read` / `knowledge:create` / `knowledge:update` / `knowledge:delete` / `knowledge:share` / `knowledge:manage`，登记 `common/role_permissions.py` + `scripts/init_permissions.py`（过 CI `gen_permission_matrix.py --check` 门禁，`docs/modules/permission-codes.md` 重新生成）。
- 新增 API：知识库/目录/文档 CRUD、上传、重试、共享授权、`POST /knowledge/search` 语义检索（返回带引用来源的命中）、原件下载（租户 + 可见性校验）。
- 新增前端：`packages/api/src/modules/knowledge.ts`；`apps/admin/src/pages/knowledge/`（知识库列表、目录树 + 文档表 + 拖拽上传 + 学习状态徽标 + 重试、共享弹窗、检索页 + 引用面板 + 预览抽屉）；路由与 `access` 接入。
- Alembic 迁移：建表 + `CREATE EXTENSION IF NOT EXISTS vector`（幂等；生产已存在）。
- 部署：compose 新增 knowledge worker；`.env` 新增 `KB_*` / `ZHIPU_API_KEY`；nginx 上传路径 `client_max_body_size 60m`；CI/测试 PG 镜像切换为 `pgvector/pgvector:pg18`；文档中 PostgreSQL 版本由 16 更正为 18。

## Design Principles
- **服务端为真相源**：共享、权限、处理状态只存在于服务端；桌面壳零改动，经 `desktop.baseUrl` 直接可用。
- **复用优先**：租户隔离（`TenantMixin` + `tenant_context`）、RBAC 权限码、`get_storage()` 存储抽象、Celery 基础设施全部复用，不引入新中间件。
- **资源有界**：独立队列 + 单并发 worker + 文件大小上限 + 磁盘临时目录，任何一份"坏文档"都不能影响挂号核心业务容器。
- **可见即可检**：检索范围严格等于调用者可见的知识库集合，在 SQL 层过滤，不在应用层事后裁剪。
- **引用可追溯**：每个 chunk 保留页码/章节/序号，命中结果必须能点回原文位置。

## Scope

### In Scope
- `apps/server`：`modules/knowledge/`、`models/knowledge.py`、`enums/knowledge.py`、`tasks/knowledge_task.py`、`infrastructure/embedding/`、`infrastructure/document_parser/`、`common/role_permissions.py`、`scripts/init_permissions.py`、`celery_app.py`（队列 + 路由 + autodiscover）、`core/config.py`（`KB_*` 配置）、`api/v1/__init__.py`（路由注册）、Alembic 迁移、`tests/conftest.py` / `conftest_pg.py`（PG 下先建 vector 扩展）、pytest。
- `packages/api/src/modules/knowledge.ts` + `index.ts` 导出。
- `apps/admin`：`src/pages/knowledge/**`、`config/routes.ts`、`src/access.ts`、菜单入口。
- `docker-compose.yml`（knowledge worker）、`.env.example`、`docs/deployment-baota-docker.md`（pgvector 安装步骤 + PG 版本更正）、`.github/workflows/test.yml`（PG 服务镜像）。

### Out of Scope（独立后续 change）
- **AI 问答生成**（基于检索结果用 LLM 生成带引用的回答）：`add-knowledge-qa-generation`。本变更只交付检索 + 引用，不生成回答。
- **MCP 暴露**（把知识库封装成 MCP server 供 Agent 调用）：`add-knowledge-mcp-server`。
- **Tauri 本地/离线知识库**（LanceDB + 本地 embedding）：仅在出现离线或隐私隔离需求时另立。
- OCR / 扫描件识别、PPTX 解析、混合检索（zhparser/pg_trgm 全文，生产 PG 未编 contrib）、doctor 端接入、按租户的存储配额计费。
- 自托管 embedding 模型（受生产 3.6G 内存约束，待升配后评估）。

## Impact
- Affected specs: `knowledge-base` (new)、`knowledge-retrieval` (new)
- Affected code:
  - `apps/server/app/modules/knowledge/**`、`apps/server/app/models/knowledge.py`、`apps/server/app/enums/knowledge.py`、`apps/server/app/tasks/knowledge_task.py` (new)
  - `apps/server/app/infrastructure/{embedding,document_parser}/**` (new)
  - `apps/server/app/common/role_permissions.py`、`apps/server/scripts/init_permissions.py`、`apps/server/app/celery_app.py`、`apps/server/app/core/config.py`、`apps/server/app/api/v1/__init__.py`、`apps/server/tests/conftest.py`、`apps/server/tests/conftest_pg.py`
  - `apps/server/migrations/versions/kb01_knowledge_base.py` (new)、`apps/server/requirements.txt`（pypdf、python-docx、pgvector）
  - `packages/api/src/modules/knowledge.ts` (new)、`packages/api/src/index.ts`
  - `apps/admin/src/pages/knowledge/**` (new)、`apps/admin/config/routes.ts`、`apps/admin/src/access.ts`
  - `docker-compose.yml`、`apps/server/.env.example`、`.github/workflows/test.yml`、`docs/deployment-baota-docker.md`、`docs/modules/knowledge.md`、`docs/modules/permission-codes.md`（生成）
- 生产环境前置（已于 2026-10-26 完成，见 tasks.md 阶段 0）：Docker 垃圾清理（磁盘 11G→17G 可用）、pgvector 0.8.7 编译安装并在 `hospital_booking` 建扩展。

## Verification
- `cd apps/server && pytest tests/test_knowledge*.py`（切片、状态机、访问控制、检索范围；需 pgvector 测试库）
- `cd apps/server && python scripts/gen_permission_matrix.py --check`（权限码登记门禁）
- `pnpm --filter @hospital/api run test`、`pnpm --filter @hospital/admin run build`
- 生产冒烟（部署后）：上传一份 PDF → 状态到 ready → 检索命中 → 点击引用定位到页；上传扫描件 → failed 且原因可读 → 重试仍 failed（预期）；用无权限账号检索 → 不含他人私有库内容。
