# Server Refactor Complete Todo

## 1. 基线与安全网

- [x] 跑一次 `apps/server` 全量单测并记录基线结果
- Result: `186 passed in 801.21s (0:13:21)`
- [x] 为 `admin`、`appointments`、`patients`、`doctor_portal`、`import_export` 补关键行为测试
- [x] 为 `content`、`booking_notices`、`store_email_recipients` 补 API 兼容测试，不只测 wrapper
- [ ] 补 `async_client` 级别的集成测试，覆盖登录、鉴权、分页、权限失败场景
- Status: 已新增并通过 `content`、`booking_notices`、`store_email_recipients` 的公开/兼容接口测试
- Status: 已新增并通过 `admin` / `doctor_portal` / `import_export` 的 `async_client` 集成测试，以及一条 403 权限失败测试
- [x] 扩大架构测试，覆盖所有已迁移 wrapper 文件
- [x] 新增架构测试，限制新模块必须落在 `app/modules/*` 或 `app/infrastructure/*`

## 2. 结构骨架补全

- [x] 创建 `app/common/deps`，迁移 `app/api/deps.py`
- [x] 创建 `app/common/responses`，收拢统一响应模型和辅助函数
- [x] 创建 `app/common/errors`，收拢通用异常和错误映射
- [x] 创建 `app/common/utils`，迁移适合放到公共层的工具函数
- [x] 调整 `app/api/v1/__init__.py` 的 router 注册方式，支持按模块聚合
- [x] 评估 `app/main.py` 是否拆出 app factory / router registry / lifecycle

## 3. 已迁移模块的后续收尾

- [ ] `admin` 再拆细：`router_auth` / `router_admins` / `router_roles` / `router_monitoring` 内部继续减小文件
- [ ] `doctor_portal` 再拆细：分成 `profile`、`schedules`、`appointments`、`queue`、`history`、`follow_up`
- [ ] `import_export` 再拆细：分成 `export`、`template`、`import` 子 router
- [ ] `patients` 模块补 service 行为测试，覆盖黑名单、家庭成员、积分、删除约束
- [ ] `appointments` 模块补取消、过号、复诊、队列查询等更全的行为测试
- [x] `content` 模块补 list/detail/create/update/delete 的兼容测试

## 4. 已迁移的 API 入口

以下资源已经迁到 `app/modules/*`。
2026-03-12 起，`app/api/v1` 仅保留 `__init__.py` 作为注册层，旧 wrapper 已删除：

- [x] `analytics.py`
- [x] `appointments.py`
- [x] `audit_logs.py`
- [x] `auth.py`
- [x] `blacklists.py`
- [x] `consultation_fees.py`
- [x] `custom_schedules.py`
- [x] `departments.py`
- [x] `doctor_booking_settings.py`
- [x] `doctors.py`
- [x] `email_templates.py`
- [x] `export.py`
- [x] `feedbacks.py`
- [x] `leave_requests.py`
- [x] `medical_records.py`
- [x] `messages.py`
- [x] `rule_sets.py`
- [x] `schedule_suspensions.py`
- [x] `schedule_templates.py`
- [x] `schedules.py`
- [x] `settings.py`
- [x] `shift_types.py`
- [x] `statistics.py`
- [x] `rest_days.py`
- [x] `store_visit_type_configs.py`
- [x] `stores.py`
- [x] `upload.py`
- [x] `users.py`
- [x] `user_favorites.py`
- [x] `websocket.py`

## 5. 尚未拆分的大服务

### 高优先级

- [x] `rule_engine_service.py`
- [x] `schedule_service.py`
- [x] `schedule_template_service.py`
- [x] `rule_set_service.py`
- [x] `consultation_fee_service.py`
- [x] `admin_service.py`
- [x] `settings_service.py`

### 中优先级

- [x] `waitlist_service.py`
- [x] `excel_service.py`
- [x] `doctor_service.py`
- [x] `wechat_service.py`
- [x] `message_service.py`
- [x] `store_service.py`
- [x] `rule_set_import_service.py`

### 低优先级

- [x] `blacklist_service.py`
- [x] `department_service.py`
- [x] `leave_request_service.py`
- [x] `medical_record_service.py`
- [x] `custom_schedule_service.py`
- [x] `shift_type_service.py`
- [x] `point_service.py`
- [x] `visit_type_service.py`
- [x] `notification_service.py`
- [x] `sms_service.py`
- [x] `email_service.py`
- [x] `export_service.py`
- [x] `image_processor.py`
- [x] `revenue_service.py`
- [x] `feedback_service.py`
- [x] `user_service.py`

## 6. 基础设施层尚未迁移的内容

- [x] `email`
- [x] `wechat`
- [x] `sms`
- [x] `excel`
- [x] `image`
- [x] `notification`
- [ ] 如有需要，补 `cache/redis` 适配层而不是直接在业务中使用 `RedisCache`

## 7. 数据与运行期目录

- [x] 检查 `apps/server/logs`、`apps/server/uploads` 的历史残留，评估是否清理或迁移
- [x] 确认所有写文件逻辑都使用 `var/server/*` 默认目录
- [x] 更新 `.gitignore`，覆盖新的运行期产物
- [x] 更新 `.env.example` 的所有运行期目录说明
- Status: 已确认源码默认值、当前 `.env` 覆盖值和静态挂载都指向 `apps/server/var/server/*`
- Status: 历史残留目录 `apps/server/logs` 与 `apps/server/uploads` 已清理

## 8. 文档

- [x] 更新 `docs/server/README.md`
- [x] 更新 `docs/server/config.md`
- [x] 补一份新的 server 架构说明，解释 `modules/common/infrastructure`
- [x] 评估 `apps/server/docs` 下性能监控文档是否需要迁移或归并
- [x] 更新 OpenSpec 任务状态与实施顺序
- Status: 已新增 `docs/server/performance-monitoring.md` 作为统一入口，`apps/server/docs/*.md` 仍保留为历史参考

## 9. 兼容层删除条件

- [x] 定义“哪些 wrapper 可以删”的标准
- [x] 删除 `services/storage/*` 兼容层
- [x] 删除 `services/appointment_service.py` 兼容 facade
- [x] 删除 `services/patient_service.py` 兼容 facade
- [x] 删除 `api/v1/*` 中已彻底迁移的 wrapper，或统一改为纯注册层
  - 2026-03-12: 已完成，注册表直连 app.modules.*，删除所有 wrapper，只保留 __init__.py

## 10. 最终验收

- [x] 全量单测通过
- [x] 关键集成测试通过
- [x] `api/v1` 中已迁移文件全部保持薄包装
- [ ] 新功能开发不再向旧大文件追加代码
- [ ] 文档、OpenSpec、代码结构三者一致
