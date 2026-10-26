# Spec Delta: knowledge-retrieval

## ADDED Requirements

### Requirement: 语义检索范围必须严格等于调用者可见的知识库集合

`POST /api/v1/knowledge/search` SHALL 对持有 `knowledge:read` 的管理员提供语义检索。检索 MUST 先计算调用者可见知识库集合（自有 ∪ 租户公共 ∪ 被共享 ∪ `knowledge:manage` 全部），并在 SQL 层以该集合过滤切片；未传 `kb_ids` 时默认全部可见库；传入的 `kb_ids` 含任何不可见库时 MUST 返回 403，不得静默裁剪。仅 `status = ready` 的文档切片可被命中。

#### Scenario: 默认检索全部可见库

- **WHEN** 管理员 B 不带 `kb_ids` 检索「术前禁食时间」
- **THEN** 命中仅来自 B 自有、租户公共或被共享给 B 的知识库，不含他人私有库的任何切片

#### Scenario: 指定不可见库被拒绝

- **WHEN** B 在 `kb_ids` 中混入一个未共享给自己的私有库 id
- **THEN** 返回 403，不返回任何命中

#### Scenario: 处理中文档不被命中

- **WHEN** 某文档处于 `embedding` 状态且已有部分切片写入
- **THEN** 检索结果不包含该文档的任何切片，直到其 `status = ready`

### Requirement: 检索结果必须携带可定位的引用来源

每条命中 MUST 返回 `chunk_id`、`doc_id`、`doc_title`、`kb_id`、`page_no`、`section`、`snippet`（命中片段原文）、`score`（余弦相似度，0–1）与 `preview_url`。前端 MUST 将引用渲染为可点击项，点击后在预览中定位到对应页码/章节。结果 MUST 按 `score` 降序，`top_k` 默认 8、上限 `KB_SEARCH_TOP_K_MAX`（默认 20）。

#### Scenario: 引用字段完整

- **WHEN** 检索返回 5 条命中
- **THEN** 每条均含上述全部字段，`snippet` 为该切片原文（非摘要），`page_no` 与原文所在页一致

#### Scenario: 点击引用定位原文

- **WHEN** 用户点击某条命中的引用（PDF，`page_no = 12`）
- **THEN** 预览抽屉打开对应文档并定位到第 12 页，高亮或滚动至命中片段所在区域

#### Scenario: top_k 越界

- **WHEN** 请求 `top_k = 50`
- **THEN** 返回 400，提示上限为 20

### Requirement: 查询向量与文档向量必须使用同一 embedding 模型与维度

知识库 MUST 记录创建时使用的 `embedding_model` 与 `embedding_dims`；检索 MUST 使用与目标库一致的模型对查询向量化。当目标库记录的模型/维度与当前服务配置不一致时，检索 MUST 返回 409 `KB_EMBEDDING_MISMATCH` 并提示需要重建，MUST 不返回错配结果。切换模型后的重建 MUST 作用于整库全部文档，MUST 不允许同库混维。

#### Scenario: 模型切换后检索被拦截

- **WHEN** 服务配置从 `embedding-3/1024` 切换为另一模型后，用户检索一个仍记录为 `embedding-3/1024` 的知识库
- **THEN** 返回 409 `KB_EMBEDDING_MISMATCH`，界面提示「该知识库需重建索引后方可检索」

#### Scenario: 同库混维被拒绝

- **WHEN** 处理任务尝试向一个 `embedding_dims = 1024` 的库写入 2048 维向量
- **THEN** 写入被拒绝，文档置为 `failed`、`failed_stage = embedding`，错误信息指明维度不匹配

### Requirement: 检索必须走向量索引并对提供方故障给出明确错误

检索 SQL MUST 以 `embedding <=> :query` 排序并命中 `knowledge_chunks` 的 HNSW 索引，会话内 MUST 设置 `hnsw.ef_search`（默认 100）。embedding 提供方不可用或超时时，接口 MUST 返回 503 `KB_EMBEDDING_UNAVAILABLE`，MUST 不向客户端透出第三方错误体。查询文本 MUST 不写入日志。

#### Scenario: 走索引而非全表扫描

- **WHEN** 对含 10 万切片的租户执行检索并 `EXPLAIN`
- **THEN** 执行计划使用 `knowledge_chunks` 的 HNSW 索引（Index Scan），而非 Seq Scan + Sort

#### Scenario: 提供方不可用

- **WHEN** 向量化查询文本时提供方返回 5xx 或超时
- **THEN** 接口返回 503 `KB_EMBEDDING_UNAVAILABLE`，响应体不含提供方原始错误，前端提示「检索服务暂不可用，请稍后重试」

#### Scenario: 查询文本不落日志

- **WHEN** 任意检索请求完成
- **THEN** 结构化日志仅含 `tenant_id`、`admin_id`、`kb_count`、`top_k`、耗时与命中数，不含查询原文
