# 通用审批流引擎设计 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-21
> 审查目标：企业级流程审批引擎设计评审（add-workflow-approval-engine）

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 用户未指定特定领域深入需求，任务为综合设计评审。集中调度可快速收敛且输出完整度最高，Team Lead 直接裁决效率最佳。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角（56 项事实）

**产品定位与业务场景：**
- 系统现有审批为硬编码单级审批（停诊审核 `leave_requests`、加号审批 `extra_quota`）
- 新设计目标：通用审批中心 + 可配置流程引擎，一期接入 `leave_request` 和 `extra_quota`
- 一期不含拖拽设计器，使用"配置表单 + 流程预览"
- 后续扩展：拖拽设计器、更多节点类型、超时自动升级、移动端审批

**权限体系现状：**
- 现有权限码：`approval-flow:list/create/update/manage/delete`，`approval:read/approve`
- 新设计权限码：`workflow:definition:*`、`workflow:task:*`、`workflow:instance:*`
- TENANT_ADMIN 拥有全部审批流权限；STORE_ADMIN 仅有 `approval:read` + `approval:approve`
- 系统预定义角色 6 个：SUPER_ADMIN、PLATFORM_ADMIN、TENANT_ADMIN、STORE_ADMIN、DOCTOR、PATIENT
- 通配符匹配机制：`*` 全局、`prefix:*` 前缀

**业务适配器协议：**
- `WorkflowBusinessAdapter` 接口：`businessType`、`getDetail`、`getPayload`、`onApproved`、`onRejected`、`onCancelled`
- `leave_request` 适配：通过后复用现有停诊/调班处理逻辑
- `extra_quota` 适配：通过后增加排班 `extra_quota` 并同步总号源
- 无配置流程时走旧逻辑（兼容）

**管理端页面规划：**
- 我的待办、我的已办、我发起的
- 流程实例详情（Timeline + 业务表单）
- 流程定义管理（列表、创建、编辑）
- 流程版本发布
- 流程预览用 Steps/Timeline/Card + 条件分支说明

**通知场景：**
- 新待办生成、审批通过、审批拒绝、转交任务、撤回流程、超时提醒、流程完成、流程失败
- 渠道：站内信、系统消息、短信、微信推送、邮件
- 流程引擎只产生事件，不直接依赖消息实现（outbox 模式）

### Designer — 用户视角（74 项事实）

**现有 UI 模式：**
- admin 前端使用 React 18 + TypeScript + Umi 4 + Ant Design 5 + ProComponents
- 列表页标准模式：ProTable + 搜索表单 + 操作按钮
- 表单页标准模式：ProForm / ProFormText / ProFormSelect 等
- 详情页标准模式：Descriptions + Tabs
- 弹窗标准模式：Modal + Form

**现有审批相关页面：**
- 停诊审批：`apps/admin/src/pages/operations/leave-requests/`
- 加号审批：`apps/admin/src/pages/schedule/extra-quota/`
- 两者均为单级审批，硬编码逻辑

**路由配置模式：**
- `apps/admin/config/routes/` 按业务域拆分（platform, medical-services, organization, operations, system）
- 路由格式：`{ path: '/approval/...', component: '...', name: '...', access: '...' }`
- 权限通过 `access` 字段控制

**流程设计器技术方案：**
- 自研轻量方案，不引入 reactflow 等外部依赖
- 节点用 Ant Design Card + 绝对定位
- 连线用 SVG `<path>`
- 拖拽用项目已有的 `@dnd-kit`
- 属性配置用 ProForm 弹窗

**状态展示模式：**
- 审批状态 Badge：pending(processing)、approved(success)、rejected(error)、cancelled(default)
- 时间线组件：Ant Design Timeline 展示审批记录
- 当前节点高亮 + 已处理节点显示处理人/时间/意见

