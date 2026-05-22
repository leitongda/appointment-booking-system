# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-22
> 审查目标：为 admin 端添加字典功能，并将系统内部分数据迁移到字典管理

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合功能规划任务无明确主导领域，集中调度可快速收敛且输出完整度最高。Team Lead 协调并行研究，自行完成交叉验证和裁决。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约
- 三端架构：机构端(admin)、患者端(H5+小程序)、医生端(doctor)
- 技术栈：React 18 + Umi 4 + Ant Design 5 + ProComponents / Python 3.12 + FastAPI + SQLAlchemy 2.x(async) + PostgreSQL 16

**功能完成度：**
- 机构端 13 个声称功能全部已实现，额外实现 11 个未列出功能（租户管理、审批流、支付等）
- 患者端 9 个声称功能全部已实现，额外实现 6 个功能
- 医生端 9 个声称功能全部已实现，额外实现 4 个功能

**系统内硬编码数据调查 — 后端 Python 枚举（46 个 Enum 类）：**

models 层枚举（9 个）：
- `FeedbackType` (feedback.py:7) — suggestion/complaint/bug/other
- `FeedbackStatus` (feedback.py:15) — pending/processing/resolved/closed
- `MessageType` (message.py:8) — appointment/consultation/schedule/system/stop_clinic/feedback
- `RequestType` (leave_request.py:7) — stop_clinic/schedule_change
- `RequestStatus` (leave_request.py:13) — pending/approved/rejected/cancelled
- `SupportTicketType` (support_ticket.py:11) — suggestion/complaint/bug/other
- `SupportTicketStatus` (support_ticket.py:20) — pending/processing/resolved/closed
- `SupportTicketPriority` (support_ticket.py:29) — low/medium/high/urgent
- `EmailTemplateType` (email_template.py:7) — 12 种邮件模板类型

schemas 层枚举（20+ 个）：AppointmentType, ScheduleMode, NotificationChannel, NotificationStatus, Platform, EventType, ExtraQuotaType, ApprovalStatus, ActionType, TimeUnit, VisitScope 等。多处与 models 层枚举重复定义。

module 层枚举（7 个，unified_message/schemas.py）：NotificationEventType, NotificationStatus, DeliveryStatus, ChannelType, Priority, StrategyType, RuleType

common/core 层枚举（3 个）：RoleType, EventType(events), WSMessageType

**系统内硬编码数据调查 — 前端常量：**

shared/constants/ 目录（8 个文件）：STATUS, TIME_SLOT, SCHEDULE_STATUS, WEEKDAY, APPOINTMENT_TYPE, SCHEDULE_MODE, APPOINTMENT_STATUS, APPOINTMENT_SOURCE, REFUND_STATUS, GENDER, DOCTOR_TITLE, PATIENT_RELATIONSHIP, MINIAPP_THEME_PRESETS 等

admin/constants/ 目录（3 个文件）：EDUCATION_OPTIONS, TIME_SLOT_OPTIONS, WEEKDAY_OPTIONS, APPOINTMENT_STATUS_OPTIONS, SCHEDULE_STATUS_OPTIONS, YES_NO_OPTIONS, NOTICE_TYPE_OPTIONS, NEWS_TYPE_OPTIONS, BANNER_LINK_TYPE_OPTIONS, BANNER_POSITION_OPTIONS, EMAIL_TEMPLATE_TYPE_OPTIONS, 以及 rule-set.ts 中 10+ 个规则引擎选项

admin 页面内联硬编码（16+ 处）：PROCESSING_METHOD_OPTIONS, COPY_CONTENT_OPTIONS, QUOTA_TYPE_OPTIONS, PAGE_STYLE_OPTIONS, EDUCATION_OPTIONS(重复), TARGET_TYPE_OPTIONS, PRIORITY_OPTIONS, MESSAGE_TYPE_OPTIONS(重复), SEND_MODE_OPTIONS, RULE_TYPE_OPTIONS, EVENT_TYPE_OPTIONS, RELATIONSHIP_OPTIONS(重复), ID_CARD_TYPE_OPTIONS, TYPE_OPTIONS 等

