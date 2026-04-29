# 消息通知系统架构 — 自适应多智能体研究画布

> 协作模式：对等协作
> 日期：2026-04-28
> 审查目标：消息通知系统全链路架构分析 — 多渠道、多角色、多租户场景下的模板管理、通知规则、发送记录、失败重试、已读回执、定时提醒

---

## 模式选择

**选定模式：** 对等协作

**选择理由：**
消息系统天然跨产品（通知场景矩阵）、交互（多端通知体验）、技术（多渠道架构）三个维度，无单一主导领域。7 个发送渠道、8 个功能模块、多角色多租户的设计需要三方对等碰撞。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**通知场景清单：**
- 患者端 7 个场景：预约成功、就诊提醒（提前24h）、叫号通知、预约取消、停诊通知、候补成功、就诊完成
- 医生端 3 个场景：排班通知、请假审核结果（WebSocket 实时）、系统消息
- 租户管理员 3 个场景：订阅到期提醒（7/3/1/0天，优先级0/1/2/2）、用量警告（80%/90%/100%）、欠费通知
- 来源：appointments/service_booking.py:698, service_flow.py, tasks/notification_task.py:230, infrastructure/notifications/service.py:143,223,305

**发送渠道现状：**
| 渠道 | 状态 | 配置位置 |
|------|------|---------|
| 站内信 | 已实现 | messages 表 |
| 微信订阅消息（小程序） | 已实现 | system_settings (category=wechat) |
| 短信 | 部分实现（仅验证码） | system_settings (category=sms) |
| 邮件 | 已实现 | system_settings (smtp_*) |
| WebSocket 实时推送 | 已实现（医生端） | 无需额外配置 |
| APP Push | 未实现 | — |
| 企业微信 | 未实现 | — |
| 微信服务号 | 未实现 | — |

**角色消息矩阵：**
- 患者：站内信 ✅、微信订阅 ✅、短信 🔶、邮件 🔶
- 医生：站内信 ✅、WebSocket ✅
- 管理员：站内信 ✅

**消息模板现状：**
- 站内消息模板（message_templates 表）：5 个已定义（appointment_success, appointment_remind, queue_call, appointment_cancelled, stop_clinic_patient）
- 微信订阅消息模板：3 个 template_id 配置在 system_settings
- 邮件模板（email_templates 表）：7 种类型（预约确认、提醒、取消、签到、叫号、完成、停诊）
- 模板变量替换：字符串 `{variable}` 占位符替换（service_templates.py:116）

**SaaS 多租户特征：**
- 所有通知表包含 tenant_id 字段
- 模板支持全局（tenant_id=NULL）和租户自定义
- 微信配置按租户隔离（system_settings）
- 通知偏好按用户维度存储（含 tenant_id）
- 租户级通知（订阅/用量/欠费）走独立基础设施模块
- 业务通知用量限制：未实现

**前端通知 UI：**
- 机构端：公告列表/表单、消息列表/发送、预约须知、通知日志（6 个页面）
- 患者端 H5：消息中心（Tab 分类、下拉刷新、左滑删除、跳转关联业务）
- 患者端小程序：个人中心消息入口，消息模块标注"待实现"
- 医生端：消息中心 + WebSocket 实时连接状态指示器

### Designer — 用户视角

**页面清单与结构：**
| 端 | 页面 | 路由 | 组件行数 |
|---|------|------|---------|
| Admin | 公告列表 | /content-center/content/notice | 54 |
| Admin | 公告表单 | /content-center/content/notice/create | 142 |
| Admin | 消息列表 | /content-center/message/list | 75 |
| Admin | 发送消息 | /content-center/message/create | 94 |
| Admin | 预约须知 | /organization/medical-config/booking-notice | 276 |
| Admin | 通知日志 | /system/monitoring/notification-logs | 153 |
| Patient H5 | 消息中心 | /message | 272 |
| Doctor | 消息中心 | /message | 282 |
| Patient Miniapp | 个人中心（消息入口） | /packageProfile/pages/index | 625 |

