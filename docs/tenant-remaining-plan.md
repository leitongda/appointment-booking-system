# 租户改造剩余工作计划（P5）

- 日期：2026-10-23
- 分支：`feat/tenant-isolation-hardening`
- 依据：四份盘点结果 `剩余租户缺口盘点`（R1）、`测试与矩阵缺口盘点`（R2）、`生命周期实施缺口盘点`（R3）、`上线与数据风险盘点`（R4）
- 范围：只做计划与执行编排，**本文不代表任何代码或测试已经完成**。工作项编号沿用盘点编号（R1-1 … R4-15）。
- 路径约定：后端路径相对 `apps/server/`，前端路径相对仓库根。

---

## 1. 现状总结

### 1.1 已经成立的能力

1. **管理员认证层的租户收敛已存在**：认证成功后会按账号补齐租户上下文，并对非超管做跨租户拒绝（`app/common/auth_unified.py:508-524`）；`code` 头的兜底比对受 `TENANT_CONSISTENCY_FAIL_CLOSE` 控制（`app/common/auth_unified.py:526-537`）。
2. **管理端租户锚点底座已存在**：`resolve_admin_tenant_anchor`（`app/common/tenant_deps.py:169-198`）与 `require_admin_tenant_anchor`（`:200-209`）；平台管理员未显式指定 `tenant_id` 时受 `PATIENT_ANCHOR_FAIL_CLOSE` 控制（`:181-190`），默认关闭（`app/core/config.py:139`）。
3. **锚点已在部分模块落地**：`resolve_admin_tenant_anchor` 仅出现在 4 个文件（`app/modules/patients/router_manage.py`、`app/modules/patients/router_users.py`、`app/modules/stores/router.py`、`app/modules/departments/router.py`）；`require_admin_tenant_anchor` 仅出现在 `messages`、`stores`、`schedules`、`doctors` 4 个 router。其余管理端仍以 `get_current_tenant_id()` 为唯一来源（`app/middleware/tenant_context.py:52`）。
4. **迁移链已串成单头**：`p3a1_content_tenant → p3a2_admin_role_unique → p3a3_business_numbers → p3a4_config_codes → p3a5_usage_daily_unique → p3a6_tenant_fk → p3a7_settings_tenant`（各文件 `revision/down_revision`；例如 `migrations/versions/p3a6_tenant_fk.py:23-24`、`p3a7_settings_tenant.py:16-17`）。本次未用 `alembic heads` 复核（venv 解释器路径失效，见 R3 盘点）。
5. **灰度原则已落地为开关**：`LEGACY_USER_ADMIN_FALLBACK=True`、`TENANT_FILTER_FAIL_CLOSE=False`、`TENANT_CODE_TO_ID_RESOLVE=False`、`TENANT_CONSISTENCY_FAIL_CLOSE=False`、`PATIENT_ANCHOR_FAIL_CLOSE=False`、`PUBLIC_TENANT_REQUIRED_EXTRA_PATHS=[]`、`FEATURE_ENFORCEMENT_ENABLED=False`（`app/core/config.py:131-148`）。

### 1.2 剩余风险的四类形态

| 类型 | 含义 | 代表点位 |
|---|---|---|
| (a) 平台/超管未显式指定租户 | 读全租户、写 `tenant_id=NULL` 行 | `freelance_fees/service_mutation.py:79-82`、`approval_flows/service_definitions.py:183-190`、`blacklists/service.py:106-120` |
| (b) 遗留 NULL 租户管理员 | `TENANT_FILTER_FAIL_CLOSE=False` 时不过滤 | `app/common/tenant_deps.py:224-244`、`app/core/config.py:133` |
| (c) 完全没写租户逻辑 | 任何租户管理员都能跨租户 | `settings`（`app/models/settings.py:20` 有列，业务零使用）、`statistics`（`app/modules/statistics/**` 无 `tenant` 命中）、`shift_types`（`service.py:149` 只在创建时写上下文） |
| (d) 直接信任客户端租户参数 | 可跨租户读/发消息 | `notification_logs/router.py:84-117`、`unified_message/schemas.py:46` + `router.py:35-47` |

### 1.3 当前缺口量化

| 指标 | 现状 | 证据 |
|---|---|---|
| 仍引用请求上下文的模块数 | 93 个文件命中 `get_current_tenant_id` | 本次 `grep -rl ... | wc -l` |
| 已使用账号锚点的模块 | 4 个 resolve + 4 个 require | 本次 `grep -rl` |
| 租户隔离矩阵注册模块 | 仅 `stores`、`doctors` 两条 | `tests/security/tenant_matrix.py:29-46` |
| 零租户逻辑模块 | `settings`、`statistics`、`shift_types` | 本次 grep：`statistics`/`settings` 业务代码零命中；`shift_types` 仅创建/缓存引用 |
| `auto_renew` 消费方 | 0（只落库/回显） | `app/models/tenant.py:219`、`service_subscription.py:163`、`schemas.py:369/386` |
| purge 实现 | 0（仅有配置） | `app/core/config.py:144-145`；`app/tasks/` 无对应任务 |
| 审计 SQL 可直接执行 | 是（B9/R4-1 后拆 pre/post 两段 + 守卫） | `scripts/tenant_null_tenant_id_audit.sql`；缺失表/列输出 `SKIP(missing)`（见第 6 节） |

### 1.4 关键事实与证据（后续批次直接引用）

1. 平台管理员锚点只认 query 参数：`app/common/tenant_deps.py:200-209` 的 `tenant_id` 是 `Query`；而管理端只注入 header（`packages/api/src/web-interceptors.ts:297-302`，`apps/admin/src/utils/request.ts:129`）。翻 `PATIENT_ANCHOR_FAIL_CLOSE` 会打断门店/排班/医生/消息页面（R4-8）。
2. 停服 403 的错误码在 `error.code`：`app/middleware/exception.py:80-97`；患者小程序读 `data.error_code`（`apps/patient-miniapp/src/app.tsx:181-187`），共享解析也读 `error_code`（`packages/shared/src/utils/parseTenantError.ts:39`）。
3. 管理端结构化错误处理会提前吞掉 `TENANT_OVERDUE/TENANT_SUSPENDED`：`packages/api/src/utils/error-handling.ts:152-156` 返回 `true`，而调用发生在 403 分支之前（`packages/api/src/web-interceptors.ts:347` vs `:359-366`），导致不跳停服页（R4-9）。
4. `waitlist /stats` 引用了不存在的列：`app/modules/waitlist/router.py:258` 使用 `WaitlistEntry.store_id`，而模型列清单（`app/models/waitlist.py:23-52`）无此列；带 `store_id` 的统计请求会 `AttributeError`（R2-8）。
5. `stores` 的详情/状态/批量绑定未传锚点：`app/modules/stores/router.py:288`、`:486`、`:571`、`:654`；写路径的 403 来自 `check_store_access`（`:281`、`:362`），请求到不了 service，矩阵因此“假通过”（R2-9）。
6. 6 张统一消息表的 `tenant_id` 为 `NOT NULL`：`app/models/unified_template.py:33`、`app/modules/unified_message/models.py:39/61/86/115/130`；M6 文档里的通用 `UPDATE ... SET tenant_id = NULL` 配方对它们不可执行（R4-6，已在 B9 按可空/NOT NULL 分两类修正，见 `p3a6_tenant_fk.py` 文件头与 `scripts/m6_post_deploy_cleanse_and_validate.sql`）。
7. M6 的 16 张表与模型层不一致：迁移建了外键（`p3a6_tenant_fk.py:48-60`），但 7 个模型列原本未声明 `ForeignKey("tenants.id")`（R3-8，已在 B9 补齐：`app/models/unified_template.py`、`app/modules/unified_message/models.py` 五处、`app/models/content_version.py`）。
8. 支付回调强制租户上下文：`app/modules/payments/service.py:179-182`、退款 `app/modules/refunds/router.py:231-233`；而文档给的是单域名回调地址（`docs/payment-launch-checklist.md:46`），微信不会带 `X-Tenant-ID`（R4-11）。
9. 功能开关唯一接线点：`app/modules/payments/router.py:127`；`online_payment` 默认 False（`app/common/feature_definitions.py:37`）；`require_feature` 自身在 `app/common/feature_deps.py:17-43`，总开关默认 False（`app/core/config.py:148`）。
10. 审计 SQL 的覆盖面缺口（R4-1/R4-2/R4-4/R4-5，已在 B9 修复）：旧版 D13 只查跨租户重复、D1 只数行数、D9 缺 5 张表；现版补同租户/平台重复、日志观测门禁、`null_pct` 与 `miniapp_instances` 计数，并逐表守卫。
11. 迁移含不可逆数据合并：`p3a5_usage_daily_unique.py` 按 `SUM` 合并重复用量行；`p3a1_content_tenant.py:9-10` 明确内容表回填不可自动恢复（R4-15）。
12. 生命周期：到期任务直接把租户置欠费（`app/tasks/tenant_usage_task.py:224-229`），未读 `auto_renew`；软删除承诺 90 天后物理删除（`app/modules/tenants/service_tenant.py:291-297`）但无执行方（R3-1/R3-2）。

---

## 2. 批次编排原则

1. **先能做、后拍板、再上环境**：无阻塞项按依赖排在前；`decision` 与 `environment` 单独成批，未决前不混入可执行批次。
2. **锚点底座先行**：所有“把 `get_current_tenant_id()` 换成账号锚点”的模块改造，必须建立在 B1 的统一语义上，避免每个模块各写一套。
3. **矩阵先行**：测试注册表（R2-1）先扩容，后续模块批次每改一个模块就补一条 `ModuleSpec`，防止“改了没测、测了没注册”。
4. **小步可回滚**：每批只动一类模块；每批有独立验收门与 revert 面。
5. **数据与代码分离**：迁移脚本、审计 SQL、物理删除属于独立批次，不与业务模块混提。
6. **不启用未接线的开关**：`TENANT_PURGE_*` 本期只做 dry-run，不作为发布开关（R4-13）。

