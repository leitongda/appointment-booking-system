# 📋 预约管理模块需求文档

## 一、模块概述

预约管理模块是医院挂号系统的核心模块，负责处理患者预约挂号、签到、就诊、取消等全流程业务。

## 二、功能清单

### 2.1 机构端功能

| 功能 | 说明 |
|------|------|
| 预约列表 | 查看所有预约记录，支持多维筛选 |
| 预约详情 | 查看预约详细信息 |
| 预约统计 | 按门店/科室/医生/时间维度统计 |
| 签到管理 | 生成签到二维码，查看签到记录 |
| 建卡配置 | 配置就诊人信息采集字段 |
| 爽约管理 | 爽约记录，黑名单规则配置 |

### 2.2 患者端功能

| 功能 | 说明 |
|------|------|
| 预约挂号 | 选择科室/医生/时段，提交预约 |
| 我的预约 | 查看预约列表和详情 |
| 取消预约 | 取消未就诊的预约 |
| 扫码签到 | 到院后扫码签到 |
| 待支付订单重试支付 | 对待支付预约重新拉起微信支付 |

### 2.3 医生端功能

| 功能 | 说明 |
|------|------|
| 今日预约 | 查看当日预约患者 |
| 历史预约 | 查看历史预约记录 |
| 叫号管理 | 呼叫下一位患者 |

## 三、业务规则

### 3.1 预约规则
- 可提前预约天数：由系统设置配置（默认14天）
- 当天预约：由系统设置控制是否允许
- 每人每天限制：最多预约N次（默认3次）
- 同一医生同一时段：不可重复预约

### 3.2 取消规则
- 就诊前N小时内不可取消（默认2小时）
- 取消后号源自动释放
- 已支付且未就诊的预约取消时，系统同步发起退款；若退款调用失败，则整笔取消回滚
- 已完成预约的退款仅保留后台管理员例外处理，不开放患者自助

### 3.3 爽约规则
- 预约后未签到视为爽约
- 爽约N次后加入黑名单（默认3次）
- 黑名单用户限制预约

### 3.4 支付与退款规则
- 免费预约直接进入已预约状态，不创建支付单
- 付费预约创建后进入待支付状态，并返回可直接用于小程序支付的 `payment_params`
- 待支付预约仅允许预约本人重新获取支付参数；未显式传入 `openid` 时，后端回退到当前登录用户绑定值
- 支付成功回调仅结算待支付预约，重复成功回调按幂等成功处理
- 支付超时任务仅会将仍处于待支付状态的预约标记为已过期，并只释放一次号源
- 商户订单号以运行时 `appointment_no` 为准，支付/退款统一复用该值
- 退款接口金额单位统一为“元”
- `PaymentProfile.notify_url` 仅用于支付回调；退款回调优先使用 `PaymentProfile.refund_notify_url`，未配置时回退到 `notify_url`
- 退款创建、退款成功回调、退款失败回调都会同步更新预约上的 `refund_status` 与 `refund_amount`

## 四、状态流转

```
0 待支付 → 1 已预约 → 2 已签到 → 4 就诊中 → 5 已完成
    ↓          ↓         ↓        ↓
    7 已过期   6 已取消   7 已过号  5 已完成
                \       /
                 8 已爽约
```

- `3 历史候诊` 目前不属于运行时有效主状态，按历史遗留死状态处理，不再作为前后端正常流转分支
- 支付轴与退款轴独立维护，不把退款处理中塞回预约主状态

## 五、动作矩阵

