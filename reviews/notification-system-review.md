# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-04-18
> 审查目标：通知系统四通道（短信/邮箱/站内通知/微信推送）实现状态与逻辑正确性

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 任务为聚焦于通知功能域的技术审计，需要快速收敛识别各通道实现状态和逻辑缺陷。PM 评估功能完整性，Designer 评估前端交互体验，Engineer 评估技术实现质量。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**通知功能范围：**
- 后端通知相关模块：messages（站内消息）、email_templates（邮件模板）、store_email_recipients（邮件接收人）、websocket（实时推送）、booking_notices（预约须知，非通知发送）
- 基础设施层：infrastructure/notification/service.py（停诊/预约/就诊提醒/叫号）、infrastructure/sms/service.py（短信验证码）、infrastructure/email/service.py（邮件发送）、infrastructure/wechat/service.py（微信登录+订阅消息）
- 前端消息中心：admin（消息列表+发送）、doctor（WebSocket实时）、patient-h5（下拉刷新）、patient-miniapp（下拉刷新）

**四通道实现状态：**
- 短信：部分实现 — 验证码发送可用（Redis缓存+频率限制+5分钟有效期），但阿里云/腾讯云SDK代码为注释状态（`infrastructure/sms/service.py:126-188`），`SMS_PROVIDER` 默认值为 `"mock"`（config.py:122），停诊短信仅打印日志（`infrastructure/notification/service.py:117-158`）
- 邮箱：完整实现 — SMTP异步发送（aiosmtplib）、邮件模板渲染（{{variable}}占位符）、7种事件钩子、门店级接收人管理
- 站内通知：完整实现 — Message/MessageTemplate 数据模型、CRUD API（14个端点）、未读统计（按类型分组）、批量发送、租户+门店隔离
- 微信推送：部分实现 — 仅预约提醒场景（每30分钟定时任务），其他场景（预约成功/取消/叫号等）未覆盖；`send_subscribe_message()` 已实现（`infrastructure/wechat/service.py:159-222`）

**通知场景覆盖矩阵：**

| 场景 | 站内信 | 邮件 | WebSocket | 微信 | 短信 |
|------|--------|------|-----------|------|------|
| 预约成功 | 已实现 | 已实现 | 已实现(医生端) | 未实现 | 未实现 |
| 预约取消 | 已实现 | 已实现 | 未实现 | 未实现 | 未实现 |
| 就诊提醒 | 已实现 | 未实现 | 未实现 | 已实现 | 未实现 |
| 叫号 | 已实现 | 已实现 | 已实现(医生端) | 未实现 | 未实现 |
| 签到 | 未实现 | 已实现 | 已实现(医生端) | 未实现 | 未实现 |
| 就诊完成 | 未实现 | 已实现 | 已实现(医生端) | 未实现 | 未实现 |
| 停诊 | **已实现**(纠正) | 死代码中存在 | 未实现 | 未实现 | 仅日志 |
| 爽约 | 未实现 | 已实现 | 未实现 | 未实现 | 未实现 |
| 支付通知 | 未实现 | 未实现 | 未实现 | 未实现 | 未实现 |

**通知模板：**
- 站内消息模板：MessageTemplate 模型存在，API已实现（CRUD），但前端未使用模板功能
- 邮件模板：EmailTemplate 模型完整，7种事件类型模板，变量占位符替换
- 微信模板：仅配置表存储 template_id，无管理界面
- 短信模板：未实现模板系统，停诊短信内容硬编码

**通知偏好设置：**
- 前端 Patient-H5 和 MiniApp 有通知开关 UI，但仅存在前端 state 中，未持久化到后端
- 无独立的通知偏好数据模型
- 无细粒度通知类型控制

### Designer — 用户视角

**通知页面与路由：**
- Admin：`/content-center/message`（消息列表+发送），Header NotificationButton（Popover+4 Tab），每分钟轮询未读数
- Doctor：`/message`（消息中心283行），WebSocket 实时推送，连接状态指示器（实时/连接中/离线），4 Tab 分类
- Patient-H5：`/message`（273行），PullToRefresh 下拉刷新，InfiniteScroll 无限滚动，SwipeAction 滑动删除，Framer Motion 动画
- MiniApp：`packageProfile/pages/message/index`（346行），PullToRefresh，useReachBottom 上拉加载，分包预加载

