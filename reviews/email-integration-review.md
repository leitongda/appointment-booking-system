# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：领域主导（Engineer 主导）
> 日期：2026-05-15
> 审查目标：邮箱接入消息系统的可行性分析 + Admin 端功能完善

---

## 模式选择

**选定模式：** 领域主导（Engineer 主导）

**选择理由：** 邮件接入的核心瓶颈在技术层（渠道策略、用户邮箱数据获取、重试机制、同步/异步桥接），需要 Engineer 深度分析。PM 和 Designer 作为辅助提供产品优先级和页面设计视角。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 医院挂号系统，SaaS 多租户架构，包含机构端/患者端/医生端三平台
- 技术栈：React 18 + FastAPI + PostgreSQL + Redis + Celery

**功能完成度（消息通知）：**
- 站内信：已实现（Message 模型 + InAppChannel + 前端消息列表页）
- 短信：已实现（SmsService + SmsChannel + 4 种业务短信模板）
- 微信：已实现（WechatChannel + 订阅消息 + 24h 提醒）
- 邮件：已实现（EmailService + EmailChannel + 事件钩子 + 门店接收人）
- WebSocket：已实现（ConnectionManager + WebSocketChannel，仅医生端）

**邮箱当前接入场景：**
- 路径 A：事件钩子 `dispatch_event_email()` -> Celery `process_event_email` -> 发送给门店邮件接收人（非患者/医生）
- 路径 B：统一通知分发器中 EmailChannel 已注册但不在默认策略中
- 路径 C：租户告警 `TenantNotificationService` 高优先级通过邮件推送
- 路径 D：验证码邮件 `send_verification_code_email()`

**消息类型与当前渠道策略：**

| 消息类型 | 当前策略 |
|---------|---------|
| appointment* (4种) | wechat -> sms -> in_app |
| stop_clinic | wechat -> sms -> in_app |
| schedule | websocket -> in_app |
| system | in_app |
| consultation/feedback | in_app |
| queue_call | websocket -> in_app |

所有策略均不含 email。

### Designer — 用户视角

**页面清单（9 个消息/通知相关页面）：**

| 路由 | 组件 | 行数 |
|------|------|------|
| /content-center/message/list | MessagePage | 251 |
| /content-center/message/create | MessageFormPage | 191 |
| /content-center/message/templates | UnifiedTemplatesPage | 383 |
| /content-center/message/recipient-rules | RecipientRulesPage | 266 |
| /system/config/email-templates | EmailTemplatesPage | 187 |
| /system/config/email-templates/create | EmailTemplateFormPage | 188 |
| /system/config/email-recipients | StoreEmailRecipientsPage | 299 |
| /system/monitoring/notification-logs | NotificationLogsPage | 290 |
| /system/monitoring/notification-quota | NotificationQuotaPage | 236 |

**组件一致性问题：**
- system 页面使用 `OperationGroup` + `OperationButton` + `CreateButton` 抽象组件
- message 页面使用原生 `Button` + `Popconfirm` 手写操作列
- message/templates 和 recipient-rules 未使用 `useListPage` hook
- ModalForm 属性名不一致：`destroyOnClose` vs `destroyOnHidden`（实为 Modal vs Drawer 的正常 API 差异）

**信息架构：**
- 邮件功能分散在两个一级菜单下：运营中心（消息管理）和系统管理（邮件模板/接收人/日志/配额）
- 消息管理和邮件模板之间无直接导航链接

### Engineer — 技术视角

**存储层：**
- `Account.email` 字段存在（String(100)，带索引，租户内唯一）
- `User.email` 字段存在（旧表，String(100)，带索引，租户内唯一）
- `AccountDoctor` 和 `AccountUser` 扩展表中无 email 字段
- `Patient` 模型中无 email 字段
- `NotificationPreference.email_enabled` 字段存在，默认 True
- SMTP 配置存储在 `system_settings` 表（category="email"），密码明文存储

**核心引擎：**
- `_DEFAULT_CHANNEL_STRATEGY` 在 dispatcher.py:46-57 和 unified_message/service.py:69-80 两处定义，完全一致，均不含 email
- `_get_user_contact_info()` 仅返回 `(phone, openid)`，不查询 email
- `EmailChannel.validate_recipient()` 仅检查 `event.recipient_email` 是否存在，不做 DB fallback
- `NotificationEvent` schema 中 `recipient_email: Optional[str]` 已定义但所有业务调用方均未填充
- 两套消息体系并存（旧版 + 统一消息中心），通过 feature flag 切换

