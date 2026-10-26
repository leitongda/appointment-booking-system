# Spec Delta: knowledge-base

## ADDED Requirements

### Requirement: 知识库与目录必须按租户隔离并支持树形组织

系统 SHALL 允许持有 `knowledge:create` 的管理员在本租户内创建知识库，并在知识库内以目录树（任意层级）组织文档。所有知识库、目录、文档、切片、共享记录 MUST 携带 `tenant_id` 并在服务层按当前租户上下文过滤；跨租户数据在任何接口中 MUST 不可见、不可寻址。

#### Scenario: 创建知识库默认私有

- **WHEN** 管理员 A 创建知识库「院感制度」且未指定可见性
- **THEN** 知识库 `visibility = private`、`owner_admin_id = A`，仅 A 与持有 `knowledge:manage` 的管理员可见

#### Scenario: 目录树移动

- **WHEN** 管理员把目录「2026 版」从「制度/旧版」移动到「制度/现行」下
- **THEN** 该目录及其全部子目录与文档的归属随之变更，文档的 `file_key` 与切片不变、不触发重新处理

#### Scenario: 跨租户不可寻址

- **WHEN** 租户 T2 的管理员以租户 T1 的知识库 id 或文档 id 请求任何知识库接口
- **THEN** 返回 404，且响应体不泄露该资源是否存在

### Requirement: 文档上传必须校验类型与大小并立即进入待处理状态

系统 SHALL 接受 PDF、DOCX、XLSX、TXT、MD 五类文档上传，单文件大小 MUST 不超过 `KB_MAX_FILE_MB`（默认 50MB）。上传成功后文档 MUST 以 `status = pending` 落库并投递到 `knowledge` 队列；类型不支持或超限的文件 MUST 在上传接口被拒绝，不得进入队列。原件 MUST 经 `get_storage()` 抽象保存于 `tenants/{tenant_id}/knowledge/{kb_id}/{doc_id}/` 前缀下（复用现有租户目录约定），存储 key MUST 不对外暴露。

#### Scenario: 支持的类型成功入库

- **WHEN** 管理员在知识库目录下拖拽上传一份 12MB 的 PDF
- **THEN** 接口返回文档记录 `status = pending`，原件已落存储，`knowledge` 队列收到一条 `process_document` 任务

#### Scenario: 不支持的类型或超限被拒绝

- **WHEN** 管理员上传一份 `.pptx` 或一份 80MB 的 PDF
- **THEN** 接口返回 400，错误信息分别指明「不支持的文件类型」或「超过 50MB 上限」，存储与队列均无残留

#### Scenario: 上传入口提示合规约束

- **WHEN** 管理员打开上传区域
- **THEN** 界面固定展示「请勿上传含患者个人信息的文件」提示

### Requirement: 文档处理状态机必须全程可见且失败可重试

文档处理 MUST 按 `pending → parsing → embedding → ready` 推进，任一阶段失败 MUST 置为 `failed` 并记录 `failed_stage` 与用户可读的 `error_message`。处理任务 MUST 幂等：开始时清除该文档已有切片。持有 `knowledge:update` 的可见者 SHALL 可对 `failed` 文档发起重试；对非 `failed` 状态的文档发起重试 MUST 返回 409。

#### Scenario: 正常处理流转

- **WHEN** 一份含文本层的 PDF 被投递处理
- **THEN** 状态依次经过 `parsing`、`embedding` 到达 `ready`，`chunk_count > 0`、`page_count` 等于 PDF 页数，前端列表在轮询中看到状态变化

#### Scenario: 扫描件解析失败并给出原因

- **WHEN** 一份无文本层的扫描 PDF 被处理
- **THEN** 状态为 `failed`、`failed_stage = parsing`、`error_message` 为「PDF 无文本层（疑似扫描件），暂不支持 OCR」，该文档不产生任何切片

#### Scenario: embedding 提供方持续不可用

- **WHEN** 向量化阶段连续 3 次收到提供方 429/5xx
- **THEN** 任务按指数退避重试，超过上限后状态为 `failed`、`failed_stage = embedding`，日志仅记录调用次数与错误类别，不记录文本内容