**交互模式统计：**
- 患者端 H5 消息中心：Tab 分类（全部/预约/就诊/系统）、下拉刷新（PullToRefresh）、上拉加载（InfiniteScroll）、左滑删除（SwipeAction）、未读蓝色边框
- 医生端消息中心：Tab 分类（全部/排班/预约/系统）、分页加载、全部已读按钮、删除按钮、WebSocket 状态指示器（绿/蓝/红 Tag）
- 管理端：HeaderActions Popover 下拉面板预览消息、Bell 图标 + Badge、全部已读按钮

**站内信交互：**
- 已读/未读：点击标记已读，蓝色边框标识未读
- 全部已读：患者端 Dialog 确认、医生端 Modal 确认、管理端 HeaderActions 按钮
- 删除：患者端左滑、医生端点击按钮、管理端 API
- 跳转：患者端点击消息跳转预约详情/就诊记录（按 messageType 和 relatedId）

**公告/通告 UI：**
- 管理端：ProTable 列表展示，类型枚举（系统公告/停诊通知/活动通知），置顶 Tag，富文本编辑器
- 其他端：公告作为站内消息类型展示

**通知偏好设置 UI：**
- 后端 API 和 TypeScript 类型已定义（notification-preference.ts:3-25）
- 通道级开关：sms, email, wechat, in_app
- 类型级开关：appointment, reminder, queue_call, stop_clinic, system
- 免打扰时段：quietHoursStart, quietHoursEnd
- 前端设置页面：未找到实现

**消息提示组件：**
- 管理端：HeaderActions Bell + Badge + Popover（858 行大组件）
- 患者端：TabBar 消息按钮 showBadge, 消息统计卡片
- 医生端：消息列表头像 Badge 红点
- 无障碍：LiveRegion 组件支持屏幕阅读器播报（toast-live.tsx）

**跨端差异：**
| 维度 | H5 (antd-mobile) | 小程序 (Taro+NutUI) | 管理端 (Ant Design Pro) | 医生端 (Ant Design) |
|------|-------------------|---------------------|------------------------|---------------------|
| 交互 | 触摸优化、左滑删除 | 消息模块待实现 | 表格、Popover | 列表、WebSocket |
| 状态管理 | React State | React State | Umi Max | React State |
| 实时通信 | 无 | 无 | 无 | WebSocket |

**消息类型定义（packages/shared/src/types/message.ts）：**
- MessageType: appointment | consultation | schedule | system | stop_clinic | feedback
- Message 接口：id, userId, userType, title, content, messageType, relatedId, isRead, readAt, createdAt
- UnreadCount 接口：total, appointment, consultation, schedule, system, stopClinic, feedback

### Engineer — 技术视角

**存储层事实：**
- 5 个通知相关表：Message, MessageTemplate, NotificationLog, NotificationPreference, BookingNotice
- Message 表：13 个字段，tenant_id + store_id 双维度索引
- MessageTemplate 表：支持全局模板（tenant_id=NULL）和租户自定义，唯一约束 code
- NotificationLog 表：channel(sms/email/in_app/wechat), status(pending/sent/failed), retry_count
- NotificationPreference 表：唯一约束 (user_id, user_type)，5 个类型开关 + 4 个通道开关 + 免打扰时段

**核心引擎事实：**
- 4 个后端模块：messages, notification_logs, notification_preferences, booking_notices
- MessageService：创建消息、发送通知（含偏好检查）、模板渲染
- MessageTemplateService：模板 CRUD + 变量渲染（字符串替换）
- 通知发送流程：偏好检查 → 模板渲染 → 渠道发送 → 日志记录
- 模板渲染方式：`{variable}` 占位符的字符串替换（service_templates.py:116-123）

**API/协议事实：**
- 消息中心 API：14 个端点（CRUD + 模板管理 + 发送/批量发送）
- 通知日志 API：4 个端点（列表 + 统计 + 详情 + 重试）
- 通知偏好 API：2 个端点（获取 + 更新）
- WebSocket 事件类型（医生端）：11 种（PATIENT_SIGNED_IN, PATIENT_CALLED, QUEUE_UPDATED 等）
- Celery 队列：notification 专用队列，预约提醒每 30 分钟执行