**交互模式统计：**
- 实时通知覆盖：Doctor端WebSocket（✅），Admin端1分钟轮询（❌ 无WS），Patient-H5（❌ 手动刷新），MiniApp（❌ 手动刷新）
- 未读标记：Admin Badge + 每分钟刷新，Doctor Tab Badge + WS推送，Patient-H5 Tab Badge + 卡片蓝色边框，MiniApp 顶部文字 + 红点
- 批量操作：全部已读（4端均有），批量删除（未实现），清空已读（API支持但前端未调用）
- 通知跳转：Patient端按类型跳转详情页，Doctor端仅标记已读无跳转

**微信小程序订阅消息：**
- 未找到 `wx.requestSubscribeMessage` 调用
- 小程序用户无法在微信服务通知中收到消息

**移动端适配：**
- Patient-H5：Ant Design Mobile，卡片布局，滑动删除，动画效果
- MiniApp：NutUI + Taro，分包策略（packageProfile），支持主题色动态变化和长辈模式

**通知偏好设置：**
- Patient-H5 `/settings`：推送通知开关（Switch），仅前端 state
- MiniApp `packageProfile/pages/settings/index`：预约提醒开关 + 系统通知开关，仅前端 state
- 无后端同步、无细粒度控制、无免打扰时段

### Engineer — 技术视角

**存储层事实：**
- 站内消息：PostgreSQL Message 表（tenant_id, store_id, user_id, user_type, message_type, related_id, is_read, extra_data）
- 邮件模板：PostgreSQL EmailTemplate 表（无 tenant_id，全局共享）
- 消息模板：PostgreSQL MessageTemplate 表（无 tenant_id，全局共享）
- 短信验证码：Redis `sms:{tenant_id}:{phone}:{code_type}`，有效期300秒
- 微信 Token：Redis `wechat:token:{tenant_id}:{app_id}`，缓存7000秒
- 分布式锁：Redis `tenant:{tenant_id}:{lock_name}`

**核心引擎事实：**
- 短信：SmsService 验证码生成（6位数字）+ Redis存储 + 60秒频率限制；阿里云/腾讯云发送方法为注释状态
- 邮件：EmailService 使用 aiosmtplib 异步发送；EmailTemplateService 使用 {{variable}} 占位符渲染；email_hook_task 通过 Celery 异步投递
- 站内消息：MessageService 完整 CRUD + 未读统计（按类型分组）；WebSocket ConnectionManager 按 doctor_id 管理，支持 Redis Pub/Sub 多实例广播
- 微信：WechatService.send_subscribe_message() 已实现；WechatTokenManager 使用 DCL + 分布式锁防止并发刷新；Token 过期自动重试（40001/42001）
- 事件分发：dispatch_event_email() 通过 Celery task.delay() 异步投递，不阻塞主流程

**API/协议事实：**
- WebSocket 路由：`/api/v1/ws/doctor/{doctor_id}?token={jwt_token}`，仅医生端
- WebSocket 消息类型：14种（CONNECTED, HEARTBEAT, ERROR, 6种患者状态, QUEUE_UPDATED, NEW_APPOINTMENT, SCHEDULE_SUSPENDED, LEAVE_REQUEST_REVIEWED, SYSTEM_MESSAGE）
- Celery 队列：default / scheduled / notification（通知任务路由到 notification 队列）
- 邮件重试：max_retries=2, default_retry_delay=60

**安全机制事实：**
- WebSocket JWT Token 验证
- 短信验证码 60秒频率限制 + 300秒有效期
- 微信 Token 分布式锁（防止并发刷新）
- 所有通知操作有日志记录

