# unified-message-migration — 自适应多智能体研究画布

> 协作模式：对等协作
> 日期：2026-05-14
> 审查目标：.claude/plans/iridescent-crunching-seahorse.md（统一消息中心重构迁移策略）

---

## 模式选择

**选定模式：** 对等协作

**选择理由：** 用户主动选择。迁移计划涉及产品兼容性、前端影响、技术架构三个维度的复杂权衡，适合三方对等交叉验证。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 项目名称：医院挂号系统，全栈 SaaS 多租户架构
- 自我描述："一套完整的医院挂号系统解决方案，包含机构端、患者端（H5 + 小程序）、医生端三个平台"
- 技术栈：React 18 + FastAPI + SQLAlchemy 2.x + PostgreSQL 16 + Redis 7 + Celery

**功能完成度 — 消息/通知系统：**
- MessageService 4 个 send_* 方法全部已实现
- 5 个渠道（in_app/sms/email/wechat/websocket）全部已实现
- NotificationDispatcher 分发器已实现
- 用户通知偏好已实现
- Celery 预约提醒/重试/邮件钩子任务已实现

**send_* 方法实际调用情况：**
- `send_appointment_notification`: 5 处调用（service_booking.py:305,516,654 + service_flow.py:190,256）
- `send_schedule_notification`: 2 处直接调用（service_generation.py:282 + service_mutation.py:350）+ 2 处间接调用（service_mutation.py:108,164 通过 `_send_schedule_notification_to_doctor`）
- `send_stop_clinic_notification`: 2 处调用（schedule_suspensions/service.py:232 + service_mutation.py:384）
- `send_system_notification`: **0 处外部调用**，仅在 service_messages.py 内部降级路径中使用

**计划声称 vs 实际差异：**
- 计划声称"18 个 API 端点"，实际后端 14 个端点，前端 messageApi 14 个方法，完全对齐
- 计划声称 service_booking.py 有 4 个调用点，实际 3 个
- 计划声称 service_flow.py 有 6 个调用点，实际 2 个
- 计划声称 send_system_notification 调用者为 "messages/service_messages.py 内部"，实际该方法无任何外部调用者

### Designer — 用户视角

**前端消息页面清单与结构：**
- 计划中 8 个前端文件全部存在，已验证
- admin/NotificationButton.tsx: 382 行，Popover + Tabs + List
- admin/message/index.tsx: 74 行，ProTable
- admin/message/form.tsx: 94 行，消息发送表单
- admin/system/notification-logs.tsx: 179 行，通知日志 + 统计卡片
- doctor/message/index.tsx: 299 行，Tabs + List + WebSocket 实时刷新
- patient-h5/message/index.tsx: 307 行，Tabs + PullToRefresh + InfiniteScroll + SwipeAction
- patient-h5/profile/index.tsx: 255 行，消息通知入口 + Badge

**前端 API 依赖分析：**
- messageApi 定义 14 个方法（非计划声称的 18 个）
- notificationLogApi: 4 个方法（仅 admin 端使用）
- notificationPreferenceApi: 2 个方法（doctor 端和 patient-h5 端使用）
- 前端实际调用的唯一端点仅 7 个（getList, getUnreadCount, markAsRead, markAllAsRead, delete, send, getAllList）
- 未使用的方法: getDetail, clearRead, sendBatch, getTemplates, createTemplate, updateTemplate, deleteTemplate

**多端一致性：**
- 三端消息页面完全独立实现，无共享 UI 组件
- Tab 分类不一致: admin 无 Tab（ProTable 筛选）, doctor 4 Tab（all/schedule/appointment/system）, patient-h5 4 Tab（all/appointment/consultation/system）
- 分页方式不一致: admin ProTable 内置, doctor List 内置, patient-h5 InfiniteScroll 无限滚动
- 实时更新不一致: admin 60s 轮询, doctor WebSocket, patient-h5 无实时推送
- 删除操作不一致: admin Dropdown, doctor 右侧链接, patient-h5 滑动删除

**类型定义不一致：**
- admin 端 HeaderActions/types.ts 使用 snake_case（message_type, is_read, created_at）
- packages/shared/src/types/message.ts 使用 camelCase（messageType, isRead, createdAt）
- admin 端 NotificationButton.tsx import 本地 snake_case 版本
- admin 端 message/index.tsx import shared camelCase 版本

### Engineer — 技术视角