**微信推送实现：**
- WechatService：send_subscribe_message（service.py:159-222）
- WechatTokenManager：Redis 缓存 Token（7000s 过期），键格式 wechat:token:{tenant_id}:{app_id}
- WechatConfigResolver：配置优先级 环境变量 → system_settings → 门店级配置
- Token 过期自动重试（错误码 40001/42001）

**短信实现：**
- SmsService：仅验证码场景，6 位数字，5 分钟有效，60 秒间隔
- 工厂模式：mock（默认）/ aliyun（TODO）/ tencent（TODO）
- Redis 隔离：sms:{tenant_id}:{phone}:{code_type}

**邮件实现：**
- EmailService：SMTP 发送，支持模板（send_by_template）
- 配置项：smtp_host, smtp_port, smtp_user, smtp_password, smtp_ssl, sender_name, sender_email
- 邮件模板服务：email_template_service.py

**安全机制事实：**
- 通知 API 权限：message:list, message:send, message:delete
- 偏好设置与用户绑定（user_id + user_type 唯一约束）
- 微信 openid 作为用户标识，不直接暴露

**依赖和模块耦合事实：**
- 预约模块直接调用 MessageService（appointments/service_flow.py:190,256）
- 停诊模块直接调用 MessageService（schedule_suspensions/service.py）
- 业务模块与通知模块是硬编码的直接调用关系
- 外部 SDK：aiosmtplib ✅, wechatpayv3 ✅, alibabacloud_dysmsapi（注释）, tencentcloud-sdk-python（注释）
- 未集成：APP Push SDK、企业微信 SDK、微信服务号 SDK

**Celery 任务配置：**
| 任务 | 调度 | 队列 | 功能 |
|------|------|------|------|
| send_appointment_reminder_task | 每 30 分钟 | notification | 预约提醒（遍历租户） |
| refresh_wechat_token | 每 2 小时 | default | 微信 Token 刷新 |
| email_hook_task | 按需 | notification | 邮件异步处理 |
| no-show-auto-mark | 每 30 分钟 | scheduled | 爽约检测（非通知） |

**多租户隔离实现：**
- 数据层：所有通知表包含 tenant_id 索引
- 缓存层：Redis 键格式包含 tenant_id
- 配置层：微信/短信配置按租户存储在 system_settings
- 任务层：Celery 任务遍历租户，使用 set_tenant_context/clear_tenant_context
- 模板层：支持全局模板 + 租户覆盖

**错误处理和重试事实：**
- NotificationLog 有 retry_count 字段，但无自动重试逻辑
- 微信推送仅 Token 过期自动重试一次
- Celery 配置 task_acks_late=True，Worker 丢失时任务重新入队
- 通知日志 API 有手动重试端点 /notification-logs/{id}/retry

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 完整投票矩阵（对等协作模式）

| # | 议题 | PM | Designer | Engineer | Critic 质询 | 共识？ |
|---|------|-----|----------|----------|-------------|--------|
| 1 | 小程序消息模块是 P0 缺口 | +1 (阻断性) | +1 (体验割裂) | +1 (前后端未对接) | 质疑渠道必要性 | 🤝 (3/3) |
| 2 | 短信业务通知需补全 | +1 (P0, 触达率) | 中立 | +1 (8-16h) | — | 🤝 (2/3) |
| 3 | 通知偏好设置前端缺失 | +1 (P1→P0) | +1 (P0) | +1 (8-12h) | 🚨 关键：原因不明 | 🤝 (3/3) |
| 4 | 缺少统一通知发送抽象层 | +1 (事件驱动) | +1 (多渠道统一) | +1 (32-48h) | — | 🤝 (3/3) |
| 5 | 消息去重机制缺失 | 未讨论 | 未讨论 | 未讨论 | 🚨 关键：4渠道同内容 | ⚠️ (0/3) |
| 6 | Celery 租户遍历扩展性 | +1 (精度问题) | 未讨论 | +1 (16-24h) | 🚨 关键：1000+租户 | 🤝 (2/3) |
| 7 | 跨端交互一致性 | 中立 | +1 (P0) | +1 | — | 🤝 (2/3) |
| 8 | 失败通知自动重试 | 未讨论 | 未讨论 | +1 (12-20h) | — | 🤝 (1/3) |
| 9 | 模板引擎升级(Jinja2) | +1 (P2) | 未讨论 | +1 (12-20h) | 影响范围存疑 | 🤝 (2/3) |
| 10 | SaaS 用量统计/限制 | +1 (P0) | 中立 | 未讨论 | — | 🤝 (1/3) |
| 11 | 两套通知体系统一 | 未讨论 | 未讨论 | 未讨论 | 普通：设计还是债务？ | ⚠️ (0/3) |
| 12 | 通知频率限制(防骚扰) | 未讨论 | 未讨论 | 未讨论 | 普通：被遗漏 | ⚠️ (0/3) |

