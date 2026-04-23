## ADDED Requirements

### Requirement: 预约列表分页上限按条件放宽
系统 SHALL 允许管理员在 `GET /appointments` 中使用更大的 `page_size`，并在满足条件时将上限放宽到可配置最大值（默认 500）。
系统 SHALL 对非管理员或不满足条件的请求维持常规上限（100）。

#### Scenario: 管理员带日期范围请求大分页
- **WHEN** 管理员请求 `GET /appointments`，且提供 `start_date` 与 `end_date`，并设置 `page_size` 为 500
- **THEN** 系统返回分页结果，`page_size` 生效且不超过配置上限

#### Scenario: 非管理员请求大分页
- **WHEN** 非管理员请求 `GET /appointments` 且 `page_size` 大于 100
- **THEN** 系统返回校验错误并提示常规上限为 100

#### Scenario: 管理员缺少日期范围请求大分页
- **WHEN** 管理员请求 `GET /appointments` 且 `page_size` 大于 100，但缺少 `start_date` 或 `end_date`
- **THEN** 系统返回校验错误并提示必须提供日期范围

#### Scenario: 超过配置上限
- **WHEN** 管理员请求 `GET /appointments` 且 `page_size` 超过配置上限
- **THEN** 系统返回校验错误并提示允许的最大值