**依赖和模块耦合事实：**
- 事件钩子系统（core/events.py）解耦业务与通知
- 停诊通知服务（infrastructure/notification/service.py）内同时调用站内信+邮件+短信，但站内信发送停诊通知的方法未被实际调用
- 微信推送仅在 Celery 定时任务中使用，未在其他业务流程中集成
- 消息模板 CRUD API 已实现，但业务代码中创建消息时未使用模板系统（标题/内容硬编码）

**多租户支持：**
- Message 表有 tenant_id 和 store_id 字段
- Redis 缓存键包含 tenant_id
- EmailTemplate 和 MessageTemplate 表无 tenant_id（全局共享）
- 系统配置（SMTP/微信/短信）全局共享，无租户隔离

---

## Round 2：辩论层

### Team Lead 交叉验证纠正

**事实纠正 1 — 停诊通知站内信实际已被调用**
- PM 报告"停诊通知站内信方法未被调用"为事实错误
- 实际调用路径：
  - `schedule_suspensions/service.py:157` → `_send_stop_clinic_notifications()` → `message_service.send_stop_clinic_notification()`（第232行）
  - `schedules/service_mutation.py:382` → `message_service.send_stop_clinic_notification()`
- 但 `infrastructure/notification/service.py:notify_suspend()` 确实是**死代码**（仅定义，从未被任何代码调用）
- 覆盖矩阵中"停诊"站内信应更正为"已实现"

**事实纠正 2 — `infrastructure/notification/service.py` 整体为死代码**
- `notify_suspend()`：从未被调用（grep 确认）
- `notify_appointment_success()`：从未被调用（grep 确认，预约成功通知在 `appointments/service_booking.py:308` 直接调用 MessageService）
- `notify_appointment_remind()`：从未被调用（grep 确认，就诊提醒在 Celery 任务中处理）
- `notify_queue_call()`：从未被调用（grep 确认，叫号通知在 `appointments/service_flow.py:192` 直接调用 MessageService）
- 结论：该文件是遗留代码，所有通知已在业务模块层直接实现

**交叉发现 1 — 通知调用路径碎片化**
- 同一业务事件的通知通过不同代码路径执行：
  - 停诊：`schedule_suspensions/service.py` 发站内信，但无邮件/SMS（老路径死代码中才有）
  - 预约成功：`appointments/service_booking.py` 发站内信 + WebSocket，邮件通过 `dispatch_event_email()` 触发
  - 叫号：`appointments/service_flow.py` 发站内信 + WebSocket，邮件通过事件钩子
- 无统一通知入口，各通道调用分散在不同模块

**交叉发现 2 — 通知模板系统设计定位不清**
- MessageTemplate CRUD API 完整存在，但业务代码硬编码标题/内容
- `scripts/init_message_templates.py` 存在初始化脚本（含停诊模板定义），但模板在运行时未被读取使用
- 邮件模板系统（EmailTemplate）则完整集成到业务流程中

### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 短信通道：业务通知未接入 | 可能是有意的设计取舍（成本），非缺陷 | 缺乏用户需求数据 | 待定：需确认是否需要短信通知 |
| 邮件通知仅面向门店 | 符合机构管理系统定位（通知工作人员） | 设计合理性待确认 | 设计合理，非缺陷 |
| 站内信模板未使用 | 技术债：API完整但业务代码硬编码 | 模板定位不清 | P1：统一迁移 |
| 微信推送仅预约提醒 | 需确认是否为产品设计决策 | 缺乏归责分析 | P1：扩展覆盖场景 |
| 通知偏好未持久化 | 功能缺失，用户每次看到默认值 | 无用户投诉数据 | P2：完善持久化 |
| 停诊通知路径碎片化 | 死代码 + 活跃代码不一致 | 事实错误已纠正 | P0：清理死代码，统一路径 |
| WebSocket 仅医生端 | 医生端需要实时性，患者端非必需 | 缺乏场景分析 | 设计合理，非缺陷 |
| 模板表无租户隔离 | SaaS 多租户下的潜在风险 | 需评估安全影响 | P1：添加 tenant_id |
| infrastructure/notification 死代码 | 遗留代码清理 | 未被 Round 1 发现 | P0：删除或标记废弃 |
| 通知发送失败静默处理 | fire-and-forget 模式有消息丢失风险 | 缺乏监控告警 | P0：添加失败监控 |

