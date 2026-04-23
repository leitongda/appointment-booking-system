# Change: 修复预约支付闭环与退款链路

## Why
当前仓库已经具备支付配置、支付路由、微信支付封装、退款记录、患者端支付页面和管理端退款页面等基础能力，但“预约创建 -> 支付 -> 回调确认 -> 重试支付 -> 退款 -> 退款回调”仍未形成可上线的业务闭环。

现状存在几个关键断点：
- 付费预约创建时服务层返回支付数据，但路由仍按普通预约对象处理，导致付费预约主链路会在接口层中断
- 患者端重试支付接口与后端契约不一致，缺少 `openid` 或服务端归属解析
- 预约响应模型没有暴露支付字段，患者端和管理端拿不到实际支付状态
- 管理端退款请求字段名和金额单位与后端不一致
- 退款记录保存的原始商户订单号与支付下单使用的订单号不一致
- 直接支付接口缺少认证、权限和归属校验
- 支付回调、退款回调、超时取消和重复回调缺少闭环级测试覆盖

如果不先解决这些问题，后续即使继续建设 `PaymentProfile` 和 `PaymentRoute` 平台能力，也无法保证当前预约支付业务真实可用。

## What Changes
- 统一付费预约创建的返回契约，明确 `payment_required`、`payment_amount`、`payment_params` 和预约主体数据
- 完成患者端待支付订单重试支付链路，明确 `openid` 来源与权限边界
- 为预约列表、预约详情等接口补齐支付和退款相关字段
- 修复管理端退款提交契约，统一金额单位为“元”，并与后端模型一致
- 统一支付下单、支付回调、退款创建、退款回调所使用的商户订单号规则
- 为支付订单创建、支付状态查询、退款创建增加认证、权限和归属校验
- 增强支付回调与退款回调的幂等性，处理支付超时与晚到回调的状态竞争
- 将运行时支付配置解析顺序与 `payment-profile-routing` 设计对齐，并明确与 legacy `stores.wechat_*` 的兼容策略
- 补充单元测试、集成测试、文档和上线验证清单

## Impact
- Affected specs:
  - `appointment` (new)
  - `payment-profile-routing` (modified)
- Affected code:
  - `apps/server/app/modules/appointments/**`
  - `apps/server/app/modules/payments/**`
  - `apps/server/app/modules/refunds/**`
  - `apps/server/app/infrastructure/payments/**`
  - `apps/server/app/tasks/payment_task.py`
  - `apps/server/app/schemas/appointment.py`
  - `packages/api/src/modules/appointment.ts`
  - `packages/shared/src/types/appointment.ts`
  - `apps/patient-miniapp/src/packageBooking/**`
  - `apps/patient-miniapp/src/pages/appointment/**`
  - `apps/admin/src/pages/appointment/**`
  - `docs/modules/appointment.md`
  - `docs/api/README.md`

