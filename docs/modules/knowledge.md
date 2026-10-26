# 📚 知识库（RAG）模块文档

> openspec change：`add-knowledge-base-rag`（proposal / design / specs 见 `openspec/changes/add-knowledge-base-rag/`）

## 一、模块概述

机构知识库让管理员把制度规范、SOP、药品说明、培训材料等非结构化资料按目录沉淀到服务端，后台自动"学习"（解析 → 切片 → 向量化），
支持按意思做语义检索并给出可点开定位的引用来源；资料可受权限约束地共享给同事，处理失败可一键重试。

- 知识库本体在服务端，admin 页面同时服务 web 与 Tauri 桌面壳（桌面壳零改动）。
- 向量存储：PostgreSQL + pgvector（`vector(1024)` + HNSW 余弦索引），不引入额外中间件。
- embedding：国内厂商 OpenAI 兼容 API，预设可切换——硅基流动 `BAAI/bge-m3`（免费，推荐）/ 智谱 `embedding-3` / 阿里百炼 `text-embedding-v3`，均 1024 维；生产机内存不足以自托管模型。
- 处理管线：Celery 独立队列 `knowledge`，单并发 worker，与核心业务 worker 隔离。

## 二、功能清单（机构端 admin）

| 功能 | 说明 | 权限码 |
|------|------|--------|
| 知识库列表 | 全部可见 / 我的 / 共享给我 / 租户公共；新建、重命名、删除 | `knowledge:read` / `create` / `update` / `delete` |
| 目录树 | 任意层级目录，新建 / 重命名 / 移动 / 删除（仅空目录） | `knowledge:update` |
| 文档上传 | PDF / DOCX / XLSX / TXT / MD，单文件 ≤ `KB_MAX_FILE_MB`（默认 50MB），拖拽多选 | `knowledge:create` |
| 学习状态 | pending → parsing → embedding → ready / failed，失败显示可读原因，处理中自动轮询 | `knowledge:read` |
| 重新处理 | 仅 `failed` 可重试，幂等（先清旧切片） | `knowledge:update` |
| 预览 / 下载 | PDF 内嵌查看器并按页定位；TXT/MD 直接展示；Word/Excel 展示抽取文本 | `knowledge:read` |
| 共享 | 按同事或按角色授予 read / edit，可撤销，立即生效 | `knowledge:share` |
| 智能检索 | 语义检索可见库，返回文档 / 页码 / 章节 / 片段 / 相似度，点击定位原文 | `knowledge:read` |
| 治理 | 查看并操作租户内全部知识库（含他人私有库） | `knowledge:manage` |

## 三、权限模型

权限码只决定"能否使用这类功能"；对具体知识库还有级别判定（`app/modules/knowledge/service_access.py`）：

| 级别 | 来源 | 可做 |
|------|------|------|
| owner | 知识库拥有者，或持 `knowledge:manage` | 全部：含共享、删库、改可见性 |
| edit | 被共享 `edit` | 上传、整理目录、重命名、重试、删文档；**不含**再分享与删库 |
| read | 被共享 `read`，或库为「租户公共」 | 检索、预览、下载 |

可见性集合 = 自有 ∪ 租户公共 ∪ 被共享（按人或按角色） ∪ manage 时租户内全部。
不可见 → 404（不泄露存在性），可见但级别不足 → 403。跨租户一律 404。

## 四、数据模型

| 表 | 说明 |
|----|------|
| `knowledge_bases` | 知识库；记录 `embedding_model` / `embedding_dims` 作为模型指纹，`visibility` private/tenant |
| `knowledge_folders` | 目录树（`parent_id` 自引用），同级同名唯一 |
| `knowledge_documents` | 文档元数据 + 处理状态（`status` / `failed_stage` / `error_message` / `page_count` / `chunk_count`） |
| `knowledge_chunks` | 切片 + `embedding vector(1024)`；`page_no` / `section` / `seq` 是引用定位依据；HNSW 索引 `ix_knowledge_chunks_embedding_hnsw` |
| `knowledge_shares` | 共享授权：`grantee_type` admin/role、`permission` read/edit |

所有表带 `tenant_id`；迁移 `kb01_knowledge_base`（会检查 pgvector 扩展是否存在，见部署文档 3.4）。

原件经 `get_storage()` 落盘，key 形如 `tenants/{tenant_id}/knowledge/{kb_id}/{doc_id}/{yyyymm}/{uuid}.pdf`，**不对外暴露**；下载/预览走 `GET /knowledge/documents/{id}/file`，服务端做租户 + 可见性校验。

## 五、处理管线

```
upload (API) ──► status=pending ──► Celery knowledge 队列
                                        │
                     parsing ◄──────────┘  解析（pypdf / python-docx / openpyxl / 文本）→ 切片（~800 字，重叠 80）
                        │
                     embedding             智谱 embedding-3 批量向量化（≤32/批）
                        │
                     ready                 写 knowledge_chunks，更新 doc/kb 计数
```

- 幂等：任务开头删除该文档旧切片，重试 / 重复投递安全。
- 失败分类：解析阶段（无文本层扫描件、加密 PDF、空文档、原件丢失）→ `failed(parsing)`；向量化阶段（配置缺失、4xx、维度不匹配）→ `failed(embedding)`。
- 可重试错误（429 / 5xx / 网络）按 60s / 180s / 600s 退避重试 3 次，期间状态停留 `embedding`，耗尽后 `failed(embedding)`。
- 模型指纹校验：provider 的模型/维度必须等于知识库记录值，否则直接失败并提示重建。
- 日志只记录调用次数 / token 数 / 错误类别，**不记录文本内容**。

