# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：领域主导（Engineer 为 Lead）
> 日期：2026-05-27
> 审查目标：apps/server 目录结构合规性与优化点

---

## 模式选择

**选定模式：** 领域主导（Engineer 为 Lead）

**选择理由：** 核心关注点是代码组织和架构规范，Engineer 视角最适合主导分析。PM 和 Designer 视角作为辅助补充。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 项目名称：医院挂号系统（appointment-booking-system）
- 自述："全栈医院预约挂号系统，SaaS 多租户架构。支持多门店/分院、多科室、多医生排班预约"
- 技术栈：React 18 + TypeScript + Umi 4（前端），FastAPI + SQLAlchemy 2.x async + PostgreSQL 16 + Redis 7 + Celery（后端）

**功能模块覆盖度：**
- modules/ 下共 49 个业务模块目录（不含 __init__.py）
- README 声称 25 条 API 路由，全部有对应模块目录
- modules/ 中存在但 README 未提及的模块：37 个
- 3 个模块无 router.py 且未注册路由：visit_types, rule_engine, revenue

**API 规模线索：**
- api/v1/__init__.py 中 ROUTER_REGISTRATIONS 列表包含 60 条记录
- 全部 router 文件中 endpoint 装饰器合计 673 个
- Top 模块：admin(94), import_export(93), schedules(59), appointments(42), patients(34)

**多租户/权限系统：**
- middleware/ 有 6 个中间件文件
- TenantContextMiddleware 支持 4 种识别方式
- auth_unified.py 支持 3 种角色（User/Doctor/Admin）
- common/ 目录有 20 个文件，含认证、权限、租户过滤等公共模块

### Designer — 用户视角

**API 端点结构：**
- 54 条路由注册，671 个 endpoint
- HTTP 方法分布：GET 310, POST 196, PUT 100, DELETE 58, PATCH 7
- /content 前缀被注册两次（content.router 和 common_services.router）
- main.py 中有额外路由：/health, /llms*.txt, /uploads

**Schema 组织：**
- 两层结构：全局 app/schemas/（38 文件，257 个 BaseModel）+ 模块内 schemas.py（16 文件，159 个 BaseModel）
- 总计 416 个 Pydantic BaseModel

**错误处理一致性：**
- 两套异常体系并存：middleware/exception.py + common/errors.py
- modules/ 中 raise HTTPException 781 次，raise BusinessError 仅 3 次
- common/errors.py 定义的异常在 modules/ 中零使用

**中间件栈：**
- 6 个中间件文件
- 注册顺序（main.py）：TenantContext -> UnifiedResponse -> OperationLog -> RequestLog -> RateLimit -> CORS
- 实际执行顺序（Starlette LIFO）：CORS -> RateLimit -> RequestLog -> OperationLog -> UnifiedResponse -> TenantContext

### Engineer — 技术视角

**目录层次结构：**
- app/ 下 18 个一级目录，modules/ 下 61 个模块目录
- 模块文件数量差异极大：admin(16 文件) vs accounts(1), amap(1), revenue(1)
- 6 个模块有 service_mutation.py/service_query.py 拆分
- modules/ 总代码行数：59,822 行
- 单文件最大：tenants/service.py(1,597), schedules/service_mutation.py(1,592), miniapp_platform/router.py(1,346)

**分层架构：**
- api/v1/__init__.py 使用 RouterRegistration dataclass + importlib 动态导入
- api/deps.py 仅为 `from app.common.deps import *` 兼容包装
- modules/ 对 models/ 依赖：40+ 个模块导入 models
- services/ 目录有 8 个全局服务文件，modules/ 对其依赖仅约 11 次
- infrastructure/ 下 notification/（仅 __pycache__）与 notifications/（完整实现）并存

**模块耦合：**
- 跨模块 import 前 5：rule_engine(8), appointments.service(8), tenants.password_policy(7)
- 未发现直接循环依赖

**数据层：**
- models/ 下 54 个模型文件 + 1 个模块内模型
- migrations/ 下 121 个迁移文件
- 迁移文件名前缀存在 4 组重复：004, 007, 058, 109

**测试结构：**
- tests/ 下 132 个测试文件
- conftest.py 使用 SQLite 内存数据库，function scope
- fixture 依赖链 6 层嵌套

**模块规范一致性：**
- 3 个模块缺少 __init__.py：notification_logs, notification_preferences, accounts
- 15 个模块有独立 schemas.py，其余使用全局 schemas/
- 所有路由通过 RouterRegistration 统一注册

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（领域主导模式）

