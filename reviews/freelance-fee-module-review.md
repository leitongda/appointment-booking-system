# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-29
> 审查目标：兼职费用模块架构设计

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 标准新模块设计任务，需求已明确给出，需要 PM + Designer + Engineer 三方快速收敛产出可执行的架构方案。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 系统定位为"全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约"
- 来源：`CLAUDE.md:14`
- 现有 61 个后端模块，60 条 API 路由
- 来源：`apps/server/app/api/v1/__init__.py:14-75`

**功能完成度：**
- 现有财务相关模块：consultation_fees（诊费管理）、payments（支付）、refunds（退款）、revenue（收入计算，纯 service 无路由）、points（积分）
- 来源：`apps/server/app/modules/` 目录
- 系统中无任何"兼职人员"、"freelancer"、"part_time"相关模型、枚举或概念
- 来源：grep 搜索整个 `apps/server/app/` 目录

**用户/角色体系：**
- 双账户体系（旧表 Admin/Doctor/User + 新统一 Account 表），渐进式迁移中
- RoleType 枚举仅 3 种：admin、doctor、user
- 来源：`apps/server/app/enums/core.py:57-64`
- 权限码格式：`permission:action`（如 `doctor:create`、`leave-request:approve`）
- 来源：`apps/server/app/common/permission_deps.py:104-152`

**多租户：**
- 所有业务表含 `tenant_id` 字段
- TenantContextMiddleware 通过 ContextVar 实现异步上下文隔离
- Celery 任务中使用 `set_tenant_context()` / `clear_tenant_context()` 手动管理
- 来源：`apps/server/app/middleware/tenant_context.py:28-29`、`apps/server/app/tasks/payment_task.py:60-65`

**Celery 定时任务：**
- 3 个队列：default、scheduled、notification
- Beat 调度使用 crontab 表达式
- 任务中使用同步数据库会话 `get_sync_db()`
- 多租户任务遍历活跃租户逐个处理
- 来源：`apps/server/app/celery_app.py:19-76`、`apps/server/app/tasks/payment_task.py:47-66`

### Designer — 用户视角

**页面清单与结构：**
- admin 共 33 个页面模块，路由按业务域拆分为 12 个文件
- 来源：`apps/admin/src/pages/` 目录、`apps/admin/config/routes/`
- 财务中心（`/finance`）现有：支付查询、退款管理
- 来源：`apps/admin/config/routes/finance.ts`

**交互模式统计：**
- ProTable 为标准列表组件（59 个页面使用）
- 通用模式：PageContainer + ProTable + createListRequest + useListPage
- 来源：`apps/admin/src/utils/proTable.ts:175-250`、`apps/admin/src/hooks/useListPage.ts:50-124`
- 表单模式 3 种：FormPage（全页）、ModalForm（弹窗）、原生 Modal+Form
- 来源：`apps/admin/src/components/FormPage/index.tsx:1-154`

**财务/费用相关 UI：**
- 金额展示：`¥X.XX` 格式，precision={2}，suffix="元"
- 来源：`apps/admin/src/pages/payment/index.tsx:79`、`dashboard/index.tsx:255`
- 退款管理：ProTable 列表 + Drawer 详情
- 来源：`apps/admin/src/pages/refund/index.tsx:1-164`
- 积分管理：双 Tab（积分流水 + 用户积分），ModalForm 调整积分
- 来源：`apps/admin/src/pages/points/index.tsx:1-307`
- 审批/审核：Tab 切换（待办/已办/已发起），通过/拒绝用 Modal + TextArea
- 来源：`apps/admin/src/pages/approval/instances/index.tsx:1-261`

**组件一致性：**
- ProTable(59)、PageContainer(几乎所有)、ProForm(30+)、ModalForm(10+)
- ProCard(12)、StatisticCard(5)
- 来源：grep 搜索结果

**API 请求模式：**
- 51 个 API 模块在 `packages/api/src/modules/`
- 标准结构：getList / getDetail / create / update / delete
- 来源：`packages/api/src/modules/` 目录

### Engineer — 技术视角