**重试机制：**
- `notification_retry_task._retry_email()` 返回 False（Celery 同步环境无法使用异步 EmailService）
- `unified_message_retry_task._retry_email()` 同样返回 False
- `email_hook_task` 使用同步 smtplib，支持 autoretry（max_retries=2）

---

## Round 2：辩论层

### Engineer Lead 交叉评审

**议题 1：`_get_user_contact_info` 增加 email 查询**
- 裁决：+1（同意）
- 理由：Account 表已有 email 字段，改动仅在查询层。函数被 4-5 处调用，修改后所有下游渠道自动获得 email。
- 成本：3h。风险：返回值从 2 元组变 3 元组，需同步修改所有调用方。建议使用 NamedTuple。

**议题 2：`_DEFAULT_CHANNEL_STRATEGY` 加入 email**
- 裁决：反驳（不同意直接加入主渠道策略）
- 理由：中国医疗场景用户触达率 微信 > 短信 > 邮件。患者大概率未提供邮箱，email 会频繁失败。
- 建议：email 仅作为 `system` 类型消息的可选渠道，不加入 appointment 降级链。
- 成本：2h（如果加入）。

**议题 3：EmailChannel DB fallback**
- 裁决：+1（同意）
- 理由：参照 WechatChannel 的 fallback 模式实现。这是邮件能作为通用渠道工作的前提。
- 成本：2h。风险：N+1 查询，建议 dispatcher 层批量预加载。

**议题 4：邮件重试机制**
- 裁决：+1（同意，方案需调整）
- 建议：复用 `email_hook_task._send_email_sync()`（同步 smtplib），而非 asyncio.run() 桥接。
- 成本：4h。

**议题 5：Admin 页面组件一致性**
- 裁决：+1（同意，优先级降为 P2）
- 成本：6h。纯前端技术债，不影响功能。

**议题 6：邮件功能菜单整合**
- 裁决：+1（同意，方案调整）
- 建议：不合并菜单，在消息管理页面增加"邮件设置"快捷入口卡片。
- 成本：1.5h。

**隐性工作量：** 业务调用方填充 `recipient_email` 字段，约 3h x 6 个场景。

### Critic 质询

**[Critic -> 全体] 质询 1：患者邮件通知的实际需求缺乏数据支撑**
- Patient 模型无 email 字段，AccountUser 扩展表也无 email。当前没有一条路径向患者发送邮件。
- 医院挂号场景下患者核心触达渠道是微信和短信，邮件延迟高、打开率低。
- 级别：普通

**[Critic -> 全体] 质询 2：邮件模板 XSS 安全漏洞**
- 三套 render_template 实现中两套存在注入风险：email_template_service 和 email_hook_task 使用简单字符串替换，无 HTML 转义。
- 如果向患者发送邮件，patient_name 等字段直接拼入 HTML 构成存储型 XSS 攻击向量。
- 级别：🚨 关键

**[Critic -> 全体] 质询 3：两套消息体系并存的工作量被严重低估**
- 灰度切换期间任何邮件改动都必须在两套系统中同步实现，实际成本约 2 倍。
- 级别：🚨 关键

**[Critic -> 全体] 质询 4：邮件不在默认策略中可能是刻意设计决策**
- 当前降级链 wechat -> sms -> in_app 已覆盖即时性递减的三个渠道。
- ChannelStrategy 模型支持租户级自定义，少数租户需求可通过租户配置满足。
- 级别：普通

**[Critic -> 全体] 质询 5：现有邮件系统已满足核心需求**
- 路径 A（事件钩子）已完整实现门店管理员邮件通知。邮件作为门店后台通知渠道已通过独立路径实现。
- 级别：普通

**[Critic -> 全体] 质询 6：UnifiedTemplate 与 EmailTemplate 模板系统定位冲突**
- 两套模板功能高度重叠，Admin 前端已有两个独立模板管理页面，用户不知道在哪里管理邮件模板。
- 级别：🚨 关键

**[Critic -> 全体] 质询 7：SMTP 密码明文存储风险等级上升**
- 如果 email 成为面向患者的渠道，SMTP 被攻破的影响范围将显著扩大。
- 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 裁决回应 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | XSS 安全漏洞 | 采纳。模板渲染统一为 Jinja2 SandboxedEnvironment + autoescape 作为邮件接入前提 | 是 | 纳入计划 P1 |
| 2 | 双系统工作量 | 采纳。承认双系统同步修改成本翻倍，建议优先完善现有路径而非接入主链路 | 是 | 纳入计划决策 |
| 3 | 模板系统冲突 | 部分采纳。短期保持两套并行（各司其职），长期统一到 UnifiedTemplate | 是 | 纳入计划 P2 |