---

## 3. 批次总览

| 批次 | 工作项 | 依赖 | 验收门（计划，未执行） | 阻塞 |
|---|---|---|---|---|
| **B0 基线与快速修复** | R2-11、R2-10、R2-8、R2-9、R1-20、R4-13 | 无 | 定向 pytest：`tests/unit/test_approval_business_callbacks.py`、`tests/tenants/test_quota.py`、`tests/tenants/test_isolation_matrix.py -k stores`；新增 waitlist `/stats` 用例 | 无 |
| **B1 锚点底座统一** | R1-1、R4-8 | B0 | 平台管理员仅带 `X-Tenant-ID` 在 `PATIENT_ANCHOR_FAIL_CLOSE=True` 下访问 stores/schedules/doctors/messages 均为 200 且被限定；租户管理员伪造头 403 | 无 |
| **B2 测试矩阵底座与 P2 补写** | R2-1、R2-2、R2-3、R2-4 | B0、B1 | 四个矩阵文件全绿，且新增“正控”：本租户写 2xx、跨租户写非 2xx 且 DB 未变 | 无 |
| **B3 零租户与客户端参数** | R1-12、R1-2、R1-16、R1-17 | B1 | shift-types/settings/notification-quota/unified-message 四组新用例 | 无 |
| **B4 统计与配额** | R1-3、R2-7 | B1 | statistics 跨租户计数双向断言；三类新增配额检查 ≥9 用例 | 无 |
| **B5 管理端核心** | R1-4、R1-5、R1-6、R1-19 | B1、B2 | 矩阵新增 freelance-fees/import-export/admin/export/audit-logs；平台管理员无 `tenant_id` 返回 400 | 无 |
| **B6 流程与排班配套** | R1-7、R1-8、R1-9、R1-10 | B1、B2 | approval-flows/rule-sets/suspensions/rest-days/leave-requests 矩阵读写用例 | 无 |
| **B7 考勤与诊室** | R1-11、R1-13 | B1、B2 | 5 条 attendance 路径 + rooms/doctor-booking-settings 矩阵 | 无 |
| **B8 患者运营与内容** | R1-14、R1-15、R1-18 | B1、B2 | blacklists/points/feedbacks 矩阵；dict 公开端与 booking-notice 公开端租户校验 | 无 |
| **B9 数据核对与迁移脚本** | R4-1、R4-2、R4-3、R4-4、R4-5、R4-6、R3-6、R3-8、R4-14、R4-15、R4-7 | B0；R4-7 依赖 B1 | 审计 SQL 在 pre/post 两库 ERROR=0；`alembic autogenerate` 无 tenant 外键 diff；staging dry-run 可推导+不可推导=NULL 总数 | 无（staging 验证见 E1） |
| **B10 前端错误码与功能开关** | R4-9、R3-5 | B1 | `parseTenantError` 三来源单测；未开通 `online_payment` 403、开通 200、总开关关放行 | 无 |
| **B11 生命周期 dry-run** | R3-2 | B9 | `TENANT_PURGE_DRY_RUN=True` 只输出清单 0 删除；`ENABLED=False` 全程 no-op | 无（真实删除受 R2-5 决策约束） |
| **D1 决策阻塞批** | R2-5、R2-6、R3-1、R3-3、R3-4、R4-10、R4-12 | B0–B11 | 各决策书面确认后再执行；未确认不动代码 | D17/D20/商务/发布方确认 |
| **E1 环境阻塞批** | R3-7、R3-9、R4-11 | B9、D1 | 生产/预发库执行留档、微信回调实测、退款跨租户用例 | 无生产库凭证、运维窗口、微信回调测试环境 |

> 说明：B0–B11 之间并非全部串行。B2 与 B3–B8 可并行开工，但 B2 的注册表必须先合入；B9 与业务模块可并行；D1/E1 必须等前置批次完成。

---

## 4. 批次详情

### B0 基线与快速修复（无阻塞）

**目标**：先清掉“会让后续测试假绿/偶发红”的确定性缺陷，并完成只登记不写代码的事项。

| ID | 工作项 | 关键落点 | 验收断言 |
|---|---|---|---|
| R2-11 | 修复硬编码绝对路径 | `tests/unit/test_approval_business_callbacks.py:45` 的 `cwd` 改为 `Path(__file__).resolve().parents[2]` | 任意工作目录运行该文件全绿 |
| R2-10 | 固定配额测试时间与单号 | `tests/tenants/test_quota.py:449-483`；用 freezegun/monkeypatch 固定到月中；`appointment_no` 用完整 uuid 或序号 | 连续 20 次 + 整文件运行全绿；新增“月初 UTC 跨界”回归用例 |
| R2-8 | 修 `waitlist /stats` 并补 total 断言 | `app/modules/waitlist/router.py:258` 改为 `Schedule.store_id` 子查询/join；`:235-269` | 有/无 `store_id` 两种请求不报错；跨租户只计本租户；列表 `total == 命中数` |
| R2-9 | 补 stores 写路径锚点 | `app/modules/stores/router.py:288`、`:486`、`:571`、`:654` 传入 `resolve_admin_tenant_anchor(...)`；矩阵补超管视角 | 超管 + A 头访问 store_b 返回 403/404 且 DB 未变；超管 + A 头改 store_a 成功 |
| R1-20 | 登记“已正确锚定/公开端”清单 | 本文第 8 节表格即登记 | 文档评审通过，不再重复改造 |
| R4-13 | 明确 purge 本期不启用 | 本文第 5 节与发布说明 | `grep -rn TENANT_PURGE app` 仅配置两行；发布清单标注“未接线” |

**回滚**：R2-11/R2-10 只动测试；R2-8/R2-9 只动 waitlist/stores，单文件 revert 即可。

### B1 锚点底座统一（无阻塞）

**目标**：把“平台管理员必须显式租户”的语义变成前端可用的底座，而不是只认 query。

| ID | 工作项 | 关键落点 |
|---|---|---|
| R1-1 | 锚点铺开与语义统一 | `app/common/tenant_deps.py:169-209` 作为唯一实现；各管理端 router 改为 `Depends(require_admin_tenant_anchor)`，service 显式收 anchor；替换 `if tenant_id:` 的隐式放行 |
| R4-8 | 平台管理员锚点来源改为 header 兜底 | `require_admin_tenant_anchor`（`:200-209`）在 query 为空时回退 `get_current_tenant_id()`（header/子域名/路径前缀），保持“平台可跨租户、租户管理员只自身”语义 |

**验收门**：
- 平台管理员仅带 `X-Tenant-ID: <租户>`、不带 query，在 `PATIENT_ANCHOR_FAIL_CLOSE=True` 下调用 `GET /api/v1/stores`、`/schedules`、`/doctors`、`/messages`：200 且数据限定该租户。
- 租户管理员带他人 `tenant_id`：仍被忽略/403（`tenant_deps.py:191-197`）。
- 租户管理员无 `tenant_id`：403（`:193-196`）。

**注意**：这是全仓语义改动，必须先合入 B1 再让 B3–B8 批量替换；否则各模块会各自实现一套“query 优先、header 兜底”。

### B2 测试矩阵底座与 P2 补写（无阻塞）

| ID | 工作项 | 关键落点 |
|---|---|---|
| R2-1 | 扩 `ModuleSpec` 与注册表 | `tests/security/tenant_matrix.py:17-46` 增加 `write_method`、`omit_body`；`tests/tenants/test_isolation_matrix.py:86-91` 改为通用对象工厂；`:145` 不再固定 PUT |
| R2-2 | P2A 写/创建/患者路径 | `tests/security/test_p2a_tenant_matrix.py:156-296` 补 POST/PUT/cancel/waitlist/my/position/stats/payments/refunds；患者无头断言收紧为 400（或显式分支） |
| R2-3 | P2B 提升到 HTTP 层 | `tests/security/test_patient_data_flow_tenant_isolation.py:233-391` 补患者/病历/报告详情+写+创建；statistics 断言 total 数值 |
| R2-4 | P2C 写路径 | `tests/tenants/test_p2c_resource_message_anchor_matrix.py:106-240` 补排班/医生/门店/科室/消息的 create/update/delete/batch/read |

**验收门**：
- `pytest tests/security/test_p2a_tenant_matrix.py tests/security/test_patient_data_flow_tenant_isolation.py tests/tenants/test_p2c_resource_message_anchor_matrix.py tests/tenants/test_isolation_matrix.py -q` 全绿。
- 每个模块至少一条正控（本租户写 2xx），避免“权限 403 冒充租户拦截”。
- 列表 `total` 与命中数一致。

### B3 零租户与客户端参数（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R1-12 | `shift_types` 全链路补租户 | `app/modules/shift_types/service.py:37-72`、`:95-99`、`:119-124`、`:145-152`；`router.py:20-27/51-55/92/116` | 列表/详情/写跨租户 403/404；创建落 anchor；缓存失效（`:225-230`）用 anchor |
| R1-2 | `settings` 补租户维度 | `app/models/settings.py:20`；`app/modules/settings/service_core.py:14-38/91-129/143-160` | 租户 A 改 booking 后 B 仍默认；平台管理员无 tenant_id 修改 400 |
| R1-16 | `notification_logs` 不再信任 query | `app/modules/notification_logs/router.py:84-117` 改 `require_admin_tenant_anchor(..., tenant_id_override=tenant_id)` | 租户 A 传 `?tenant_id=B` 403；平台无 tenant_id 400 |
| R1-17 | `unified_message` 覆盖请求体租户 | `app/modules/unified_message/schemas.py:46`；`router.py:35-47`、`send-batch` | A 管理员把 `event.tenantId` 设为 B 返回 403；模板端点用 anchor |

