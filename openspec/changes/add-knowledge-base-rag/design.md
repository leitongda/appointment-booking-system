# Design: add-knowledge-base-rag

## Context

**生产环境实测（2026-10-26）**，所有决策都受它约束：

| 项 | 实测 | 对设计的影响 |
|---|---|---|
| 机器 | 腾讯云 OpenCloudOS 9.4，4 核 / 3.6G 内存 / 1G swap（已用 322M）/ 40G 盘 | 内存是唯一硬约束：不能跑本地 embedding 模型；处理任务必须单并发、有上限 |
| 部署形态 | 宝塔混合：PG 18.0、Redis 7 装在宿主机；Docker 只跑 backend / celery_worker(-c 4, default,scheduled,notification) / beat / flower，四容器均 `read_only: true`，`/tmp` 与 `/app/var`(64m) 为 tmpfs | tmpfs 占的是内存 → 大文件解析不能用 `/tmp`；要挂磁盘 scratch 卷 |
| 存储 | `STORAGE_TYPE=local`，`./apps/server/uploads` bind mount；MinIO 未上生产 | 原件走 `get_storage()` 抽象，生产落本地盘，不新增组件 |
| PostgreSQL | 18.0（宝塔源码编译，**非文档所写 16**）；contrib 未编（无 pg_trgm）；`shared_buffers=128MB`、`maintenance_work_mem=64MB`；pgvector **0.8.7 已编译安装**，`hospital_booking` 已 `CREATE EXTENSION vector`，HNSW/halfvec 验证通过，业务用户 `hospital` 可用 | 向量库零新增组件；全文检索（zhparser）不在本期；HNSW 建索引前需会话级提高 `maintenance_work_mem` |
| 业务规模 | 业务库 26MB、uploads 496K、负载 0.03 | 现有业务极轻，知识库是增量主用户 |
| 出网 | github.com HTTPS 可达但 git smart-HTTP 常卡死；国内镜像快 | 依赖安装用 pip 国内源；pgvector 源码由本地 scp 上传 |

**客户端形态**：admin 已有 Tauri 2 桌面壳（`add-admin-tauri-desktop-shell`），壳只是 React 产物的发布形态，经 `desktop.baseUrl` 打后端。知识库功能落在 admin 页面即同时覆盖 web 与桌面，**Tauri 侧零改动**。

**干系人**：机构管理员/运营（上传、整理、分享）、机构内其他管理员（检索、阅读被共享资料）、平台方（租户隔离、合规、成本）。

## Goals / Non-Goals

- Goals
  - 上传 PDF / DOCX / XLSX / TXT / MD，后台自动"学习"（解析 → 切片 → 向量化），状态全程可见，失败可重试。
  - 按知识库 → 目录树组织；可分享给同事（按人或按角色，只读/可编辑）；`knowledge:manage` 可治理租户内全部知识库。
  - 语义检索，命中结果带可点开定位的引用来源（文档、页码/章节、片段）。
  - 严格租户隔离；检索范围 = 调用者可见库集合，在 SQL 层过滤。
  - 任何"坏文档"不影响挂号核心业务容器（资源有界）。
- Non-Goals（见 proposal Out of Scope）
  - LLM 回答生成、MCP 暴露、本地/离线库、OCR、混合全文检索、自托管 embedding、doctor 端。

## Decisions

### D1. 知识库放服务端，桌面壳零改动
- 决策：知识库本体（文档、向量、权限、状态）全部在 `apps/server`；admin 新增页面；Tauri 不加插件、不改 Rust。
- 理由：分享/权限/学习状态/重试都是多用户服务端语义；桌面壳已通过 `desktop.baseUrl` 打通后端；一份实现同时服务 web 与桌面。
- 备选：Tauri 本地库（LanceDB + 本地 ONNX embedding）——与共享/权限需求矛盾，每台机器复制一份权限模型，否决；作为未来离线补充另立 change。