图例：
- ✅ = +1（同意）
- ❌ = 反驳（不同意）
- ⚡ = Critic 质询（Critic 不参与投票，仅对议题发起质询）
- 🤝 = 2/3 或 3/3 同意（共识，基于 PM/Designer/Engineer 三方投票）
- ⚠️ = ≤1/3 同意（分歧）

### 独到发现

1. **PM 交叉发现**：Celery 每 30 分钟粒度导致提醒时间不精确，提出三级提醒策略（24h/2h/30min）
2. **PM 交叉发现**：WebSocket 仅医生端实现，患者端叫号通知缺乏实时性
3. **PM 交叉发现**：已读回执(isRead/readAt)的商业价值未被利用（运营分析、合规证据、用户分群）
4. **Designer 交叉发现**：消息类型跨端分类不一致（H5: 全部/预约/就诊/系统 vs 医生端: 全部/排班/预约/系统 vs 小程序: 全部/预约/反馈/系统）
5. **Designer 交叉发现**：删除交互跨端不一致（H5 左滑 vs 医生端点击 vs 小程序无删除），且左滑对无障碍不友好
6. **Designer 交叉发现**：未读状态仅靠颜色区分（蓝色边框/背景色/红点），色盲用户无法辨别
7. **Engineer 交叉发现**：WechatConfigResolver 配置优先级链复杂（环境变量→system_settings→门店级），门店级配置未完全实现
8. **Engineer 交叉发现**：角色消息矩阵的渠道映射硬编码在 service_messages.py:21-34 的 `_CHANNEL_FIELD_MAP`

### Critic 质询

1. [Critic → 全体] 质询 1：消息去重 — 预约成功触发站内信+微信+短信+邮件，用户收到 4 条相同内容通知
   - 论据：NotificationPreference 按通道开关但无"智能去重"逻辑
   - 要求回应：PM / Engineer
   - 级别：🚨 关键

2. [Critic → 全体] 质询 2：通知偏好 UI 缺失原因 — 后端API+TS类型已完成，前端UI缺失
   - 论据：需求文档与技术实现脱节，用户无法控制通知行为
   - 要求回应：PM / Designer
   - 级别：🚨 关键

3. [Critic → 全体] 质询 3：Celery 遍历租户扩展性 — 1000+租户时单任务可能超时
   - 论据：for each tenant → fetch appointments → send，N+1 查询问题
   - 要求回应：Engineer
   - 级别：🚨 关键

4. [Critic → Engineer] 质询 4：两套通知体系分离 — infrastructure/notifications vs modules/messages
   - 论据：两个独立代码路径，统一管理困难
   - 要求回应：Engineer
   - 级别：普通

5. [Critic → PM] 质询 5：小程序/APP Push 渠道必要性 — 微信订阅消息是否已足够？
   - 论据：医疗预约低频高重要性，APP Push 增量价值存疑
   - 要求回应：PM
   - 级别：普通

6. [Critic → PM/Engineer] 质询 6：通知频率限制被遗漏 — 租户 1 小时发 1000 条如何拦截？
   - 论据：NotificationLog 记录历史但无频率控制或异常检测
   - 要求回应：PM / Engineer
   - 级别：普通