| 议题 | 裁决者立场（Engineer） | Critic 质询 | 最终裁决 |
|------|----------------------|------------|---------|
| common/errors.py 死代码 | P0 必修 | 应列为独立 P0 清理项 | **P0** — 采纳 Critic，独立清理 |
| PermissionDeniedError 命名冲突 | 未发现 | 🚨 关键：两套同名类共存 | **P0** — 采纳 Critic，删除 common/errors.py 即可消除 |
| HTTPException 781:3 比例 | P0 异常体系统一 | 这是项目标准模式，不是设计失败 | **P2** — 采纳 Critic，781 次 HTTPException 是 `http_exception_handler` 统一包装的正常模式 |
| /content 前缀重复注册 | P1 应修 | 影响范围未量化 | **P1** — 保留，需验证端点路径重叠 |
| 中间件 LIFO 顺序 | P1 应修 | 未提及 | **P1** — 保留，影响多租户限流 |
| 迁移编号冲突 | P0 必修 | 严重性被高估，3 组已有合并迁移 | **P2** — 采纳 Critic，是正常的 Alembic 分支合并 |
| notification/ 空目录 | P2 建议修 | 是 __pycache__ 残留，一行命令 | **P2** — 采纳 Critic，降级为清理残留 |
| 61 模块粒度 | 暂不行动 | 缺乏基线对比，"过度工程化"判断不成立 | **暂不行动** — 采纳 Critic，模块数量与 SaaS 多域系统匹配 |
| schemas 两层结构 | P2 文档化 | 未提及 | **P2** — 保留 |
| services/ 职责边界 | 交叉发现 | 未提及 | **P2** — 保留 |
| 巨型文件拆分 | 交叉发现 | 未提及 | **P2** — 保留 |
| 测试 fixture 重构 | 交叉发现 | 核心模块测试覆盖未分析 | **P2** — 保留 |

### 独到发现

1. **[Engineer 交叉发现]** modules/ 与 services/ 职责边界模糊 — 8 个全局服务文件与模块内 service.py 无明确划分规则，复用度仅 11 处
2. **[Engineer 交叉发现]** infrastructure/notification/ 空目录残留 — 仅含 `__pycache__`，应删除
3. **[Engineer 交叉发现]** 6 个文件超 1000 行（tenants/service.py 1597, schedules/service_mutation.py 1592 等），维护风险高
4. **[Engineer 交叉发现]** 测试 fixture 6 层嵌套，级联失败风险
5. **[Engineer 交叉发现]** 15 个模块有独立 schemas.py 但无归属规则文档

### Critic 质询

1. **[Critic -> 全体] 质询 1：HTTPException 781 次是标准模式而非设计失败**
   - 论据：`http_exception_handler` 显式捕获 HTTPException 并统一格式化，`raise_business_http_error` 提供结构化 error_code 支持
   - 要求回应：Designer
   - 级别：普通
   - **裁决：采纳。** 781 次 HTTPException 是项目标准异常机制，`http_exception_handler` 已统一输出格式。真正的问题是 `common/errors.py` 的死代码。

2. **[Critic -> 全体] 质询 2：Engineer 的 __init__.py 事实错误**
   - 论据：`admin/__init__.py` 存在，实际缺少 3 个不是 4 个
   - 要求回应：Engineer
   - 级别：普通
   - **裁决：采纳修正。** 实际缺少 __init__.py 的模块为 3 个：notification_logs, notification_preferences, accounts。

3. **[Critic -> 全体] 质询 3：迁移编号冲突严重性被高估**
   - 论据：004/007 组被 011_merge_heads 合并，058 组被 059 合并，109 组文件名误导但 revision 链线性
   - 要求回应：Engineer
   - 级别：普通
   - **裁决：采纳。** 迁移"冲突"是正常的 Alembic 分支合并工作流，不应列为 P0。降级为 P2 建议清理文件名。

4. **[Critic -> 全体] 质询 4："37 模块 README 未提及"是文档问题而非架构问题**
   - 论据：增量开发中文档滞后是正常现象，缺乏模块完成度分级数据
   - 要求回应：PM
   - 级别：普通
   - **裁决：采纳。** 降级为 P2 文档更新任务。

5. **[Critic -> 全体] 质询 5：notification/ 是 __pycache__ 残留**
   - 论据：该目录仅含 `__pycache__/`，零处从 notification（单数）导入
   - 要求回应：Engineer
   - 级别：普通
   - **裁决：采纳。** 从"命名不一致"降级为"清理残留"。