**存储层事实：**
- 所有模型继承 Base + AuditMixin，UUID 主键 String(36)
- 来源：`apps/server/app/db/base.py:1-18`
- 金额字段统一使用 `Numeric(10, 2)`
- 来源：`apps/server/app/models/appointment.py:68`、`consultation_fee.py:36-37`
- Alembic 迁移文件命名：`{三位数字}_{snake_case描述}.py`，共 122 个迁移
- 来源：`apps/server/migrations/versions/`
- 表名规范：英文复数 snake_case（如 `appointments`、`leave_requests`）

**核心引擎事实：**
- 模块标准结构：`modules/{name}/router.py` + `service.py`
- Service 构造函数接收 `AsyncSession`
- 来源：`apps/server/app/modules/leave_requests/service.py:19-21`
- 大模块可用 Mixin 拆分 service（如 consultation_fees 的 service_types.py、service_store.py、service_doctors.py）
- 来源：`apps/server/app/modules/consultation_fees/service.py:1-16`

**API/协议事实：**
- BaseSchema 配置：alias_generator=to_camel、populate_by_name=True、from_attributes=True、by_alias=True
- 来源：`apps/server/app/schemas/base.py:6-28`
- Schema 分层：XxxBase → XxxCreate / XxxUpdate / XxxResponse / XxxQuery
- 分页响应：PageResponse[T]（含 code、message、data、total、page、page_size）
- 来源：`apps/server/app/schemas/response.py:20-33`
- 审核 API 模式：POST `/{id}/review` + require_permission("module:action")
- 来源：`apps/server/app/modules/leave_requests/router.py:123-164`

**安全机制事实：**
- 统一认证 `get_current_account()` 根据 token type 分发到 admin/doctor/user
- 权限检查 `require_permission()` 支持通配符匹配
- 多租户 Service 层手动添加 `tenant_id` 过滤条件
- 来源：`apps/server/app/common/auth_unified.py:498-551`、`permission_deps.py:104-152`

**依赖和模块耦合事实：**
- 枚举定义在 `app/enums/` 按业务域分文件，继承 `str, Enum`
- 审计工具 `set_create_audit()` / `set_update_audit()` 在 `app/utils/audit.py`
- 全局 service 仅 3 个文件（email_template_service、rule_performance_service、storage/）
- 来源：`apps/server/app/enums/`、`app/utils/audit.py`、`app/services/`

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 产品定位自洽性 | 系统扩展为运营管理平台，兼职费用属营销运营域 | Q1: 为什么挂号系统需要兼职模块 | 接受扩展定位，模块放运营中心 |
| 角色体系扩展 | 不新增 RoleType，复用 admin + 权限码 | Q2: freelancer 角色影响范围 | 权限码隔离，不改认证核心 |
| 兼职人员视角 | MVP 仅 admin 端管理 | Q3: 缺少兼职人员自身视角 | P2 再做兼职人员自助端 |
| 结算引擎复杂度 | 规则引擎 + 人工审核，非全自动 | Q4: 多阶段结算远超普通定时任务 | 系统计算 + 人工确认 |
| 流量配合判定 | 管理员手动输入金额 | Q5: 6 倍浮动区间无判定标准 | MVP 人工，后续可接入评分 |
| content 模块关系 | 独立建模，不扩展 content | Q6: 笔记与 content 概念冲突 | 不同业务域，独立更清晰 |
| 外部数据源 | MVP 人工录入，预留 API 扩展 | Q7: 点赞/评论数据从哪来 | 截图+人工录入，防作弊靠审核 |
| 结算审批 | 内置简化审核，不复用通用审批 | Q8: 结算审批与请假审批不同 | 三步流程：提交-审核-确认 |
| 数据量级 | 小规模设计（单租户 <100 人） | Q9: 规模未知 | 索引优化即可 |
| 法律合规 | 记录审计日志，税务线下处理 | Q10: 资金流转和税务 | 预留 tax_amount 字段 |
| 次日 vs 周末 | 顺延到下一个工作日 | Q11: 规则逻辑矛盾 | 计算理论日 + 自动顺延 |
| 工程深度 | 接受批评，补充技术判断 | Q12: Engineer 仅记录未判断 | Numeric(10,2) 足够 |
| 多门店结算 | 兼职人员绑定门店，按门店结算 | Q13: 多门店场景未考虑 | store_id 字段 + 门店级汇总 |
| 竞品分析 | 无成熟 SaaS，自建合理 | Q14: 为何不买独立工具 | 社交媒体兼职场景太特殊 |