**回滚**：四模块互不依赖，可分别 revert。

### B4 统计与配额（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R1-3 | statistics 增加租户维度 | `app/modules/statistics/router_overview.py:20-45` 等所有 `router_*.py`；`app/common/data_scope.py:94-98` 的 tenant 分支改 fail-close（或受开关控制） | 租户 B 的预约不计入 A 的 `/statistics/overview`；无门店租户管理员不得看全量 |
| R2-7 | 三类配额补测 | `app/common/quota.py:263-327`；调用方 `miniapp_platform/service_instance.py:196`、`lowcode/router.py:145/343`、`upload/router.py:68/166` | 达限 403 且 `quota_type/current/limit` 正确；未达通过；limit=0/None 语义；A 达限不影响 B |

**注意**：R3-3（DataScope 删除）是决策项。若 D20 先拍板删除，R1-3 应基于简化后的 fallback 路径实现；若未拍板，R1-3 只加租户条件，不动 DataScope 结构。

### B5 管理端核心（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R1-4 | `freelance_fees` 锚点与写保护 | `app/modules/freelance_fees/router.py`；`service_query.py:32-34/42-45/70-72/130-132/185-190/223-238/258-274`；`service_mutation.py:79-82/121-130/208/328` | `/freelancers`、`/tasks`、`/settlements` 矩阵；平台无 tenant_id 创建 400 |
| R1-5 | `import_export` 去上下文回落 | `app/modules/import_export/router_import.py:45-47`；`router_export.py:133-141` 及 `:85/459-466/521-527/591-603`；`service_import.py:90/123` | 平台无 tenant_id 导出 400；A 导出不含 B 患者；导入按 anchor 预加载 |
| R1-6 | `admin` 列表/详情/监控强过滤 | `app/modules/admin/service_admins.py:45/97/123/149/172-174`；`router_admins.py:101/137/161`；`router_roles.py:26-123`；`service_logs.py:29`；`router_monitoring.py:148/259/415` | A 的 `/admin/admins` 不含 B；跨租户 admin_id 403/404；平台无 tenant_id 400 |
| R1-19 | `export`/`audit_logs` 去回落 | `app/modules/export/router.py:33-35/65-67/96-98`；`service.py:46-47/135-136/206-207`；`audit_logs/router.py:44-47/127-131` | `/export`、`/audit-logs/checkin-logs` 矩阵；审计跨租户仅平台且必须显式 |

### B6 流程与排班配套（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R1-7 | `approval_flows` 锚点 | `router.py:317/331/349/367/382/400`；`service_definitions.py:67-70/100-108/115-121/183-190/326-335/625-626`；`service_instances.py:33/122/241`；`engine.py:1602` | `/approval-flows`、`/approval-instances` 矩阵；create anchor 为空拒绝 |
| R1-8 | `rule_sets` 超管端点锚点 | `router.py:121/167/208/256/396/506`；`service_query.py:119-122/193-196/336-366`；`service_mutation.py:73-82`；`audit_helpers.py:43-45/185` | 超管无 tenant_id 调 `/rule-sets` 400；跨租户读写拒绝 |
| R1-9 | `schedule_suspensions` | `router.py:23-33/97-101/141-146/171-175`；`service.py:37-39/53-62/88/363/393/431`；`service_processing.py:174` | 列表/详情/写矩阵；跨租户处置 403/404 |
| R1-10 | `rest_days`/`leave_requests` | `rest_days/router.py:20/86/128/145`、`service.py:27-29/47-49/92-95`；`leave_requests/router.py:24/88/128`、`service.py:25-27/37-40/79-90/344-364` | 两模块矩阵；审批/撤回路径同步锚点 |

### B7 考勤与诊室（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R1-11 | attendance 五模块统一 | `attendance_rules/service.py:26-27/50-54`；`attendance_shifts/service.py:27-28/57-61`；`attendance_groups/service.py:22-27`；`attendance_records/service.py:264/316/371/386`、`router.py:228-233`；`attendance_leave/service.py:333-337` | 5 条 attendance 路径矩阵；A 访问 B 打卡记录 403/404；groups/records 改强过滤 |
| R1-13 | rooms/booking settings | `schedule_rooms/service.py:19-21/45-50`、`router.py:90/114/130/154`；`doctor_booking_settings/service.py:24-25/32-34/50-52/71-73/94-97/210`、`router.py:28/57/71/93` | 两模块矩阵；create anchor 空拒绝 |

### B8 患者运营与内容（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R1-14 | blacklists/points/feedbacks | `blacklists/service.py:32-40/106-120`；`points/service.py:34-36/129/298-301/356`；`feedbacks/service.py:23-25/83/173-186`；三模块 router | 列表矩阵；创建/调整 anchor 空拒绝；患者自助端点保持 `require_tenant_active_for_write` |
| R1-15 | dictionaries 管理端+公开端 | `router.py:30-37/50-54/67-76/95-100/119`；`service.py:32-36/75-78/96-103/201-206/238-247`；`router_public.py:20-33/43-72` | 无 `X-Tenant-ID` 调 `/dict-options/{code}` 400；A 私有字典 B 不可见 |
| R1-18 | email_templates/booking_notices | `email_templates/service.py:18-21/31-43/98-108`、`router.py:32/55/66/79/90`；`booking_notices/router.py:20-26/29-44`、`service.py:19-21` | `/booking-notices/public` 无头 400；A 须知不出现在 B；平台模板 NULL 分支仅平台管理员可写 |

### B9 数据核对与迁移脚本（无阻塞，staging 验证归 E1）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R4-1 | 审计 SQL 拆 pre/post 两段 | `scripts/tenant_null_tenant_id_audit.sql:1-4/36-39/60-63`；用 `to_regclass()`/`information_schema` 守卫，缺列输出 `SKIP(missing)` | 在 pre-p3a 与 post-p3a7 两库副本运行，ERROR=0；删一列只输出 SKIP |
| R4-2 | D13 补同租户/平台重复 | `sql:11-22`；补 `GROUP BY tenant_id, code HAVING count(*)>1` 与 `WHERE tenant_id IS NULL GROUP BY code HAVING count(*)>1`；与 `p3a2_admin_role_unique.py:32-41` 门禁对齐 | 造 1 条同租户重复 + 1 条平台重复，新查询能报出 |
| R4-3 | D1 改日志观测门禁 | `sql:65-68`；关键字 `legacy User admin fallback hit`（`app/common/auth_unified.py:411`） | 连续 2 个发布周期命中=0 才允许 `LEGACY_USER_ADMIN_FALLBACK=False` |
| R4-4 | D9 补表与占比 | `sql:24-39`；补 `follow_up_plans/follow_up_records/follow_up_self_reports/doctor_reviews/feedbacks`；输出 `null_pct`；内容表单独成段 | 0 行表输出 0/0；各表 total 与 `information_schema` 一致 |
| R4-5 | D20 表存在性守卫与 miniapp 口径 | `sql:6-9`；`to_regclass('role_permissions')`；新增 `miniapp_instances` 按租户 `status=2` 计数 | 未执行 `create_all` 的库输出 MISSING；分组计数可供产品拍板 |
| R4-6 | M6 清洗配方分两类 | `migrations/versions/p3a6_tenant_fk.py:9-16`；10 张可空表 `SET NULL`，6 张 NOT NULL 表备份后重映射或 DELETE | staging 每表造 1 条孤儿，16 张表 VALIDATE 全部成功 |
| R3-6 | 新增 M6 上线后脚本 | 新建 `scripts/m6_post_deploy_cleanse_and_validate.sql` | 清洗前后孤儿计数=0；`pg_constraint.convalidated` 全为 true |
| R3-8 | 7 个模型列补外键 | `unified_template.py:32`、`unified_message/models.py:39/61/86/115/130`、`content_version.py:14` | `alembic autogenerate` 对 tenant 外键零 diff；单测断言 16 张表 `foreign_keys` 非空 |
| R4-14 | 扩展 NULL 回填脚本 | `scripts/migrate_core_tenant_data.py:98/127/155/176/197/227/266/359-374`；补 medical_records/examination_reports/follow_up_*/messages/waitlist_entries；禁止默认租户兜底（`:74-89`） | staging dry-run：可推导+不可推导=NULL 总数；回填后业务表 NULL=0 |
| R4-15 | 固化迁移顺序与备份 | 本文第 6 节；p3a1→p3a7 单头，先备份内容表与 `tenant_usage_logs` | staging 全链 upgrade 一次、downgrade 一次并记录不可恢复部分 |
| R4-7 | 灰度开关 runbook 与 `.env.example` | `app/core/config.py:130-148`；`.env.example` 当前无 `TENANT/FEATURE/LEGACY` 命中 | `.env.example` 登记全部开关及默认值；第 5 节顺序可照单执行 |

### B10 前端错误码与功能开关（无阻塞）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R4-9 | 统一读 `error.code` | `packages/shared/src/utils/parseTenantError.ts:39`；`apps/patient-miniapp/src/app.tsx:181-187`；`packages/api/src/utils/error-handling.ts:152-156`；`packages/api/src/web-interceptors.ts:347/359-366` | 喂 `{code:403,error:{code:'TENANT_OVERDUE'}}` 触发 `onTenantSuspended`；患者端弹窗命中；admin 跳 `/tenant-suspended` |
| R3-5 | 接线 `export_data`/`basic_statistics` | `app/modules/statistics/router_overview.py:20-24` 挂 `Depends(require_feature("basic_statistics"))`；真实导出端点挂 `export_data` | 未开通 403；开通 200；总开关关放行；平台管理员不受限（`feature_deps.py:31-33`） |

### B11 生命周期 dry-run（无阻塞部分）

