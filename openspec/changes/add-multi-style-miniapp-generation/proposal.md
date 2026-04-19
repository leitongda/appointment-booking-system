# Change: 支持多风格小程序模板生成

## Why
当前小程序平台已经在往“模板 + 实例 + 发布”方向演进，但仍主要围绕单一患者端壳层设计。若要服务更多行业客户，仅靠颜色换肤无法满足交付诉求，需要在保持业务逻辑稳定的前提下，支持多套信息架构和页面编排显著不同的小程序模板生成能力。

## What Changes
- 新增“多风格小程序模板生成”能力，允许同一套业务内核支撑多个前端模板
- 第一阶段支持 5 套预制模板：现代综合医疗、高端专科门诊、亲子儿科、女性健康、长辈友好/中医康养
- 模板不仅包含视觉 token，还包含导航结构、首页模块树、页面壳层与默认内容编排
- 小程序实例创建时必须能够绑定模板，并基于模板生成可发布的小程序前端壳层
- 构建发布流程需记录模板版本与实例生成结果，为第二阶段“模板 + 配置混合”打基础

## Impact
- Affected specs:
  - `miniapp-style-template-system` (new)
  - `miniapp-instance-management` (modified)
  - `miniapp-build-release` (modified)
- Affected code:
  - `apps/patient-miniapp/**`
  - `apps/admin/src/pages/miniapp-platform/**`
  - `apps/server/app/modules/miniapp_platform/**`
  - `packages/api/src/modules/miniapp-platform.ts`
  - `docs/plans/**`
  - `scripts/**`
