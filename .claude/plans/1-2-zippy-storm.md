# 租户系统全面审查报告

## 背景

对项目的多租户 SaaS 架构进行全面审查，对照 13 个独立维度（原 16 项中有 3 项重复）评估现有实现的完整度，识别缺失功能和优化方向。

> **审查质量声明：** 本报告经自适应多智能体团队（PM/Designer/Engineer + Critic）三轮审查验证，P0 安全缺陷全部经代码级确认，准确性 88%。完整审查画布见 `reviews/tenant-system-gap-analysis-review.md`。

## 总体评估

项目在**租户隔离、认证鉴权、订阅管理、缓存隔离**方面实现扎实，是生产级水准。主要短板集中在：**日志/审计的租户维度缺失、备份恢复未实现、运维自动化不足**。

## 已实现优势（审查补充）

审查中确认的系统优势，作为差距分析的参照基准：

1. **23个业务模型已正确包含 tenant_id**（占全部业务模型66%），覆盖所有核心业务链路
2. **Redis 全维度隔离**：短信验证码、Token、会话、黑名单、分布式锁全部包含租户维度
3. **租户切换器细节优化**：5分钟缓存、表单页保护、全屏过渡遮罩、空状态处理
4. **订阅管理完整闭环**：从计划定义 -> 配额检查 -> 用量统计 -> 到期提醒 -> 自动欠费标记
5. **Celery 任务最佳实践**：显式参数传递 tenant_id（ContextVar 无法跨进程，当前方式正确）
6. **多端租户感知分层**：管理端完整感知、患者端守卫式阻断、医生端透明隔离

---

## 维度逐一分析

### 1. 租户管理 — 部分实现

已实现: CRUD、状态管理(禁用/正常/欠费/试用)、订阅计划、配额覆盖、品牌配置、域名配置、唯一性校验、批量统计、前端管理页面。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TM-1 | `features` 字段使用 Pydantic schema 替代原始 JSON，防止脏数据 | P0 |
| TM-2 | 租户初始化钩子：创建时自动生成默认角色/科室/门店模板 | P1 |
| TM-3 | 租户管理员仪表板：`/tenants/me` 下增加用量仪表盘和账单摘要 | P1 |
| TM-4 | 租户自助注册流程：注册表单 -> 试用激活 -> 引导配置 | P1 |
| TM-5 | 租户标签/分组：按行业/地区/客户等级分组筛选 | P2 |

### 2. 租户认证 — 完整

已实现: JWT 含 tenant_id、登录时租户状态检查(禁用/欠费/到期)、跨租户访问拒绝、写操作守卫、角色守卫(平台/租户管理员)、Token 黑名单隔离、会话隔离、结构化错误码、平台管理员跨租户切换。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TA-1 | 租户级密码策略配置(复杂度/过期) | P1 |
| TA-2 | 并发会话限制：Redis 维护租户维度会话计数 | P2 |

### 3. 租户隔离 — 完整

已实现: 23 个业务模型均有 tenant_id、统一过滤工具(tenant_filter.py)、四种租户识别方式(Header/子域名/路径)、ContextVar 异步隔离、Redis 全维度隔离(短信/Token/会话/锁/限流)、8 个隔离测试文件。

**已确认的安全缺陷:**

| 编号 | 问题 | 优先级 | 文件 |
|------|------|--------|------|
| TI-1 | `audit_logs/router.py` 查询签到日志无 tenant_id 过滤 | P0 | `modules/audit_logs/router.py` |
| TI-2 | `feedbacks/service.py` 查询无 tenant_id 过滤 | P0 | `modules/feedbacks/service.py` |
| TI-3 | 文件下载接口缺少租户访问校验(当前仅路径隔离) | P0 | 文件相关模块 |

### 4. 租户监控 — 部分实现

已实现: TenantUsageLog 每日统计、QuotaChecker 实时配额检查、用量汇总 API、Celery 定时任务(每日统计/订阅到期/用量限制)、规则引擎性能监控。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TMo-1 | 请求日志(RequestLogMiddleware)增加 tenant_id 维度，支持按租户分析性能 | P0 |
| TMo-2 | 租户活跃度统计(DAU/WAU/MAU) | P1 |
| TMo-3 | 用量趋势分析 API：`/tenants/{id}/usage/trends` 返回周/月同比 | P1 |
| TMo-4 | 外部告警渠道集成：邮件/企业微信推送 | P1 |
| TMo-5 | Prometheus metrics 端点 | P2 |

### 5. 租户日志 — 部分实现

已实现: OperationLogMiddleware 自动记录写操作、RequestLogMiddleware 记录耗时、全局异常处理、敏感字段脱敏、模块/操作名称映射。

**已确认的缺陷:**