### D2. 向量存储：PostgreSQL + pgvector（同库）
- 决策：`knowledge_chunks.embedding vector(1024)`，HNSW 索引 `vector_cosine_ops (m=16, ef_construction=64)`，与业务表同在 `hospital_booking`。
- 理由：零新增组件；事务内同时写元数据与向量；租户/可见性过滤与向量检索在同一条 SQL 内完成（`WHERE kb_id = ANY(:visible) ORDER BY embedding <=> :q LIMIT k`）。
- 备选：Qdrant/Milvus 容器——多吃 150M+ 内存且要同步两套数据，否决；独立 pgvector 容器——仅作宿主机 PG 不可用时的退路。
- 细节：
  - 维度定 1024：质量/存储折中（10 万 chunk ≈ 400M 表 + ~600M 索引）。`knowledge_bases` 记录 `embedding_model` / `embedding_dims`，模型切换 = 整库重建，禁止混维。
  - 建索引：迁移中 `SET LOCAL maintenance_work_mem = '256MB'` 再 `CREATE INDEX`；HNSW 支持增量插入，后续写入不需重建。
  - 检索会话 `SET LOCAL hnsw.ef_search = 100`（默认 40，召回优先）。
  - pgvector 版本钉 0.8.7；PG 大版本升级时需按 `docs/deployment-baota-docker.md` 新增章节重编。

### D3. Embedding：国内厂商 OpenAI 兼容 API，预设可切换
- 决策：`app/infrastructure/embedding/{base.py, openai_compatible.py, __init__.py}`，`BaseEmbeddingProvider.embed(texts) -> list[list[float]]`；唯一实现 `OpenAICompatibleEmbeddingProvider`（POST `{base_url}/embeddings`，Bearer 鉴权，可选 `dimensions` 参数）。`KB_EMBEDDING_PROVIDER` 预设：`siliconflow`（硅基流动 `BAAI/bge-m3`，免费，不接受 dimensions；**推荐**）/ `zhipu`（`embedding-3`，¥0.5/百万 token）/ `dashscope`（阿里百炼 `text-embedding-v3`）/ `openai_compatible`（自定义 `KB_EMBEDDING_BASE_URL` + `KB_EMBEDDING_MODEL`）。三预设默认模型均 1024 维，与 `vector(1024)` 一致；`KB_EMBEDDING_API_KEY` 通用，zhipu 预设兼容旧的 `ZHIPU_API_KEY`。建库时记录 `get_embedding_config().model/dims` 为模型指纹。
- 验证过不可用的：用户提供的 SenseNova 网关（`token.sensenova.cn/v1`）只有 7 个对话模型、`/embeddings` 对所有模型名 404——对话模型留给后续问答生成 change。
- 理由：生产 3.6G 内存已用 swap，bge-small-zh 也要 300–500M，bge-m3 2G+，TEI/ollama 容器不可行；国内厂商数据不出境，成本可忽略（千万 token 量级几十元）。
- 工程约束：批量 ≤ 64 文本/次；指数退避重试 3 次；429/5xx 归类为可重试错误，任务进入 `retry`，超过上限置 `failed(stage=embedding)`；**只记录调用次数与 token 数，不记录文本内容**到日志。
- 备选：OpenAI text-embedding-3——数据出境，医疗场景否决；自托管——待升配 8G+ 后另评估（抽象层已留）。

### D4. 处理管线：Celery 独立队列，单并发，幂等
- 决策：新队列 `knowledge`，`celery_app.py` 增 `Queue("knowledge")` 与 `task_routes["app.tasks.knowledge_task.*"] = {"queue": "knowledge"}`；compose 新增服务 `celery_knowledge_worker`：
  ```
  celery -A app.celery_app worker -l info -Q knowledge -c 1 \
    --max-tasks-per-child=20 --max-memory-per-child=400000
  ```
  挂载 `./apps/server/var/kb-tmp:/app/kb-tmp`（磁盘），env `KB_TMP_DIR=/app/kb-tmp`。现有 `celery_worker` 的 `-Q default,scheduled,notification` **不变**。