**适合迁移到字典管理的数据（25 项）：**
- 医生职称、学历选项、证件类型、就诊人关系、反馈类型、消息类型、公告类型、新闻类型、轮播图链接类型/位置、预约须知类型、邮件模板类型、通知事件类型、接收人规则类型、工单类型/优先级、停诊处置方式、公告目标类型/优先级、消息发送模式、医生页面风格、小程序主题、默认时段配置、预约类型、预约来源、加号类型

**不适合迁移到字典管理的数据：**
- 通用状态(0/1)、性别、星期、排班时段标识、预约状态(状态机耦合)、排班状态(状态机耦合)、审批状态/动作(引擎耦合)、角色类型(认证核心)、WebSocket 消息类型(协议层)、排班方式(算法耦合)、规则引擎选项(技术性枚举)、安全相关配置

**关键发现：**
- 系统内无现有字典功能，grep 搜索 "dict"/"dictionary"/"字典" 在 admin 前端无结果
- 多个硬编码数据存在重复定义（EDUCATION_OPTIONS 在 admin/constants 和 doctor/form.tsx 各定义一次；MESSAGE_TYPE_OPTIONS 在 message/templates.tsx 和 message/form.tsx 各定义一次）
- 后端枚举存在 models 层和 schemas 层双重定义（FeedbackType, MessageType, RequestType 等）
- ShiftType 已有数据库表和完整 CRUD 模块，是系统中"可配置枚举数据"的先例模式

### Designer — 用户视角

**页面清单与结构：**
- admin 端共 14 个页面目录，schedule(10059行) 和 system(9678行) 最复杂
- 22 个管理类页面具有列表+新增+编辑 CRUD 模式

**CRUD 页面交互模式：**
- 列表组件：全部使用 ProTable（53 个文件）
- 搜索/筛选：模式 A — createListRequest(28 页面)；模式 B — toProTableResult 手动包装(17 页面)
- 新增/编辑：模式 A — 独立 FormPage 表单页(23 文件)；模式 B — ModalForm 弹窗(约 10 页面)
- 删除：Popconfirm 简单确认(33 页面)；增强 ConfirmModal（带影响范围）；批量删除仅 5 页面
- 详情：独立页面（多数）或 Drawer/Modal（少数）

**通用组件和 Hook：**
- ListOperations 组件（CreateButton, OperationButton, OperationGroup, createOperationColumn）：13 页面使用
- FormPage 组件：23 文件使用
- useListPage hook：27 页面使用
- useFormInitialValues / useFormSubmit hooks：各 9 文件使用
- createListRequest / toProTableResult 工具函数：28 / 17 页面使用

**两种列表页实现风格：**
- 统一风格（useListPage + createListRequest + ListOperations）：约 27 页面（代表：shift-types, email-templates, user, role, banner）
- 手写风格（手动 actionRef + toProTableResult + 手写操作列）：约 17 页面（代表：department, store, doctor）

**路由结构：**
- 一级菜单：平台管理、医疗服务、财务中心、组织架构、运营中心、审批中心、系统管理
- 已有"字典类"路由分布：班次类型在"组织架构 > 医疗配置"下，诊费类型在"医疗服务 > 诊费管理"下
- 无"字典管理"独立路由分组

**参考页面（字典管理最相似的现有 CRUD 页面）：**
- 班次类型管理（shift-types.tsx 139行 + shift-type-form.tsx 158行）— 最简洁的 CRUD 示例
- 诊费类型管理（consultation-fee-types.tsx 96行 + consultation-fee-type-form.tsx 136行）
- 邮件模板管理（email-templates.tsx 188行 + email-template-form.tsx 189行）

### Engineer — 技术视角