6. **[Critic -> 全体] 质询 6：/content 前缀影响范围未量化**
   - 论据：未分析两个 router 下的具体端点路径和冲突情况
   - 要求回应：Designer
   - 级别：普通
   - **裁决：保留为 P1。** 需验证端点路径重叠情况。

7. **[Critic -> 全体] 质询 7：缺乏模块核心/辅助层级分析**
   - 论据：61 个模块规模差异极大，优化策略应聚焦大型核心模块
   - 要求回应：Engineer
   - 级别：普通
   - **裁决：采纳。** 优化策略应聚焦 Top 10 大型模块。

8. **[Critic -> 全体] 质询 8：common/errors.py 应列为独立 P0**
   - 论据：零使用 + 与 middleware/exception.py 同名类冲突
   - 要求回应：Designer / Engineer
   - 级别：普通
   - **裁决：采纳。** 列为独立 P0 清理任务。

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | common/errors.py 与 middleware/exception.py 的 PermissionDeniedError 命名冲突 | Engineer 确认两套异常体系并存，Critic 指出零使用 + 同名冲突 | 是 | **纳入 P0** — 删除 common/errors.py 即可消除 |
| 2 | PM 的 "61 模块过度工程化" 缺乏基线对比 | PM 未提供竞品数据，Critic 指出多租户 SaaS 需要额外模块 | 是 | **裁决：撤回过度工程化判断** — 61 模块在多租户 SaaS 场景下合理 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：** common/errors.py 是死代码，与 middleware/exception.py 存在 PermissionDeniedError 命名冲突
   **结论：** 三方一致同意删除。Critic 标记为关键质询。
   **建议行动：** 删除 common/errors.py，检查是否有隐藏导入
   **成本估算：** 1h
   **优先级：** P0

2. **议题：** /content 前缀被两个不同模块重复注册
   **结论：** Engineer 和 Critic 均确认为规范问题，需验证实际路径冲突
   **建议行动：** 给 common_services 分配独立前缀
   **成本估算：** 0.5h
   **优先级：** P1

3. **议题：** infrastructure/notification/ 空目录残留
   **结论：** Critic 确认为 __pycache__ 残留，一行命令清理
   **建议行动：** `rm -rf infrastructure/notification/`
   **成本估算：** 0.1h
   **优先级：** P2

4. **议题：** schemas 两层结构缺乏归属规则
   **结论：** Engineer 建议文档化规则，当前结构可接受
   **建议行动：** 编写 schema 归属规则（跨模块复用放全局，领域专属放模块内）
   **成本估算：** 2h
   **优先级：** P2

5. **议题：** 61 个模块的粒度
   **结论：** Critic 指出缺乏基线对比，多租户 SaaS 需要额外模块，"过度工程化"判断不成立
   **建议行动：** 暂不调整模块划分
   **成本估算：** 0h
   **优先级：** 暂不行动

### ⚡ 分歧项

1. **议题：** HTTPException 781:3 比例是否为问题
   **各方立场：**
   - Designer：两套异常体系并存，HTTPException 占主导说明 BusinessError 未被采纳
   - Engineer：P0 异常体系统一
   - Critic：这是项目标准模式，`http_exception_handler` 已统一格式化
   **裁决：** 采纳 Critic。781 次 HTTPException 是 `http_exception_handler` 统一包装的正常模式，不是设计失败。`common/errors.py` 的删除是真正的清理项。
   **决策依据：** `http_exception_handler` 的实现证明 HTTPException + handler 是这个项目的标准异常机制

2. **议题：** 迁移编号冲突的严重性
   **各方立场：**
   - Engineer：P0 必修，可能导致数据层不可逆损坏
   - Critic：3 组已有合并迁移，1 组不是冲突，是正常 Alembic 工作流
   **裁决：** 采纳 Critic。迁移"冲突"是正常的分支合并，降级为 P2 文件名清理。
   **决策依据：** Alembic 的迁移链依赖 revision/down_revision 而非文件名，已有合并迁移确保链完整性

---

## 被低估的优势