### Critic 质询

1. [Critic → Engineer] 停诊通知"未被调用"的事实错误
   - 论据：`schedule_suspensions/service.py:232` 确实调用了 `send_stop_clinic_notification()`
   - 要求回应：确认遗漏原因
   - 级别：普通
   - **已回应**：PM/Engineer 报告中的确遗漏了 `schedule_suspensions` 模块的调用路径。Team Lead 交叉验证已纠正。

2. [Critic → PM] 短信"未实现"是缺陷还是设计取舍？
   - 论据：短信成本与业务价值未分析，站内信+微信可能已满足需求
   - 要求回应：说明定义依据
   - 级别：普通
   - **已回应**：缺乏用户数据支撑，归入待定。

3. [Critic → Engineer] 模板系统设计定位？
   - 论据：API完整但业务代码硬编码，存在矛盾
   - 要求回应：明确设计意图
   - 级别：普通
   - **已回应**：初始化脚本存在但未集成，属技术债。

4. [Critic → Designer] 患者端 WebSocket 必要性？
   - 论据：未分析实时性需求，轮询可能足够
   - 要求回应：提供场景分析
   - 级别：普通
   - **已回应**：患者端通知多为异步场景（预约结果），手动刷新可接受。

5. [Critic → PM] **通知系统产品定位的根本性模糊**
   - 论据：患者通知 vs 工作人员通知目标不同，未区分优先级
   - 要求回应：明确核心目标
   - 级别：🚨 关键
   - **已回应**：系统定位为机构管理 SaaS，核心目标是机构运营效率。工作人员通知（邮件/WebSocket）优先级最高，患者通知（站内信/微信）次之。

6. [Critic → PM] 微信推送场景归责？
   - 论据：可能受微信订阅消息授权率限制
   - 要求回应：产品决策还是技术遗漏
   - 级别：普通
   - **已回应**：需确认，但 `send_subscribe_message()` 基础设施已完备，扩展成本低。

7. [Critic → Designer/PM] 通知偏好未持久化的影响？
   - 论据：缺乏用户投诉数据
   - 要求回应：实际影响评估
   - 级别：普通
   - **已回应**：功能存在但无效，优先级 P2。

8. [Critic → Engineer] **通知发送失败处理的完备性**
   - 论据：fire-and-forget 模式可能导致消息静默丢失，缺乏监控
   - 要求回应：评估消息丢失风险
   - 级别：🚨 关键
   - **已回应**：站内信写入数据库有事务保证；邮件有 Celery 重试（max_retries=2）；微信推送失败记录 failed_users 但无后续处理；短信发送失败仅日志。**建议增加通知发送监控和失败重试看板。**

9. [Critic → Engineer] 事件钩子系统优势被遗漏
   - 论据：架构设计亮点未提及
   - 要求回应：说明遗漏原因
   - 级别：普通
   - **已回应**：已补充至"被低估的优势"。

10. [Critic → Engineer] **模板表无租户隔离的多租户安全风险**
    - 论据：EmailTemplate/MessageTemplate 无 tenant_id，多租户下可能冲突
    - 要求回应：评估安全风险
    - 级别：🚨 关键
    - **已回应**：当前模板表无租户隔离，租户 A 创建的模板对所有租户可见。虽然当前所有模板为系统内置（通过初始化脚本），但随着功能演进（允许租户自定义模板），将产生数据混淆风险。

11. [Critic → Engineer] WebSocket 多实例广播未验证
    - 论据：声称支持 Redis Pub/Sub 但未验证
    - 要求回应：提供实现证据
    - 级别：普通
    - **已回应**：代码中 Redis Pub/Sub 实现完整（websocket.py:241-298），包含频道订阅和消息广播逻辑。未发现测试用例。

### Critic 关键质询追踪