**API 模式：**
- `packages/api/src/modules/` 统一请求封装
- 标准模式：`getXxxList`、`getXxxDetail`、`createXxx`、`updateXxx`、`deleteXxx`
- 内置性能监控 (createApiTimer)、重试逻辑 (withRetry)

### Engineer — 技术视角（72 项事实）

**数据模型差异（现有 vs 新设计）：**

| 维度 | 现有 Phase 1 实现 | 新企业级设计 |
|------|-------------------|-------------|
| 表命名 | `approval_*` (5 张) | `workflow_*` (7 张) |
| 版本机制 | `version: Integer` 字段 | `workflow_versions` 独立表 + 快照 |
| 任务模型 | 无独立任务表，用 `ApprovalRecord` 查询 | `workflow_tasks` 独立表 |
| 审计记录 | `ApprovalRecord` | `workflow_actions` + `request_id` |
| 事件系统 | WebSocket 直调（try-except） | `workflow_outbox_events` 表 |
| 运行日志 | 无 | `workflow_runtime_logs` 表 |
| 并发控制 | 无乐观锁 | `version` 字段乐观锁 |
| 幂等性 | 无 | `request_id` 唯一约束 |
| 审批人快照 | 无，实时查询 | `assignee_snapshot` JSON |
| 自动审批 | 无 | `actor_type=system` + `action_type=auto_approve` |

**状态机差异：**

| 实例状态 | 现有 | 新设计 |
|---------|------|--------|
| 草稿 | - | draft |
| 审批中 | pending | running |
| 已通过 | approved | approved |
| 已拒绝 | rejected | rejected |
| 已撤回 | withdrawn | cancelled |
| 已终止 | - | terminated |
| 已挂起 | - | suspended |
| 回调失败 | - | failed |

| 任务状态 | 现有 | 新设计 |
|---------|------|--------|
| 待处理 | (隐含) | pending |
| 已通过 | approve (action) | approved |
| 已拒绝 | reject (action) | rejected |
| 已转交 | delegate (action) | transferred |
| 已取消 | - | cancelled |
| 已跳过 | - | skipped |
| 已超时 | - | expired |

**条件路由安全：**
- 现有：8 个运算符（eq/neq/gt/gte/lt/lt/in/contains），扁平列表按 priority 匹配
- 新设计：结构化 JSON 条件组（`all`/`any`），12 个运算符（+ not_in/exists），白名单字段验证
- 禁止 eval/脚本表达式/用户输入代码

**并发与幂等：**
- 现有：无乐观锁，无幂等键，多审批人并发可能导致重复推进
- 新设计：`workflow_tasks.version` + `workflow_instances.version` 乐观锁，`request_id` 幂等键，`UNIQUE(tenant_id, request_id)` 约束

**索引设计：**
- 现有：标准索引
- 新设计：GIN 索引（`candidate_user_ids` JSONB）、复合索引（业务关联、租户列表、用户已办）

**事务边界：**
- 现有：service 层事务，回调直接调用
- 新设计：审批动作 + 任务更新 + 实例推进同事务，外部系统通过 outbox 异步

**WebSocket 通知：**
- 现有：`WSMessageType` 新增 5 个审批类型，`notify_doctor()` 直调
- 新设计：流程引擎产生事件 → outbox → 统一消息服务消费

**路由注册：**
- 现有：`/approval-flows` + `/approval-instances` 两个前缀
- 新设计：`/workflows/definitions` + `/workflows/tasks` + `/workflows/instances` 三个前缀

---

## Round 2：辩论层

### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 表命名：`approval_*` vs `workflow_*` | 倾向 `workflow_*` | 全链路成本被低估 | **保留 `approval_*`** |
| 是否需要独立任务表 | 需要 | ApprovalRecord 已有类似功能 | **需要，但职责分离更清晰** |
| 是否需要 outbox 模式 | 需要 | Celery 已在技术栈中 | **不需要，用 Celery 替代** |
| 是否需要乐观锁 | 必须 | Redis 分布式锁更简单 | **用 Redis 分布式锁** |
| 权限码命名空间 | 建议 `workflow:*` | 改名无业务收益 | **保留 `approval:*`** |
| 条件路由 all/any 组合 | 需要 | 无真实业务场景支撑 | **一期仅支持 AND，后续按需扩展** |
| 审批人快照机制 | 必须 | ApprovalRecord 已存 approver_id+name | **需要，存入任务记录** |
| 自动审批支持 | 需要 | 医疗场景有合规风险 | **保留能力，规则需业务确认** |
| 运行日志表 | P1 | structlog 可能更合适 | **用 structlog，不建表** |

### 独到发现

1. **Phase 1 是骨架代码**：现有引擎从未与任何业务模块集成，所有"迁移成本"讨论前提不成立
2. **已有基础设施被严重低估**：Celery（3 个队列）、Redis 7、WebSocket、中间件栈、权限体系——新设计的每个新组件都有更简单的替代方案
3. **表命名变更的连锁成本**：从 `approval_*` 到 `workflow_*` 影响数据库/ORM/路由/权限/前端/文档 6 层

### Critic 质询（15 条，3 条关键）

**[Critic -> 全体] 质询 1：Product Positioning Contradiction**
- 论据：只有 2 个业务场景，不需要 7 张表 + outbox 的通用引擎
- 要求回应：PM
- 级别：普通

**[Critic -> 全体] 质询 2：Phase 1 代码被系统性忽视**
- 论据：665 行引擎代码从未在真实业务中运行
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 3：Outbox 模式的必要性未经论证**
- 论据：Celery 已在技术栈中，try-except 直调可能已够用
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 4：权限码命名空间切换的影响被低估**
- 论据：6 个预定义角色绑定旧权限码，改名无业务收益
- 要求回应：PM + Designer
- 级别：普通

**[Critic -> 全体] 质询 5：条件路由 all/any 组合的用户场景缺失**
- 论据：停诊/加号审批可能只需 AND 关系
- 要求回应：PM
- 级别：普通

**[Critic -> 全体] 质询 6：竞品对比缺失**
- 论据：未引用 Camunda/Activiti/飞书审批等成熟方案
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 7：测试覆盖为零**
- 论据：approval_flows 模块无任何测试
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 8：审批人快照的存储成本和查询模式**
- 论据：ApprovalRecord 已存 approver_id+name，快照是否多余
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 9：自动审批的边界和风险**
- 论据：医疗场景自动审批有合规风险
- 要求回应：PM
- 级别：普通

**[Critic -> 全体] 质询 10：运行日志表的价值未量化**
- 论据：structlog 可能比数据库表更合适
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 11：Designer 提出的自研流程设计器技术风险**
- 论据：SVG 自动布局 + dnd-kit 同步复杂度高
- 要求回应：Designer + PM
- 级别：普通

**[Critic -> 全体] 质询 12：现有 WebSocket 通知的改进方案被跳过**
- 论据：加重试逻辑 + Redis 队列比 outbox 简单得多
- 要求回应：Engineer
- 级别：普通

**[Critic -> 全体] 质询 13（关键）：表命名决策的连锁影响被系统性忽视**
- 论据：`approval_*` -> `workflow_*` 影响数据库/ORM/路由/权限/前端/文档 6 层
- 要求回应：PM + Engineer
- 级别：🚨 关键

**[Critic -> 全体] 质询 14（关键）：现有引擎没有集成任何业务模块，但三方假设它已经工作**
- 论据：leave_requests 和 extra_quota 完全没有引用 approval_flows
- 要求回应：Engineer + PM
- 级别：🚨 关键