**后端模块结构：**
- 56 个路由注册，通过 RouterRegistration dataclass 动态 import
- 标准模块组成：router.py + service.py + schemas.py(可选) + model 在 app/models/
- 两种 service 模式：组合模式（QueryMixin + MutationMixin）和单一 class 模式

**现有字典/配置相关模型：**
- SystemSetting（settings.py）— key-value 存储，支持 category 分组和 store 级覆盖
- ShiftType（shift_type.py）— 独立字典实体，字段：id, code(unique), name, description, enabled, tenant_id

**后端枚举使用模式：**
- 数据库存储：String 列 + default=EnumClass.VALUE.value
- Pydantic schema：枚举作为字段类型
- 枚举在 models 和 schemas 间重复定义

**前端 API 模块结构：**
- 51 个 TypeScript API 模块，统一模式：import request + 定义接口 + 导出 xxxApi 对象
- packages/api/src/index.ts 统一 re-export

**数据库迁移：**
- 迁移文件在 migrations/versions/，使用顺序整数 revision ID
- 最新迁移编号：109

**认证和权限模式：**
- 认证依赖注入：get_current_admin / get_current_super_admin / get_current_account
- 权限控制：require_permission("xxx:xxx") 装饰器式依赖注入
- 租户隔离：所有业务表有 tenant_id 字段

---

## Round 2：辩论层

### 交叉评论投票矩阵（简化版 — 集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 字典模型设计 | 通用字典引擎（一张表存所有字典） | 通用引擎 vs 结构化字典的选择 | 采用通用字典引擎，type + item 两层结构 |
| 迁移分批策略 | 25 项按优先级分批迁移 | appointment_type 深度耦合风险 | 分三批：纯显示类 → 有状态流转类 → 深度耦合类 |
| schemas 枚举 vs 字典可配置性 | 需要明确方案 | Pydantic 枚举校验与字典动态性的根本矛盾 | 分两类处理：显示类改 str，核心业务类保留枚举 |
| 三端同步策略 | 需要统一 API | 三端字典数据同步策略空白 | 统一字典 API，admin 管理 API + 公开查询 API |
| 路由位置 | 待定 | 集中式 vs 分散式 | 集中在"系统管理"下，但提供快捷入口 |
| 字典缓存策略 | 待定 | 前端缓存策略空白 | Redis 后端缓存 + 前端 localStorage 持久化 |
| 字典变更实时性 | 待定 | 已打开页面如何感知变更 | MVP 接受延迟（刷新页面生效） |
| 层级覆盖机制 | 待定 | SystemSetting 的 store_id 覆盖模式 | 字典统一为租户级隔离，不支持门店级覆盖 |

### 独到发现

1. **后端枚举重复定义是字典化的附带收益**：FeedbackType 在 models/feedback.py 和 schemas/feedback.py 各定义一次，字典化后可消除这种重复，减少维护负担
2. **ShiftType 是字典化的最佳参考实现**：已有完整 model + service + router + admin CRUD 页面，可作为字典模块的模板
3. **admin 页面内联硬编码（16+ 处）比 shared/constants 更急需治理**：这些内联定义无法被其他端复用，且存在重复定义问题

### Critic 质询

1. [Critic -> PM] 质询 1：appointment_type 在后端被引用 75 处，是否低估了迁移风险？
   - 论据：appointment_type 深度嵌入排班任务生成逻辑（schedule_task.py 第 261、581 行）
   - 要求回应：重新评估迁移优先级
   - 级别：普通

2. [Critic -> PM] 质询 2：FeedbackStatus 和 SupportTicketStatus 的分类决策遗漏
   - 论据：两者都有状态流转逻辑，但未被明确分类为"适合"或"不适合"迁移
   - 要求回应：补充分类决策
   - 级别：普通

3. [Critic -> PM] 质询 3：25 项迁移清单缺少患者端和小程序端影响评估
   - 论据：三端架构但评估仅聚焦 admin 端
   - 要求回应：确认三端影响范围
   - 级别：普通