- 理由：现有 worker `-c 4`，4 个大 PDF 同时解析足以打爆 3.6G；独立队列让坏文档只拖慢知识库自己；`--max-memory-per-child` 兜底解析器内存泄漏。
- 任务：`process_document(doc_id)` 单任务内分阶段推进状态，每阶段落库一次（`parsing` → `embedding` → `ready`），失败记录 `failed_stage` + `error_message`（用户可读，如"PDF 无文本层（疑似扫描件），暂不支持 OCR"）。
- 幂等：任务开头 `DELETE FROM knowledge_chunks WHERE doc_id = :id`，重试或重复投递都安全。
- 重试：`POST /knowledge/documents/{id}/retry` 仅接受 `status = failed`，置回 `pending` 并重新投递；其他状态返回 409。

### D5. 解析与切片
- 解析器：`app/infrastructure/document_parser/{base.py, pdf.py, docx.py, xlsx.py, text.py}`，统一产出 `list[Block(text, page_no, section)]`。PDF 用 pypdf 逐页抽文本并保留页码；DOCX 用 python-docx，标题样式作为 `section`；XLSX 用 openpyxl（已有依赖），每行拼成一段、sheet 名作 section；TXT/MD 按空行分段，MD 的 `#` 标题作 section。
- 切片：按段落聚合至目标 ~800 中文字符（≈ 500 token），重叠 80 字符；每个 chunk 保留 `page_no`/`section`/`seq`，这是引用定位的依据。
- 大小/类型：`KB_MAX_FILE_MB=50`，MIME 白名单；超限或不支持类型在上传接口即拒绝（400），不进入队列。
- 读取：local 存储直接读上传目录（零临时文件）；非 local 存储下载到 `KB_TMP_DIR`（磁盘卷）后处理，`finally` 删除。
- 存储 key：`build_tenant_storage_folder(f"knowledge/{kb_id}/{doc_id}", tenant_id)` → `tenants/{tenant_id}/knowledge/{kb_id}/{doc_id}/{yyyymm}/{uuid}.{ext}`，复用现有租户目录约定；key 不对外暴露，下载按 doc_id 经可见性校验。

### D6. 数据模型（全部 `TenantMixin` + `AuditMixin`，`id` 为 String(36) UUID，与现有模型一致）
- `knowledge_bases`：`name`、`description`、`owner_admin_id`、`visibility`(`private`|`tenant`)、`embedding_model`、`embedding_dims`、`doc_count`、`chunk_count`。
- `knowledge_folders`：`kb_id`、`parent_id`(nullable)、`name`、`sort_order`；唯一约束 `(kb_id, parent_id, name)`。
- `knowledge_documents`：`kb_id`、`folder_id`(nullable)、`title`、`file_name`、`file_key`、`mime_type`、`size_bytes`、`status`(`KnowledgeDocStatus`: pending/parsing/embedding/ready/failed)、`failed_stage`、`error_message`、`page_count`、`chunk_count`、`uploaded_by`、`processed_at`。
- `knowledge_chunks`：`doc_id`、`kb_id`(冗余，供检索过滤)、`seq`、`content`、`page_no`、`section`、`token_count`、`embedding vector(1024)`；索引：HNSW(embedding)、btree(kb_id)、btree(doc_id, seq)。
- `knowledge_shares`：`kb_id`、`grantee_type`(`admin`|`role`)、`grantee_id`、`permission`(`read`|`edit`)、`granted_by`；唯一 `(kb_id, grantee_type, grantee_id)`。
- 可见性判定（`KnowledgeAccessService.visible_kb_ids(admin)`，单次查询）：`owner_admin_id = me` ∪ `visibility = 'tenant'` ∪ `shares` 命中我或我的角色 ∪ 持有 `knowledge:manage` 则租户内全部。所有列表/检索/下载接口都以此集合为边界。