### 独到发现

1. **兼职费用模块本质是"任务佣金管理"** — 不同于传统薪资/报销，核心是"发布任务 → 验证完成 → 多阶段结算"的状态机，需要独立建模而非套用现有财务模式。
2. **外部数据采集是最大技术风险** — 社交媒体平台 API 限制严格，MVP 阶段必须接受人工录入方案。
3. **多租户 + 多门店的结算维度** — 兼职人员绑定门店，结算在门店维度进行，与现有 tenant_id 隔离模式一致。

### Critic 质询

1. **[Critic -> PM] 质询 1：产品定位自洽性**
   - 论据：医院挂号系统为什么需要兼职费用模块？系统已 61 模块，继续膨胀的维护成本？
   - 要求回应：PM
   - 级别：普通

2. **[Critic -> Engineer] 质询 2：角色体系扩展影响**
   - 论据：新增角色对 get_current_account()、权限码、前端路由守卫的影响范围未评估
   - 要求回应：Engineer
   - 级别：普通

3. **[Critic -> Designer] 质询 3：缺少兼职人员视角**
   - 论据：所有 UI 分析仅 admin 视角，兼职人员自身的"我的任务/收入"页面未考虑
   - 要求回应：Designer
   - 级别：普通

4. **[Critic -> Engineer] 质询 4：结算引擎复杂度**
   - 论据：5 种规则、3 种时间点、人工例外、日历感知，远超现有 Celery 任务模式
   - 要求回应：Engineer
   - 级别：普通

5. **[Critic -> PM] 质询 5：流量配合判定标准缺失**
   - 论据：5~30 元浮动区间（6 倍），判定标准、数据源、审核流程均未定义
   - 要求回应：PM
   - 级别：普通

6. **[Critic -> 全体] 质询 6：content 模块关系**
   - 论据：兼职笔记与现有 content（News/Notice/Banner）概念重叠，扩展还是独立？
   - 要求回应：Engineer / PM
   - 级别：普通

7. **[Critic -> 全体] 质询 7：外部数据源可行性**
   - 论据：点赞/评论数据获取方式未评估，社交媒体 API 限制严格
   - 要求回应：PM / Engineer
   - 级别：普通

8. **[Critic -> Designer] 质询 8：结算审批特殊性**
   - 论据：结算审批需核实金额、展示证据、支持加急，与请假审批本质不同
   - 要求回应：Designer
   - 级别：普通

9. **[Critic -> 全体] 质询 9：数据量级**
   - 论据：预期兼职人员数量、每人每日发布量、结算任务规模均未知
   - 要求回应：PM / Engineer
   - 级别：普通

10. **[Critic -> 全体] 质询 10：法律合规**
    - 论据：税务代扣、结算周期合规性、资金流转路径、审计证据保留
    - 要求回应：PM
    - 级别：普通

11. **[Critic -> 全体] 质询 11：次日 vs 周末逻辑矛盾**
    - 论据：周五发布 → 次日周六 → 周六不结算 → 实际下周一，"次日"承诺无法兑现
    - 要求回应：PM
    - 级别：普通

12. **[Critic -> Engineer] 质询 12：技术判断缺失**
    - 论据：Engineer 仅记录事实未做判断，Numeric 精度、UUID vs 工号、迁移链影响未评估
    - 要求回应：Engineer
    - 级别：普通

13. **[Critic -> 全体] 质询 13：多门店结算复杂度**
    - 论据：兼职人员是否跨门店？结算维度是门店还是租户？统计按什么汇总？
    - 要求回应：PM / Engineer
    - 级别：普通