4. [Critic -> Designer] 质询 4：字典页面是否需要排序和批量操作
   - 论据：字典数据有层级关系（职称、学历），且不应硬删除
   - 要求回应：明确排序和删除策略
   - 级别：普通

5. [Critic -> Designer] 质询 5：两种列表页风格应选哪种
   - 论据：27 页面统一风格 vs 17 页面手写风格混用
   - 要求回应：确认字典页面采用的风格
   - 级别：普通

6. [Critic -> Designer] 质询 6：字典路由位置——集中式 vs 分散式
   - 论据：现有字典类数据分散在不同路由下
   - 要求回应：评估两种方案利弊
   - 级别：普通

7. [Critic -> Engineer] 质询 7：字典 API 是否需要批量查询
   - 论据：页面可能同时需要 3-5 个字典，前端无缓存机制
   - 要求回应：设计批量查询接口和前端缓存策略
   - 级别：普通

8. [Critic -> Engineer] 质询 8：数据迁移方案是否考虑零停机和回滚
   - 论据：迁移涉及建表、seed 数据、逐步切换三步
   - 要求回应：设计分阶段迁移方案
   - 级别：普通

9. [Critic -> Engineer] 质询 9：字典是否需要层级覆盖机制
   - 论据：SystemSetting 支持 store_id 覆盖，"默认时段配置"已有此能力
   - 要求回应：明确层级覆盖策略
   - 级别：普通

10. [Critic -> PM + Engineer] 质询 10：字典化后 schemas 层枚举如何处理
    - 论据：枚举校验与字典可配置性存在根本矛盾
    - 要求回应：明确技术方案
    - 级别：普通

11. [Critic -> PM + Designer + Engineer] 质询 11：字典变更后已打开页面如何感知
    - 论据：admin 端无全局状态管理库
    - 要求回应：确定实时性要求
    - 级别：普通

12. [Critic -> PM + Engineer] 质询 12：新增字典类型是否需要改代码
    - 论据：通用引擎 vs 结构化字典的选择影响扩展性
    - 要求回应：明确设计边界
    - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| A | appointment_type 深度耦合排班逻辑，75 处引用，迁移风险高 | Team Lead 裁决：从第一批移除，待框架稳定后第三批迁移 | 是 | 纳入计划：第三批迁移 |
| B | Pydantic 枚举校验与字典可配置性根本矛盾 | Team Lead 裁决：分两类——纯显示类改 str，核心业务类保留枚举 | 是 | 纳入计划：字典模型设计 |
| C | 三端字典数据同步策略空白 | Team Lead 裁决：统一字典 API，admin 管理 + 公开查询双 API | 是 | 纳入计划：API 设计 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：字典模型设计**
   **结论：** 采用通用字典引擎模式，两张表（dict_types + dict_items），不为每种字典建独立表
   **建议行动：** 创建 dict_types 表（id, code, name, description, tenant_id, status）和 dict_items 表（id, dict_type_id, label, value, sort_order, status, tenant_id）
   **成本估算：** 16h（模型 + 迁移 + API + admin CRUD）
   **优先级：** P0

2. **议题：迁移分批策略**
   **结论：** 分三批迁移，按业务耦合度排序
   **建议行动：**
   - 第一批（纯显示类，不参与业务逻辑判断）：医生职称、学历、证件类型、就诊人关系、公告类型、新闻类型、轮播图位置/链接类型、预约须知类型、医生页面风格、停诊处置方式、公告目标类型/优先级
   - 第二批（有状态流转或轻度业务耦合）：反馈类型、工单类型/优先级、消息类型、邮件模板类型、通知事件类型、接收人规则类型、消息发送模式、预约来源、加号类型、小程序主题
   - 第三批（深度耦合，需重构业务代码）：预约类型、默认时段配置
   **成本估算：** 第一批 8h，第二批 12h，第三批 16h
   **优先级：** P0（第一批），P1（第二批），P2（第三批）