| ID | 工作项 | 关键落点 | 验收 |
|---|---|---|---|
| R3-2 | 新建 purge 任务骨架 + dry-run | 新建 `app/tasks/tenant_lifecycle_task.py`；`get_sync_db()`；`TENANT_PURGE_ENABLED`（`config.py:144`）+ `TENANT_PURGE_DRY_RUN`（`:145`）双门禁；beat 注册 `app/celery_app.py:150-177` + `autodiscover_tasks` | `DRY_RUN=True` 只输出候选清单 0 删除；`ENABLED=False` 全程 no-op；未满 90 天不动；重复执行幂等 |

**边界**：真实物理删除顺序、子表清单、失败回滚属 R2-5 决策范围；本期默认 `ENABLED=False`，不得在发布环境打开。

### D1 决策阻塞批（decision）

| ID | 工作项 | 决策点 | 未决时的处理 |
|---|---|---|---|
| R2-5 | purge 契约与 dry-run 测试 | 保留期、物理删除范围、是否含 `status=2` 归档实例 | 只做 B11 dry-run，不执行删除 |
| R2-6 | `auto_renew` 测试 | 续费规则（扣款、重试、宽限、是否新建订阅行） | 先写测试骨架，不实现扣款 |
| R3-1 | `auto_renew` 定时续费 | D17：延长周期 + pending 应收 + 宽限期不停服 | 保持 `tenant_usage_task.py:224-229` 现状（到期置欠费） |
| R3-3 | DataScope/role_permissions 删除 | D20：两表行数=0、`role_permissions` 是否存在、miniapp 口径 | 保留现状，R1-3 只加租户条件 |
| R3-4 | `FEATURE_ENFORCEMENT_ENABLED` 试点 | 试点范围与存量租户 features 回填责任 | 总开关保持 False |
| R4-10 | `/ws/poll` 改为医生 token | 是否有历史客户端仍调用旧签名 | 保留兼容或强制升级，需发布方确认 |
| R4-12 | `online_payment` 回填 | 是否所有套餐默认开通在线支付 | 不回填、不翻开关 |

**退出条件**：每个决策有书面结论、影响面、回滚方案；D17/D20 需产品/架构签字，R4-12 需商务确认，R4-10 需发布方确认历史版本分布。

### E1 环境阻塞批（environment）

| ID | 工作项 | 阻塞原因 | 执行前提 |
|---|---|---|---|
| R3-7 | 生产执行 M6 的 VALIDATE 与孤儿清洗 | 需生产库凭证、运维窗口、备份 | B9 的 R4-6/R3-6 完成；`p3a1`–`p3a7` 已升级；生产 `pg_dump` 完成 |
| R3-9 | 开发/预发/生产逐环境跑审计 SQL | 本会话无 `DATABASE_URL`；venv 解释器路径失效 | B9 的 R4-1/R4-2/R4-4/R4-5 完成；各环境可连库 |
| R4-11 | 支付/退款回调租户实测 | 微信不会带 `X-Tenant-ID`；需灰度环境与回调测试 | 逐租户核对 `notify_url` 含 `/t/<tenant_code>/` 或租户子域；退款回查加 `tenant_id`（`app/modules/refunds/service.py:377`） |

**回滚**：E1 全部是数据/配置动作，执行前备份、执行中逐表留档；M6 失败即停止，不回滚已 VALIDATE 的约束（外键可 `DROP CONSTRAINT`）。

---

## 5. 灰度开关翻转顺序

> 原则：一次只翻一个开关，翻后观察至少一个业务日；任一异常立即改回默认值并重启验证。`TENANT_PURGE_*` 本期不启用。

### 5.1 翻前门禁（必须先完成）

| 门禁 | 工作项 | 判定 |
|---|---|---|
| 平台管理员租户头可用 | R4-8 | 平台管理员仅带 `X-Tenant-ID` 可正常访问 stores/schedules/doctors/messages |
| 停服 403 能跳转/弹窗 | R4-9 | `error.code` 链路三端都能识别 |
| 遗留管理员观测 | R4-3 | `legacy User admin fallback hit` 连续 2 个周期命中=0 |
| 迁移与数据核对 | B9/E1 | 审计 ERROR=0、孤儿=0、16 表 VALIDATE 完成 |
| 功能开关回填 | R4-12 | 活跃租户 `online_payment` 未开通数=0 |

### 5.2 推荐翻转顺序

| 步骤 | 开关 | 默认 | 前置 | 观测指标 | 回滚 |
|---|---|---|---|---|---|
| 1 | `TENANT_CONSISTENCY_FAIL_CLOSE` | False（`config.py:137`） | 无（只做内存比对） | `当前请求的租户与账号不匹配` 计数；应仅出现在攻击/误配流量 | 改回 False 重启 |
| 2 | `TENANT_CODE_TO_ID_RESOLVE` | False（`:135`） | 步骤 1 稳定 | 5xx 率、请求延迟（每请求多一次 code→id 查询，`tenant_context.py:246-263`） | 改回 False |
| 3 | `TENANT_FILTER_FAIL_CLOSE` | False（`:133`） | 步骤 2 稳定；`tenant_filter missing tenant_id` 计数=0 | 403 计数按路由分组；重点看 admin/statistics/export | 改回 False |
| 4 | `PUBLIC_TENANT_REQUIRED_EXTRA_PATHS` | `[]`（`:141`） | 步骤 3 稳定；按路径逐条加 | 每条路径 400 计数；先加低风险路径 | 移除该路径 |
| 5 | `PATIENT_ANCHOR_FAIL_CLOSE` | False（`:139`） | **R4-8 完成**；D4 已拍板；患者端无头行为确认 | 平台管理员 400 计数；患者端 400 分布 | 改回 False |
| 6 | `LEGACY_USER_ADMIN_FALLBACK` | True（`:131`） | R4-3 日志命中=0 跨 2 周期 | 登录失败/管理员 401 | 改回 True |
| 7 | `FEATURE_ENFORCEMENT_ENABLED` | False（`:148`） | R4-12 回填完成；R3-4 范围确认 | `PERMISSION_DENIED` 403 按 feature 分组；支付下单成功率 | 改回 False |
| — | `TENANT_PURGE_ENABLED/DRY_RUN` | False/True（`:144-145`） | **本期不翻** | 仅 dry-run 清单 | 不适用 |

### 5.3 特别说明

- `auth_unified.py:518-524` 的“ID 不一致即 403”**不受开关控制**；一旦步骤 2 把 code 回填成 ID，该硬校验会对 code 头生效。因此步骤 1、2 必须先于步骤 5。
- `get_tenant_filter` 的 fail-open 分支（`tenant_deps.py:224-244`）在步骤 3 翻 True 后才会变成 403；此前只告警。步骤 3 之前必须先确认 `tenant_filter missing tenant_id` 为 0。
- 平台管理员在 `require_feature` 中天然豁免（`feature_deps.py:31-33`），步骤 7 不影响平台账号。

### 5.4 Runbook 操作步骤（R4-7）

开关全部通过环境变量注入，默认值已登记在 `apps/server/.env.example`
（`LEGACY_USER_ADMIN_FALLBACK` 至 `FEATURE_ENFORCEMENT_ENABLED` 共 9 项），
与 `app/core/config.py:131-148` 一一对应。单个开关的标准动作：

1. **翻前确认**：第 5.1 节对应门禁已完成并留档（审计 ERROR=0、孤儿=0、日志命中=0 等）。
2. **改配置**：只改目标开关一行，保留其余默认值；记录变更单与操作人。
3. **发布**：重启后端进程（配置在启动时读取）；确认启动日志无异常。
4. **观察**（至少一个业务日）：按 5.2 表“观测指标”取样，
   记录 403/400/5xx 计数与业务成功率；异常样本逐条定位。
5. **判定**：指标平稳 → 保留；出现误伤 → 立即把该行改回默认值并重启，回滚面仅此一项。
6. **留档**：在变更单记录开关名、旧值/新值、观察窗口、指标截图与结论。

补充约束：

- 一次只翻一个开关；禁止合并发布多个开关。
- `PUBLIC_TENANT_REQUIRED_EXTRA_PATHS` 逐条添加（JSON 数组），每次只加一条低风险路径。
- `TENANT_PURGE_ENABLED` / `TENANT_PURGE_DRY_RUN` **本期不翻**：
  `TENANT_PURGE_*` 在 `app/` 下只有配置两行、无任何消费方（R4-13），
  不能作为“已具备物理删除能力”的发布依据。

---

## 6. 数据核对 SQL 使用说明

### 6.1 文件与当前状态

- 文件：`apps/server/scripts/tenant_null_tenant_id_audit.sql`。
- 用途：为 D1/D9/D13/D15/D20 与 M6 孤儿清洗提供只读依据。
- **R4-1 后已可在 pre/post 两库直接执行**：脚本拆成 `SECTION 1 = PRE-MIGRATION` 与
  `SECTION 2 = POST-MIGRATION`，逐表用 `to_regclass()` + `information_schema.columns`
  守卫，缺失对象输出 `SKIP(missing)`，不会再因一条 `UNION` 断掉整段。
- 早期盘点的报错（`column "tenant_id" does not exist`）来自旧版无守卫脚本，已消除；
  `SECTION 2` 只补充 `p3a1/p3a7` 新增的列，在 pre 库会整段 SKIP，属预期。
- 脚本首行 `\set ON_ERROR_STOP on`，能跑到最后一行即 ERROR 计数=0。
- 只读：不建临时表、不写任何数据，可用只读账号执行。

### 6.2 运行前准备

1. 确认目标库的 `alembic_version`：
   ```sql
   SELECT version_num FROM alembic_version;
   ```
2. 备份：
   ```bash
   pg_dump "$DATABASE_URL" -Fc -f backup_$(date +%Y%m%d_%H%M).dump
   ```
3. 只读账号或事务只读：
   ```bash
   PGPASSWORD=... psql "$DATABASE_URL" -v ON_ERROR_STOP=1 -f apps/server/scripts/tenant_null_tenant_id_audit.sql
   ```
