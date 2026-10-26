# Implementation Tasks: add-knowledge-base-rag

## 阶段 0：生产环境前置（2026-10-26 已执行）

- [x] 0.1 生产 Docker 垃圾清理：删除 3 个被取代的中间构建、7 个月前旧项目镜像、pg16/redis/minio 未用镜像，构建缓存 `--keep-storage=2GB` 修剪；磁盘可用 11G → 17G（73% → 58%），四容器全程 healthy
- [x] 0.2 镜像 tag 对齐：运行中镜像 `786c2d159430` 重新打为 `hospital_backend:latest` 与 `deployed-20261026`；01:51 无 ARG 的胖构建改名 `hospital_backend:stray-chromium-20261026` 保留待处置（**未删除，由用户决定**）
- [x] 0.3 pgvector 0.8.7 源码由本地 scp 上传，`make PG_CONFIG=/www/server/pgsql/bin/pg_config && make install`（PG 18.0），`hospital_booking` 执行 `CREATE EXTENSION vector`
- [x] 0.4 冒烟验证：HNSW 余弦索引建立、最近邻查询正确、halfvec/sparsevec 类型存在、业务用户 `hospital` 可用 vector 类型
- [x] 0.5 compose 新增 `celery_knowledge_worker`（`-Q knowledge -c 1 --max-tasks-per-child=20 --max-memory-per-child=400000`，挂 `./apps/server/var/kb-tmp:/app/kb-tmp`，与现有四容器同样的 `read_only`/`security_opt`/`extra_hosts`）
- [ ] 0.6 nginx：知识库上传路径 `client_max_body_size 60m`（宝塔站点配置；随 6.3 生产部署执行）
- [x] 0.7 `.env.example` 与生产 `.env`：`KB_ENABLED=false`、`KB_EMBEDDING_PROVIDER=zhipu`、`KB_EMBEDDING_MODEL=embedding-3`、`KB_EMBEDDING_DIMS=1024`、`ZHIPU_API_KEY`、`KB_MAX_FILE_MB=50`、`KB_TMP_DIR=/app/kb-tmp`
- [x] 0.8 `.github/workflows/test.yml`：PostgreSQL service 镜像切换为 `pgvector/pgvector:pg18`，确保迁移在 CI 可执行

## 阶段 1：数据模型与迁移（apps/server）

- [x] 1.1 `app/enums/knowledge.py`：`KnowledgeDocStatus`（pending/parsing/embedding/ready/failed）、`KnowledgeVisibility`（private/tenant）、`KnowledgeShareGrantee`（admin/role）、`KnowledgeSharePermission`（read/edit）
- [x] 1.2 `app/models/knowledge.py`：`KnowledgeBase`、`KnowledgeFolder`、`KnowledgeDocument`、`KnowledgeChunk`（`pgvector.sqlalchemy.Vector(1024)`）、`KnowledgeShare`，全部 `TenantMixin + AuditMixin`，约束与索引按 design D6
- [x] 1.3 `requirements.txt`：`pgvector`（SQLAlchemy 类型）、`pypdf`、`python-docx`（openpyxl 已有）
- [x] 1.4 Alembic `kb01_knowledge_base.py`：`CREATE EXTENSION IF NOT EXISTS vector` → 建 5 表 → `SET LOCAL maintenance_work_mem='256MB'` 后建 HNSW(`vector_cosine_ops`, m=16, ef_construction=64) + btree 索引；downgrade 只删表不卸扩展
- [x] 1.5 本地 `alembic upgrade head` / `downgrade -1` 往返验证（本地 PG 需 pgvector）

## 阶段 2：基础设施（embedding / 解析 / 存储）

- [x] 2.1 `app/infrastructure/embedding/base.py`：`BaseEmbeddingProvider.embed(texts) -> list[list[float]]`、`model_name`、`dims`；`get_embedding_provider()` 按 `KB_EMBEDDING_PROVIDER` 装配
- [x] 2.2 `app/infrastructure/embedding/zhipu.py`：智谱 `embedding-3`，`dimensions=1024`，批量 ≤ 64，httpx 超时 30s，429/5xx 抛 `EmbeddingRetryableError`，其余抛 `EmbeddingError`；日志只记次数/类别
- [x] 2.3 `app/infrastructure/document_parser/`：`base.py`（`Block(text, page_no, section)`）、`pdf.py`（pypdf 逐页；全文为空 → `ParseError("PDF 无文本层（疑似扫描件），暂不支持 OCR")`）、`docx.py`、`xlsx.py`、`text.py`；`get_parser(mime_type)`
- [x] 2.4 `app/modules/knowledge/chunker.py`：按段落聚合至 `KB_CHUNK_CHARS=800`、重叠 `KB_CHUNK_OVERLAP=80`，保留 `page_no/section/seq`
- [x] 2.5 存储 key 规范 `knowledge/{tenant_id}/{kb_id}/{doc_id}/{file_name}`，复用 `get_storage()`；临时文件统一写 `KB_TMP_DIR` 并 `finally` 清理

## 阶段 3：处理管线（Celery）

