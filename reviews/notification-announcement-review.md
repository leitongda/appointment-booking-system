# 通知管理 & 公告管理 评审报告

> 日期：2026-06-25
> 模式：集中调度（轻量 → 标准，因涉及数据正确性风险镜头）
> 范围：通知管理（infrastructure/notifications + unified_message + 3 Celery tasks）+ 公告管理（platform_announcements + content/notices）

---

## 系统架构概览

### 通知管理 — 双系统并存

| 系统 | 位置 | 状态 | 表 |
|------|------|------|-----|
| Legacy | `infrastructure/notifications/dispatcher.py` + `modules/messages/` | 已标记 deprecated | `notification_logs` |
| Unified | `modules/unified_message/` | 新系统，部分迁移 | `notification_groups` + `notification_recipients` + `notification_deliveries` + 4 张配置表 |
| Tenant | `infrastructure/notifications/service.py` | 独立系统 | `tenant_notifications` |

切换机制：`notification_task.py` 中 `_should_use_unified()` 函数判断使用哪个系统。

### 公告管理 — 双子系统

| 子系统 | 级别 | 用途 |
|--------|------|------|
| Content Notice | 门店级 | 门店管理员管理通知/公告 |
| Platform Announcement | 平台级 | 超管向租户广播公告 |

---

## P0 — 必须修复

### P0-1：平台公告 `read_count` 永远为 0

- **证据级别**：E1（直接证据）
- **来源**：`models/platform_announcement.py:41` 定义字段，`modules/platform_announcements/service.py` 全文无 `increment` 操作
- **置信度**：High
- **影响**：前端显示"阅读率"列（`platform-announcement.tsx:70`），但永远是 0%，功能完全失效
- **误报抑制**：用户确实会看到这个列，每次查看列表都会遇到；无已有防护
- **工程成本**：Low（1h）| **风险降低**：Medium | **杠杆率**：高

### P0-2：平台公告 `publish_at`（定时发布）被忽略

- **证据级别**：E1
- **来源**：`service.py:125` — `publish()` 方法直接覆盖 `publish_at = datetime.utcnow()`
- **置信度**：High
- **影响**：用户在创建表单中设置定时发布时间（`platform-announcement-form.tsx:155`），但发布时被忽略
- **误报抑制**：用户每次使用定时发布功能都会遇到；无已有防护
- **工程成本**：Medium（3h，需加 Celery 定时任务）| **风险降低**：Medium | **杠杆率**：中

### P0-3：平台公告 `expire_at`（过期时间）未生效

- **证据级别**：E1
- **来源**：`service.py` 全文无 `expire_at` 过滤；`get_list` 和 `get_published` 均不检查
- **置信度**：High
- **影响**：过期公告永久显示，用户设置的过期时间无效
- **误报抑制**：所有设置了过期时间的公告都会受影响；无已有防护
- **工程成本**：Low（1h，查询加 WHERE 条件）| **风险降低**：Medium | **杠杆率**：高

### P0-4：内容公告浏览量计数竞态条件

- **证据级别**：E1
- **来源**：`modules/content/service.py:392-397` — `increment_view` 先读后写，无锁
- **置信度**：High
- **影响**：高并发时浏览量计数不准确（丢失更新）
- **误报抑制**：公告详情页无认证要求（`router.py:281`），可被外部并发访问；低频场景影响小
- **工程成本**：Low（0.5h，改用 `UPDATE ... SET view_count = view_count + 1`）| **风险降低**：Medium | **杠杆率**：高

### P0-5：平台公告 `target_tenant_ids` 类型不匹配

- **证据级别**：E1
- **来源**：`schemas/platform_announcement.py:54` 声明 `list[str] | None`，`models/platform_announcement.py:24` 存储为 `Text`（JSON 字符串）
- **置信度**：High
- **影响**：API 返回 JSON 字符串而非数组，前端 multi-select 组件可能异常
- **误报抑制**：每次获取公告详情都会触发；前端可能有 JSON.parse 兜底（需验证）
- **工程成本**：Low（1h，schema 添加 `@validator` 或 model 改 `JSON` 列）| **风险降低**：High | **杠杆率**：高

---

## P1 — 应该修复

### P1-1：通知系统双轨并存，常量重复定义

- **证据级别**：E1
- **来源**：`dispatcher.py:20-54`、`unified_message/service.py:44-78`、`notification_preferences/service.py:8-21`
- **置信度**：High
- **影响**：`_CHANNEL_FIELD_MAP`、`_TYPE_FIELD_MAP`、`_DEFAULT_CHANNEL_STRATEGY` 在三处重复定义，修改一处易遗漏其他
- **工程成本**：Medium（2h，提取到 `app/constants/notification.py`）| **风险降低**：Medium | **杠杆率**：中

### P1-2：新通知系统（unified_message）无重试任务

- **证据级别**：E1
- **来源**：`notification_retry_task.py` 只查 `notification_logs` 表；`notification_deliveries` 表有 `retry_count`/`next_retry_at` 字段但无对应任务
- **置信度**：High
- **影响**：新系统发送失败的通知永远不重试
- **工程成本**：Medium（3h，新增 Celery task）| **风险降低**：High | **杠杆率**：高

### P1-3：前端批量操作无并发控制