3. **议题：schemas 枚举处理方案**
   **结论：** 采用 Critic 建议的方案 (3)——分两类处理
   **建议行动：**
   - 纯显示类字典：Pydantic schema 字段改为 `str` 类型，校验由字典服务层负责
   - 核心业务类字典（appointment_type, schedule_mode 等）：保留 Python 枚举，字典仅作为前端显示配置
   **成本估算：** 每个字典项 0.5-1h（改 schema + 改前端）
   **优先级：** P0（随迁移批次同步执行）

4. **议题：三端统一 API 设计**
   **结论：** 提供两套 API——管理 API（admin 端 CRUD）和公开查询 API（三端共用）
   **建议行动：**
   - 管理 API：`/api/v1/dicts` (CRUD) + `/api/v1/dicts/:type/items` (字典项 CRUD)
   - 公开查询 API：`/api/v1/dict-options/:type` (获取已启用的字典项列表) + `/api/v1/dict-options/batch?types=xxx,yyy` (批量查询)
   - admin 端通过管理 API 加载全量字典，患者端/小程序端通过公开 API 加载已启用项
   **成本估算：** 8h（API 开发 + 文档）
   **优先级：** P0

5. **议题：字典页面 UI 方案**
   **结论：** 采用统一风格（useListPage + createListRequest + ListOperations），ModalForm 编辑字典项
   **建议行动：**
   - 字典类型列表页：ProTable 展示所有字典类型，点击进入字典项管理
   - 字典项管理页：左侧字典类型树/列表，右侧字典项 ProTable（支持拖拽排序、启用/禁用、新增/编辑/删除）
   - 使用 ModalForm 编辑字典项（参考 shift-type-form.tsx）
   - 字典项"删除"改为"禁用"，不物理删除
   **成本估算：** 12h（列表页 + 表单页 + 拖拽排序）
   **优先级：** P0

6. **议题：路由位置**
   **结论：** 集中在"系统管理"下，路由路径 `/system/dictionaries`
   **建议行动：** 在 system.ts 路由配置中新增 `/system/dictionaries` 路由，权限为 `canSystemManagement`
   **成本估算：** 1h
   **优先级：** P0

7. **议题：字典缓存策略**
   **结论：** 后端 Redis 缓存 + 前端 localStorage 持久化
   **建议行动：**
   - 后端：字典数据缓存到 Redis，TTL 30 分钟，字典变更时主动失效
   - 前端：字典数据缓存到 localStorage，页面加载时先读缓存，后台异步刷新
   **成本估算：** 6h（Redis 缓存 + 前端缓存层）
   **优先级：** P1

8. **议题：字典变更实时性**
   **结论：** MVP 接受延迟，用户刷新页面即可看到变更
   **建议行动：** 字典管理页面操作成功后提示"变更将在其他页面刷新后生效"
   **成本估算：** 0.5h
   **优先级：** P0

### ⚡ 分歧项

1. **议题：层级覆盖机制**
   **各方立场：**
   - PM：字典统一为租户级隔离即可，门店级覆盖是过度设计
   - Designer：不需要门店级覆盖，UI 保持简单
   - Engineer：SystemSetting 的 store_id 覆盖模式可以保留，字典不重复此能力
   **裁决：** 字典统一为租户级隔离，不支持门店级覆盖。"默认时段配置"保留在 SystemSetting 中不迁移。
   **决策依据：** 字典数据的本质是"可配置的选项列表"，门店级覆盖属于"系统配置"范畴，已有 SystemSetting 支持。

### 🚨 关键质询回应

| # | 关键质询 | 回应 |
|---|---------|------|
| A | appointment_type 迁移风险 | 从第一批移除，放入第三批（深度耦合类）。迁移前需完成字典框架稳定 + 排班任务 fallback 策略 |
| B | Pydantic 枚举 vs 字典可配置性 | 分两类：纯显示类改 str + 字典服务校验；核心业务类保留枚举，字典仅作前端配置 |
| C | 三端同步策略 | 统一公开查询 API `/api/v1/dict-options/:type`，三端共用；admin 端额外有管理 API |