7. [Critic → PM/Engineer] 质询 7：模板条件逻辑限制影响范围
   - 论据：字符串替换无法实现条件显示，前端硬编码违背模板管理初衷
   - 要求回应：PM / Engineer
   - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 消息去重 — 4渠道同内容打扰 | 三方均未在 Round 1/2 讨论此问题 | 否 | 归入行动计划 P1，需设计渠道优先级策略 |
| 2 | 通知偏好 UI 缺失原因 | PM 确认应为 P0，Designer 确认需实现，但无人说明缺失原因 | 部分 | 归入行动计划 P0，需用户确认缺失原因 |
| 3 | Celery 租户遍历扩展性 | Engineer 承认性能风险（16-24h 修复），PM 提出三级提醒策略 | 是 | 纳入计划 P1 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：小程序消息模块是阻断性缺口**
   **结论：** 后端微信订阅消息已实现但前端未对接，小程序端消息中心标注"待实现"，患者主要入口之一的消息功能缺失。
   **建议行动：** 完成小程序消息中心页面开发，对接已有后端 API（message API + WebSocket），保持与 H5 端体验一致。
   **成本估算：** 16-24 小时（Engineer：前端页面开发 + API 对接）
   **优先级：** P0

2. **议题：短信业务通知渠道需补全**
   **结论：** 短信工厂模式已有框架（mock/aliyun/tencent），但 aliyun/tencent 实现为 TODO，当前仅支持验证码。业务通知（预约提醒、取消通知等）缺少短信兜底，影响触达率。
   **建议行动：** 实现 aliyun 或 tencent 短信 Provider，扩展 SmsService 支持业务通知模板发送。
   **成本估算：** 8-16 小时（Engineer：Provider 实现 + 业务通知模板集成）
   **优先级：** P0

3. **议题：通知偏好设置前端 UI 需实现**
   **结论：** 后端 API + TypeScript 类型定义已完成，前端设置页面缺失。用户无法控制通知渠道开关和免打扰时段。
   **建议行动：** 在患者端/医生端/管理端分别开发通知偏好设置页面。
   **成本估算：** 8-12 小时（Designer + Engineer）
   **优先级：** P0

4. **议题：缺少统一通知发送抽象层**
   **结论：** 各渠道（站内信/微信/短信/邮件/WebSocket）独立调用，业务模块硬编码依赖 MessageService。缺少统一接口导致渠道策略（去重、优先级、降级）无法实现。
   **建议行动：** 设计 NotificationDispatcher 统一接口，各渠道实现适配器，业务模块通过事件触发通知。
   **成本估算：** 32-48 小时（Engineer：架构重构）
   **优先级：** P1

5. **议题：失败通知自动重试机制**
   **结论：** NotificationLog 有 retry_count 字段但无自动重试逻辑，仅有手动重试 API。微信推送仅 Token 过期重试一次。
   **建议行动：** 开发 Celery 定时任务扫描失败通知，实现指数退避重试策略。
   **成本估算：** 12-20 小时（Engineer）
   **优先级：** P1

6. **议题：Celery 预约提醒任务优化**
   **结论：** 每 30 分钟遍历所有租户存在扩展性风险（N+1 查询），且 30 分钟粒度导致提醒时间不精确。
   **建议行动：** 方案 A：改为按租户分发子任务并行执行；方案 B：预约创建时设置精准定时任务。同时实现三级提醒（24h/2h/30min）。
   **成本估算：** 16-24 小时（Engineer）
   **优先级：** P1

7. **议题：跨端消息类型分类统一**
   **结论：** H5（全部/预约/就诊/系统）、医生端（全部/排班/预约/系统）、小程序（全部/预约/反馈/系统）分类不一致，导致跨端体验割裂。
   **建议行动：** 基于 MessageType 枚举统一各端 Tab 分类，补充缺失的消息类型展示。
   **成本估算：** 4-8 小时（Designer + Engineer）
   **优先级：** P1

8. **议题：消息去重策略（回应 Critic 关键质询 #1）**
   **结论：** 当前无去重机制，用户可能收到 4 条相同内容通知。需要设计渠道优先级策略（如：微信成功则不发送短信）。
   **建议行动：** 在 NotificationDispatcher 中实现渠道降级和去重逻辑：首选渠道发送成功则跳过降级渠道。
   **成本估算：** 8-12 小时（Engineer，随统一抽象层一起实现）
   **优先级：** P1