14. **[Critic -> PM] 质询 14：竞品分析缺失**
    - 论据：是否有成熟工具？为何自建？最小可用版本包含什么？
    - 要求回应：PM
    - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| - | 本轮未标记关键质询 | - | - | - |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：产品定位与模块归属**
   **结论：** 系统正从"预约挂号"向"医院运营管理平台"扩展。兼职费用属于营销/运营域，放在运营中心（operations）菜单下，与 content、feedback、points 同级。模块命名 `freelance_fees`，路由前缀 `/freelance-fees`。
   **建议行动：** 模块目录 `modules/freelance_fees/`，路由注册到 operations 域。
   **成本估算：** 2h（路由注册 + 菜单配置）
   **优先级：** P0

2. **议题：角色体系 — 不新增 RoleType**
   **结论：** 兼职人员不作为独立角色类型。复用现有 admin 角色体系，通过新增权限码 `freelance:*`（freelance:list、freelance:create、freelance:settle 等）控制访问。兼职人员本身是"被管理的资源"而非系统用户。
   **建议行动：** 新增权限码定义，分配给对应角色。
   **成本估算：** 1h
   **优先级：** P0

3. **议题：外部数据采集 — MVP 人工录入**
   **结论：** 社交媒体平台 API 限制严格（小红书无公开 API），MVP 阶段所有外部数据（点赞数、评论数、是否收录）由管理员手动录入。系统提供结构化录入界面，后续可考虑 API 对接或截图 OCR。
   **建议行动：** 任务表设计 `likes_count`、`comments_count`、`is_indexed` 等字段，管理员通过表单录入。
   **成本估算：** 3h（录入表单 + 数据模型）
   **优先级：** P0

4. **议题：结算逻辑 — 系统计算 + 人工确认**
   **结论：** 系统根据发布记录和录入的互动数据自动计算各项金额（基础 5 元、互动 0.5 元/条、点赞奖励 10 元），"一周后补贴 5~30 元"由管理员手动输入。结算流程：系统生成待确认结算 → 管理员审核/调整 → 确认结算。
   **建议行动：** 结算 service 实现自动计算逻辑 + 管理员调整接口。
   **成本估算：** 8h（核心结算逻辑）
   **优先级：** P0

5. **议题：结算时间 — 工作日顺延**
   **结论：** 系统计算"理论结算日"（发布日 + N 天），遇到周末或节假日自动顺延到下一个工作日。Celery Beat 每天下午 5 点扫描理论结算日 <= 今天且状态为"待结算"的记录，创建结算单。
   **建议行动：** 实现工作日计算工具函数 + Celery 定时任务。
   **成本估算：** 4h（工作日计算 + 定时任务）
   **优先级：** P0

6. **议题：独立建模，不扩展 content 模块**
   **结论：** 兼职笔记是"任务记录"而非"内容管理"，与 content 模块（News/Notice/Banner）业务语义不同。独立建模更清晰，避免污染 content 模块的职责边界。
   **建议行动：** 创建独立的 `freelance_tasks` 表。
   **成本估算：** 包含在数据模型设计中
   **优先级：** P0

7. **议题：MVP 仅 admin 端管理**
   **结论：** 第一版仅在 admin 端提供兼职费用管理功能（兼职人员管理、任务管理、结算管理）。暂不做独立的兼职人员端。管理员在后台完成所有操作。
   **建议行动：** admin 端新增 3 个页面：兼职人员列表、任务管理、结算管理。
   **成本估算：** 包含在前端开发中
   **优先级：** P0

8. **议题：多门店 — 兼职人员绑定门店**
   **结论：** 兼职人员绑定到具体门店（store_id），结算按门店维度进行。管理员查看本门店的兼职费用汇总，平台管理员可查看跨门店汇总。与现有 tenant_id + store_id 隔离模式一致。
   **建议行动：** freelancers 表含 store_id 字段。
   **成本估算：** 包含在数据模型设计中
   **优先级：** P0

9. **议题：内置简化审核流程**
   **结论：** 不复用通用审批流（approval_flows），兼职费用模块内置自己的审核流程。结算单状态：pending → confirmed → paid。管理员直接在结算页面确认/驳回，无需走多级审批。
   **建议行动：** 结算表含 status 字段 + 审核相关字段。
   **成本估算：** 2h
   **优先级：** P0