### 独到发现

1. **邮件的核心价值在 B 端而非 C 端**。Critic 指出邮件通知的目标受众应该是门店管理员而非患者，这与现有架构设计意图一致。
2. **`NotificationEvent.recipient_email` 是隐性断点**。Engineer 发现所有业务调用方均未填充该字段，这是最大的隐性工作量。
3. **`NotificationPreference.email_enabled` 从未被检查**。EmailChannel 不检查用户偏好，与 WechatChannel/SmsChannel 行为不一致。

---

## Round 3：共识层

### 核心裁决

**邮件接入策略：分层接入，B 端优先，C 端暂缓。**

基于 Critic 的根本性质疑（"在回答'怎么接入'之前，先回答'是否需要接入'"），裁决如下：

1. **面向患者（C 端）的邮件通知：暂缓**。理由：Patient 模型无 email 字段、患者邮箱填写率未知、微信/短信已覆盖即时通知需求、XSS 安全问题需先修复。
2. **面向门店管理员（B 端）的邮件通知：已满足**。路径 A（事件钩子）已完整实现，无需接入主分发链路。
3. **面向系统管理员的邮件通知：可增强**。system 类型消息可加入 email 作为可选渠道。
4. **基础设施完善：立即执行**。DB fallback、重试机制、偏好检查等基础能力应优先完善，为未来邮件接入做好准备。

### ✅ 共识项

1. **EmailChannel 增加 DB fallback 查询邮箱**
   - 结论：参照 WechatChannel 模式，在 validate_recipient 中增加 Account/User 表查询
   - 建议行动：修改 email.py:24-28，增加 DB fallback 逻辑
   - 成本估算：2h
   - 优先级：P0

2. **`_get_user_contact_info` 增加 email 返回值**
   - 结论：函数返回值扩展为 3 元组（phone, openid, email），使用 NamedTuple 提高可读性
   - 建议行动：修改 service_messages.py:29-51 + 5 处调用方
   - 成本估算：3h
   - 优先级：P0

3. **修复邮件重试机制**
   - 结论：复用 `email_hook_task._send_email_sync()` 作为重试底层，统一两处重试实现
   - 建议行动：修改 notification_retry_task.py 和 unified_message_retry_task.py 中的 `_retry_email`
   - 成本估算：4h
   - 优先级：P1

4. **EmailChannel 增加 NotificationPreference 检查**
   - 结论：在发送前检查 `email_enabled` 偏好，与 WechatChannel/SmsChannel 保持一致
   - 建议行动：修改 email.py send() 方法
   - 成本估算：1h
   - 优先级：P1

5. **统一模板渲染为 Jinja2 SandboxedEnvironment + autoescape**
   - 结论：三套 render_template 统一为安全实现，作为邮件接入主链路的前置条件
   - 建议行动：修改 email_template_service.py 和 email_hook_task.py 的渲染逻辑
   - 成本估算：4h
   - 优先级：P1

6. **消息管理页面增加邮件设置快捷入口**
   - 结论：不合并菜单，在 message/index.tsx 增加快捷入口卡片链接到邮件配置页
   - 建议行动：修改 message/index.tsx
   - 成本估算：1.5h
   - 优先级：P2

7. **Admin 消息页面组件一致性统一**
   - 结论：message 页面统一使用 OperationGroup + OperationButton + useListPage
   - 建议行动：重构 message/index.tsx、templates.tsx、recipient-rules.tsx
   - 成本估算：6h
   - 优先级：P2

### ⚡ 分歧项

1. **是否将 email 加入 `_DEFAULT_CHANNEL_STRATEGY` 的 appointment 类型降级链**
   - Engineer 立场：反驳。患者大概率无邮箱，email 会频繁失败。仅建议加入 system 类型。
   - Critic 立场：支持反驳。ChannelStrategy 租户级配置已可满足少数需求。
   - 裁决：不加入 appointment 降级链。system 类型可加入 `["email", "in_app"]`。租户级需求通过 ChannelStrategy 配置。

2. **是否废弃 EmailTemplate 统一到 UnifiedTemplate**
   - Critic 立场：两套模板功能重叠，应合并。
   - Engineer 立场：短期保持并行（各司其职），长期统一。
   - 裁决：P2 规划。EmailTemplate 服务于路径 A（事件钩子），UnifiedTemplate 服务于路径 B（主分发器）。当路径 A 迁移到统一消息中心后，EmailTemplate 可废弃。

---

## 被低估的优势