---

## 被低估的优势

1. **消除枚举重复定义**：字典化后，后端 models 层和 schemas 层的重复枚举可统一为一份，减少维护负担
2. **消除前端硬编码重复**：admin 页面内联的 16+ 处硬编码选项可统一为字典 API 调用，消除 EDUCATION_OPTIONS 等的重复定义
3. **ShiftType 先例可复用**：ShiftType 的 model + service + router + admin CRUD 模式可直接作为字典模块的模板，降低开发成本

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 创建字典表（dict_types + dict_items）+ Alembic 迁移 | 4h | 高 — 字典功能基础设施 | Engineer | 待执行 |
| P0 | 后端字典模块（router + service + schemas） | 8h | 高 — 字典 CRUD API | Engineer | 待执行 |
| P0 | 前端字典 API 模块（packages/api/src/modules/dict.ts） | 2h | 高 — 前端调用基础 | Engineer | 待执行 |
| P0 | admin 端字典管理页面（类型列表 + 字典项管理） | 12h | 高 — 核心功能交付 | Designer + Engineer | 待执行 |
| P0 | 路由注册 + 权限配置 | 1h | 高 — 功能入口 | Engineer | 待执行 |
| P0 | 第一批数据迁移（11 项纯显示类字典） | 8h | 高 — 消除硬编码 | Engineer | 待执行 |
| P1 | 后端 Redis 字典缓存 | 3h | 中 — 性能优化 | Engineer | 待执行 |
| P1 | 前端 localStorage 字典缓存层 | 3h | 中 — 减少请求 | Engineer | 待执行 |
| P1 | 第二批数据迁移（10 项有状态流转字典） | 12h | 中 — 扩展字典覆盖 | Engineer | 待执行 |
| P1 | 公开查询 API（/api/v1/dict-options） | 4h | 中 — 三端共用 | Engineer | 待执行 |
| P2 | 第三批数据迁移（2 项深度耦合字典） | 16h | 中 — 需重构业务代码 | Engineer | 待执行 |
| P2 | 字典项拖拽排序功能 | 4h | 低 — 体验优化 | Engineer | 待执行 |
| 待定 | 患者端/小程序端字典数据接入 | 8h | 待定 — 需确认影响范围 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. 创建字典表 + 后端模块 + admin CRUD 页面 + 第一批数据迁移（总计 35h）
2. 统一风格开发（useListPage + createListRequest + ListOperations + ModalForm）

### P1：本轮迭代（高价值、中等成本）

1. Redis 缓存 + 前端缓存层（6h）
2. 第二批数据迁移 + 公开查询 API（16h）

### P2：下个周期规划（中等价值、较高成本）

1. 第三批数据迁移（预约类型、默认时段配置）— 需重构排班业务代码（16h）
2. 字典项拖拽排序（4h）

### 待定：需用户确认

1. 患者端和小程序端是否需要接入字典 API？影响范围评估后决定（8h）

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 8 项达成共识（字典模型、迁移分批、schemas 处理、API 设计、UI 方案、路由位置、缓存策略、实时性）

**关键分歧：**
- 1 项裁决（层级覆盖机制 — 裁决为不支持门店级覆盖）

**Top 3 P0 行动：**
1. 创建字典表 + 后端字典模块（12h）— 字典功能基础设施
2. admin 端字典管理页面（12h）— 核心功能交付
3. 第一批数据迁移 — 11 项纯显示类字典（8h）— 消除硬编码

**Critic 关键洞察：**
- 最大架构风险是字典动态性与 Python 枚举 + Pydantic 校验的静态性矛盾 — 已通过分两类处理方案解决
- appointment_type 在后端 75 处引用且深度耦合排班逻辑 — 已从第一批移至第三批
- 三端字典数据同步策略需统一 API — 已设计公开查询 API

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