9. **议题：SaaS 通知用量统计与限制**
   **结论：** NotificationLog 记录发送历史但无聚合统计和配额限制。SaaS 分级定价需要通知配额管理。
   **建议行动：** 利用现有 NotificationLog 数据开发用量统计 API，实现租户级通知配额检查。
   **成本估算：** 16-24 小时（Engineer + PM）
   **优先级：** P1

### ⚡ 分歧项

1. **议题：两套通知体系是否需要统一**
   **各方立场：**
   - PM：未关注此问题
   - Designer：未关注此问题
   - Engineer：未明确表态
   - Critic：质疑 separation of concerns
   **裁决/建议：** 当前分离合理（infrastructure 处理平台级通知，modules 处理业务通知），但应共享统一的通知发送抽象层。归入 P2 观察项。
   **决策依据：** 两套体系服务不同对象（平台运营 vs 业务用户），强行统一增加耦合风险。

2. **议题：APP Push / 企业微信 / 微信服务号的优先级**
   **各方立场：**
   - PM：认为缺失影响 B2B 客户和触达率（P2）
   - Designer：未明确评估
   - Engineer：每渠道 24-40h 开发成本
   - Critic：质疑医疗预约场景下 APP Push 的增量价值
   **裁决/建议：** 暂不实现。医疗预约低频场景，微信订阅消息 + 短信已覆盖核心触达需求。企业微信可待 B2B 客户明确提出需求后再排期。
   **决策依据：** ROI 不高（开发成本高、医疗场景低频），现有渠道组合可满足 90%+ 场景。

3. **议题：通知频率限制（防骚扰）**
   **各方立场：**
   - PM：未讨论
   - Designer：未讨论
   - Engineer：未讨论
   - Critic：提出租户/用户级别的频率限制需求
   **裁决/建议：** 归入待定。需要 PM 明确业务规则（频率阈值、冷却时间、超限处理策略）。
   **决策依据：** 需要产品策略输入才能设计技术方案。

---

## 被低估的优势

1. **多租户隔离实现完善** — Critic 提醒：数据层(tenant_id)、缓存层(Redis键)、配置层(system_settings)、任务层(上下文切换) 四层隔离均已实现，这是扎实的架构基础。
2. **通知偏好数据模型设计完整** — 5 个类型开关 + 4 个通道开关 + 免打扰时段，虽无前端 UI 但后端已准备就绪。
3. **微信推送多租户配置解析** — WechatConfigResolver 支持环境变量→system_settings→门店级三级优先级，适应不同部署场景。
4. **Celery 任务租户隔离模式** — set_tenant_context / clear_tenant_context 模式可复用于其他需要遍历租户的任务。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 完成小程序消息中心页面 | 16-24h | 高 — 患者主要入口 | Designer + Engineer | |
| P0 | 实现短信业务通知(aliyun/tencent) | 8-16h | 高 — 触达率兜底 | Engineer | |
| P0 | 开发通知偏好设置 UI | 8-12h | 高 — 用户控制权 | Designer + Engineer | |
| P1 | 统一通知发送抽象层(NotificationDispatcher) | 32-48h | 高 — 架构基础 | Engineer | |
| P1 | 消息去重+渠道降级策略 | 8-12h | 高 — 用户体验 | Engineer | |
| P1 | 失败通知自动重试 | 12-20h | 中 — 送达率 | Engineer | |
| P1 | Celery 提醒任务优化(并行+三级提醒) | 16-24h | 中 — 精度+扩展性 | Engineer | |
| P1 | 跨端消息类型分类统一 | 4-8h | 中 — 体验一致性 | Designer + Engineer | |
| P1 | SaaS 通知用量统计与配额 | 16-24h | 中 — 商业模式 | PM + Engineer | |
| P2 | 模板引擎升级(Jinja2) | 12-20h | 中 — 模板灵活性 | Engineer | |
| P2 | HeaderActions 组件拆分 | 4-8h | 低 — 可维护性 | Designer + Engineer | |
| P2 | 无障碍增强(键盘导航/色盲友好) | 8-12h | 中 — 合规与包容性 | Designer + Engineer | |
| 待定 | 通知频率限制(防骚扰) | 待定 | 待定 — 需产品策略 | PM + Engineer | |
| 待定 | APP Push / 企业微信渠道 | 24-40h/渠道 | 待定 — 需用户确认需求 | PM + Engineer | |