| 编号 | 问题 | 优先级 | 文件 |
|------|------|--------|------|
| TL-1 | 操作日志 `log_data` 不含 `tenant_id` | P0 | `middleware/operation_log.py:238-250` |
| TL-2 | 请求日志不记录租户上下文 | P0 | `middleware/request_log.py` |
| TL-3 | 操作日志查询 API 无租户过滤 | P0 | 操作日志相关 router |

补充:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TL-4 | 日志保留策略：按租户配置保留天数 | P2 |

### 6. 租户审计 — 部分实现

已实现: AuditMixin(created_by/updated_by)、set_create_audit/set_update_audit 工具、规则集审计日志、签到审计日志查询。

**已确认的缺陷:** `audit_logs/router.py` 查询签到记录完全没有 tenant_id 条件(见上方 TI-1)。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TAu-1 | 新增 `TenantAuditLog` 模型：记录租户级关键操作(配额变更/状态变更/订阅变更)，含 before/after snapshot | P0 |
| TAu-2 | 数据变更差异追踪：关键模型(Tenant/Admin/Store/Doctor)记录变更前后值 | P1 |
| TAu-3 | 审计报告生成与导出(PDF/Excel) | P2 |

### 7. 租户通知 — 部分实现（审查修正：从"完整"降级）

已实现（后端）: TenantNotification 模型、完整 CRUD 服务、订阅到期提醒(7/3/1天，含去重)、用量警告(80%/90%/100%)、欠费通知、API 端点(`/tenants/me/notifications`)、多渠道调度器、预约提醒三级策略、失败重试。

> **审查发现：** 前端无租户通知管理界面。前端仅有系统消息中心（Message API），NotificationButton 组件消费的是 Message API 而非 TenantNotification API。后端完整但前端未对接，因此降级为"部分实现"。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TN-1 | 平台级公告功能：向全部/部分租户广播消息 | P1 |
| TN-2 | 通知文案模板化：按租户自定义通知内容 | P2 |
| TN-3 | 通知阅读率统计 | P2 |

### 8. 租户支持 — 未实现

完全缺失。需要:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TS-1 | 新增 `SupportTicket` 模块：工单提交、状态流转(待处理->处理中->已解决->已关闭)、分配、SLA 计时 | P1 |
| TS-2 | SLA 配置：在 SubscriptionPlan.features 中配置响应时间 | P2 |
| TS-3 | 帮助文档/FAQ 模块 | P2 |

### 9. 租户反馈 — 部分实现

已实现: Feedback 模型完整 CRUD、类型分类(建议/投诉/错误/其他)、状态流转、回复通知、统计。

**已确认的安全缺陷:** `feedbacks/service.py` 所有查询无 tenant_id 过滤 — 租户 A 可看到租户 B 的反馈(见上方 TI-2)。

补充:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TF-1 | 反馈满意度评价 | P2 |
| TF-2 | 租户反馈统计面板 | P2 |

### 10. 租户升级 — 部分实现

已实现: 订阅计划功能开关、配额覆盖机制、订阅创建时自动激活欠费租户、自动续费标记。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TU-1 | 降级检查：降级前校验当前资源是否超出新配额 | P0 |
| TU-2 | 功能开关统一校验框架：FeatureFlagService 统一管理 | P1 |
| TU-3 | 计划对比页面 | P1 |
| TU-4 | 灰度功能发布：features 中增加 beta_features | P2 |

### 11. 租户迁移 — 部分实现

已实现: 初始迁移脚本(单租户到多租户)、Alembic 迁移。

缺失/优化:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TMi-1 | ~~导入导出增加租户过滤~~ **审查修正**：导入(import_export/service_import.py)和导出(export/router.py)已实现租户过滤，降级为"验证导出完整性并补充端到端测试" | P1 |
| TMi-2 | 跨租户数据迁移 API：`POST /tenants/{id}/migrate` | P1 |
| TMi-3 | 迁移前数据校验：检查目标租户配额、ID 冲突 | P1 |

### 12. 租户备份 — 未实现

完全缺失。需要:

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TB-1 | 租户数据导出备份 API：`POST /tenants/{id}/export` 导出为 JSON/SQL | P0 |
| TB-2 | 自动备份调度：Celery 任务按订阅计划配置周期 | P1 |
| TB-3 | 备份文件 AES-256 加密存储 | P1 |
| TB-4 | 备份完整性校验(SHA256) | P2 |

### 13. 租户恢复 — 未实现

完全缺失。仅有软删除恢复(TenantService.restore)。

| 编号 | 建议 | 优先级 |
|------|------|--------|
| TR-1 | 租户数据导入恢复 API：`POST /tenants/{id}/import` | P0 |
| TR-2 | 恢复前预检：检查配额、ID 冲突 | P1 |
| TR-3 | 恢复后完整性验证 | P1 |
| TR-4 | 灾难恢复预案文档(RPO/RTO 目标) | P1 |