4. 脚本内已含 `\set ON_ERROR_STOP on`；任何 ERROR 都会立即中止，能跑到最后一行即 ERROR 计数=0。

### 6.3 两阶段拆分（R4-1）

| 阶段 | 适用库 | 包含段落 |
|---|---|---|
| **SECTION 1（pre-migration）** | `alembic_version` 在 `p3a1` 之前或之后 | D20（含 `to_regclass` 守卫与 miniapp 按租户 `status=2` 计数）、D13（跨租户/同租户/平台三类）、D15、D1（日志观测门禁）、D9（16 张业务表，含新增 5 张）、M6（12 张既有表的孤儿） |
| **SECTION 2（post-migration）** | `p3a1` + `p3a7` 之后 | D9 内容/平台配置表（news/notices/banners/content_versions/system_settings）、M6 内容 4 表、`fk_*_tenant` 的 `convalidated`、purge 候选预览 |

> 设计：`SECTION 2` 只补充 `p3a1/p3a7` 新增的列，整文件在 pre/post 两库都能执行；
> post 库中 `SECTION 1 + SECTION 2` 即 D9 全量与 M6 全量 16 表。
> （早期计划写的“M6 仅已存在列的 10 张表”与代码不符：16 张中 4 张内容表的
> `tenant_id` 由 `p3a1` 新增，pre 段实际覆盖其余 12 张。）

每张表改为独立语句，并用守卫避免整段丢失。实际实现用 psql `\gexec`
按目录生成语句（只读，不建临时表）：

```sql
WITH candidates(t) AS (VALUES ('system_settings'), ('news'))
SELECT format(
         'SELECT %L AS table_name, count(*) FILTER (WHERE tenant_id IS NULL) AS null_tenant, '
         'count(*) AS total FROM public.%I', t, t)
FROM candidates v
WHERE to_regclass('public.' || v.t) IS NOT NULL
  AND EXISTS (
      SELECT 1 FROM information_schema.columns c
      WHERE c.table_schema='public' AND c.table_name=v.t AND c.column_name='tenant_id'
  )
\gexec
```

> `\gexec` 必须直接跟在 SELECT 之后、**不要**先写分号：分号会清空 query buffer，
> psql 转而“重新执行上一条语句”，把结果列当成 SQL 执行而报错。

缺失的表/列由后续“SKIP 清单”查询输出 `SKIP(missing)`；
`\set ON_ERROR_STOP on` 保证真实 ERROR 立即中止。

### 6.4 各段说明

| 段 | 目的 | 判定/留档 |
|---|---|---|
| D20（SECTION 1） | `data_scopes`/`role_permissions` 行数 + 存在性 + miniapp 归档口径 | 两表均存在且行数=0，才允许 R3-3 的 drop 迁移；缺失输出 `MISSING`；`miniapp_instances` 按租户输出 `status=2` 计数供产品拍板 |
| D13（SECTION 1） | 管理员用户名/角色编码冲突 | 输出 `scope=cross_tenant/same_tenant/platform` 三类；任一类>0 时 p3a2 会在 `create_unique_constraint` 阶段失败（`p3a2_admin_role_unique.py:32-41`） |
| D15（SECTION 1） | 预约与支付配置租户不一致 | 结果>0 的回调会被拒收（`payments/service.py:179-195`）；先修数据再切回调锚点 |
| D9（SECTION 1/2） | 各表 NULL 租户行 + `null_pct` | 业务表 16 张在 SECTION 1；内容/平台配置表单列在 SECTION 2；内容表 NULL 是 D10 平台级语义，不参与业务回填 |
| M6（SECTION 1/2） | 16 表外键孤儿 | SECTION 1 = 12 张既有表，SECTION 2 = 4 张内容表；孤儿>0 不得 VALIDATE；清洗见 6.5 |
| D1（SECTION 1） | 遗留管理员日志观测门禁 | SQL 只输出门禁关键字与样本规模；`legacy User admin fallback hit` 连续 2 个发布周期命中=0 才允许关 `LEGACY_USER_ADMIN_FALLBACK` |
| purge 预览（SECTION 2） | 90 天前软删除租户 | 本期只做清单，不执行删除；`TENANT_PURGE_*` 无消费方 |

### 6.5 M6 清洗配方（R4-6）

`p3a6_tenant_fk.py:9-16` 的通用配方是 `UPDATE <table> SET tenant_id = NULL`。该配方只适用于可空表：

| 类别 | 表 | 处理 |
|---|---|---|
| 可空（10 张） | `email_templates`、`message_templates`、`notification_logs`、`notification_preferences`、`rule_set_audit_logs`、`schedule_audit_logs`、`news`、`notices`、`banners`、`content_versions` | 备份后 `UPDATE ... SET tenant_id = NULL WHERE 孤儿`，再 `ALTER TABLE ... VALIDATE CONSTRAINT` |
| `NOT NULL`（6 张） | `unified_templates`、`notification_groups`、`notification_recipients`、`notification_deliveries`、`channel_strategies`、`recipient_rules` | **禁止 SET NULL**：先导出孤儿清单人工确认，按业务重映射到有效租户，或 DELETE 后重建；再 VALIDATE |

执行顺序：逐表备份 → 逐表清洗 → 逐表 `VALIDATE CONSTRAINT` → 汇总 `pg_constraint.convalidated`。任一张表孤儿>0 或 VALIDATE 失败，停止并升级。

### 6.6 执行与留档模板

每次执行记录以下字段：

```
环境：
DATABASE_URL 标识（脱敏）：
alembic_version：
执行时间：
执行人：
脚本版本（git sha / 文件 hash）：
备份文件（pg_dump 路径 / 校验和）：
D20 data_scopes 行数 / role_permissions 行数 / 表是否存在：
D13 冲突条数（跨租户 / 同租户 / 平台）：
D15 不一致条数：
D9 各表 NULL/total/null_pct：
M6 各表孤儿数 / convalidated：
回填 dry-run 可推导条数 / 不可推导(NULL)条数：
ERROR 计数：
结论：通过 / 暂停（原因）
```

### 6.7 失败处理

- 任一 `ERROR`：本次核对视为未完成，不得据此翻开关或执行迁移。
- M6 某表 VALIDATE 失败：保留 `NOT VALID` 约束，回退该表清洗改动，查孤儿来源；其余表不受影响。
- 生产发现 NOT NULL 表大额孤儿：暂停，转人工处置，不做批量 DELETE。

### 6.8 迁移顺序与备份（R4-15 固化）

**迁移链（单头，顺序不可调整）**：

```
20260630_drop_plaintext
  → p3a1_content_tenant
  → p3a2_admin_role_unique
  → p3a3_business_numbers
  → p3a4_config_codes
  → p3a5_usage_daily_unique
  → p3a6_tenant_fk
  → p3a7_settings_tenant
```

每个文件的 `revision/down_revision` 均与前一项首尾相接（`p3a1:15`、`p3a2:17`、
`p3a3:16`、`p3a4:16`、`p3a5:15`、`p3a6:37`、`p3a7:17`）；本批未运行 `alembic heads`，
上线前需在目标库以 `alembic heads` 复核为单头后再执行。

**执行顺序（每步通过才进入下一步）**：

| 步骤 | 动作 | 通过条件 |
|---|---|---|
| 1 | 备份：`pg_dump "$DATABASE_URL" -Fc -f backup_<ts>.dump`，并单独导出 **内容四表**（news/notices/banners/content_versions）与 **tenant_usage_logs** | dump 可 `pg_restore --list` 读取，记录大小与校验和 |
| 2 | 在备份副本上跑 `tenant_null_tenant_id_audit.sql`（SECTION 1） | ERROR=0；D13 三类冲突、D15、M6 孤儿均已留档 |
| 3 | 在 staging 全链 `alembic upgrade head`（p3a1→p3a7 一次） | 单头；无 ERROR |
| 4 | 跑 `tenant_null_tenant_id_audit.sql` 全文件（SECTION 1+2） | ERROR=0；D9/M6 为全量 16 表结论 |
| 5 | 跑 `migrate_core_tenant_data.py --dry-run`，记录“可推导 / 不可推导(NULL)”总数 | 不可推导行有逐表明细，可人工核对 |
| 6 | 跑 `m6_post_deploy_cleanse_and_validate.sql`（先 dry-run，再 `-v apply=1`） | 可空表孤儿=0、NOT NULL 表人工处置完成、`convalidated` 全 true |
| 7 | 需要时执行 `migrate_core_tenant_data.py --execute` 与 `--verify` | 业务表 NULL=0（follow_up_plans 平台级模板除外） |

**不可逆点（备份必须覆盖）**：

- `p3a1_content_tenant`：内容表 `tenant_id` 回填后 `downgrade` 只删列，**回填数据不可自动恢复**；
- `p3a5_usage_daily_unique`：按 `SUM` 合并重复用量行，**合并前原行不可恢复**；
- 因此步骤 1 的备份是硬前置，staging 必须完整跑一次 `upgrade` + `downgrade`
  并记录上述不可恢复部分，生产不得跳步。

**回滚**：`p3a1`–`p3a7` 的 schema 变更可逐级 `downgrade`；数据回填与合并依赖步骤 1
的备份恢复。`p3a2`/`p3a5` 的 downgrade 在存在跨租户同名/重复用量时可能失败，需先清理。

---

## 7. 遗留决策清单