- [x] 3.1 `celery_app.py`：`Queue("knowledge")` + `task_routes["app.tasks.knowledge_task.*"] = {"queue": "knowledge"}`；现有 worker `-Q` 不变
- [x] 3.2 `app/tasks/knowledge_task.py::process_document(doc_id)`：开头清旧切片 → `parsing`（解析 + 切片，落 `page_count`）→ `embedding`（分批向量化，校验维度 = 库 `embedding_dims`）→ 写 `knowledge_chunks` → `ready`（落 `chunk_count/processed_at`）；任一阶段异常置 `failed(failed_stage, error_message)`；`EmbeddingRetryableError` 走 `self.retry(max_retries=3, 指数退避)`
- [x] 3.3 `KnowledgeService.retry_document()`：仅 `failed` 可重试（否则 409），置 `pending` 并投递
- [x] 3.4 文档删除：删切片 → 删原件（storage）→ 删记录；知识库删除级联目录/文档/共享

## 阶段 4：API 与权限

- [x] 4.1 权限码登记：`common/role_permissions.py` 新增 `ADMIN_KNOWLEDGE_PERMISSIONS`（6 码）、`seed/init_permissions.py` 登记；`python scripts/gen_permission_matrix.py --check` 通过
- [x] 4.2 `app/modules/knowledge/service_access.py`：`visible_kb_ids(admin)` 单查询（自有 ∪ tenant 公共 ∪ shares 命中 admin/角色 ∪ manage 全部）、`assert_can(admin, kb, action)`（owner/manage/edit/read 矩阵按 design D7）
- [x] 4.3 `router.py`：知识库 CRUD、目录 CRUD/移动、文档列表（含状态）、上传（类型/大小校验 → 存储 → `pending` → 投递）、删除、重试、共享增/删/列、下载 `GET /knowledge/files/{key:path}`（租户 + 可见性校验，参考 `modules/upload/router.py` 现有写法）
- [x] 4.4 `POST /knowledge/search`：`knowledge:read` → `visible` 交集校验（不可见 → 403）→ 模型/维度一致性校验（不一致 → 409 `KB_EMBEDDING_MISMATCH`）→ embed(query)（失败 → 503 `KB_EMBEDDING_UNAVAILABLE`）→ `SET LOCAL hnsw.ef_search=100` + 单条 SQL（design D8）→ 组装带 `preview_url` 的命中；`top_k` 越界 → 400
- [x] 4.5 `schemas.py`：请求/响应 Pydantic 模型；`api/v1/__init__.py` 注册路由，`KB_ENABLED=false` 时路由返回 404
- [x] 4.6 pytest：`tests/test_knowledge_access.py`（可见性矩阵、跨租户 404、共享/撤销）、`tests/test_knowledge_pipeline.py`（状态机、幂等重试、扫描件失败、维度不匹配）、`tests/test_knowledge_search.py`（范围过滤、403/409/503、字段完整）、`tests/test_knowledge_chunker.py`

## 阶段 5：前端（packages/api + apps/admin）

- [x] 5.1 `packages/api/src/modules/knowledge.ts`：类型 + 函数（列表/详情/目录/上传/重试/共享/检索/下载 URL），`index.ts` 导出；vitest 覆盖参数拼装
- [x] 5.2 `apps/admin/src/pages/knowledge/index.tsx`：知识库列表（我的 / 共享给我 / 租户公共），新建弹窗
- [x] 5.3 `pages/knowledge/detail/`：目录树 + `ProTable` 文档表（状态徽标、失败原因、重试按钮）+ `Upload.Dragger`（类型/大小前端预校验、固定合规提示）；处理中以 react-query `refetchInterval` 轮询，全部终态后停止
- [x] 5.4 `pages/knowledge/search/`：检索框 + 结果列表（片段、来源、页码、分数）+ 预览抽屉（PDF `#page=N` 定位；非 PDF 显示抽取文本 + 原件下载）；409/503 友好提示
- [x] 5.5 `ShareModal`：选同事/角色 + read/edit，撤销
- [x] 5.6 `config/routes.ts` + `src/access.ts` + 菜单：`knowledge:read` 控入口，`create/share/manage/update/delete` 控按钮
- [x] 5.7 `pnpm --filter @hospital/admin run build` 通过（tsc/eslint 亦通过）；桌面壳目验属人工冒烟，随 6.4 一并执行（无 Tauri 侧改动）

## 阶段 6：文档、部署与验证

- [x] 6.1 `docs/deployment-baota-docker.md`：新增「pgvector 安装（PG 18，源码编译步骤与 PG 升级后重编说明）」章节；`docs/{deployment-baota-docker,architecture,tech-stack,PRD,deployment}.md` 与 `openspec/project.md` 中 PostgreSQL 版本由 16 更正为 18
- [x] 6.2 `docs/modules/knowledge.md`：数据模型、状态机、权限矩阵、配置项、运维（队列/内存/失败率观测）
- [ ] 6.3 生产部署：迁移 → 权限 seed → compose `up -d --build` 拉起 knowledge worker → `KB_ENABLED=false` 先上 → 单租户灰度开启
- [ ] 6.4 生产冒烟（proposal Verification）：PDF 上传→ready→检索→引用定位；扫描件 failed + 原因 + 重试；无权限账号检索不含他人私有库；`EXPLAIN` 确认走 HNSW
- [ ] 6.5 观测一周：knowledge worker 内存峰值、`failed_stage` 分布、embedding 调用量/费用；据此决定 OCR / 配额 / 升配