#### Scenario: 失败重试幂等

- **WHEN** 管理员对 `failed` 文档点击「重新处理」
- **THEN** 状态回到 `pending` 并重新投递；任务开始时删除该文档旧切片；最终 `ready` 时 `chunk_count` 与首次成功处理一致、无重复切片

#### Scenario: 非失败状态不可重试

- **WHEN** 对 `parsing` 或 `ready` 状态的文档调用重试接口
- **THEN** 返回 409，状态不变、不产生新任务

### Requirement: 知识库共享必须受权限约束且可撤销

知识库 owner 或持有 `knowledge:manage` 的管理员 SHALL 可将知识库共享给本租户内的同事（按管理员）或角色（按角色），权限为 `read` 或 `edit`。`edit` MUST 仅包含上传、整理目录、重试，MUST 不包含再分享与删除知识库；`read` MUST 仅包含检索与预览。撤销共享后被授权者 MUST 立即失去可见性。被共享库 MUST 保持 `tenant_id` 一致，不得跨租户共享。

#### Scenario: 共享只读给同事

- **WHEN** owner A 把知识库共享给管理员 B（`read`）
- **THEN** B 的「共享给我」列表出现该库，B 可检索与预览，但上传/重试/删除/共享接口均返回 403

#### Scenario: 可编辑者不能再分享或删库

- **WHEN** 被授予 `edit` 的 B 尝试把该库共享给 C 或删除该库
- **THEN** 返回 403

#### Scenario: 按角色共享

- **WHEN** owner 把知识库共享给角色「护理部」（`read`）
- **THEN** 所有持有该角色的管理员均可见，后续被授予该角色的管理员自动可见

#### Scenario: 撤销共享立即生效

- **WHEN** owner 删除对 B 的共享记录
- **THEN** B 的下一次列表、检索、预览请求均不再包含该库内容

#### Scenario: manage 权限可治理全部

- **WHEN** 持有 `knowledge:manage` 的管理员查看知识库列表
- **THEN** 列表包含本租户内所有知识库（含他人私有库），且可对其执行全部操作

### Requirement: 原件下载与预览必须经租户与可见性校验

文档原件 MUST 仅能通过服务端接口下载，接口 MUST 校验当前租户与调用者对该文档所属知识库的可见性；存储 key 不得作为公开 URL 暴露。预览 MUST 基于同一校验路径提供，PDF 预览 MUST 支持按页码定位。

#### Scenario: 无可见性直接访问 key

- **WHEN** 管理员 C（对该库无任何权限）凭猜测或泄露的 `file_key` 请求下载接口
- **THEN** 返回 404，不返回文件内容

#### Scenario: PDF 预览定位到页

- **WHEN** 可见者从检索结果点击引用（`page_no = 7`）
- **THEN** 预览抽屉打开该 PDF 并定位到第 7 页

### Requirement: 文档处理必须在独立队列执行且资源有界

文档解析与向量化任务 MUST 路由到独立的 `knowledge` 队列，由独立 worker 进程以并发 1 执行，并设置单子进程最大任务数与内存上限；现有 `default/scheduled/notification` 队列的 worker MUST 不消费该队列。解析过程中的临时文件 MUST 写入磁盘路径 `KB_TMP_DIR`，MUST 不使用容器内 tmpfs（`/tmp`、`/app/var`），且处理结束后 MUST 清理。

#### Scenario: 坏文档不影响核心业务队列

- **WHEN** 一份文档的解析耗时 10 分钟并占用大量内存
- **THEN** 预约通知、排班生成等 `default/scheduled/notification` 队列任务不受排队影响；knowledge worker 子进程在超出内存上限时被回收，任务按失败处理

#### Scenario: 临时文件落盘并清理

- **WHEN** 任意文档处理完成（成功或失败）
- **THEN** `KB_TMP_DIR` 下该文档的临时文件已删除，容器 tmpfs 使用量无增长
