# 架构依赖摘要

生成时间：2026-06-29
审计工具：codegraph（索引就绪）+ Grep import 分析 + 入口回溯

## 依赖拓扑总览

仓库：pnpm + Turbo monorepo，前后端分层基本清晰。

### 前端依赖拓扑（健康）

```
apps/{admin,doctor,patient-h5,temp-registration,website} ──┬─> @hospital/api ──> @hospital/shared
apps/{patient-miniapp,miniapp-instance}                    ┘
```

- 各 app 间**零源码耦合**，仅经共享包通信。
- 共享包**无反向 import apps/\* 源码**，边界完整。
- 已知问题：`packages/shared/src/miniapp/wechatAuth.ts` 反向 import `@hospital/api`（未在 package.json 声明，靠 pnpm hoisting 运行的隐式循环；ImageUpload 已用依赖注入正确规避，wechatAuth 未跟进）。
- 例外：`apps/mini-appointment-miniapp` 完全绕过共享层自造 util/request/auth（详见重复实现报告）。

### 后端依赖拓扑（分层成立，存在 4 类设计气味）

```
api/v1 (路由注册 84 模块)
   └─> modules/<name>/ (router → service → models/schemas)
         ├─> common/ (横切认证/权限，被 57 文件引用，健康)
         └─> infrastructure/ (email/sms/storage/payments/notifications，应最底层)
```

## 循环依赖（4 处，均用延迟 import 规避，可运行但属设计气味）

| 严重度 | 循环对 | 位置 | 拆分建议 |
|--------|--------|------|----------|
| 高（前端） | `packages/shared` → `@hospital/api` 未声明隐式循环 | `packages/shared/src/miniapp/wechatAuth.ts:1` import `@hospital/api` 的 userApi | 网络调用上移到 apps 层，shared 只留纯逻辑+类型；或效仿 ImageUpload 用注入函数 |
| 中 | `appointments` ↔ `waitlist` | `modules/appointments/service_booking.py:660` ↔ `modules/waitlist/service_promotion.py:10` | 抽 waitlist_promotion 共享 service 单向依赖；或事件驱动 |
| 中 | `approval_flows` ↔ `leave_requests` | `modules/approval_flows/business_callbacks.py:12` ↔ `modules/leave_requests/service.py:142` | approval_flows 引入 Protocol 回调接口，业务模块实现 callback |
| 中 | `payments` ↔ `refunds` | `modules/payments/service.py:343` ↔ `modules/refunds/service.py:36` | 合并到 billing/payment_flow，或抽 payment_state 查询层 |

## 跨层 / 边界泄漏

| 严重度 | 问题 | 位置 | 建议 |
|--------|------|------|------|
| 高 | infrastructure 反向依赖 4 个 modules 业务层（6 处） | `infrastructure/email/service.py`、`infrastructure/notifications/quota.py`、`infrastructure/image/processor.py`、`infrastructure/notifications/channels/wechat.py` import `app.modules.{email_templates,settings,notification_logs,unified_message}` | infra 改为接收 DTO/回调，由 modules 层主动调用并传入配置；或纯数据访问下沉到 models 层 |
| 中 | router 层直接操作 model/DB 绕过 service（≥10 模块） | `modules/{accounts,admin,appointments,audit_logs,attendance_records,analytics,cms,doctor_portal}/router*.py` 内 `select(...).execute()` | 强制 router→service→models 单向 |
| 中 | 安全横切关注点错置于 tenants 模块 | `modules/tenants/password_policy.py` 的 PasswordPolicyValidator 被 auth/admin/accounts/doctors 4 模块经延迟 import 引用 | 迁移到 `app/common/password_policy.py`（无状态校验）+ settings 配置 |

## 上帝模块 / 异常扇入扇出

| 严重度 | 目标 | 数据 | 建议 |
|--------|------|------|------|
| 中 | `modules/schedules/service_mutation.py` | **1623 行**（最大上帝服务）；扇出 5，扇入 23 | 按子操作继续拆分（生成/冲突/暂停/批量） |
| 低 | `modules/appointments/` | 扇出 7（依赖最多：payments/refunds/rule_engine/settings/unified_message/visit_types/waitlist） | 已拆 service_booking/query，可再把支付/退款链路抽到协调层 |
| 低 | `modules/unified_message/service.py` | 974 行，扇入 17 | 按 channel 拆分 |
| 信息 | `app/common/` | 被 57 文件引用 | 横切层广泛引用属正常设计，健康 |

## 关键文件路径（绝对）

- `/Users/leijiadashao/letond/appointment-booking-system/packages/shared/src/miniapp/wechatAuth.ts:1` — 前端隐式循环（**P0，前端唯一硬伤**）
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/infrastructure/email/service.py:12` — infra 反向耦合（模块级 import）
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/infrastructure/notifications/quota.py:15` — infra 反向耦合
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/modules/appointments/service_booking.py:660` ↔ `modules/waitlist/service_promotion.py:10` — 循环
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/modules/approval_flows/business_callbacks.py:12` ↔ `modules/leave_requests/service.py:142` — 循环
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/modules/payments/service.py:343` ↔ `modules/refunds/service.py:36` — 循环
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/modules/tenants/password_policy.py:30` — 错置的横切关注点
- `/Users/leijiadashao/letond/appointment-booking-system/apps/server/app/modules/schedules/service_mutation.py` — 1623 行上帝服务

## 建议优先级

- **P0**：修复 wechatAuth 隐式循环（前端唯一硬伤，删 shared→api 依赖）
- **P1**：infrastructure 反向解耦（6 处）；approval_flows 引入回调接口解环
- **P2**：密码策略迁移到 common；router 绕过 service 治理；schedules 服务继续拆分