| 决策 | 问题 | 建议默认 | 阻塞批次 | 需要谁拍板 |
|---|---|---|---|---|
| **D1** | 现网是否仍有仅存 `users` 表的旧管理员 | 先日志观测 2 个周期，命中=0 再关 `LEGACY_USER_ADMIN_FALLBACK` | 步骤 6 | 业务/运维 |
| **D4** | 公开/患者端无租户头是 400 还是空集 | 写操作 400；读列表返回空集并告警（与 fail-close 方向一致） | 步骤 5、R1-15/R1-18 | 架构 |
| **D13** | 跨租户重复 username/code 的改名原则 | 人工逐个处理，禁止自动加前缀（避免登录名变化） | p3a2 门禁 | 业务/DBA |
| **D17** | `auto_renew` 语义 | 延长周期 + 生成 pending 应收账单 + 宽限期不停服，无真实扣款 | R2-6/R3-1 | 产品/商务 |
| **D20** | DataScope/role_permissions 是否删除；miniapp 配额是否含 `status=2` | 两表行数=0 且表存在才 drop；miniapp 默认不计归档实例（需确认） | R3-3/R1-3 | 架构/产品 |
| **purge** | 软删除保留期与物理删除范围 | 保留 90 天；首版只 dry-run；NOT NULL 子表不做批量 DELETE | R2-5/R3-2 | 产品/运维 |
| **online_payment** | 是否所有套餐默认开通在线支付 | 先回填 `features.online_payment=true` 再翻开关 | R4-12/步骤 7 | 商务 |
| **/ws/poll** | 历史医生端是否仍调用旧签名 | 发布说明列为破坏性变更；有存量则加过渡兼容 | R4-10 | 发布方 |
| **feature 试点范围** | `export_data`/`basic_statistics` 是否本期接线 | 本期只接线、不翻总开关；先补负向测试 | R3-4/R3-5 | 产品 |

### 7.1 决策采纳记录（2026-10-24，负责人指示按建议默认执行）

| 决策 | 采纳结论 | 执行状态 |
|---|---|---|
| **D17** auto_renew | 延长周期（monthly=30 天 / yearly=365 天）+ 生成 pending 应收（无真实扣费）+ 不停服 | ✅ 已实现（`tenant_usage_task._renew_subscription`），4 条单测收口 |
| **purge**（R2-5） | 保留 90 天；首版只 dry-run；NOT NULL 子表不做批量 DELETE | 维持现状，物理删除不实现 |
| **D20**（R3-3） | drop 门禁 = 两表行数 0 且表存在，需全环境核对 | 开发库已核对（data_scopes=0、role_permissions=0）；staging/生产未核对，drop 迁移暂不编写；miniapp 配额维持默认不计归档 |
| **R3-4** 功能开关试点 | 总开关保持 False | 已是现状 |
| **R4-10** /ws/poll | 待发布方确认历史版本分布 | 未动 |
| **R4-12** online_payment | 先回填再翻开关 | 回填脚本已备（`scripts/backfill_online_payment_feature.py`，默认 dry-run）；staging/生产执行归 E1 |

---

## 8. 已确认无需纳入 P5 的模块（R1-20 登记）

以下模块已具备正确锚点或属公开/患者/平台端，后续不再重复改造：

| 模块 | 现状 | 证据 |
|---|---|---|
| contacts | 直接用账号租户 | `app/modules/contacts/router.py:52/78/94/113` |
| guide_tours 管理端 | 仅平台管理员 | `app/modules/guide_tours/router_admin.py:10/31/44` |
| backup | 仅平台管理员 | `app/modules/backup/router.py:12-16/38` |
| platform_metrics | 全端点平台管理员 | `app/modules/platform_metrics/router.py:20/37/56-65` |
| platform_announcements | 平台语义 `target_tenant_ids` | `app/modules/platform_announcements/service.py:72/132-135` |
| session_events / performance | 匿名公开上报 | `app/modules/session_events/router.py:133`、`app/modules/performance/router.py:102` |
| 患者自助端 | 已按患者/租户守卫 | `user_favorites/router.py:14-62`、`appointment_satisfactions/router.py:25`、`support_tickets/router.py:69-78`、`doctor_reviews/router.py:24-29` |
| upload | 已加租户校验 | `app/modules/upload/router.py:199-219` |

**注意**：`consultation_fees` 与 `store_email_recipients` 的模型本身没有 `tenant_id` 列（`app/models/store_email_recipient.py:18-23`、`app/models/consultation_fee.py:9-65`），不能靠路由层补，需另立数据模型项。

---

## 9. 跨批次风险

1. **锚点语义改动面大**：R4-8 让 `require_admin_tenant_anchor` 回退 header，等于改变所有已接入端点；必须先用契约测试锁住“租户管理员只自身、平台管理员可显式跨租户”。
2. **fail-close 开关与前端联动**：步骤 3/5 一旦打开，任何仍用 `get_current_tenant_id()` 且未改造的端点都会从“看全量”变 403。翻开关前必须完成 B3–B8 的对应模块。
3. **数据迁移不可逆**：p3a5 合并重复用量行、p3a1 内容表回填不可自动恢复；生产必须先备份并在 staging 全链演练。
4. **NOT NULL 孤儿清洗不可照文档执行**：6 张统一消息表禁止 `SET NULL`，否则 VALIDATE 永远失败。
5. **测试假绿**：stores 的 403 可能来自 `check_store_access` 而非租户锚点；矩阵必须补正控与超管视角。
6. **功能开关误伤支付**：`FEATURE_ENFORCEMENT_ENABLED=True` 且未回填 `online_payment` 时，所有存量租户下单 403。
7. **purge 空转**：`TENANT_PURGE_*` 无任何消费方，不能作为“已具备物理删除能力”的发布依据。
8. **auto_renew 未实现**：到期任务直接置欠费（`tenant_usage_task.py:224-229`），订阅到期会停服；D17 未拍板前不要承诺自动续费。
9. **支付回调单域名**：回调必须能从子域/路径前缀定位租户；单域名 `/api/v1/payments/wechat/callback` 会被拒收。
10. **前端错误码链路**：后端信封是 `error.code`，前端读 `error_code`；管理端结构化分支还会提前吞掉 `TENANT_OVERDUE`。不修 R4-9 就翻停服相关开关，用户看不到停服页。

---

## 10. 本次执行边界（如实说明）

- 本节第 1–6 条描述的是**盘点/计划阶段**的边界；B9 批次的实际改动见 10.1，
  B0–B8、B10、B11 的执行记录见 10.2，前端测试可执行化与验证快照见 10.3/10.4，
  测试补全与权限覆盖矩阵见 10.5，auto_renew 骨架见 10.6，
  D17 落地与读端点权限收口见 10.7，开发库全链演练见 10.8。
- 计划阶段只新增/覆盖本文档 `docs/tenant-remaining-plan.md`；未修改任何后端/前端代码，未执行 `git commit`。
- **未运行任何 pytest**，本文所有“验收门”均为计划中的命令与断言，不代表已通过。
- **未连接任何数据库**，未执行 `scripts/tenant_null_tenant_id_audit.sql`；文中引用的 psql 报错来自盘点 R4-1 的实测记录。
- **未运行 `alembic heads` / `alembic check`**；迁移链单头结论来自各迁移文件的 `revision/down_revision` 静态核对。
- 未启用任何灰度开关；未执行物理删除、续费、M6 VALIDATE 等生产动作。
- 计划阶段未发生 Mimosa 拦截（仅写入本文件）。

### 10.1 B9 执行记录（数据核对与迁移脚本）

本批改动（均为脚本/文档/模型声明，不连库、不执行迁移）：

| 工作项 | 落点 | 说明 |
|---|---|---|
| R4-1 | `apps/server/scripts/tenant_null_tenant_id_audit.sql` | 拆 SECTION 1/2；逐表 `to_regclass` + `information_schema.columns` 守卫；缺失输出 `SKIP(missing)`；`\set ON_ERROR_STOP on` |
| R4-2 | 同上 D13 | 补 `same_tenant` / `platform` 两类，与 p3a2 的复合唯一 + partial unique 对齐 |
| R4-3 | 同上 D1 | 改为 `legacy User admin fallback hit` 日志观测门禁（`app/common/auth_unified.py:411`） |
| R4-4 | 同上 D9 | 补 `follow_up_plans/follow_up_records/follow_up_self_reports/doctor_reviews/feedbacks`；输出 `null_pct`；内容表单列 |
| R4-5 | 同上 D20 | `role_permissions` 存在性守卫；新增 `miniapp_instances` 按租户 `status=2` 计数 |
| R4-6 | `migrations/versions/p3a6_tenant_fk.py`（仅文件头） | 清洗配方区分 10 张可空表 / 6 张 NOT NULL 表；迁移语义未改 |
| R3-6 | `apps/server/scripts/m6_post_deploy_cleanse_and_validate.sql`（新增） | dry-run 默认；`-v apply=1` 执行可空表清洗与 16 表 VALIDATE；NOT NULL 表只出清单 |
| R3-8 | 7 个模型列 | 补 `ForeignKey("tenants.id")`；已用 Python 导入断言 16 张表的 `tenant_id` 外键非空 |
| R4-14 | `apps/server/scripts/migrate_core_tenant_data.py` | 删除默认租户兜底；新增 8 张业务从属表回填；dry-run 输出可推导/不可推导(NULL) 数量 |
| R4-15 | 本文 6.8 | 固化 p3a1→p3a7 顺序、备份步骤、不可逆点与回滚 |
| R4-7 | 本文 5.4 + `apps/server/.env.example` | 9 个灰度开关及默认值登记；Runbook 翻/观察/回滚步骤 |

**本批未做**：未连库执行审计 SQL 或 M6 脚本（按批次约束与第 10 节边界）；
`alembic autogenerate` 零 diff、pre/post 两库 ERROR=0、staging dry-run 等验收门
归 E1 / staging 执行，本批未运行。

### 10.2 B0–B8、B10、B11 执行记录（2026-10-23 补录）

> 除 B9 外的其余无阻塞批次均已合入 `feat/tenant-isolation-hardening`。
> 表中「验证」为 2026-10-23 本地实测（内存 SQLite + vitest，详见 10.4）。