### D7. 权限码与 RBAC
- 新增并登记：`knowledge:read`（查看/检索可见库）、`knowledge:create`（建库/上传）、`knowledge:update`（目录、重命名、重试）、`knowledge:delete`、`knowledge:share`（授权他人，仅 owner 或 manage）、`knowledge:manage`（租户内全部库的治理）。
- 被共享者的 `edit` 权限 ≤ 上传/整理，**不含**再分享与删库；只读者仅检索与预览。
- 登记位置：`common/role_permissions.py`（`ADMIN_KNOWLEDGE_PERMISSIONS`，并入 TENANT_ADMIN 默认权限）与 `scripts/init_permissions.py`（菜单 `knowledge` + 6 个按钮码）；CI 门禁 `gen_permission_matrix.py --check` 必须通过，`docs/modules/permission-codes.md` 由脚本重新生成。

### D8. 检索 API
- `POST /api/v1/knowledge/search`：`{ query, kb_ids?: string[], top_k?: number(≤20, 默认 8) }`。
- 流程：校验 `knowledge:read` → 计算 `visible` → `kb_ids` 与 `visible` 取交集（传入含不可见库时直接 403，不静默裁剪）→ 校验目标库 `embedding_model/dims` 与当前配置一致（不一致返回 409 `KB_EMBEDDING_MISMATCH`，提示重建）→ embed(query) → 单条 SQL：
  ```sql
  SET LOCAL hnsw.ef_search = 100;
  SELECT c.id, c.doc_id, d.title, c.page_no, c.section, c.content,
         1 - (c.embedding <=> :q) AS score
  FROM knowledge_chunks c JOIN knowledge_documents d ON d.id = c.doc_id
  WHERE c.kb_id = ANY(:kb_ids) AND d.status = 'ready'
  ORDER BY c.embedding <=> :q LIMIT :k;
  ```
- 响应每条命中：`chunk_id, doc_id, doc_title, kb_id, page_no, section, snippet, score, preview_url`；前端据 `page_no` 在预览抽屉定位。
- 提供方不可用：返回 503 `KB_EMBEDDING_UNAVAILABLE`（不泄露第三方错误体）。

### D8a. 文件拆分（架构适应度：router*.py ≤ 300 行、service*.py ≤ 500 行）
- `router.py`（库 / 目录 / 检索，include `router_documents.py`）、`router_documents.py`（文档 / 共享）。
- `service_base.py`（租户作用域 + 加载/级别校验 + 共用函数）、`service.py`（库 / 目录）、`service_documents.py`（文档 / 共享）、`service_access.py`、`service_search.py`、`pipeline.py`（与 Celery 解耦，测试直接调用）。
- 领域异常直接继承 `HTTPException`，detail 形状与 `raise_business_http_error` 一致（`{error_code, message}`），由全局处理器输出 `{code, message, error:{code,message}}`。

### D9. 前端（admin，web 与桌面同一产物）
- `packages/api/src/modules/knowledge.ts`：类型 + 函数（与现有模块写法一致），`index.ts` 导出。
- 页面 `apps/admin/src/pages/knowledge/`：
  - `index.tsx` 知识库列表（我的 / 共享给我 / 租户公共）；
  - `detail/` 左目录树（`Tree`）+ 右 `ProTable` 文档表（状态徽标：待处理/解析中/向量化中/已就绪/失败；失败行显示原因 + 重试按钮）+ `Upload.Dragger` 拖拽上传（桌面壳 WebView 原生支持拖拽，不需要 Tauri 插件）；处理中以 ProTable `polling`（3s）轮询，全部终态后停止（仓库未使用 react-query）；
  - `search/` 检索框 + 结果列表（片段、来源文档、页码、分数）+ 预览抽屉（PDF 以带鉴权的 blob 载入浏览器内置查看器并 `#page=N` 定位；TXT/MD 直接展示；Word/Excel 展示抽取文本切片，均可下载原件）；
  - `ShareModal` 选同事/角色 + 只读/可编辑。
- 路由 `config/routes.ts` + `access.ts` 以 `knowledge:read` 控菜单、`knowledge:create/share/manage` 控按钮。