**现有数据模型：**
- 5 张现有表: messages, message_templates, notification_logs, email_templates, notification_preferences
- Message 模型: 12 字段 + AuditMixin, 表名 messages
- MessageTemplate 模型: 9 字段, 表名 message_templates
- NotificationLog 模型: 18 字段, 不继承 AuditMixin, 表名 notification_logs
- EmailTemplate 模型: 9 字段 + AuditMixin, 表名 email_templates, 有 12 种模板类型枚举
- NotificationPreference 模型: 16 字段, 唯一约束 (user_id, user_type), 表名 notification_preferences

**现有服务层：**
- MessageService: 16 个公开方法（含 dispatcher property）
- NotificationDispatcher: 7 个核心方法
- 去重逻辑: dispatcher.py:242-272, Redis SET NX EX, TTL 86400s
- 偏好过滤: dispatcher.py:274-343, 原始 SQL text() 查询
- 静默时段检查: dispatcher.py:345-370, 支持跨天
- 偏好检查逻辑在两处独立实现: service_messages.py:74-96 和 dispatcher.py:209-240

**Celery 任务：**
- notification_task.py: 4 个任务, 全部使用同步 session（get_sync_db()）
- notification_retry_task.py: 1 个任务, 同步 session, 退避策略 1min->5min->30min
- email_hook_task.py: 1 个任务, 同步 session, smtplib 同步发送
- 3 个任务均不导入/使用 NotificationDispatcher 或 MessageService

**迁移可行性验证：**
- 计划中 13 个可复用组件全部存在
- 计划中行号引用（去重 242-272, 偏好 274-343, 静默 345-370）全部准确
- unified_message 模块目录当前不存在
- Feature flag 机制: 现有 FeatureFlagService 基于租户 features JSON, 与计划中基于环境变量的方案不一致
- Alembic: 83 个 migration 文件, env.py 未显式导入 notification_log 和 notification_preference 模型
- 计划中"5 个业务模块只调用 4 个 send_* 方法"实际为 4 个模块目录调用 3 种 send 方法（send_system_notification 无外部调用）

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 完整投票矩阵（对等协作模式）

| 议题 | PM | Designer | Engineer | Critic 质询 | 共识？ |
|------|-----|----------|----------|-------------|--------|
| 计划中 API 端点数量不准确（18 vs 14） | ✅ | ✅ | ✅ | 质询1 | 🤝 共识 |
| 计划中业务调用点数量不准确 | ✅ | ✅ | ✅ | 质询1,2 | 🤝 共识 |
| send_system_notification 是否需要迁移 | ❌ 保留 | ✅ 系统Tab为空 | ❌ 保留最小实现 | 质询2 | ⚠️ 分歧 |
| Feature flag 机制不一致 | ✅ 强烈 | ✅ | ✅ 强烈 | 质询4 | 🤝 共识 |
| 偏好检查逻辑重复实现应统一 | ✅ | ✅ | ✅ (6h) | 质询3 反驳 | 🤝 共识 |
| Celery 任务迁移风险 | ✅ P0 | ✅ | ✅ 强烈 (12h) | — | 🤝 共识 |
| admin 端类型不一致 | ✅ P2 | ✅ 严重回归 | ✅ (3h) | — | 🤝 共识 |
| 三端 UI 是否应统一 | ❌ 本轮不统一 | ❌ 不立即统一 | ❌ 本轮不统一 | 质询5 反驳 | 🤝 共识 |
| "前端无需回滚"是否成立 | ❌ 过于绝对 | ❌ 过于乐观 | ❌ 需补充验证 | 质询9 | 🤝 共识 |
| NotificationRecipient 脱敏存储 | ✅ 合规 | ✅ 安全设计 | ❌ 现有不脱敏 | — | ⚠️ 分歧 |

图例：
- ✅ = +1（同意）
- ❌ = 反驳（不同意）
- ⚡ = Critic 质询（Critic 不参与投票，仅对议题发起质询）
- 🤝 = 2/3 或 3/3 同意（共识，基于 PM/Designer/Engineer 三方投票）
- ⚠️ = ≤1/3 同意（分歧）

### 独到发现

1. **admin 端 NotificationButton 数据源分裂**（Designer）：NotificationButton.tsx 使用本地 snake_case 类型 + `messageApi.getList`，而 message/index.tsx 使用 shared camelCase 类型 + `messageApi.getAllList`。如果 API 返回 camelCase，NotificationButton 的 `!m.is_read` 会永远返回 true（undefined is falsy），所有消息显示为已读。这是一个已埋下的用户可见 bug。

2. **消息类型枚举产品语义差异**（Designer）：admin 端 ProTable 的 TYPE_MAP 包含 `reminder` 和 `notice`，但后端 MessageType 枚举中不存在这两种类型。admin 端的消息分类筛选永远不会匹配到这两种类型的数据。

