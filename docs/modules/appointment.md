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
- 已支付预约需处理退款

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
- 退款接口金额单位统一为“元”
- 退款记录始终复用原支付订单号 `APPT{appointment.id}` 作为 `out_trade_no`
- 退款创建、退款成功回调、退款失败回调都会同步更新预约上的 `refund_status` 与 `refund_amount`

## 四、状态流转

```
PENDING(待支付) → CONFIRMED(已预约) → SIGNED(已签到) → WAITING(候诊中) → SEEING(就诊中) → COMPLETED(已完成)
                       ↓                                                            
                  CANCELLED(已取消)
                       ↓
                  EXPIRED(已过期)
```

## 五、数据模型

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

## 六、API接口

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

## 七、当前实现进度（2026-04-17）

- 已完成：预约创建支付响应统一、患者端重试支付、预约支付字段透出、退款金额/字段契约统一、退款回调聚合、支付回调幂等、支付超时竞态保护
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