### D10. 配置项（`core/config.py`，`.env.example`）
`KB_ENABLED`(默认 false，灰度开关)、`KB_EMBEDDING_PROVIDER`、`KB_EMBEDDING_MODEL`、`KB_EMBEDDING_DIMS`、`ZHIPU_API_KEY`、`KB_MAX_FILE_MB=50`、`KB_TMP_DIR`、`KB_SEARCH_TOP_K_MAX=20`、`KB_CHUNK_CHARS=800`、`KB_CHUNK_OVERLAP=80`。

## Risks / Trade-offs

- **内存紧张（3.6G，已用 swap）** → 单并发 knowledge worker + `--max-memory-per-child` + 50MB 文件上限 + 磁盘 scratch；可选：生产停 flower（139M）、default worker `-c 4 → 2`（省约 200M），本期不动，留运维决策。
- **医疗数据经第三方 API 向量化** → 只选国内厂商；上传入口固定提示"请勿上传含患者个人信息的文件"；日志不落文本；`KB_ENABLED` 灰度；若后续要放敏感资料，升配后切自托管 provider（抽象层已留）。
- **embedding 提供方抖动/限流** → 批量 + 退避重试 + 任务级 retry；最终失败可一键重试；检索侧 503 明确错误码。
- **HNSW 建索引慢（`maintenance_work_mem=64MB`）** → 迁移内会话级 `SET LOCAL maintenance_work_mem='256MB'`；初期数据量小，增量插入不重建。
- **PG 18 + 宝塔源码编译 + pgvector 自编译的运维耦合** → 钉 0.8.7；部署文档新增"PG 升级后重编 pgvector"章节；`CREATE EXTENSION IF NOT EXISTS` 幂等。
- **CI 测试库无 vector 类型** → `test.yml` 的 PG service 镜像换 `pgvector/pgvector:pg18`，迁移在 CI 可完整执行。
- **扫描件/图片 PDF 占比高** → 本期明确失败并给原因，统计 `failed_stage=parsing` 比例决定是否立 OCR change。
- **chunk 表膨胀** → `knowledge_bases.doc_count/chunk_count` 可观测；配额留给 `tenants/service_usage.py` 扩展（本期不做）。

## Migration Plan

1. 迁移 `kb01_knowledge_base.py`：先查 `pg_extension`，扩展已存在则跳过（生产已安装）；不存在则尝试 `CREATE EXTENSION`，应用账号无权时报出「请超级用户执行 CREATE EXTENSION vector」的指引（pgvector 非 trusted 扩展，`hospital` 账号建不了）→ 建 5 表 → 会话级 `maintenance_work_mem='256MB'` 后建 HNSW 索引。
2. 登记权限码并运行权限 seed（现有流程），`gen_permission_matrix.py --check` 通过。
3. 部署：`.env` 加 `KB_*` 与 `ZHIPU_API_KEY`（`KB_ENABLED=false` 先上）；compose `up -d --build` 拉起 `celery_knowledge_worker`；nginx 对 `/api/v1/knowledge/documents` 路径放宽 `client_max_body_size 60m`。
4. 灰度：对一个租户置 `KB_ENABLED=true`（或按租户 feature flag，若现有租户开关机制可复用则复用），走 proposal Verification 冒烟。
5. 回滚：`KB_ENABLED=false` 隐藏入口；停 `celery_knowledge_worker`；表无其他模块外键依赖，必要时 `alembic downgrade` 一步删除；pgvector 扩展保留不卸。

## Open Questions

1. 共享粒度默认同时支持"按同事"和"按角色"——是否需要"整租户公共库"之外的更细（如按门店）？本期按 D6 的 `admin|role` 两种。
2. doctor 端是否需要只读检索入口（医生查 SOP/用药规范）？本期不做，若需要则在 doctor 端复用同一 API 另立 change。
3. 灰度开关粒度：全局 env `KB_ENABLED` 还是按租户 feature flag？取决于现有租户开关机制是否已支持功能级 flag（实现时核对 `modules/tenants`）。
4. `KB_MAX_FILE_MB=50` 是否满足机构常见培训课件体量？不够时需同时评估 nginx 与 worker 内存上限。
