# Change: 构建模板驱动的小程序实例平台

## Why
当前患者端小程序仍以“单模板 + 按门店构建 + 固定 AppID”为主，适合少量门店独立发布，但不适合未来“多个模板、多个客户、多个小程序实例”的 SaaS 场景。随着客户数增加，继续沿用“门店即小程序配置、门店即支付配置、手工改 AppID 构建上传”的方式，会导致模板升级困难、发布链路不可追踪、支付主体路由混乱。

## What Changes
- 引入模板驱动的小程序实例模型，明确区分模板、租户、实例、门店和支付主体
- 为每个客户支持选择模板并生成一个或多个小程序实例，每个实例绑定独立的微信 AppID 和发布凭证
- 将微信支付配置从“门店内嵌字段”演进为独立的支付配置中心，按租户/公司主体统一管理，并允许实例或门店按规则路由
- 建立统一的构建、上传、提审、发布、回滚任务模型，替代手工修改 `project.config.json` 的发布方式
- 定义从当前 `stores.wechat_*` 配置向新模型迁移的兼容方案

## Impact
- Affected specs:
  - `miniapp-instance-management` (new)
  - `miniapp-build-release` (new)
  - `payment-profile-routing` (new)
- Affected code:
  - `apps/server/app/models/**`
  - `apps/server/app/modules/**`
  - `apps/admin/src/pages/**`
  - `apps/patient-miniapp/**`
  - `scripts/**`
  - `docs/**`