## 六、检索

`POST /api/v1/knowledge/search`：`{ query, kbIds?, topK? }`

1. 计算可见集合；`kbIds` 含不可见库 → 403（不静默裁剪）。
2. 目标库模型/维度与当前配置不一致 → 409 `KB_EMBEDDING_MISMATCH`。
3. 查询向量化失败 → 503 `KB_EMBEDDING_UNAVAILABLE`（不透出第三方错误）。
4. `SET LOCAL hnsw.ef_search = 100`，`ORDER BY embedding <=> :q LIMIT k`，仅 `status = ready` 的文档参与。
5. 每条命中：`chunkId / docId / docTitle / kbId / pageNo / section / snippet / score / previewUrl`。

## 七、配置项

| 变量 | 默认 | 说明 |
|------|------|------|
| `KB_ENABLED` | `false` | 灰度开关；false 时 `/knowledge/*` 整体 404，前端页面提示未启用 |
| `KB_EMBEDDING_PROVIDER` | `zhipu` | 预设 `siliconflow`（免费 bge-m3，推荐）/ `zhipu` / `dashscope` / `openai_compatible`（自定义网关） |
| `KB_EMBEDDING_API_KEY` | — | 提供方 key（zhipu 预设兼容 `ZHIPU_API_KEY`） |
| `KB_EMBEDDING_BASE_URL` / `KB_EMBEDDING_MODEL` | 预设值 | 留空用预设；`openai_compatible` 必填。维度必须与 `vector(1024)` 一致；切换模型 = 整库重建 |
| `KB_EMBEDDING_SEND_DIMENSIONS` | 按预设 | `true`/`false` 控制请求是否带 `dimensions` 参数（bge 系列不支持） |
| `KB_EMBEDDING_DIMS` | `1024` | 与 `knowledge_chunks.embedding vector(1024)` 一致 |
| `KB_EMBED_BATCH_SIZE` | `32` | 每次请求的文本数 |
| `KB_MAX_FILE_MB` | `50` | 单文件上限；nginx `client_max_body_size` 需同步放宽 |
| `KB_TMP_DIR` | `var/server/kb-tmp` | 非 local 存储时下载原件的临时目录，**必须是磁盘卷**（容器 `/tmp` 是 tmpfs） |
| `KB_SEARCH_TOP_K_MAX` | `20` | 检索条数上限 |
| `KB_CHUNK_CHARS` / `KB_CHUNK_OVERLAP` | `800` / `80` | 切片目标字符数 / 重叠 |

## 八、部署与运维

- compose 新增 `celery_knowledge_worker`：`-Q knowledge -c 1 --max-tasks-per-child=20 --max-memory-per-child=400000`，挂 `./apps/server/uploads:ro` 与 `./apps/server/var/kb-tmp`（宿主机需 `mkdir -p && chmod 1777`）。
- `backend` 服务也需要 `KB_*` / `KB_EMBEDDING_API_KEY` 环境变量（检索时向量化查询）。
- 推荐生产 `.env`：`KB_EMBEDDING_PROVIDER=siliconflow` + `KB_EMBEDDING_API_KEY=<硅基流动 key>`（bge-m3 免费、1024 维、中文检索质量好；注册即送额度，无需绑卡）。
- 上线顺序：`alembic upgrade head` → 权限 seed（`scripts/init_permissions.py`，新增 7 个码）→ `docker compose up -d --build` → `KB_ENABLED=false` 先上 → 灰度打开。
- 观测：Flower 看 `knowledge` 队列；日志关键字 `[knowledge]`；`knowledge_documents.failed_stage` 分布决定是否立 OCR change。
- 合规：分块文本会发往 embedding 厂商，上传入口固定提示"请勿上传含患者个人信息的文件"；敏感资料需升配后切自托管 provider。

## 九、代码位置

| 层 | 路径 |
|----|------|
| 路由 | `app/modules/knowledge/router.py`（库/目录/检索）、`router_documents.py`（文档/共享） |
| 服务 | `service.py`（库/目录）、`service_documents.py`（文档/共享）、`service_access.py`（可见性/级别）、`service_search.py`、`service_base.py` |
| 管线 | `app/modules/knowledge/pipeline.py`、`chunker.py`、`app/tasks/knowledge_task.py` |
| 基础设施 | `app/infrastructure/embedding/`、`app/infrastructure/document_parser/` |
| 模型 / 枚举 / 迁移 | `app/models/knowledge.py`、`app/enums/knowledge.py`、`migrations/versions/kb01_knowledge_base.py` |
| 前端 | `packages/api/src/modules/knowledge.ts`、`apps/admin/src/pages/knowledge/**`、`config/routes/knowledge.ts` |
| 测试 | `tests/unit/test_knowledge_*.py`、`tests/integration/test_knowledge_search.py`（PG）、`tests/fixtures/knowledge.py` |

## 十、不在本期范围（独立 change）

LLM 问答生成（`add-knowledge-qa-generation`）、MCP 暴露（`add-knowledge-mcp-server`）、OCR、混合全文检索、doctor 端、自托管 embedding。