### P0：立即执行（高价值、低成本）

1. **完成小程序消息中心页面**（16-24h）— 对接已有后端 message API，实现与 H5 端一致的消息列表、已读/未读、分类 Tab。消除"待实现"标签，关闭患者端核心缺口。

2. **实现短信业务通知**（8-16h）— 基于 SmsService 工厂模式实现 aliyun/tencent Provider，扩展业务通知模板发送。作为微信推送的降级渠道，提升触达率。

3. **开发通知偏好设置 UI**（8-12h）— 后端 API 和类型定义已就绪，开发患者端/医生端/管理端的通知偏好设置页面，让用户控制通知渠道和免打扰时段。

### P1：本轮迭代（高价值、中等成本）

1. **统一通知发送抽象层 NotificationDispatcher**（32-48h）— 设计统一接口，各渠道实现适配器模式。解耦业务模块与通知模块，支持渠道降级和去重策略。

2. **消息去重+渠道降级策略**（8-12h）— 随统一抽象层一起实现。首选渠道发送成功则跳过降级渠道，避免 4 条相同内容打扰用户。

3. **失败通知自动重试**（12-20h）— Celery 定时任务扫描失败通知，指数退避重试（1min→5min→30min），最大重试 3 次。

4. **Celery 提醒任务优化**（16-24h）— 按租户分发子任务并行执行，解决 N+1 查询。支持三级提醒策略（24h/2h/30min）。

5. **跨端消息类型分类统一**（4-8h）— 基于 MessageType 枚举统一 H5/医生端/小程序的 Tab 分类。

6. **SaaS 通知用量统计与配额**（16-24h）— 利用 NotificationLog 数据开发用量统计 API，实现租户级配额检查和超限告警。

### P2：下个周期规划（中等价值、较高成本）

1. **模板引擎升级**（12-20h）— 从字符串替换迁移到 Jinja2，支持条件逻辑和循环，提升模板表达能力。

2. **HeaderActions 组件拆分**（4-8h）— 将 858 行大组件拆分为 MessagePreview、StoreActions、TenantSwitcher 等独立组件。

3. **无障碍增强**（8-12h）— 消息列表键盘导航、WebSocket 状态非视觉反馈、未读状态非颜色标识。

### 待定：需用户确认

1. **通知频率限制（防骚扰）** — 需 PM 明确业务规则：租户级/用户级频率阈值、冷却时间、超限处理策略（静默丢弃/排队延迟/告警通知管理员）。

2. **APP Push / 企业微信 / 微信服务号渠道** — 需确认目标用户画像和渠道优先级。当前微信订阅消息 + 短信是否已满足需求？

3. **通知偏好 UI 缺失的历史原因** — Critic 关键质询：为什么后端已完成但前端未实现？是排期问题还是产品策略决策？影响 P0 行动项的执行方式。

---

## 摘要

**使用模式：** 对等协作

**关键共识：**
- 9 项达成共识（3 项 P0 + 6 项 P1）

**关键分歧：**
- 3 项需要决策者介入（两套通知体系统一、新渠道优先级、通知频率限制）

**Top 3 P0 行动：**
1. 完成小程序消息中心页面（16-24h，Designer + Engineer）
2. 实现短信业务通知 aliyun/tencent Provider（8-16h，Engineer）
3. 开发通知偏好设置 UI（8-12h，Designer + Engineer）

**Critic 关键洞察：**
- 消息去重是被三方系统性遗漏的核心问题 — 需要渠道优先级和降级策略
- 通知偏好 UI 缺失的原因需要澄清 — 影响是产品策略还是排期问题
- Celery 租户遍历的扩展性需要提前规划 — 1000+ 租户时可能成为瓶颈

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| — | — | — | 全程对等协作，未切换 |
