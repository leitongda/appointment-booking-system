## 1. 后端实现

### 1.1 配置与常量
- [x] 1.1.1 在 `apps/server/app/core/config.py` 增加 `APPOINTMENTS_MAX_PAGE_SIZE`（默认 500）
- [x] 1.1.2 在 `apps/server/.env.example` 补充配置说明

### 1.2 API 校验规则
- [x] 1.2.1 调整 `GET /appointments` 的 `page_size` 上限至可配置值
- [x] 1.2.2 当 `page_size` > 100 时，仅允许管理员请求且必须提供 `start_date` 与 `end_date`
- [x] 1.2.3 返回明确的校验错误信息（包含允许的上限与所需条件）

### 1.3 Schema 对齐
- [x] 1.3.1 更新 `AppointmentListQuery.page_size` 的上限与描述

## 2. 文档与调用端
- [x] 2.1 更新 `docs/api/README.md` 中的分页说明（默认 10，常规上限 100，预约列表在条件满足时可至 500）
- [x] 2.2 视需要补充 `packages/api/src/modules/appointment.ts` 的注释说明

## 3. 测试与验证
- [x] 3.1 新增或补充后端测试：
  - 管理员 + 日期范围 + `page_size=500` 返回成功
  - 非管理员请求 `page_size>100` 返回 422
  - 管理员缺少日期范围请求 `page_size>100` 返回 422
  - `page_size` 超过配置上限返回 422