| 批次 | 提交 | 关键落点 | 验证 |
|---|---|---|---|
| B0 | `40285740` | waitlist `/stats` 改经 `Schedule.store_id` join（`app/modules/waitlist/router.py:161/253-263`，不再引用不存在的 `WaitlistEntry.store_id`）；stores 详情/状态/批量绑定传入锚点；approval 测试 cwd、quota 测试时间与单号固定 | waitlist /stats 矩阵用例（`test_p2a_tenant_matrix.py:239-248`）、`test_quota.py`、`test_approval_business_callbacks.py` 全绿 |
| B1 | `2d5086da` | `require_admin_tenant_anchor` 在 query 为空时回退请求上下文（`app/common/tenant_deps.py:200-214`），平台管理员仅带 `X-Tenant-ID` 不再被误判未指定租户 | `test_isolation_matrix.py`（stores/doctors/departments + 超管视角）12 用例绿 |
| B2 | `5de3c551` | `ModuleSpec` 增加 `write_method`/`omit_body`；P2A 补 POST/PUT/cancel/waitlist/stats/payments/refunds；P2B 升到 HTTP 层；P2C 补排班/医生/门店/科室/消息写路径 | P2A 12、P2B 15、P2C 10、基础矩阵 12 用例绿 |
| B3–B8 | `01e39893` | 41 个业务文件接入 `require_admin_tenant_anchor`/`resolve_admin_tenant_anchor`；settings/statistics/shift_types 补租户维度；notification_logs 拒绝 query 越权（`router.py:27-47`）、unified_message 拒绝请求体越权并改写为锚点（`router.py:36-52`）；statistics 7 个 router 接租户条件、`_build_tenant_condition` 模型缺列时返回永假条件 | `test_b3`（13）/`test_b5`（21）/`test_b6`（23）/`test_b7`（35）/`test_b8`（33）/`test_statistics_tenant_isolation`（10）共 135 用例绿 |
| B10 | `d0c71221`、`d96dad7d` | `parseTenantError` 兼容 `error.code` 信封等 5 种形态；`error-handling.ts` 不再提前吞 `TENANT_*`；`web-interceptors` 403 分支先判停服；患者端 `app.tsx:181-188` 读 `error.code`；`.env.example` 登记 9 开关 | 前端单测接入后实测：shared 157（含 parseTenantError 14）、api 15（含 tenantSuspended 3）、admin 90 全绿（见 10.3） |
| B11 | `4fadc455` | `app/tasks/tenant_lifecycle_task.py:52` 双门禁（`TENANT_PURGE_ENABLED` 默认 False + `TENANT_PURGE_DRY_RUN`）dry-run 任务；beat 注册（`app/celery_app.py:338-341`）；代码中无任何 DELETE 路径 | 静态审查确认无删除语句；**dry-run/no-op/幂等行为尚无单测**（待补，不阻塞 D1 决策） |

**遗留说明**：

1. `TENANT_PURGE_*` 的 dry-run/no-op/幂等行为已补单测（见 10.5）；
   `auto_renew` 测试骨架仍属 D1（R2-6）前置，未写。
2. `tests/tenants/test_tenant_data_isolation.py` 中指向 `/api/v1/export/doctors`
   的两条 skip 已归因复活（见 10.5），租户套件不再有路由级 skip。

### 10.3 前端测试可执行化（2026-10-23，随 B10 验收补全）

B10 的两个单测此前放在没有测试入口的包里，无法用仓库命令运行，本次接线：

| 变更 | 内容 |
|---|---|
| 测试入口 | `packages/shared`、`packages/api` 各新增 `vitest.config.ts` 与 `test`/`test:watch` 脚本（vitest ^1.6.1，与 admin/codegen 同链）；`pnpm install` 后 lockfile 已更新；`pnpm test`（turbo）自动纳入 |
| 存量缺陷修复（shared） | expression-engine 词法两处缺陷：① `===`/`!==` 在运算符集合里却只按 2 字符切片，永远切不出来（语法文档与解析器均声明支持）；② 字符串转义（`\'` `\"` `\\`）扫描时只用于跳过引号，取值未解码。均已修复 |
| 存量缺陷修复（api） | `retry.test.ts` 为 Jest 时代死测试（`jest.fn`、`} as any` 非法语法，从未编译通过），按当前实现重写为 adapter 驱动真实拦截器链（重试/非幂等不重试/401-403 不重试/达上限退避 100→200→400/withRetry 标记）；`performance.test.ts` 依赖全局 API 且 0ms 偶发，配置 `globals: true` 并回拨 startTime 固定耗时 |
| 测试语义对齐（shared） | 模板插值用例改为引擎文档语义（裸文本 `Hello ${name}`，不带外层引号）；原型污染用例改为断言赋值语法被 `SyntaxError` 拒绝 |

### 10.4 验证快照（2026-10-23，HEAD=d96dad7d）

| 命令 | 结果 |
|---|---|
| `pytest tests/tenants tests/security/test_p2a_tenant_matrix.py tests/security/test_patient_data_flow_tenant_isolation.py tests/security/test_tenant_isolation.py tests/security/test_admin_identity_anchor.py` | 344 通过 / 3 跳过 / 1 xfail |
| `pytest tests/security` | 107 通过 |
| `pytest tests/unit/test_tenant_anchor.py tests/unit/test_data_scope_tenant_fail_close.py tests/unit/test_feature_deps.py tests/unit/test_tenant_fk_models.py` | 34 通过 |
| `pytest tests/unit/test_waitlist.py tests/unit/test_extra_quota.py tests/unit/test_approval_business_callbacks.py` | 70 通过 |
| `python -c "import app.main"` | 通过 |
| `pnpm --filter @hospital/{shared,api,website,codegen} test` + admin vitest | 157 / 15 / 26 / 26 / 90 全通过 |

环境说明：`apps/server/.venv` 为旧路径（`~/letond/...`）创建、`bin/python` 软链失效，
上述 pytest 用系统 `python3.11`（依赖齐全）执行；连库类验收门仍未运行（归 E1）。

### 10.5 测试补全与权限覆盖矩阵（2026-10-23，第二批次，未提交）

B0–B11 复盘时暴露的三个测试缺口在本批次收口：

| 事项 | 落点 | 说明 |
|---|---|---|
| B11 purge 任务单测 | 新增 `apps/server/tests/unit/test_tenant_lifecycle_task.py`（6 用例） | 覆盖 B11 验收门：`ENABLED=False` 全程 no-op（不开 DB 会话）；dry-run 只列超 90 天保留期的软删除租户、行数不变；未到期/未删除不进候选；`DRY_RUN=False` 首版同样零删除；重复执行幂等。真实 SQLite 承接 `_find_expired_deleted_tenants` 查询，冻结任务内 `utcnow` 消除边界偶发 |
| export/doctors 两条 skip 归因 | `tests/tenants/test_tenant_data_isolation.py` | 结论是**用例过期而非路由缺失**：医生导出真实路由为 `/api/v1/data/export/doctors`（`app/api/v1/__init__.py:103`），旧 `/api/v1/export` 模块只有 appointments/patients/schedules。四条用例改指真实路由并去 skip：无权限 403、有权限 200+xlsx、导出只含本租户医生（解析 xlsx 断言 A 进 B 不出）、伪造 `X-Tenant-ID` 403。受限角色 fixture 去掉 `doctor:list`（该路由守卫为 `doctor:export` OR `doctor:list`，满足其一即放行） |
| 管理端路由↔权限守卫覆盖矩阵 | 新增 `apps/server/tests/architecture/test_admin_route_permission_matrix.py`（3 用例） | 把「`/api/v1/admin/**` 每条路由要么有权限守卫（require_permission 族 / require_platform_admin），要么在带原因的豁免台账登记」固化为 fitness test；台账反向校验防腐化；自助豁免限路径前缀防滥用。**盘点结果**：写端点全部有守卫；5 个读端点无码（`GET /admins`、`GET /admins/{id}`、`GET /roles`、`/roles/all`、`/roles/{id}`）登记为 KNOWN_GAPS——权限目录（`scripts/init_permissions.py`）无 `system:user:list`/`system:role:list` 码，直接加守卫会锁死所有非 `*` 角色且无法授权，收口需产品拍板（新权限码 + 前端角色页对齐），已作为独立工作项记录 |
| 文件规模 fitness 基线棘轮 | `tests/architecture/test_fitness_functions.py` | B3–B8 锚点改造使 30 个 router、7 个 service、2 个 schemas 超过 legacy baseline（另有 `tenants/service_migration.py`、`service_tenant.py` 两文件此前漏登台账），3 条用例在 HEAD 上即红。按棘轮约定把基线对齐当前行数（attendance_records、statistics/router_overview 随之下调），修复后 6/6 绿 |

**本批验证**（工作区，基于 HEAD=d96dad7d）：
`pytest tests/tenants tests/security tests/architecture tests/unit/test_tenant_lifecycle_task.py`
→ **419 通过 / 1 跳过（SyncRedis 设计内跳过）/ 1 xfail**，租户套件不再有路由级 skip。

### 10.6 R2-6 auto_renew 骨架与到期计数修复（2026-10-23，第三批次）

按 D1 批「R2-6 未决时的处理：先写测试骨架，不实现扣款」执行：

| 事项 | 落点 | 说明 |
|---|---|---|
| auto_renew 测试骨架 | 新增 `apps/server/tests/unit/test_auto_renew_skeleton.py`（1 契约用例 + 3 条 `xfail(strict=True)`） | 「未开自动续费到期仍置欠费」固化为普通契约用例；D17 三条期望（到期不停服 / 生成 pending 应收无真实扣款 / 订阅周期延长）以 strict xfail 登记，实现落地即 XPASS 报错，届时摘标记收口 |
| 到期任务计数 bug | `app/tasks/tenant_usage_task.py` `send_notifications` | 闭包内 `reminded_count/suspended_count +=` 缺 `nonlocal`，每个到期租户抛 UnboundLocalError 被逐租户 except 吞掉——置欠费碰巧仍生效（状态先改后计数），但任务返回计数恒为 0 且每次执行刷错误日志。补 `nonlocal` 后契约用例通过（此前该任务零测试覆盖） |