10. **议题：税务和合规 — 线下处理**
    **结论：** MVP 阶段系统不处理税务代扣。系统记录完整的审计日志（谁在什么时间确认了多少钱的结算），税务处理由财务线下完成。数据模型预留 `tax_amount` 字段。
    **建议行动：** 结算表含 tax_amount 字段（默认 0），操作日志记录所有结算操作。
    **成本估算：** 0.5h（仅字段定义）
    **优先级：** P1

### ⚡ 分歧项

1. **议题：结算审批是否复用通用审批流**
   **各方立场：**
   - PM：复用通用审批流可减少开发量
   - Designer：通用审批流无法满足结算金额核实需求
   - Engineer：内置审核更简单，通用审批流的配置成本高于收益
   **裁决：** 内置简化审核。理由：结算审批的核心是"核实金额"而非"多级审批"，通用审批流的抽象层级过高，适配成本大于收益。
   **决策依据：** 结算审批是二元决策（确认/驳回），不需要多级流转。

2. **议题：兼职人员是否需要独立登录端**
   **各方立场：**
   - PM：需要，兼职人员应能查看自己的任务和收入
   - Designer：MVP 不需要，admin 端管理即可
   - Engineer：独立端增加认证复杂度，建议后续做
   **裁决：** MVP 不做独立端。理由：当前需求描述中兼职人员不需要登录系统，所有操作在线下完成（发布笔记、互动），系统仅记录结果和管理结算。后续可做兼职人员自助查看页面。
   **决策依据：** 需求原文中兼职人员的工作内容（发布笔记、互动）均在外部平台完成，不需要系统交互。

---

## 被低估的优势

1. **现有模块结构高度一致** — router.py + service.py + BaseSchema + ProTable 的标准化程度极高，新模块可以 90% 复用现有模式，开发效率远高于从零搭建。
2. **多租户基础设施完备** — ContextVar + tenant_id 过滤 + Celery 租户遍历，兼职费用模块可以直接接入，无需额外基础设施。
3. **Celery Beat 调度成熟** — crontab 表达式 + 多队列 + 重试机制，结算定时任务可以直接复用。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 数据模型设计 + Alembic 迁移 | 4h | 高 | Engineer | 待开始 |
| P0 | 枚举定义（任务状态、结算状态） | 1h | 高 | Engineer | 待开始 |
| P0 | 后端 service + router（兼职人员 CRUD + 任务 CRUD + 结算逻辑） | 16h | 高 | Engineer | 待开始 |
| P0 | Celery 定时任务（结算扫描 + 工作日顺延） | 4h | 高 | Engineer | 待开始 |
| P0 | 前端 API 模块 | 2h | 高 | Engineer | 待开始 |
| P0 | 前端页面（兼职人员列表 + 任务管理 + 结算管理） | 12h | 高 | Designer | 待开始 |
| P0 | 权限码注册 + 路由配置 | 2h | 高 | Engineer | 待开始 |
| P1 | 结算统计报表（按门店/按人员/按时间段） | 6h | 中 | Designer + Engineer | 待开始 |
| P1 | 操作日志集成 | 2h | 中 | Engineer | 待开始 |
| P2 | 兼职人员自助查看页面 | 8h | 中 | Designer + Engineer | 待开始 |
| P2 | 社交媒体数据 API 对接 | 16h | 中 | Engineer | 待开始 |
| 待定 | 税务代扣计算 | 8h | 待定 | PM + Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **数据模型设计 + Alembic 迁移**（4h）
   - 创建 freelancers、freelance_tasks、freelance_interactions、freelance_settlements、freelance_settlement_items 5 张表
   - 包含 tenant_id、store_id 多租户隔离字段
   - 金额字段使用 Numeric(10, 2)
   - 生成 Alembic 迁移文件 123_add_freelance_fee_tables.py

2. **枚举定义**（1h）
   - 新增 `app/enums/freelance.py`
   - TaskStatus（pending/published/indexed/modified/rejected）
   - SettlementStatus（pending/confirmed/paid/cancelled）
   - InteractionType（comment/dm）
   - 在 `enums/__init__.py` 中 re-export