3. **patient-h5 无障碍实现远超其他端**（Designer）：patient-h5 有完善的 `announce()` 函数、`aria-label` 覆盖、`sr-only` 类、键盘导航支持。doctor 端缺少键盘导航和 announce 机制。迁移验收应包含无障碍基线。

4. **去重策略从 Redis 切换到数据库**（Engineer）：现有去重使用 Redis SET NX EX（TTL 自动过期），计划改为数据库 dedup_key unique 约束。性能下降一个数量级，且需要额外清理任务。

5. **Alembic env.py 未导入新模型**（Engineer）：env.py 的显式导入列表中没有 notification_log 和 notification_preference，新模型如果也不注册，`alembic revision --autogenerate` 不会检测到新表。

6. **偏好检查重复实现可能有细微差异**（Critic）：两处实现服务于不同路径——业务层快速路径 vs 分发器标准路径。合并需确认以哪个为准。

### Critic 质询

1. [Critic → 全体] 质询 1：计划的"核心发现"存在多处事实错误，基础假设需要重新校准
   - 论据：4 条核心发现中至少 3 条被证伪（5 个模块→3 个模块目录、4 个 send 方法→3 个、18 个端点→14 个）
   - 要求回应：PM + Engineer
   - 级别：普通

2. [Critic → 全体] 质询 2：迁移排序的第一个候选者实际上是一个空操作
   - 论据：send_system_notification 排第一但无外部调用者，无法通过集成测试验证
   - 要求回应：Engineer
   - 级别：普通

3. [Critic → 全体] 质询 3：偏好检查逻辑的"重复实现"是否真的是缺陷？
   - 论据：两处实现服务于不同调用路径（业务层快速路径 vs 分发器标准路径），可能是有意为之
   - 要求回应：Engineer
   - 级别：普通

4. [Critic → 全体] 质询 4：环境变量 Feature Flag 是升级还是倒退？
   - 论据：现有 FeatureFlagService 已有三级优先级、租户级灰度、Beta 功能，环境变量方案放弃了这些能力
   - 要求回应：Engineer + PM
   - 级别：普通

5. [Critic → 全体] 质询 5：三端 UI 独立实现可能是合理的架构选择
   - 论据：admin/doctor/patient-h5 的用户画像、使用场景、设备形态完全不同，统一 UI 可能降低体验
   - 要求回应：Designer
   - 级别：普通

6. [Critic → 全体] 质询 6：6 张新表的复杂度是否与项目规模匹配？
   - 论据：当前只有 3-4 个事件类型、3 个活跃模块，但新设计引入了通用规则引擎和渠道策略配置系统，可能是过度设计
   - 要求回应：PM + Engineer
   - 级别：🚨 关键

7. [Critic → 全体] 质询 7：数据迁移方案完全空白
   - 计划只提了双写策略，但从未说明旧表存量数据如何进入新表。没有数据迁移方案的双写策略没有意义
   - 要求回应：Engineer
   - 级别：🚨 关键

8. [Critic → 全体] 质询 8：UnifiedTemplate 的 code 字段 unique 约束在多租户下是否正确？
   - 论据：全局唯一意味着租户 A 创建 appointment_success 后租户 B 不能用同名，应为 (tenant_id, code) 联合唯一
   - 要求回应：Engineer
   - 级别：🚨 关键

9. [Critic → 全体] 质询 9：计划声称"前端无需回滚"过于绝对
   - 论据：JSON 字段顺序、null vs 缺失、错误码格式、snake_case 依赖都可能导致前端问题
   - 要求回应：Engineer + Designer
   - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 6 张新表复杂度是否过度设计（质询6） | PM: 需评估规则引擎必要性；Engineer: RecipientRule 5 种规则类型超出当前需求 | 部分充分 | 待定：需用户确认 |
| 2 | 数据迁移方案完全空白（质询7） | 三方均未提供方案，Engineer 确认 Alembic env.py 未导入模型 | 不充分 | 待定：需用户确认 |
| 3 | UnifiedTemplate code 全局唯一约束错误（质询8） | Engineer 确认应为 (tenant_id, code) 联合唯一 | 充分 | 纳入计划 P0 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：计划中 API 端点数量和业务调用点数量不准确**
   **结论：** 三方一致同意。实际 14 个端点（非 18），实际 5 个活跃调用点（非 10 个），send_system_notification 无外部调用
   **建议行动：** 修正计划中的所有数字，基于实际调用链重新评估迁移范围
   **成本估算：** 2h（文档修正 + 调用链验证）
   **优先级：** P0