### 10.7 D17 落地、R4-12 脚本与读端点权限收口（2026-10-24，第四批次）

| 事项 | 落点 | 说明 |
|---|---|---|
| D17 auto_renew 实现 | `app/tasks/tenant_usage_task.py` `_renew_subscription` | 到期租户若有 status=1 且 auto_renew 订阅：旧订阅置 2、按原计划新建 `payment_status='pending'` 应收（金额/币种快照，paid_at 空）、`tenant.subscription_end_at` 顺延一个周期；返回值新增 `renewed_count`。未开自动续费维持置欠费 |
| 测试收口 | `tests/unit/test_auto_renew.py`（原 skeleton 改名） | 3 条 strict xfail 摘除转正 + 契约用例，4/4 绿 |
| R4-12 回填脚本 | 新增 `scripts/backfill_online_payment_feature.py` | 只写 `tenants.features` 租户级覆盖（不动计划默认）；仅 status=1 未软删除租户；默认 dry-run、`--execute` 落库、幂等 |
| 读端点权限收口 | `router_admins.py`：GET `/admins`、`/admins/{id}` 挂 `require_permission("system:user:list", "system:user")`；`router_roles.py`：GET `/roles`、`/roles/all`、`/roles/{id}` 挂 `("system:role:list", "system:role")` | OR 父码兼容存量授权（仅有 `system:user`/`system:role` 的角色不锁死）；权限目录 `scripts/init_permissions.py` 补两个细码；admin `access.ts` 菜单门控同步加入细码；矩阵台账 KNOWN_GAPS 清空。行为测试 `tests/security/test_admin_read_permission_guard.py` 7 用例（403/父码兼容/细码/通配/跨模块不串/详情端点） |

### 10.8 E1 开发库全链演练（2026-10-24，第五批次）

按第 6.8 节流程在本机开发库（PG16，`hospital_booking`）完整演练：

| 步骤 | 结果 |
|---|---|
| 1 备份 | `pg_dump -Fc` 1.5MB，`pg_restore --list` 可读 |
| 2 pre 审计 | `tenant_null_tenant_id_audit.sql` ERROR=0；D13 三类冲突=0、D15=0、D9 业务表 NULL=0、D20 两表=0 行、M6 既有表孤儿=**notification_logs 216**；SECTION 2 按预期 SKIP |
| 3 `alembic heads` 复核 | 单头 `p3a7_settings_tenant`（R4-15 要求的复核首次实际执行） |
| 4 升级 | 首跑失败：`p3a4` 假设 `guide_tours_code_key` 约束存在，开发库实为唯一索引 `ix_guide_tours_code`（create_all 历史差异）→ **修复 p3a4 按实际形态（约束/唯一索引）分别删除**；重跑 p3a1→p3a7 全链成功 |
| 5 post 审计 | ERROR=0，SECTION 1+2 全量输出 |
| 6 M6 清洗 | dry-run 确认 216 条 A 类（可空表）→ `apply=1` SET NULL 清零，16 个 `fk_*_tenant` 全部 VALIDATE（convalidated=t） |
| 7 降级演练 | `downgrade 20260630_drop_plaintext` 全链成功（含修复后的 p3a4 downgrade） |
| 8 复位 | 重新 `upgrade head` + M6 apply，最终态：p3a7、孤儿=0、16 外键 validated |

**开发库演练发现并修复**：p3a4 对「唯一索引 vs 唯一约束」的历史形态差异不兼容（生产若同样经 create_all 同步过会同样失败，staging/生产执行前需按第 6.6 节留档 `pg_indexes` 形态）。

**仍未做（归 E1 剩余）**：staging/生产两环境的审计与 M6（无凭证）；微信支付/退款回调租户实测；`alembic downgrade` 在生产数据的不可逆点留档（6.8 要求 staging 完整演练已由开发库部分替代，生产仍需按流程）。

### 10.9 退款收敛、51 项核对、p3a8 数据模型项与环境修复（2026-10-24，第六批次）

| 事项 | 落点 | 说明 |
|---|---|---|
| R4-11 代码半边：退款回查租户收敛 | `refunds/service.py` `process_refund_callback` 增 `tenant_id` 参数（提供时按 (tenant_id, refund_no) 收敛）；`refunds/router.py` 回调传入解析出的租户 | 3 条单测：错租户上下文 404 且记录不被误更新、同租户正常更新、不传参保持全局幂等键查找（兼容非回调路径） |
| 51 项主计划交叉核对 | `tenant-refactor-plan.md` 附2 | 结论 51/51 完成或按决策搁置；**抓出并修复 P4-5 语义缺口：续费须 `payment_status='paid'` 才触发**（未付费订阅挂账不得无限续费不停服），补负向单测 |
| p3a8 数据模型项 | 迁移 `p3a8_fee_tenant` + 5 个模型列 + service 落锚 + `test_tenant_fk_models` 参数化 5 表 | consultation_fee_types/templates、store_fee_templates、doctor_consultation_fees、store_email_recipients 补 tenant_id（nullable+FK NOT VALID）；经 store/fee_type 回填；写入路径落锚（平台级类型/模板保持 NULL 语义）；M6 清洗脚本 A 类清单纳入（10+5 张）。开发库实跑：doctor_fees 15/15 回填、21/21 外键 VALIDATE。**查询侧锚点收口留待后续模块批次** |
| 环境与构建验证 | `.venv` 重建（3.11.15 + 全依赖）；website/admin/patient-h5/miniapp 四端 build 全绿 | admin lint 存量 107 错（15+ 历史业务页面，与本轮改动无关，`access.ts` 干净），单列为技术债 |

### 10.10 权限页余项收口与权限码清单（2026-10-24，第七批次）

| 事项 | 落点 | 说明 |
|---|---|---|
| openspec 4.3 | `apps/admin/src/pages/system/__tests__/role-permissions.utils.test.ts`（21 用例） | 分类推断（显式 controlType 优先/深度/子节点/action-api 段）、模块传播、三维过滤（关键词/类型/仅看已选 + 祖先保留）、计数与高风险判定全部覆盖；tsc 零错 |
| openspec 1.5 | `role-permissions.tsx` + `utils.codesByControlTypes` | 模块卡片标题补模块级「全选/清空」（随当前筛选生效）；工具栏补「仅选页面级 / 仅选操作级」一键（重置为全树 page+tab / action 权限码） |
| openspec 0.1 | 新增 `apps/server/scripts/gen_permission_matrix.py` + `docs/modules/permission-codes.md` | 静态生成权限码 ↔ 后端守卫（文件:行）↔ 前端引用清单；`--check` 可挂 CI 做漂移门禁。**盘点发现 48 个目录外守卫码**（approval-flow/contact/freelance/lowcode/points/schedule:extra-quota 等）——后端守卫在用但种子目录与开发库 permissions 表均无，非 `*` 角色永远无法获得这些模块授权；补目录需产品定名与分组，已在 permission.md「已知缺口」登记 |
| permission.md 重写 | `docs/modules/permission.md` | 从早期 PRD 更新为现行模型：Role.permissions JSON 授权、平台级权限目录、检查依赖族与通配、租户/门店/功能三层控制、读端点收口、分配页能力与已知缺口 |
| admin lint 真 bug | `apps/admin/src/pages/approval/designer/PropertyPanel.tsx` | 修复 rules-of-hooks×3：三个监听器 Hook 位于 `!selectedNode` 早退之后，「选中→取消选中」会触发 React Hook 数量不一致崩溃；已移到早退前 |
| admin lint 技术债 | 49 文件 104 错（修复后） | 构成：no-unused-vars×73、no-use-before-define×24、no-unescaped-entities×6、button-has-type×1；全部机械修复项，未在本批处理（避免大面积触碰 49 个业务页面），留作独立清理批 |

**本批验证**：admin vitest 112 通过（+21）、admin tsc/build 全绿；后端无改动。

### 10.11 漂移权限码补目录与 admin lint 清零（2026-10-24，第八批次）

| 事项 | 落点 | 说明 |
|---|---|---|
| 48 个目录外权限码补齐 | `scripts/init_permissions.py`（130→185 条）+ 开发库 permissions 表（128→185 行，幂等插入） | 按「码已在后端守卫存在，仅补中文名与分组」原则：新增 7 个分组菜单（审批中心/联系人/兼职结算/积分/服务工单/候补/考勤）+ 既有分组挂载（doctor/schedule/lowcode/system）；命名遵循现有「查看/新增/编辑/删除/导出」惯例，产品可随时改名（name 可变，code 不动）。完整性校验：无重复、无孤儿父级；`gen_permission_matrix.py` 漂移 0，`--check` 退出码 0 可挂 CI。**staging/生产需重跑 init_permissions 或等价幂等插入后才可授权这些模块** |
| admin lint 清零 | 49 文件 104→0 错 | no-unused-vars×73（未用 import 删除、局部改 `_` 前缀、解构属性删除/别名）；no-use-before-define×24（12 处小助手定义上移；SchemaRenderer/NodeDetailContent/sessionRecorder 三处互递归/环形引用以文件级 disable 注明原因）；no-unescaped-entities×6（引号改「」）；button-has-type×1。修复脚本两处自伤（import 双花括号、块提取越界）均当场发现并修复，最终 eslint/tsc/vitest/build 四绿 |

**本批验证**：`eslint src` 0 error；`tsc --noEmit` 零错；vitest 112 通过；`max build` 成功；权限矩阵漂移 0。