3. **后端 service + router**（16h）
   - 模块目录：`modules/freelance_fees/`（router.py + service.py + service_query.py + service_mutation.py）
   - API 端点：
     - `GET/POST /freelance-freelancers` — 兼职人员 CRUD
     - `GET/POST /freelance-tasks` — 发布任务 CRUD
     - `POST /freelance-tasks/{id}/interaction` — 录入互动数据
     - `GET/POST /freelance-settlements` — 结算管理
     - `POST /freelance-settlements/{id}/confirm` — 确认结算
     - `POST /freelance-settlements/{id}/reject` — 驳回结算
     - `GET /freelance-settlements/statistics` — 结算统计
   - 权限码：freelance:list、freelance:create、freelance:update、freelance:delete、freelance:settle

4. **Celery 定时任务**（4h）
   - 新增 `tasks/freelance_task.py`
   - `freelance.generate_settlements` — 每天 17:00 扫描待结算记录，生成结算单
   - 工作日顺延逻辑：计算理论结算日，跳过周末和法定节假日
   - Beat 调度：`crontab(hour=17, minute=0)`

5. **前端 API 模块**（2h）
   - 新增 `packages/api/src/modules/freelance.ts`
   - freelancersApi、freelanceTasksApi、freelanceSettlementsApi

6. **前端页面**（12h）
   - 路由配置：`apps/admin/config/routes/operations.ts` 新增兼职费用子菜单
   - 页面文件：
     - `apps/admin/src/pages/freelance/freelancers.tsx` — 兼职人员列表（ProTable）
     - `apps/admin/src/pages/freelance/tasks.tsx` — 任务管理（ProTable + ModalForm 录入互动）
     - `apps/admin/src/pages/freelance/settlements.tsx` — 结算管理（ProTable + Drawer 详情 + 确认/驳回）

7. **权限码注册 + 路由配置**（2h）
   - 权限码定义在 `common/role_permissions.py`
   - 前端路由 access 配置

### P1：本轮迭代（高价值、中等成本）

1. **结算统计报表**（6h）
   - 按门店汇总、按人员汇总、按时间段汇总
   - 使用 StatisticCard + ProTable 展示

2. **操作日志集成**（2h）
   - 结算确认/驳回操作记录到 audit_logs

### P2：下个周期规划（中等价值、较高成本）

1. **兼职人员自助查看页面**（8h）
   - 独立 H5 页面或小程序页面
   - 兼职人员查看自己的任务和收入

2. **社交媒体数据 API 对接**（16h）
   - 小红书/抖音数据采集
   - 自动更新点赞数、评论数

### 待定：需用户确认

1. **税务代扣计算**（8h）
   - 是否需要系统自动计算个税？
   - 需要确认税务规则和起征点

---

## 数据模型设计

### 表 1：freelance_freelancers（兼职人员）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 主键 |
| tenant_id | String(36) | 租户 ID，FK -> tenants.id |
| store_id | String(36) | 绑定门店，FK -> stores.id |
| name | String(50) | 姓名 |
| phone | String(20) | 手机号 |
| account_name | String(100) | 社交媒体账号名 |
| account_platform | String(20) | 平台（xiaohongshu/douyin/weibo） |
| account_type | String(20) | 账号类型（old/new） |
| status | Integer | 状态（0 禁用 / 1 正常） |
| remark | Text | 备注 |
| created_at / updated_at / created_by / updated_by | AuditMixin | 审计字段 |