| 动作/事件 | 触发入口 | 允许角色 | 前置状态 | 目标状态 | 号源变化 | 支付变化 | 退款变化 | 副作用/审计 |
|------|------|------|------|------|------|------|------|------|
| 创建预约 | 患者端 `POST /appointments` | 患者 | 无 | 0待支付 / 1已预约 | `booked_slots +1` | 免费=无支付；收费=冻结支付快照 | 无 | 写预约创建日志，返回统一 `AppointmentResponse` |
| 重试支付 | 患者端 `GET /appointments/{id}/payment-params` | 预约本人 | 0待支付 | 0待支付 | 无 | 重新生成支付参数 | 无 | 权限校验为本人；不改主状态 |
| 支付成功回调 | `POST /payments/wechat/callback` | 系统 | 0待支付 | 1已预约 | 无 | 写入 `payment_transaction_id/paid_at` | 无 | 幂等处理重复回调，记录支付成功日志 |
| 支付超时 | 定时任务 `payment.cancel_expired_pending` | 系统任务 | 0待支付 | 7已过期 | `booked_slots -1` | 关闭待支付 | 无 | 写 `cancel_reason=支付超时自动取消`，记录任务日志 |
| 未支付取消 | 患者/管理员取消接口 | 患者本人 / 有权限管理员 | 0待支付 | 6已取消 | `booked_slots -1` | 无 | 无 | 记录取消原因与操作日志 |
| 已支付取消 | 患者/管理员取消接口 | 患者本人 / 有权限管理员 | 1已预约 / 2已签到 | 6已取消 | `booked_slots -1` | 保留原支付凭证 | 同事务创建退款，失败整体回滚 | 记录取消日志、退款日志 |
| 签到 | 患者扫码 / 后台签到 | 患者本人 / 管理员 | 1已预约 | 2已签到 | 无 | 无 | 无 | 记录签到日志与 `checkInMethod` |
| 取消签到 | 后台取消签到 | 超管/有权限管理员 | 2已签到 | 1已预约 | 无 | 无 | 无 | 记录操作日志 |
| 叫号 | 后台叫号 | 管理员/医生 | 2已签到 | 4就诊中 | 无 | 无 | 无 | 写 `call_time`，刷新队列 |
| 过号 | 后台过号 | 管理员/医生 | 4就诊中 | 7已过号 | 无 | 无 | 无 | 记录过号日志 |
| 重新叫号 | 后台重新叫号 | 管理员/医生 | 7已过号 | 4就诊中 | 无 | 无 | 无 | 记录重新叫号日志 |
| 完成就诊 | 后台完成 | 管理员/医生 | 4就诊中 | 5已完成 | 无 | 无 | 无 | 写 `complete_time`，记录完成日志 |
| 标记爽约 | 后台标记 | 管理员 | 1已预约 / 2已签到 | 8已爽约 | 释放后续排队占位 | 无 | 无 | 记录爽约日志/黑名单相关逻辑 |
| 管理员退款 | `POST /refunds` | 有 `appointment:refund` 且有门店权限的管理员 | 1已预约 / 2已签到 / 4就诊中 / 5已完成 | 主状态不变 | 无 | 无 | `pending -> processing/failed` | 已完成退款视为例外操作，必须填写原因 |
| 退款回调 | `POST /refunds/wechat/callback` | 系统 | 退款中 | 主状态不变 | 无 | 无 | `success/failed`，同步 `refund_status/refund_amount` | 记录退款结果日志 |
| 晚到支付回调自动退款 | 支付成功回调命中已过期/已取消预约 | 系统 | 7已过期 / 6已取消 | 主状态不变 | 无 | 补齐支付凭证 | 自动创建全额退款 | 记录“支付回调晚到”与自动退款日志 |

## 六、查询与权限

- `GET /appointments/query/{id}`：普通用户只能看自己的预约；管理员还必须通过门店访问校验
- `GET /appointments/query/by-no/{appointment_no}`：同样执行普通用户归属校验与管理员门店校验
- 退款相关接口 `refundable-amount / create / list / detail` 均要求 `appointment:refund` 权限 + 门店级访问控制

## 七、API 契约

- `AppointmentResponse` 为预约详情与列表的唯一真相，统一输出：
  - `storeName`
  - `checkInMethod`
  - `paymentAmount/paymentTime/paymentTransactionId`
  - `refundStatus/refundedAmount`
- 统计字段以 `confirmed / signedIn / inProgress / completed / cancelled / noShow` 为准，不再混用 `pending`

## 八、数据模型

### appointments 表
| 字段 | 类型 | 说明 |
|------|------|------|
| id | UUID | 主键 |
| appointment_no | VARCHAR | 预约单号(唯一) |
| user_id | UUID | 用户ID |
| patient_id | UUID | 就诊人ID |
| doctor_id | UUID | 医生ID |
| schedule_id | UUID | 排班ID |
| appointment_date | DATE | 预约日期 |
| time_slot | VARCHAR | 时段 |
| queue_number | INT | 排队序号 |
| status | SMALLINT | 状态 |
| source | VARCHAR | 来源 |

## 九、API接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /appointments | 获取预约列表 |
| GET | /appointments/:id | 获取预约详情 |
| POST | /appointments | 创建预约 |
| GET | /appointments/:id/payment-params | 获取待支付预约支付参数 |
| PUT | /appointments/:id/cancel | 取消预约 |
| PUT | /appointments/:id/sign-in | 签到 |
| PUT | /appointments/:id/call | 叫号 |
| PUT | /appointments/:id/complete | 完成就诊 |

## 十、当前实现进度（2026-04-18）

- 已完成：预约创建支付响应统一、患者端重试支付、预约支付字段透出、退款金额/字段契约统一、退款回调聚合、支付回调幂等、支付超时竞态保护
- 已完成：预约详情归属/门店校验、退款门店级越权拦截、`storeName/checkInMethod` 契约补齐、退款专用回调地址链路
- 已完成：支付配置解析中的租户默认回退，以及”显式小程序实例优先于门店路由”的顺序测试
- 已完成：`PaymentProfile/PaymentRoute` 与 legacy `stores.wechat_*` 兼容策略收口（软废弃方案）
  - Store 模型 `wechat_*` 字段已标记 `[DEPRECATED]`，指向 PaymentProfile / MiniappInstance
  - `WechatConfigResolver` store fallback 路径已加 `logger.warning(“[DEPRECATION]”)` 日志
  - `PaymentConfigResolver` 确认完全不读取 legacy store 字段
  - Store wechat-config GET/PUT API 已加 `Deprecation: true` 响应头
  - 迁移路径: 新租户应通过 miniapp-platform 管理 API 创建 MiniappInstance + PaymentProfile + PaymentRoute
- 已完成：支付/退款生命周期文档和手工联调清单
  - 生命周期文档: `docs/server/payment-lifecycle.md`
  - 联调清单: `docs/plans/payment-joint-debug-checklist.md`