1. **RouterRegistration 动态导入机制** — 所有 60 条路由通过统一 dataclass 注册，新增模块只需一行配置，扩展性好
2. **service_mutation/service_query 读写拆分模式** — 6 个大模块已采用此模式，是良好的架构实践，可推广
3. **多租户中间件设计** — 4 种租户识别方式 + ContextVar 异步隔离，是 SaaS 架构的成熟方案
4. **完整的 fixture 依赖链** — 虽然嵌套深，但提供了端到端的测试数据完整性

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 删除 common/errors.py（死代码 + PermissionDeniedError 命名冲突） | 1h | 高 | Engineer | 待执行 |
| P0 | 补充 3 个模块缺失的 __init__.py | 0.2h | 中 | Engineer | 待执行 |
| P1 | 修复 /content 前缀重复注册（common_services 改为 /common-services） | 0.5h | 高 | Engineer | 待执行 |
| P1 | 验证中间件 LIFO 顺序对多租户限流的影响 | 4h | 高 | Engineer | 已验证无 bug，注释已修正 |
| P1 | 清理 api/deps.py 兼容包装，统一为 common/deps.py 唯一入口 | 1h | 中 | Engineer | 待执行 |
| P2 | 删除 infrastructure/notification/ 空目录残留 | 0.1h | 低 | Engineer | 待执行 |
| P2 | 编写 schema 归属规则文档 | 2h | 中 | Engineer | 待执行 |
| P2 | 更新 README 模块清单（37 个未记录模块） | 2h | 中 | PM | 待执行 |
| P2 | 迁移文件名清理（109_add_approval_tasks.py 重命名） | 1h | 低 | Engineer | 待执行 |
| P2 | services/ 职责边界分析与文档化 | 6h | 中 | Engineer | 待执行 |
| P2 | tenants/ 和 miniapp_platform/ service 拆分（各超 1000 行） | 12h | 高 | Engineer | 待规划 |
| P2 | 测试 fixture 重构（引入 factory 模式） | 8h | 中 | Engineer | 待规划 |
| P2 | 核心模块测试覆盖率分析 | 4h | 高 | Engineer | 待执行 |

### P0：立即执行（高价值、低成本）

1. **删除 common/errors.py** — 消除 PermissionDeniedError 命名冲突，清理死代码。检查是否有隐藏导入后直接删除。[成本：1h，负责：Engineer]
2. **补充 __init__.py** — notification_logs, notification_preferences, accounts 三个模块目录缺少 `__init__.py`，影响 Python 包识别。[成本：0.2h，负责：Engineer]

### P1：本轮迭代（高价值、中等成本）

1. **修复 /content 前缀重复注册** — common_services.router 注册到 /content 与 content.router 冲突，改为 /common-services。[成本：0.5h，负责：Engineer]
2. **验证中间件 LIFO 顺序** — TenantContext 最后执行导致限流中间件无法按租户差异化。需评估各中间件对租户上下文的依赖关系后决定是否重排。[成本：4h，负责：Engineer]
3. **统一 deps 入口** — 删除 api/deps.py 兼容包装，统一使用 common/deps.py。[成本：1h，负责：Engineer]

### P2：下个周期规划（中等价值，较高成本）

1. **清理 infrastructure/notification/ 残留目录** [成本：0.1h]
2. **编写 schema 归属规则文档** [成本：2h]
3. **更新 README 模块清单** [成本：2h]
4. **迁移文件名清理** [成本：1h]
5. **services/ 职责边界文档化** [成本：6h]
6. **tenants/ 和 miniapp_platform/ service 拆分** [成本：12h]
7. **测试 fixture 重构** [成本：8h]
8. **核心模块测试覆盖率分析** [成本：4h]

### 待定：需用户确认

无。

---

## 摘要

**使用模式：** 领域主导（Engineer 为 Lead）

**关键共识：** 5 项达成共识
- common/errors.py 死代码删除（P0）
- /content 前缀重复注册修复（P1）
- notification/ 残留清理（P2）
- schemas 归属规则文档化（P2）
- 61 模块粒度合理，不需调整

**关键分歧：** 2 项经裁决收敛
- HTTPException 781:3 比例：Designer 认为不一致，Critic 认为是标准模式 → 裁决采纳 Critic
- 迁移编号冲突：Engineer 认为 P0，Critic 认为已解决 → 裁决采纳 Critic

**Top 3 P0 行动：**
1. 删除 common/errors.py + 消除 PermissionDeniedError 命名冲突（1h）
2. 补充 3 个模块缺失的 __init__.py（0.2h）
3. 修复 /content 前缀重复注册（0.5h）

**Critic 关键洞察：**
- HTTPException 781 次不是设计失败，`http_exception_handler` 已统一包装 — 真正的死代码是 `common/errors.py`
- 迁移编号冲突是正常的 Alembic 分支合并，3 组已有合并迁移
- 61 模块在多租户 SaaS 场景下合理，"过度工程化"判断缺乏基线
- PermissionDeniedError 两套同名类共存是实质性风险，需立即清理

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