- **证据级别**：E1
- **来源**：`message/index.tsx:61-83` — 批量已读/删除用 `Promise.all` 逐条发请求；`message/form.tsx:73-78` — 批量发送同理
- **置信度**：High
- **影响**：选中 100 条 = 100 个并发 HTTP 请求，可能触发限流或服务器过载
- **工程成本**：Low（1h，改为分批 `Promise.all` 或后端批量接口）| **风险降低**：Medium | **杠杆率**：高

### P1-4：医生端通知设置只显示 4/12 个字段

- **证据级别**：E1
- **来源**：`doctor/src/pages/settings/notification-settings.tsx:53-58` 只设置 4 个字段；`NotificationPreference` 有 12 个字段
- **置信度**：High
- **影响**：医生无法配置 `reminderEnabled`、`queueCallEnabled`、`stopClinicEnabled`、`emailEnabled`、`wechatEnabled`
- **工程成本**：Low（1h）| **风险降低**：Low | **杠杆率**：中

### P1-5：通知配额 Redis 竞态条件

- **证据级别**：E1
- **来源**：`infrastructure/notifications/quota.py:207-208` — `incr` 后 `get` 再 `set`，存在 TOCTOU
- **置信度**：High
- **影响**：高并发下配额计数可能不准确，可能超发
- **工程成本**：Low（0.5h，用 `incr` + `expire` 替代）| **风险降低**：Medium | **杠杆率**：高

---

## P2 — 建议修复

| # | 问题 | 来源 | 成本 | 杠杆率 |
|---|------|------|------|--------|
| P2-1 | 内容公告更新未传 `operator_id`，审计快照缺少操作人 | `content/router.py:320` vs `service.py:329` | 0.5h | 中 |
| P2-2 | 通知枚举重复：`NotificationChannel` ≈ `ChannelType`，`NotificationPriority`(int) vs `Priority`(string) | `enums/notification.py` | 1h | 低 |
| P2-3 | 收件人规则引擎只实现 doctor 角色，patient 角色返回空 | `rule_engine.py:140` | 1h | 中 |
| P2-4 | 统一消息软删除用 `is_read=2` 魔术数字，查询未过滤 | `unified_message/service.py:529` + `419-420` | 1h | 中 |
| P2-5 | 平台公告无详情页路由 | `config/routes/platform.ts` | 0.5h | 低 |
| P2-6 | 内容公告详情用 `dangerouslySetInnerHTML` 渲染 HTML，无 XSS 过滤 | `notice-detail.tsx:56-60` | 1h | 高 |
| P2-7 | 通知日志按天统计用 N+1 查询（30 天 = 30 条 SQL） | `notification_logs/service.py:323-338` | 1h | 中 |

---

## P3 — 记录但不行动

| # | 问题 | 说明 |
|---|------|------|
| P3-1 | `NotificationPreference` 类型定义在 `packages/api` 而非 `packages/shared` | 与 `Message`/`UnifiedTemplate` 位置不一致 |
| P3-2 | `Message.isRead` 类型为 `number` 而非 `boolean` | 类型不精确 |
| P3-3 | `recipient-rules.tsx` 用 `as any` 绕过类型检查 | `createListRequest` 返回类型不匹配 |
| P3-4 | 医生通知设置每个 Switch 有冗余 `onChange` | 与 Form `valuePropName="checked"` 重复 |
| P3-5 | 通知设置页面无 ARIA 属性 | 可访问性问题 |
| P3-6 | Prometheus 指标用 `tenant_id` 做 label | 高基数风险，租户数多时 Prometheus 内存压力大 |

---

## 行动计划

### P0 — 立即执行（共 6.5h）

| 行动 | 负责 | 成本 | 杠杆率 |
|------|------|------|--------|
| P0-1：公告详情接口增加 `read_count` 原子递增 | Engineer | 1h | 高 |
| P0-3：公告列表查询加 `expire_at > NOW()` 过滤 | Engineer | 1h | 高 |
| P0-4：`increment_view` 改用 SQL 原子递增 | Engineer | 0.5h | 高 |
| P0-5：`target_tenant_ids` 添加 Pydantic validator 做 JSON parse | Engineer | 1h | 高 |
| P0-2：`publish_at` 定时发布加 Celery beat 任务 | Engineer | 3h | 中 |

### P1 — 本轮迭代（共 8.5h）

| 行动 | 负责 | 成本 | 杠杆率 |
|------|------|------|--------|
| P1-2：为 `notification_deliveries` 新增重试 Celery task | Engineer | 3h | 高 |
| P1-1：提取常量到 `app/constants/notification.py` | Engineer | 2h | 中 |
| P1-3：前端批量操作加分批控制（每批 10 条） | Engineer | 1h | 高 |
| P1-5：Redis 配额改用 `incr` + `expire` 原子操作 | Engineer | 0.5h | 高 |
| P1-4：医生端补全通知偏好字段 | Engineer + Designer | 1h | 中 |
| P2-6：公告详情 HTML 渲染加 DOMPurify 过滤 | Engineer | 1h | 高 |

### P2 — 下周期

| 行动 | 负责 | 成本 |
|------|------|------|
| P2-1 ~ P2-5, P2-7 | Engineer | 共 5h |

---

## Open Risk

| 风险 | 说明 | 状态 |
|------|------|------|
| 双系统迁移完成度 | Legacy `dispatcher.py` 与 Unified 并存，`_should_use_unified` 特征标志未全局生效 | 需确认迁移计划 |
| `dangerouslySetInnerHTML` XSS | 公告内容 HTML 未过滤，若内容来源不可信则有安全风险 | 待确认内容来源可信度 |