| # | 关键质询内容 | 回应摘要 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | 产品定位模糊：患者通知 vs 工作人员通知 | 系统定位为机构管理 SaaS，工作人员通知优先 | 是 | 纳入计划 |
| 2 | 通知发送失败静默处理 | 站内信有事务保证，邮件有重试，微信/短信缺乏监控 | 是 | 纳入计划（P0） |
| 3 | 模板表无租户隔离 | 当前无影响（系统内置模板），未来有风险 | 是 | 纳入计划（P1） |

### 被低估的优势

1. **事件钩子系统**（`core/events.py`）：通过 Celery 异步投递，优雅解耦业务逻辑与通知，不阻塞主流程，易于扩展新的事件类型
2. **WebSocket Redis Pub/Sub 多实例广播**：支持水平扩展，多实例部署时消息可跨实例传递
3. **微信 Token DCL + 分布式锁**：双重检查锁 + 分布式锁防止并发刷新，Token 过期自动重试，实现健壮
4. **站内消息系统完整性**：从数据模型到 API 到前端消息中心，覆盖全部 CRUD + 未读统计 + 分类管理 + 批量操作

---

## Round 3：共识层

### 裁决依据

以"机构管理 SaaS"为产品定位，按以下优先级评估：
1. 工作人员通知通道完整性（直接影响机构运营效率）
2. 患者通知通道可靠性（影响患者体验但不影响核心业务流程）
3. 代码架构健康度（影响长期维护成本）
4. 多租户安全性（SaaS 基础要求）

### 共识项

1. **议题：infrastructure/notification/service.py 为死代码**
   - 结论：全部 4 个方法（notify_suspend, notify_appointment_success, notify_appointment_remind, notify_queue_call）从未被调用，实际通知在业务模块层直接执行
   - 建议行动：删除或标记为废弃
   - 成本估算：1h
   - 优先级：P0

2. **议题：通知发送失败缺乏监控**
   - 结论：fire-and-forget 模式下，邮件/微信/短信失败仅记录日志，无监控告警和后续处理
   - 建议行动：增加通知发送结果记录表 + 失败重试看板
   - 成本估算：8h
   - 优先级：P0

3. **议题：站内信模板系统未集成到业务流程**
   - 结论：MessageTemplate API 完整但业务代码硬编码标题/内容，初始化脚本存在但运行时未使用
   - 建议行动：将业务代码中的硬编码消息改为从模板系统读取
   - 成本估算：6h
   - 优先级：P1

4. **议题：模板表缺乏租户隔离**
   - 结论：EmailTemplate/MessageTemplate 无 tenant_id，当前使用系统内置模板无影响，但租户自定义模板时将产生冲突
   - 建议行动：为两个模板表添加 tenant_id 字段，查询时过滤租户
   - 成本估算：4h
   - 优先级：P1

5. **议题：微信推送仅覆盖预约提醒场景**
   - 结论：send_subscribe_message() 基础设施完备，扩展其他场景（预约成功/取消/叫号）成本低
   - 建议行动：在预约成功、预约取消、叫号场景中集成微信推送
   - 成本估算：6h
   - 优先级：P1

6. **议题：通知偏好未持久化**
   - 结论：前端有开关 UI 但仅存 state，无后端同步，功能实际无效
   - 建议行动：添加通知偏好数据模型 + API，前端同步到后端
   - 成本估算：6h
   - 优先级：P2

7. **议题：微信小程序未调用 wx.requestSubscribeMessage**
   - 结论：用户无法在微信服务通知中收到消息，微信推送的前提条件未满足
   - 建议行动：在预约成功页面添加订阅消息授权请求
   - 成本估算：3h
   - 优先级：P1

### 分歧项

1. **议题：短信业务通知是否需要接入**
   - PM 立场：短信为高触达率通道，对患者通知有价值
   - Engineer 立场：短信有成本，且当前站内信+微信可能已满足需求
   - Critic 挑战：缺乏用户需求数据支撑
   - 裁决/建议：归入待定，需用户确认业务优先级
   - 决策依据：短信成本较高，在确认用户需求前不应投入