2. **议题：Feature flag 机制应复用现有 FeatureFlagService**
   **结论：** 三方强烈同意。环境变量方案是倒退，应扩展 TenantFeatures 添加 unified_message_enabled
   **建议行动：** 在 TenantFeatures 中添加 `beta_unified_message` 字段，兼容层改为运行时检查 `FeatureFlagService.is_beta_enabled()`
   **成本估算：** 4h（修改 TenantFeatures + 注册字段 + 改造兼容层 + 测试）
   **优先级：** P0

3. **议题：Celery 任务迁移是最高风险点**
   **结论：** 三方一致同意。3 个 Celery 任务使用同步 session、绕过 MessageService/Dispatcher、直接操作数据库
   **建议行动：** Celery 任务层保持同步实现，新服务提供 `send_sync` 同步接口；独立集成测试覆盖预约提醒完整链路
   **成本估算：** 12h（适配层 + 同步/异步桥接 + 重试逻辑迁移 + 集成测试）
   **优先级：** P0

4. **议题：admin 端 snake_case/camelCase 类型不一致会导致静默失败**
   **结论：** 三方一致同意。NotificationButton 使用 snake_case 类型，迁移后 API 如果返回 camelCase，未读标记会全部失效
   **建议行动：** 统一 admin 端类型定义到 camelCase，验证 API 转换层
   **成本估算：** 3h
   **优先级：** P1

5. **议题：三端 UI 不应在本轮统一**
   **结论：** 三方一致同意。三端用户画像和设备形态不同，独立实现有其合理性。本轮聚焦后端
   **建议行动：** 仅统一消息类型枚举，不统一 UI 组件
   **成本估算：** 0h（本轮不处理）
   **优先级：** P2（下周期）

6. **议题："前端无需回滚"说法需要修正**
   **结论：** 三方一致同意。应补充前提条件列表和契约测试
   **建议行动：** 在集成测试中加入 API 契约测试，验证新旧服务响应格式一致
   **成本估算：** 2h
   **优先级：** P1

7. **议题：去重策略应保留 Redis + 数据库双层**
   **结论：** PM 和 Engineer 同意，Designer 未反驳
   **建议行动：** Redis 作为第一层热数据去重，数据库 dedup_key 作为第二层持久化保障
   **成本估算：** 4h
   **优先级：** P1

8. **议题：Alembic 新模型需要正确注册**
   **结论：** Engineer 确认 env.py 未导入相关模型
   **建议行动：** 在 models/__init__.py 中导入新模型，验证 autogenerate
   **成本估算：** 1h
   **优先级：** P0

### ⚡ 分歧项

1. **议题：send_system_notification 是否需要迁移**
   **各方立场：**
   - PM：保留接口签名，标记 deprecated，为产品扩展预留通道
   - Designer：系统 Tab 永远为空是 UI 空状态设计遗漏
   - Engineer：保留最小实现以保证兼容层完整性（2h）
   **裁决/建议：** 采纳 Engineer 方案——保留接口定义和最小实现，不列为迁移优先级
   **决策依据：** 兼容层完整性 > 零调用者的方法迁移

2. **议题：NotificationRecipient 是否应存储脱敏联系方式**
   **各方立场：**
   - PM：需要合规视角，openid_hash 应加 salt
   - Designer：安全设计合理，但需确认 admin 搜索工作流
   - Engineer：现有代码无脱敏，脱敏后无法重试发送，应直接存储真实地址
   **裁决/建议：** 采纳 Engineer 方案——直接存储真实联系方式（与现有 NotificationLog.recipient 一致），查询 API 层面做返回脱敏
   **决策依据：** 重试发送依赖真实地址，存储脱敏会导致功能不可用

---

## 被低估的优势