### 表 2：freelance_tasks（发布任务）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 主键 |
| tenant_id | String(36) | 租户 ID |
| store_id | String(36) | 门店 ID |
| freelancer_id | String(36) | 兼职人员 ID，FK -> freelance_freelancers.id |
| title | String(200) | 笔记标题 |
| content_url | String(500) | 笔记链接 |
| published_at | DateTime | 发布时间 |
| status | Integer | 状态：0 待发布 / 1 已发布 / 2 已收录 / 3 需修改 / 4 已拒绝 |
| is_indexed | Boolean | 是否被平台收录 |
| likes_count | Integer | 点赞数（管理员录入） |
| comments_count | Integer | 评论数（管理员录入） |
| base_amount | Numeric(10,2) | 基础金额（5 元） |
| bonus_amount | Numeric(10,2) | 一周后补贴金额（管理员输入 5~30） |
| likes_bonus_amount | Numeric(10,2) | 点赞奖励（0 或 10） |
| planned_base_settle_at | DateTime | 理论基础结算日（发布次日，顺延到工作日） |
| planned_bonus_settle_at | DateTime | 理论补贴结算日（发布后第 7 天，顺延到工作日） |
| planned_likes_settle_at | DateTime | 理论点赞奖励结算日（发布后第 22 天，顺延到工作日） |
| remark | Text | 备注 |
| created_at / updated_at / created_by / updated_by | AuditMixin | 审计字段 |

### 表 3：freelance_interactions（互动记录）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 主键 |
| tenant_id | String(36) | 租户 ID |
| task_id | String(36) | 关联任务，FK -> freelance_tasks.id |
| interaction_type | String(20) | 类型：comment / dm |
| content | Text | 互动内容（管理员录入） |
| amount | Numeric(10,2) | 金额（0.5 元/条） |
| interacted_at | DateTime | 互动时间 |
| created_at / updated_at / created_by / updated_by | AuditMixin | 审计字段 |

### 表 4：freelance_settlements（结算单）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 主键 |
| tenant_id | String(36) | 租户 ID |
| store_id | String(36) | 门店 ID |
| freelancer_id | String(36) | 兼职人员 ID |
| settlement_no | String(32) | 结算单号（自动生成） |
| period_start | DateTime | 结算周期开始 |
| period_end | DateTime | 结算周期结束 |
| base_total | Numeric(10,2) | 基础金额合计 |
| bonus_total | Numeric(10,2) | 补贴金额合计 |
| likes_bonus_total | Numeric(10,2) | 点赞奖励合计 |
| interaction_total | Numeric(10,2) | 互动金额合计 |
| total_amount | Numeric(10,2) | 总金额 |
| tax_amount | Numeric(10,2) | 税额（默认 0） |
| actual_amount | Numeric(10,2) | 实际支付金额（total - tax） |
| status | Integer | 状态：0 待确认 / 1 已确认 / 2 已支付 / 3 已驳回 |
| confirmed_at | DateTime | 确认时间 |
| confirmed_by | String(36) | 确认人 |
| paid_at | DateTime | 支付时间 |
| reject_reason | Text | 驳回原因 |
| remark | Text | 备注 |
| created_at / updated_at / created_by / updated_by | AuditMixin | 审计字段 |

### 表 5：freelance_settlement_items（结算明细）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String(36) | 主键 |
| settlement_id | String(36) | 结算单 ID，FK -> freelance_settlements.id |
| item_type | String(20) | 明细类型：base / bonus / likes_bonus / interaction |
| task_id | String(36) | 关联任务 ID（可为空） |
| interaction_id | String(36) | 关联互动 ID（可为空） |
| description | String(200) | 描述 |
| amount | Numeric(10,2) | 金额 |
| created_at | DateTime | 创建时间 |

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 10 项达成共识
- 模块归属运营中心、不新增角色类型、MVP 人工录入外部数据、系统计算+人工确认结算、工作日顺延、独立建模、admin 端管理、门店级结算、内置审核、税务线下处理

**关键分歧：** 2 项需权衡
- 结算审批复用 vs 内置（裁决：内置）
- 兼职人员独立端 vs admin 端（裁决：MVP 不做）

**Top 3 P0 行动：**
1. 数据模型设计 + Alembic 迁移（4h）
2. 后端 service + router — 核心业务逻辑（16h）
3. 前端页面 — 兼职人员/任务/结算管理（12h）

**Critic 关键洞察：**
- 产品定位从"预约挂号"扩展到"运营管理平台"是本模块存在的前提
- 外部数据采集（社交媒体点赞/评论）是最大技术风险，MVP 必须接受人工录入
- "次日结算"与"周末不结算"存在逻辑矛盾，需用工作日顺延解决

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| - | - | - | 未切换 |