**[Critic -> 全体] 质询 15（关键）：三方都忽略了项目的最大优势 -- 已有的基础设施**
- 论据：Celery/Redis/WebSocket/中间件栈/权限体系已有成熟替代方案
- 要求回应：Engineer + Designer
- 级别：🚨 关键

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 表命名 approval_* -> workflow_* 的全链路成本未估算 | 裁决：保留 approval_*，避免无收益的全链路变更 | 是 | 纳入计划 |
| 2 | Phase 1 从未集成业务模块，对比前提不成立 | 裁决：Phase 1 视为骨架，按新规格在原表结构上重写引擎 | 是 | 纳入计划 |
| 3 | 忽略已有 Celery/Redis/WebSocket 基础设施 | 裁决：用 Celery 替代 outbox，用 Redis 替代乐观锁，复用 WebSocket | 是 | 纳入计划 |

---

## Round 3：共识层

### ✅ 共识项

1. **保留 `approval_*` 表命名，避免无收益的全链路变更**
   - 结论：新设计规格中的 `workflow_*` 命名不采纳。保留现有 `approval_*` 命名，"审批"比"工作流"更符合业务语境
   - 建议行动：在原表结构基础上增加新表（`approval_tasks`），不重命名现有表
   - 成本估算：0h（节省了迁移成本）
   - 优先级：P0

2. **增加独立任务表 `approval_tasks`，分离任务和审计语义**
   - 结论：现有 `ApprovalRecord` 混合了"谁应该审批"和"谁审批了"两种语义。新增 `approval_tasks` 表存储待办任务
   - 建议行动：创建 `approval_tasks` 表，字段参考新设计规格（assignee_id, candidate_user_ids, assignee_snapshot, status, version）
   - 成本估算：8h（模型 + 迁移 + 引擎改造）
   - 优先级：P0

3. **用 Celery 替代 outbox 模式，复用已有基础设施**
   - 结论：不引入 `workflow_outbox_events` 表。异步通知通过 Celery 任务实现，超时检查用 Celery 定时任务
   - 建议行动：创建 `tasks/approval_tasks.py`，包含通知任务和超时检查任务
   - 成本估算：4h
   - 优先级：P0

4. **用 Redis 分布式锁替代数据库乐观锁**
   - 结论：不引入 `version` 字段做乐观锁。用 Redis `SETNX` 实现审批操作的互斥，避免并发重复推进
   - 建议行动：在 engine.py 的 approve/reject 方法中加 Redis 锁
   - 成本估算：3h
   - 优先级：P0

5. **保留 `approval:*` 权限码，不改命名空间**
   - 结论：新设计规格的 `workflow:*` 命名不采纳。保留现有 `approval-flow:*` 和 `approval:*` 权限码
   - 建议行动：无额外工作
   - 成本估算：0h
   - 优先级：P0

6. **审批人快照存入任务记录**
   - 结论：在 `approval_tasks` 表中增加 `assignee_snapshot` JSON 字段，记录审批人解析时的 ID/姓名/角色/门店
   - 建议行动：在任务创建时写入快照
   - 成本估算：2h
   - 优先级：P0

7. **条件路由一期仅支持 AND 关系，后续按需扩展**
   - 结论：不引入 `all`/`any` 条件组。保留现有扁平列表 + priority 匹配，增加 `not_in` 和 `exists` 运算符
   - 建议行动：在 condition_evaluator.py 中增加 2 个运算符
   - 成本估算：1h
   - 优先级：P0

8. **运行日志用 structlog，不建数据库表**
   - 结论：不引入 `workflow_runtime_logs` 表。关键操作用 structlog 记录，通过现有日志系统查询
   - 建议行动：在 engine.py 关键节点加 structlog 日志
   - 成本估算：2h
   - 优先级：P1

9. **Phase 1 视为骨架代码，按新规格在原表结构上重写引擎**
   - 结论：现有引擎从未集成业务模块，无需考虑"迁移"。直接在原 `approval_*` 表结构上重写引擎逻辑
   - 建议行动：重写 engine.py，增加任务管理、审批人快照、Redis 锁、Celery 通知
   - 成本估算：16h
   - 优先级：P0

