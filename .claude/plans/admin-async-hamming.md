# Admin 消息系统 -- 邮件接入情况分析

## Context

用户想确认 admin 消息相关功能逻辑，以及邮箱是否正确接入了消息系统。

## 分析结论

### 邮件渠道已实现但未接入主分发链路

邮件（email）作为通知渠道，在代码层面已经完整实现，但在实际消息分发中 **并未被使用**。具体表现：

#### 1. 邮件渠道已注册但不在默认策略中

**已有的基础设施：**
- `EmailChannel` 适配器：`apps/server/app/infrastructure/notifications/channels/email.py`
- `EmailService` 异步邮件服务：`apps/server/app/infrastructure/email/service.py`（aiosmtplib）
- `EmailTemplate` 模型：`apps/server/app/models/email_template.py`（12 种模板类型）
- 邮件渠道已在 `ChannelRegistry` 中注册

**问题所在 -- `_DEFAULT_CHANNEL_STRATEGY`：**

在 `dispatcher.py:46-57` 和 `unified_message/service.py:69-80` 中，所有消息类型的默认渠道策略均不包含 `email`：

```
appointment*      -> wechat -> sms -> in_app
schedule          -> websocket -> in_app
stop_clinic       -> wechat -> sms -> in_app
system            -> in_app
consultation      -> in_app
feedback          -> in_app
queue_call        -> websocket -> in_app
```

这意味着通过 `MessageService.send_appointment_notification()` 发送的通知 **永远不会走邮件渠道**。

#### 2. 邮件仅作为独立的"事件钩子"存在

邮件发送的唯一实际路径是 `core/events.py` 中的 `dispatch_event_email()`：
- 由预约状态变更触发（`AppointmentServiceBase._dispatch_email_event`）
- 投递 Celery 任务 `process_event_email`
- 发送给 **门店邮件接收人**（`store_email_recipients` 表），不是患者/医生
- 这是一条独立于主通知分发器的路径

#### 3. `NotificationEvent` 缺少邮箱数据

在 `service_messages.py:445-457` 中，创建 `NotificationEvent` 时只填充了：
- `recipient_phone` -- 从 Account/User 表获取
- `recipient_openid` -- 从 Account/User 表获取
- **未填充 `recipient_email`**

即使把 `email` 加入默认渠道策略，由于 `recipient_email` 为空，`EmailChannel.validate_recipient()` 也会返回失败，导致跳过。

#### 4. 用户模型可能缺少邮箱字段

`_get_user_contact_info()` 函数（`service_messages.py:29-51`）只查询 `phone` 和 `openid`，不查询 email。需要确认 Account/User 模型是否有 email 字段。

### Admin 前端消息功能完整度

| 功能模块 | 状态 | 说明 |
|---------|------|------|
| 站内信消息列表 | 完整 | 支持搜索、详情、批量操作 |
| 发送消息 | 完整 | 单条/批量，支持模板选择 |
| 统一模板管理 | 完整 | CRUD + 克隆 + 预览 + 测试发送 |
| 收件人规则 | 完整 | 5 种规则类型，事件驱动 |
| 邮件模板管理 | 完整 | CRUD + 测试发送 + 变量插件 |
| 门店邮件接收人 | 完整 | 按事件类型订阅 |
| 通知日志 | 完整 | 四通道统计 + 重试 |
| 通知配额 | 完整 | 按通道月度限额 + 趋势图 |
| 顶部通知按钮 | 完整 | 轮询未读数 + 弹出面板 |

### 已知问题

1. **邮件重试不可用**：`notification_retry_task.py` 和 `unified_message_retry_task.py` 中的 `_retry_email` 均返回 False（Celery 同步环境无法使用异步 EmailService）
2. **两套消息体系并存**：旧版 `MessageService` + 新版 `UnifiedMessageService`，通过 feature flag `beta_unified_message` 切换
3. **邮件模板有两套**：`EmailTemplate`（12 种类型）用于事件钩子；`UnifiedTemplate` 用于统一消息中心

## 总结

邮箱在消息系统中的接入状态：**基础设施完整，但未接入主通知链路**。

- 邮件渠道适配器、邮件服务、邮件模板、门店接收人管理均已实现
- 但主通知分发器的默认策略中不包含 email 渠道
- 患者/医生的通知只走 wechat -> sms -> in_app 降级链
- 邮件仅用于门店管理端的事件通知（独立路径）