2. **议题：患者端是否需要 WebSocket 实时推送**
   - Designer 立场：患者端手动刷新体验不如实时推送
   - Engineer 立场：患者端通知多为异步场景，实时性要求不高
   - Critic 挑战：缺乏用户投诉数据
   - 裁决/建议：当前设计合理，暂不增加患者端 WebSocket
   - 决策依据：患者端通知场景（预约成功/取消）不需要毫秒级实时性

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 清理 infrastructure/notification/service.py 死代码 | 1h | 高（代码健康） | Engineer | 待执行 |
| P0 | 增加通知发送结果记录 + 失败监控看板 | 8h | 高（可靠性） | Engineer | 待执行 |
| P1 | 模板表添加 tenant_id 租户隔离 | 4h | 高（多租户安全） | Engineer | 待执行 |
| P1 | 站内信模板系统集成到业务流程 | 6h | 中（代码规范） | Engineer | 待执行 |
| P1 | 微信推送扩展至预约成功/取消/叫号场景 | 6h | 高（患者体验） | Engineer | 待执行 |
| P1 | 小程序添加 wx.requestSubscribeMessage 授权 | 3h | 高（微信推送前提） | Designer+Engineer | 待执行 |
| P2 | 通知偏好持久化（数据模型+API+前端同步） | 6h | 中（功能完善） | Engineer+Designer | 待执行 |
| 待定 | 短信业务通知接入（需确认需求） | 16h | 待定 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **清理死代码** `infrastructure/notification/service.py`（1h）
   - 删除或标记 `NotificationService` 类的 4 个方法为 @deprecated
   - 确保无引用后安全删除

2. **增加通知发送监控**（8h）
   - 新建 `NotificationLog` 表记录每次通知发送结果（通道、状态、错误信息）
   - 添加 Celery 任务失败告警（接入现有日志系统）
   - 微信推送失败后增加重试机制（当前仅记录 failed_users）

### P1：本轮迭代（高价值、中等成本）

1. **模板表租户隔离**（4h）— EmailTemplate/MessageTemplate 添加 tenant_id，查询时自动过滤
2. **模板系统集成**（6h）— 业务代码从硬编码改为从 MessageTemplate 读取标题/内容
3. **微信推送扩展**（6h）— 在预约成功、取消、叫号等场景调用 `send_subscribe_message()`
4. **小程序订阅授权**（3h）— 在关键操作点添加 `wx.requestSubscribeMessage` 调用

### P2：下个周期规划（中等价值、较高成本）

1. **通知偏好持久化**（6h）— 新建 NotificationPreference 模型 + API + 前端同步

### 待定：需用户确认

1. **短信业务通知接入**（16h）— 需确认是否需要向患者发送短信通知，以及使用哪个服务商（阿里云/腾讯云）
2. **停诊通知统一入口** — 当前 `schedule_suspensions` 和 `schedules/service_mutation` 两条路径是否需要合并

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 7 项达成共识

**关键分歧：**
- 2 项需要决策者介入（短信通道优先级、患者端实时推送）

**Top 3 P0 行动：**
1. 清理 `infrastructure/notification/service.py` 死代码（1h）— 消除代码混乱根源
2. 增加通知发送结果记录 + 失败监控看板（8h）— 解决消息静默丢失风险
3. 模板表添加 tenant_id 租户隔离（4h）— 消除多租户安全隐患

**Critic 关键洞察：**
- 通知系统产品定位存在模糊：患者通知 vs 工作人员通知的优先级需明确
- fire-and-forget 模式下存在消息丢失风险，缺乏监控和告警
- 模板表全局共享在 SaaS 多租户场景下有安全隐患

**四通道状态总结：**
- 站内通知：完整可用，是系统最可靠的通知通道
- 邮箱：面向工作人员完整可用，事件钩子系统设计优雅
- 微信推送：基础设施完备，但场景覆盖仅预约提醒，需扩展
- 短信：验证码可用，业务通知未接入（服务商 SDK 为注释状态）

---

## 附录：模式切换日志

无模式切换。