10. **自动审批保留能力，规则需业务团队确认**
    - 结论：代码层面支持自动审批（`actor_type=system`），但具体规则（加号数量阈值等）需业务和合规团队确认后配置
    - 建议行动：在 engine.py 中实现 auto_approve 逻辑，配置表单支持自动审批规则
    - 成本估算：4h
    - 优先级：P1

### ⚡ 分歧项

1. **是否需要 `workflow_versions` 独立版本表**
   - 各方立场：
     - PM：需要版本快照，流程修改不影响历史实例
     - Engineer：现有 `version: Integer` 字段足够，独立表增加复杂度
     - Designer：版本管理对前端流程预览有影响
   - 裁决：**一期不引入独立版本表**。在 `approval_flow_definitions` 中增加 `snapshot_json` 字段，发布时生成快照。后续如需完整版本管理再扩展
   - 决策依据：Critic 质询 1 指出 2 个场景不需要 7 张表的复杂度。版本表是增量扩展，不阻塞核心功能

2. **流程设计器技术方案是否一期实现**
   - 各方立场：
     - PM：一期不含拖拽设计器
     - Designer：已有技术方案（dnd-kit + SVG）
     - Engineer：自研设计器技术风险高
   - 裁决：**一期不实现拖拽设计器**。使用"配置表单 + 流程预览"（Steps/Timeline/Card），后续迭代再考虑拖拽
   - 决策依据：Critic 质询 11 指出 SVG 自动布局 + dnd-kit 同步复杂度高，且 PM 明确排除了一期

---

## 被低估的优势

1. **Celery 任务队列**：已有 3 个队列（default/scheduled/notification），可直接用于审批通知和超时检查，无需 outbox 模式
2. **Redis 7**：可用于分布式锁（替代乐观锁）、缓存（审批人解析结果）、消息队列（失败通知重试）
3. **WebSocket 基础设施**：`core/websocket.py` 已有 doctor/patient 两种连接，审批通知可直接复用
4. **中间件栈**：tenant_context（租户隔离）、operation_log（操作日志）、rate_limit（限流）自动适用于新路由
5. **权限体系**：6 个预定义角色 + 通配符匹配，审批权限只需扩展，不需重建
6. **ProComponents**：admin 前端的列表/表单/详情页标准模式已建立，审批页面可直接复用

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 增加 `approval_tasks` 表 + 模型 | 8h | 高 | Engineer | 待执行 |
| P0 | 重写 engine.py（任务管理 + Redis 锁 + Celery 通知） | 16h | 高 | Engineer | 待执行 |
| P0 | 增加 `not_in`/`exists` 运算符 | 1h | 中 | Engineer | 待执行 |
| P0 | 增加 `snapshot_json` 到流程定义表 | 2h | 中 | Engineer | 待执行 |
| P0 | 创建 Celery 审批任务（通知 + 超时检查） | 4h | 高 | Engineer | 待执行 |
| P1 | 前端审批中心页面（待办/已办/发起/详情） | 24h | 高 | Designer | 待执行 |
| P1 | 前端流程定义管理页面 | 16h | 中 | Designer | 待执行 |
| P1 | structlog 运行日志 | 2h | 中 | Engineer | 待执行 |
| P1 | 自动审批能力 + 配置表单 | 4h | 中 | PM + Engineer | 待执行 |
| P2 | 停诊审核接入审批引擎 | 8h | 高 | Engineer | 待执行 |
| P2 | 加号审批接入审批引擎 | 8h | 高 | Engineer | 待执行 |
| P2 | Alembic 迁移脚本 | 2h | 高 | Engineer | 待执行 |
| 待定 | 拖拽式流程设计器 | 40h+ | 中 | Designer | 需用户确认 |
| 待定 | `all`/`any` 条件组 | 8h | 低 | Engineer | 需用户确认 |
| 待定 | 独立版本表 `approval_flow_versions` | 12h | 中 | Engineer | 需用户确认 |
| 待定 | `workflow_runtime_logs` 数据库表 | 6h | 低 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **增加 `approval_tasks` 表 + 模型**（8h）
   - 新增 `approval_tasks` 表：id, tenant_id, store_id, instance_id, node_key, node_name, task_type, status, assignee_id, candidate_user_ids, assignee_snapshot(JSON), version, created_at, completed_at
   - 新增 SQLAlchemy 模型，建立与 ApprovalInstance 的外键关系
   - Alembic 迁移脚本