1. **邮件渠道基础设施已完整**。EmailChannel、EmailService、EmailTemplate、StoreEmailRecipient、通知日志、配额管理均已实现，无需从零建设。
2. **ChannelStrategy 租户级配置已就绪**。无需修改全局默认策略，租户可自行配置邮件渠道。
3. **事件钩子路径设计合理**。fire-and-forget 模式 + Celery 异步 + 自动重试，是邮件通知的最佳实践。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | EmailChannel 增加 DB fallback 查询邮箱 | 2h | 高 | Engineer | 待执行 |
| P0 | `_get_user_contact_info` 增加 email 返回值 | 3h | 高 | Engineer | 待执行 |
| P1 | 修复邮件重试机制（复用 _send_email_sync） | 4h | 中 | Engineer | 待执行 |
| P1 | EmailChannel 增加 NotificationPreference 检查 | 1h | 中 | Engineer | 待执行 |
| P1 | 统一模板渲染为 Jinja2 SandboxedEnvironment | 4h | 中 | Engineer | 待执行 |
| P1 | system 消息类型默认渠道加入 email | 2h | 中 | Engineer | 待执行 |
| P2 | 消息管理页面增加邮件设置快捷入口 | 1.5h | 中 | Designer | 待执行 |
| P2 | Admin 消息页面组件一致性统一 | 6h | 低 | Designer | 待执行 |
| P2 | 业务调用方填充 recipient_email 字段 | 3h | 高 | Engineer | 待执行 |
| 待定 | EmailTemplate 与 UnifiedTemplate 合并 | 8h | 中 | Engineer | 需用户确认 |
| 待定 | SMTP 密码加密存储 | 2h | 中 | Engineer | 需用户确认 |
| 待定 | 患者邮件通知（C 端接入主链路） | 16h+ | 待定 | PM+Engineer | 需业务需求确认 |

### P0：立即执行（高价值、低成本）

1. **EmailChannel 增加 DB fallback**（2h）
   - 修改 `apps/server/app/infrastructure/notifications/channels/email.py:24-28`
   - 参照 WechatChannel 模式，查询 Account.email fallback 到 User.email
   - 同时检查 NotificationPreference.email_enabled

2. **`_get_user_contact_info` 增加 email**（3h）
   - 修改 `apps/server/app/modules/messages/service_messages.py:29-51`
   - 返回值改为 NamedTuple(phone, openid, email)
   - 更新 5 处调用方解构赋值

### P1：本轮迭代

3. **修复邮件重试机制**（4h）
   - 提取 `email_hook_task._send_email_sync()` 为共享工具函数
   - 修改 `notification_retry_task.py:246-258` 和 `unified_message_retry_task.py:286-294`

4. **统一模板渲染安全**（4h）
   - 修改 `email_template_service.py:163-172` 使用 Jinja2 SandboxedEnvironment + autoescape
   - 修改 `email_hook_task.py:85-117` 的 `_render_simple_template`

5. **system 消息加入 email 渠道**（2h）
   - 修改 `dispatcher.py:53` 和 `unified_message/service.py:76`
   - `system: ["in_app"]` -> `system: ["email", "in_app"]`

### P2：下个周期规划

6. **消息管理页面快捷入口**（1.5h）
7. **Admin 组件一致性统一**（6h）
8. **业务调用方填充 recipient_email**（3h）

### 待定：需用户确认

9. **EmailTemplate 与 UnifiedTemplate 合并**（8h）-- 需确认是否废弃 EmailTemplate
10. **SMTP 密码加密**（2h）-- 需确认优先级
11. **患者邮件通知**（16h+）-- 需确认是否有业务需求

---

## 摘要

**使用模式：** 领域主导（Engineer 主导）

**关键共识：**
- 7 项达成共识
- 邮件接入策略：B 端优先，C 端暂缓
- 基础设施完善（DB fallback、重试、偏好检查、模板安全）立即执行

**关键分歧：**
- 2 项需裁决（已裁决）
- email 不加入 appointment 降级链
- EmailTemplate 短期保留，长期统一

**Top 3 P0 行动：**
1. EmailChannel 增加 DB fallback 查询邮箱（2h）
2. `_get_user_contact_info` 增加 email 返回值（3h）
3. 修复邮件重试机制（4h）

**Critic 关键洞察：**
- 邮件的核心价值在 B 端（门店管理员）而非 C 端（患者），现有事件钩子路径已满足核心需求
- XSS 安全漏洞是邮件接入主链路的硬性前置条件
- 双系统并存使任何邮件改动成本翻倍，应优先完善基础设施而非激进接入

**完整画布文件：** `reviews/email-integration-review.md`