---

## P0 汇总（必须立即修复 — 安全/隔离风险）

| # | 问题 | 影响文件 | 影响范围 | 估时 |
|---|------|---------|---------|------|
| 1 | 操作日志不含 tenant_id | `middleware/operation_log.py` | 所有租户的所有写操作日志 | 0.5d |
| 2 | 请求日志不含 tenant_id | `middleware/request_log.py` | 所有租户的全部 HTTP 请求 | 0.5d |
| 3 | 签到审计日志无租户过滤 | `modules/audit_logs/router.py` | 所有租户的签到记录可跨租户查看 | 0.5d |
| 4 | 反馈模块无租户隔离 | `modules/feedbacks/service.py` + `models/feedback.py` | 所有租户的反馈数据可跨租户查看 | 1.5d |
| 5 | 文件下载无租户校验 | 文件相关模块 | 理论上可通过 URL 猜测访问其他租户文件 | 1d |
| 6 | features 字段无类型校验 | `models/tenant.py` + 新增 schema | 所有租户的功能开关配置可能存在脏数据 | 1d |
| 7 | 新增 TenantAuditLog 模型 | 新文件 | 无法追溯租户关键操作历史 | 2d |
| 8 | 降级检查(防超配额) | `modules/tenants/service.py` | 降级时可能导致配额溢出 | 1d |

**P0 总估时（后端）: ~8d**（审查修正：实际 9-10d，反馈隔离和降级检查各增 0.5d）
**前端工时估算: 15-22d**（9项建议需新增前端页面）
**总工时: 24-32d**

## 架构级建议

1. **统一租户审计表** — 新增 `tenant_audit_events`，通过事件驱动收集所有租户级操作，解决当前审计分散问题
2. **TenantContext 传播标准化** — （审查修正）Celery 任务继续使用显式参数传递 tenant_id（已是最佳实践，ContextVar 无法跨进程）；请求上下文中统一使用 TenantContext（已实现）
3. **功能开关框架化** — FeatureFlagService 统一管理 features 字段的读取、校验、灰度控制
4. **备份恢复管道** — 标准化流程：数据序列化 -> 加密 -> 存储 -> 校验 -> 恢复

## 缺少 tenant_id 的模型完整清单（审查补充）

报告仅提及 Feedback/AppointmentCheckin/OperationLog 3 个模型，审查发现共 15 个模型缺少 tenant_id：

**P1（应修复，影响业务隔离）：**
| 模型 | 文件 | 说明 |
|------|------|------|
| Feedback | feedback.py | 用户反馈（无 tenant_id 字段） |
| AppointmentCheckin | rule_set.py:262 | 签到日志（通过 appointment 关联） |
| OperationLog | admin.py | 操作日志（无 tenant_id 字段） |
| PointLog | point_log.py | 积分流水 |
| UserBehaviorLog | behavior_log.py | 用户行为日志 |
| WaitlistEntry | waitlist.py | 候补队列 |
| UserFavorite | user_favorite.py | 用户收藏 |
| StoreVisitTypeConfig | store_visit_type_config.py | 门店就诊类型配置 |
| StoreEmailRecipient | store_email_recipient.py | 门店邮件收件人 |
| BookingNotice | booking_notice.py | 预约公告 |
| DoctorBookingSetting | doctor_booking_setting.py | 医生预约设置 |
| ConsultationFee | consultation_fee.py | 诊费配置 |
| Content(新闻/公告/轮播) | content.py | 内容管理 |

**P2（可延后，日志/辅助功能）：**
| 模型 | 文件 | 说明 |
|------|------|------|
| ScheduleGenerationLog | schedule_generation_log.py | 排班生成日志 |
| AdminLoginHistory | admin.py | 登录历史 |

> 注：部分模型可能通过关联父对象的 tenant_id 实现间接隔离（如 AppointmentCheckin 通过 Appointment），需逐个验证查询路径是否包含租户过滤。

## 关键文件清单

- `apps/server/app/models/tenant.py` — 核心模型，新增 TenantAuditLog 等
- `apps/server/app/middleware/operation_log.py` — 必须增加 tenant_id
- `apps/server/app/middleware/request_log.py` — 必须增加 tenant_id
- `apps/server/app/modules/audit_logs/router.py` — 修复无租户过滤
- `apps/server/app/modules/feedbacks/service.py` — 修复无租户隔离
- `apps/server/app/common/deps.py` — 认证依赖扩展
- `apps/server/app/common/tenant_filter.py` — 复用过滤工具
- `apps/server/app/common/quota.py` — 配额检查扩展