1. **现有 FeatureFlagService 已经很成熟**（Critic 提醒）：三级优先级、租户级灰度、Beta 功能都已实现，迁移只需扩展而非重建
2. **实际迁移范围比计划预期小**（PM 提醒）：调用点实际 5 个而非 10 个，风险评级应下调
3. **前端实际只调用 7 个 API 方法**（Designer 提醒）：兼容层只需覆盖 7 个活跃端点，可节省约 30% 工作量

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 修正计划中的数字错误（端点、调用点） | 2h | 高 | Engineer | 待执行 |
| P0 | Feature flag 复用 TenantFeatures | 4h | 高 | Engineer | 待执行 |
| P0 | Celery 任务适配层 + 独立集成测试 | 12h | 高 | Engineer | 待执行 |
| P0 | UnifiedTemplate code 改为 (tenant_id, code) 联合唯一 | 1h | 高 | Engineer | 待执行 |
| P0 | Alembic 新模型注册 + env.py 导入 | 1h | 高 | Engineer | 待执行 |
| P0 | 补充数据迁移方案（旧表→新表） | 8h | 高 | Engineer | 待执行 |
| P1 | admin 端类型统一到 camelCase | 3h | 高 | Engineer | 待执行 |
| P1 | API 契约测试（新旧服务响应对比） | 2h | 高 | Engineer | 待执行 |
| P1 | 去重策略保留 Redis + 数据库双层 | 4h | 中 | Engineer | 待执行 |
| P1 | 偏好检查逻辑统一为单一实现 | 6h | 中 | Engineer | 待执行 |
| P2 | 三端消息类型枚举对齐 | 2h | 中 | PM + Engineer | 待执行 |
| P2 | 三端 UI 统一（独立任务） | 16-24h | 中 | Designer | 待执行 |
| P2 | 消息模板管理功能决策（死 API 去留） | 2h | 低 | PM | 待执行 |
| 待定 | 是否需要通用规则引擎和渠道策略配置系统 | 待评估 | 待定 | PM + Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **修正计划数字错误** — 基于实际调用链重新评估迁移范围，修正所有不准确的数字（2h, Engineer）
2. **Feature flag 复用 TenantFeatures** — 扩展 TenantFeatures 添加 beta_unified_message，兼容层改为运行时检查（4h, Engineer）
3. **Celery 任务适配层** — 保持同步实现，新服务提供 send_sync 接口，独立集成测试覆盖预约提醒链路（12h, Engineer）
4. **UnifiedTemplate 约束修正** — code 字段改为 (tenant_id, code) 联合唯一约束（1h, Engineer）
5. **Alembic 模型注册** — 在 models/__init__.py 中导入新模型，env.py 添加显式导入（1h, Engineer）
6. **补充数据迁移方案** — 设计旧表→新表的数据迁移脚本，包括 messages→notification_recipients、notification_logs→notification_deliveries、templates→unified_templates 的映射关系（8h, Engineer）

### P1：本轮迭代（高价值、中等成本）

1. **admin 端类型统一** — 统一 NotificationButton.tsx 到 camelCase 类型，验证 API 转换层（3h, Engineer）
2. **API 契约测试** — 编写新旧服务响应格式对比测试，确保前端无感知（2h, Engineer）
3. **去重策略双层实现** — Redis 热数据去重 + 数据库持久化保障（4h, Engineer）
4. **偏好检查逻辑统一** — 对比两处实现差异，确定权威逻辑，迁移到新服务（6h, Engineer）

### P2：下个周期规划（中等价值、较高成本）

1. **三端消息类型枚举对齐** — 统一 MessageType 枚举，修正 admin 端不存在的 reminder/notice 类型（2h, PM + Engineer）
2. **三端 UI 统一** — 独立前端重构任务，不与后端迁移耦合（16-24h, Designer）
3. **消息模板管理功能决策** — 7 个未使用 API 方法的去留决定（2h, PM）

### 待定：需用户确认

1. **是否需要通用规则引擎和渠道策略配置系统** — 计划引入 RecipientRule（5 种规则类型）和 ChannelStrategy（3 种策略），但当前只有 3-4 个事件类型。这可能是过度设计，也可能是合理的扩展预留。需要用户确认产品路线图中是否有更多通知场景的规划。

---

## 摘要

**使用模式：** 对等协作

**关键共识：**
- 8 项达成共识（API 数字修正、Feature flag 对齐、Celery 风险、类型统一、UI 不统一、回滚修正、去重双层、模型注册）

**关键分歧：**
- 2 项需要决策者介入（send_system_notification 去留、脱敏存储策略）
- 1 项待用户确认（规则引擎是否过度设计）

**Top 3 P0 行动：**
1. Celery 任务适配层 + 独立集成测试（12h）— 最高技术风险
2. 补充数据迁移方案（8h）— 计划完全空白
3. Feature flag 复用 TenantFeatures（4h）— 环境变量方案是倒退

**Critic 关键洞察：**
- 计划的"核心发现"4 条中 3 条有事实错误，迁移策略的论证基础需要重新校准
- 6 张新表的复杂度可能与项目规模不匹配（当前 3-4 个事件类型 vs 通用规则引擎）
- 数据迁移方案完全空白，双写策略没有意义

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 2026-05-14 | 领域主导(Engineer) | 对等协作 | 用户主动选择 |