2. **重写 engine.py**（16h）
   - 任务管理：创建/完成/转交任务
   - Redis 分布式锁：approve/reject 操作加锁
   - Celery 通知：审批事件触发 Celery 异步通知
   - 审批人快照：任务创建时写入 assignee_snapshot
   - 保持现有 start_instance/approve/reject/delegate/withdraw 接口

3. **增加 `not_in`/`exists` 运算符**（1h）
   - 在 condition_evaluator.py 中增加 2 个运算符

4. **增加 `snapshot_json` 到流程定义表**（2h）
   - 在 ApprovalFlowDefinition 模型增加 snapshot_json 字段
   - activate 时自动生成快照

5. **创建 Celery 审批任务**（4h）
   - `tasks/approval_tasks.py`：notify_approval_pending, notify_approval_result, check_timeout_tasks
   - 超时检查定时任务：扫描超时未处理的任务

### P1：本轮迭代（高价值、中等成本）

1. **前端审批中心页面**（24h）
   - 我的待办（ProTable + 筛选）
   - 我的已办（ProTable + 筛选）
   - 我发起的（ProTable + 筛选）
   - 流程实例详情（Timeline + 业务表单 + 审批操作）

2. **前端流程定义管理页面**（16h）
   - 流程定义列表（ProTable）
   - 流程定义创建/编辑（ProForm + 节点配置 + 条件配置）
   - 流程预览（Steps/Timeline/Card）

3. **structlog 运行日志**（2h）
   - 在 engine.py 关键节点加 structlog 日志

4. **自动审批能力**（4h）
   - engine.py 支持 auto_approve 逻辑
   - 配置表单支持自动审批规则

### P2：下个周期规划（中等价值、较高成本）

1. **停诊审核接入审批引擎**（8h）
2. **加号审批接入审批引擎**（8h）
3. **Alembic 迁移脚本**（2h）

### 待定：需用户确认

1. **拖拽式流程设计器**（40h+）— 技术风险高，建议用配置表单 + 流程预览替代
2. **`all`/`any` 条件组**（8h）— 无真实业务场景支撑，待有需求时再扩展
3. **独立版本表 `approval_flow_versions`**（12h）— 一期用 snapshot_json 字段替代
4. **`workflow_runtime_logs` 数据库表**（6h）— structlog 已满足调试需求

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 10 项达成共识（表命名、任务表、Celery 替代 outbox、Redis 锁、权限码、快照、条件路由、日志、引擎重写、自动审批）

**关键分歧：**
- 2 项需要决策者介入（版本表、流程设计器）

**Top 3 P0 行动：**
1. 重写 engine.py（任务管理 + Redis 锁 + Celery 通知 + 审批人快照）— 16h
2. 增加 `approval_tasks` 表 + 模型 — 8h
3. 创建 Celery 审批任务（通知 + 超时检查）— 4h

**Critic 关键洞察：**
- Phase 1 是骨架代码，从未集成业务模块——无需"迁移"，直接重写
- 已有基础设施（Celery/Redis/WebSocket）被严重低估，新设计的每个新组件都有更简单的替代方案
- 表命名变更的连锁成本（6 层影响）被系统性忽视，保留原命名是最优选择

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
