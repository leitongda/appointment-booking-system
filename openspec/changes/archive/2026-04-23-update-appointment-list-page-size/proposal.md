# Change: 扩展预约列表分页上限（按条件放宽）

> **归档说明**: 本 Change 已于 2026-04-23 归档，完成度 100%。所有任务已完成并通过测试验证。

## Why
当前 `GET /api/v1/appointments` 对 `page_size` 限制为 100，导致按医生 + 日期范围查询时无法一次拉取 500 条数据，前端或第三方集成需要分多次分页请求，增加调用复杂度和时延。

## What Changes
- 预约列表接口允许更大的 `page_size`（默认上限 500），但只在满足条件时放开（管理员 + 日期范围）
- 超出常规上限时给出更明确的校验提示，避免“未说明原因”的 422
- 上限配置化，便于不同环境按性能调节
- 更新 API 文档与调用端说明

## Impact
- Affected specs: list-appointments (new)
- Affected code:
  - `apps/server/app/api/v1/appointments.py` - 分页参数校验与权限条件
  - `apps/server/app/schemas/appointment.py` - 列表查询 schema 上限
  - `apps/server/app/core/config.py` - 配置项
  - `apps/server/.env.example` - 新配置示例
  - `docs/api/README.md` - API 分页说明
  - `packages/api/src/modules/appointment.ts` - 请求参数说明（如需）
