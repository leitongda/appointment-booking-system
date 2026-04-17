## Context

当前支付能力横跨多个模块：
- 预约创建逻辑位于 `apps/server/app/modules/appointments/service_booking.py`
- 支付下单与支付回调位于 `apps/server/app/modules/payments/`
- 退款核心逻辑位于 `apps/server/app/modules/refunds/`
- 支付配置与路由建模位于 `apps/server/app/models/miniapp_platform.py` 与 `app/infrastructure/payments/config_resolver.py`
- 患者端小程序直接调用预约创建和待支付订单重试支付
- 管理端依赖预约详情中的支付信息发起退款

这意味着支付修复不能只改一个接口，而必须统一业务状态机、API 契约、订单号规则、金额单位规则和权限规则。

## Goals / Non-Goals

- Goals:
  - 让“付费预约创建 -> 微信支付 -> 支付成功确认”真实可用
  - 让“待支付订单重试支付”可用且安全
  - 让“管理端发起退款 -> 微信退款 -> 退款回调更新状态”真实可用
  - 统一前后端金额单位和字段命名
  - 统一原支付商户订单号生成与退款引用规则
  - 明确运行时支付路由优先级，并与支付快照协同工作
  - 补足支付闭环的自动化测试
- Non-Goals:
  - 本次不引入新的支付渠道
  - 本次不实现财务对账报表
  - 本次不重构整个小程序平台信息架构
  - 本次不引入独立账务总账系统

## Decisions

### 1. 预约仍是支付业务聚合根

预约记录继续作为支付业务的主实体，使用现有字段承载支付和退款聚合状态：
- `payment_profile_id`
- `payment_miniapp_instance_id`
- `payment_mode`
- `payment_app_id`
- `payment_mch_id`
- `payment_sub_mchid`
- `payment_notify_url`
- `payment_amount`
- `payment_transaction_id`
- `paid_at`
- `refund_status`
- `refund_amount`

原因：
- 当前预约状态机已包含 `PENDING -> CONFIRMED`
- 现有前端和管理端均围绕预约展示支付状态
- 可在不新建大规模账务表的前提下先把业务闭环做完

### 2. 商户订单号统一为 `APPT{appointment.id}`

支付和退款必须引用同一商户订单号。

统一规则：
- 微信支付下单使用 `APPT{appointment.id}`
- 支付回调按 `APPT{appointment.id}` 回查预约
- 退款记录 `out_trade_no` 也保存 `APPT{appointment.id}`
- 退款申请和退款回调均基于此订单号追踪

原因：
- 当前 `PaymentService` 已使用该规则
- 该规则天然可反查预约
- 能避免 `appointment_no` 与外部支付订单号混用

### 3. 后端金额单位统一为“元”

后端数据库使用 `Numeric(10,2)` 存储支付与退款金额，`WeChatPayService` 在调用微信时再内部转换为“分”。

因此：
- 后端 API 契约统一使用“元”
- 前端展示时再自行格式化
- 前端不得在退款请求前手动乘 100

### 4. 付费预约创建返回专用响应结构

`POST /appointments` 不再只返回单一的 `AppointmentResponse`，而是返回统一的预约创建响应：
- `appointment`
- `payment_required`
- `payment_amount`
- `payment_params`

其中：
- 免费预约：`payment_required=false`
- 付费预约：`payment_required=true` 且返回可直接给 `Taro.requestPayment` 使用的 `payment_params`

### 5. 重试支付优先走服务端 openid 解析

优先方案：
- 从当前认证用户读取已绑定 `openid`
- 后端在重试支付接口内部完成归属校验和 `openid` 获取

回退方案：
- 若某些端当前无法从登录态解析 `openid`，则由客户端显式传递，但仍由后端校验预约归属

### 6. 支付路由优先级在运行时明确固定

运行时解析顺序定为：
1. 预约快照
2. 显式传入的小程序实例
3. 预约关联的小程序实例
4. 门店支付路由
5. 小程序实例默认支付配置
6. 租户默认支付配置
7. legacy `stores.wechat_*` 兼容回退（过渡期可选）

原因：
- 与现有 `payment-profile-routing` 能力保持一致
- 保证订单一旦创建支付单就冻结配置
- 保留过渡期兼容，不强制一次性迁移

### 7. 回调处理必须幂等

支付和退款回调都要支持重复到达：
- 支付成功重复回调不得重复确认预约或重复更新资源
- 退款成功/失败重复回调不得重复累加退款金额
- 支付超时任务与支付成功回调之间的竞态要有一致性保护

## Risks / Trade-offs

- 风险：调整预约创建返回结构后，可能影响所有调用端
  - 缓解：统一在 `packages/api` 和 shared types 同步调整，并补回归测试
- 风险：legacy `stores.wechat_*` 与新支付配置并存，短期存在双真相
  - 缓解：明确运行时优先级，并记录 fallback 日志
- 风险：回调链路没有真实微信环境时难以全量验证
  - 缓解：引入可 mock 的集成测试，并保留上线手工验证清单
- 风险：金额单位历史认知混乱，容易再次引入“元/分”错配
  - 缓解：在 API 文档、schema、前端注释和测试中全部显式注明单位

## Migration Plan

### Phase 1: 契约修复
- 修复预约创建响应结构
- 修复重试支付契约
- 为预约响应补齐支付字段

### Phase 2: 退款修复
- 修复退款请求字段和金额单位
- 修复 `out_trade_no` 统一规则
- 完成退款状态机与回调处理

### Phase 3: 安全与稳定性
- 给支付接口补认证和归属校验
- 完成回调幂等和支付超时竞态保护
- 补齐集成测试和文档

### Phase 4: 路由对齐
- 将运行时支付路由与 `PaymentProfile/PaymentRoute` 方案完全对齐
- 明确 legacy store 微信配置的过渡退出策略

## Open Questions

- 是否要在本次 change 中引入独立的支付事件落库表，用于保存原始回调报文？
- 过渡期是否保留 `stores.wechat_*` 作为最后 fallback，还是只允许在迁移脚本阶段读取？
- `openid` 是否已经在所有患者登录路径中可稳定获取；如果不能，哪些端需要补绑定或透传？

