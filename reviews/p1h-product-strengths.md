# P1-H: 产品强项巩固

> 状态：已完成
> 日期：2026-06-30
> 目标：提炼项目核心强项，用于 To-B 销售/售前/文档宣传

---

## 1. 强项总览

本项目在同类医院挂号系统中，工程成熟度**显著高于中位数**。以下 3 个强项是竞品难以复制的核心壁垒。

---

## 2. 强项 1：全链路可观测

### 2.1 能力清单

| 组件 | 用途 | 配置 |
|---|---|---|
| **structlog** | 结构化日志（JSON 格式） | `apps/server/app/core/logging.py` |
| **Prometheus** | 指标采集（/metrics 端点） | `docker-compose.monitoring.yml` |
| **Grafana** | 可视化看板（30 天保留） | `docker-compose.monitoring.yml` |
| **Sentry** | 错误追踪（traces 采样 0.1） | `app/main.py:172-196` |
| **request_log** | 请求审计中间件 | `app/middleware/request_log.py` |
| **operation_log** | 操作审计中间件 | `app/middleware/operation_log.py` |
| **生产配置校验** | 启动时检查 SECRET_KEY/DEBUG/限流 | `app/main.py:123-169` |

### 2.2 竞品对比

| 能力 | 本项目 | 同类竞品（典型） |
|---|---|---|
| 结构化日志 | ✅ structlog JSON | ❌ print/logging |
| 指标采集 | ✅ Prometheus + /metrics | ❌ 无 |
| 可视化看板 | ✅ Grafana 30 天 | ❌ 无 |
| 错误追踪 | ✅ Sentry | ❌ 无 |
| 请求审计 | ✅ 中间件自动记录 | ❌ 手动 |
| 操作审计 | ✅ 中间件自动记录 | ❌ 手动 |
| 启动校验 | ✅ 生产配置检查 | ❌ 无 |

### 2.3 To-B 销售话术

> "我们的系统内置全链路可观测能力：结构化日志、Prometheus 指标、Grafana 看板、Sentry 错误追踪、请求/操作审计。您不需要额外搭建监控体系，开箱即用。生产环境启动时自动校验配置安全性，避免因配置错误导致线上事故。"

---

## 3. 强项 2：审批流引擎

### 3.1 能力清单

| 能力 | 实现 | 来源 |
|---|---|---|
| **BPMN 解析** | 标准 BPMN 流程定义 | `app/modules/approval_flows/bpmn_parser.py` |
| **条件求值** | 动态条件分支 | `condition_evaluator.py` |
| **指派人解析** | 角色/指定人/会签/或签 | `assignee_resolver.py` |
| **分布式锁** | Redis 防并发审批 | `engine.py` |
| **Immutable 快照** | 审批流程版本不可变 | `engine.py` |
| **Celery 异步通知** | 审批结果实时推送 | `engine.py` |
| **超时处理** | Celery Beat 定时检查 | `tasks/` |

### 3.2 竞品对比

| 能力 | 本项目 | 同类竞品（典型） |
|---|---|---|
| BPMN 标准 | ✅ 标准 BPMN 解析 | ❌ 自定义状态机 |
| 条件分支 | ✅ 动态条件求值 | ❌ 硬编码 |
| 会签/或签 | ✅ 支持 | ❌ 不支持 |
| 分布式锁 | ✅ Redis 防并发 | ❌ 无 |
| 流程版本 | ✅ Immutable 快照 | ❌ 无版本管理 |
| 异步通知 | ✅ Celery 推送 | ❌ 同步阻塞 |

### 3.3 To-B 销售话术

> "我们内置了企业级审批流引擎，支持标准 BPMN 流程定义、条件分支、会签/或签、分布式锁防并发、流程版本不可变快照。停诊审批、请假审批、退款审批等场景开箱即用，不需要额外采购审批系统。"

---

## 4. 强项 3：多租户 RBAC + DataScope

### 4.1 能力清单

| 能力 | 实现 | 来源 |
|---|---|---|
| **4 种租户识别** | Header X-Tenant-ID > X-Tenant-Code > 子域名 > 路径前缀 | `middleware/tenant_context.py` |
| **RBAC 权限** | Role 表 + role_permissions 关联表 + 权限码（如 `doctor:create`） | `models/admin.py` |
| **DataScope** | 数据范围控制（all/tenant/store/custom） | `models/admin.py` |
| **SubscriptionPlan** | 功能+用量控制 | `models/tenant.py` |
| **JWT 黑名单** | SHA256 + Redis 租户隔离 | `core/redis.py:728-772` |
| **限流** | Redis 滑动窗口（租户+IP+路径） | `middleware/rate_limit.py` |

### 4.2 竞品对比

| 能力 | 本项目 | 同类竞品（典型） |
|---|---|---|
| 多租户 | ✅ 4 种识别方式 | ❌ 单租户 |
| RBAC | ✅ 角色+权限码+数据范围 | ❌ 简单角色 |
| 数据隔离 | ✅ DataScope（all/tenant/store/custom） | ❌ 无 |
| 订阅控制 | ✅ SubscriptionPlan | ❌ 无 |
| JWT 安全 | ✅ 黑名单+租户隔离 | ❌ 无黑名单 |
| 限流 | ✅ 租户+IP+路径 | ❌ 无 |

### 4.3 To-B 销售话术

> "我们是真正的 SaaS 多租户架构：支持 4 种租户识别方式、RBAC 权限体系（角色+权限码+数据范围控制）、订阅计划管理（功能+用量控制）。每个医院的数据完全隔离，JWT 黑名单按租户隔离，限流按租户+IP+路径粒度控制。"

---

## 5. 其他强项（补充）

| 强项 | 说明 |
|---|---|
| **10 渠道通知** | email/sms/in_app/websocket/wechat/dingtalk/feishu/wecom/integration/base |
| **178 个后端测试** | unit/integration/security/architecture/perf |
| **import-linter 架构契约** | 强制分层（api→modules→common→infrastructure→core→db） |
| **CI/CD** | 6 个 workflow（build/test/deploy/security） |
| **Docker 安全** | read_only + no-new-privileges |
| **Celery Beat 30+ 定时任务** | 黑名单解禁/预约提醒/爽约检测/排班生成/支付对账/审批超时 |

---

## 6. 使用建议

### 6.1 售前材料
- 将"全链路可观测"、"审批流引擎"、"多租户 RBAC"作为**核心卖点**
- 竞品对比表可直接用于售前 PPT

### 6.2 文档
- README.md 补充"技术亮点"章节
- CLAUDE.md 补充"架构优势"章节

### 6.3 招标/采购评审
- 强调"开箱即用"（不需要额外采购监控/审批/RBAC 系统）
- 强调"安全合规"（JWT 黑名单、限流、审计日志、Docker 安全）

---

## 7. 交付物

- 📄 `reviews/p1h-product-strengths.md`：本报告
- 📄 建议更新 README.md / CLAUDE.md 补充技术亮点章节（待执行）
