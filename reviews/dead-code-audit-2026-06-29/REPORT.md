# 本地代码冗余 / 死代码审计报告

> 只读审计 · 未修改/删除任何代码 · 第 1 轮全量 fan-out + 第 2/3 轮定向 delta（approval_flows 变更区）· 已收敛终止（连续两轮无新高置信度发现 + 达 3 轮上限）

## 仓库概况

- **技术栈**：前端 Umi 4 / React 18 / TS（admin·doctor·patient-h5·temp-registration·website）；小程序 Taro 4（patient-miniapp·mini-appointment-miniapp·miniapp-instance）；后端 FastAPI / SQLAlchemy 2.x async / PostgreSQL
- **包管理器**：pnpm 10.27 + Turbo 2（lockfile: pnpm-lock.yaml）
- **应用/包数量**：9 个 app + 3 个 package（api·shared·codegen）
- **主要入口**：各 app `.umirc.ts`/`config/config.ts`；Taro `app.config.ts`；后端 `apps/server/app/main.py` + 路由注册 `app/api/v1/__init__.py`（84 模块）
- **路由/微前端机制**：Umi 配置式 + 约定式路由（admin 已按业务域拆 config/routes/）；无微前端
- **审计范围与排除项**：apps/* + packages/* 源码；排除 node_modules/dist/build/.umi/.turbo/coverage/__pycache__/生成代码

## 总结

| 维度 | 数量 |
|------|------|
| 高置信度可清理项（P0） | 8 |
| 中置信度待确认项（P1） | 7 |
| 重复实现候选（P2） | 6 |
| 架构依赖风险（P3） | 4 循环 + 3 跨层 + 3 上帝模块 |
| 预计可减少 | ~28KB 前端死代码 + 1 死目录 + 1 死 schema 文件 + 7 死 API 模块 + 5 死依赖 + **~250MB 本地噪声** |

## P0：高置信度可清理

| 类型 | 目标 | 路径 | 证据 | 风险 | 建议动作 |
|------|------|------|------|------|----------|
| 死目录 | `app/services/` 整目录 | `apps/server/app/services/{__init__,email_template_service,rule_performance_service}.py,storage/` | `grep 'app\.services' apps/server/app`=0；真实消费方均从 `app.modules.*` 导入；仅 3 处测试 patch 旧路径 | 低 | 删整目录；测试 patch 重定向到 `app.modules.rule_engine.rule_performance_service` |
| 死文件 | `schemas/error.py` 全文 | `apps/server/app/schemas/error.py` | 全仓零 import；与 `response.py` 同名冲突 | 低 | 删除，统一用 `response.ErrorResponse` |
| 死导出 | `schemas/admin.py` 8 个登录类 | `apps/server/app/schemas/admin.py` | 8 类 import=0，同名类在 `modules/admin/schemas.py` 实际被消费 | 低 | 删这 8 类，保留 `AdminListResponse` |
| 前端死文件 | admin 3 整死文件 + 1 近死 hook | `apps/admin/src/hooks/useFormDraft.ts`、`utils/{errorHandler,formHelper}.ts`、`hooks/useResponsive.ts` | 各自 grep 仅自身命中 | 低 | 删 3 文件(~28KB)；useResponsive 删 5 个死 hook |
| 死 API 模块 | packages/api 零消费模块 | `packages/api/src/modules/{export,contact,account}.ts`、`utils/{performance,retry}.ts`、`config.ts`、`hooks/useCountdown` | `exportApi`/`contactApi`/`accountApi`/`withRetry`/`API_CONFIG`/`useCountdown` 在 apps 命中=0 | 低 | 删模块 + barrel 行（contact 需确认页面是否直连后端） |
| 死依赖 | 5 个零引用依赖 | admin:`webpack-bundle-analyzer`；根:`cli-progress`；temp-registration:`@tanstack/react-query`/`zustand`/`antd-mobile-icons` | import 命中=0，非脚本使用 | 低 | `pnpm remove` |
| 本地噪声 | `var/` (52MB 未忽略) | `var/` | `git ls-files var/`=0；.gitignore 仅忽略 `apps/server/var/` | 低 | 本地删除 + .gitignore 增 `/var/` |
| 误入库产物 | 压缩包/IDE 缓存被跟踪 | `apps/mini-appointment-miniapp.tar.gz`、`.VSCodeCounter/`(9)、`.kilo`/`.kilocode`/`.opencode` 跟踪配置 | `git ls-files` 确认被跟踪 | 低 | `git rm --cached` + .gitignore |

## P1：需要运行时或业务确认

| 类型 | 目标 | 路径 | 潜在动态入口 | 验证方法 | 建议动作 |
|------|------|------|--------------|----------|----------|
| 死包 | `packages/codegen` | `packages/codegen/` | CLI 形态，可能被后端 spawn | grep `subprocess/Popen 'codegen'` in apps/server | 未被 spawn 则移除，否则文档化 |
| 功能重叠 app | `mini-appointment-miniapp` | `apps/mini-appointment-miniapp/` | 根 package.json 仍引用，可能独立发布 | 确认发布需求 | 保留则接入共享层；否则归并 patient-miniapp |
| 孤立页面 | patient-h5 症状导诊 | `apps/patient-h5/src/pages/guide/index.tsx` | 后端可能下发 URL | 确认后端是否下发 /guide | 补路由+入口，或删除 |
| 孤立页面 | admin 字典管理 | `apps/admin/src/pages/system/dictionaries/` | 动态菜单 | 确认废弃 | 补菜单+权限键，或删除 |
| 孤立页面 | miniapp lowcode | `apps/patient-miniapp/src/pages/lowcode/index.tsx` | 后端下发跳转（小程序须在 pages 声明） | 确认可达性 | 加入 pages 数组或移除 |
| 泄漏嫌疑 | sessionRecorder 无停止钩子 | `apps/admin/src/utils/sessionRecorder.ts` | 本应在卸载时调用 | 审查录制生命周期 | 挂卸载逻辑或确认设计 |
| 死 schema 簇 | ~39 全局 + 22 模块级零引用 | `apps/server/app/schemas/{point_log,notification_log,user}.py` 等 | `__init__.py` re-export 掩盖 | 核对 re-export 消费 | 删除或移除 __init__ 导出 |

## P2：重复实现与可复用机会

| 类别 | 重复位置 | 相似证据 | 推荐收敛方案 | 预期收益 |
|------|----------|----------|--------------|----------|
| 后端 schema boilerplate | 39 文件 ~350 处 | 手写 `alias_generator=to_camel`，`BaseSchema` 已封装等价配置（CLAUDE.md 已规定） | 继承 `BaseSchema` | 高（消除 ~350 行 + 杜绝漏配 bug） |
| 小程序自造 utils | `mini-appointment-miniapp/utils/{date,validator,auth,request}.ts` ~600 行 | 重写 validate/format/request，绕过 shared+api | 接入 `shared/miniapp` + `createTaroAdapter` | 高（统一校验，避免身份证校验码不一致 bug） |
| web request 三份 | `apps/{admin,doctor,patient-h5}/utils/request.ts` | 同构骨架（拦截器+401+租户暂停） | `packages/api` 抽 `createWebInterceptors` 工厂 | 中 |
| ProColumns 散落 | admin appointment/waitlist/medical-record 等 10+ 页 | patientName/patientPhone/doctorName/status 列逐页复制 | `utils/proTable.ts` presets | 中 |
| 状态映射分叉 | shared constants vs admin constants vs 8 页面内联 | `APPOINTMENT_STATUS_MAP` 文案/键集分叉 | 统一引用 `@hospital/shared` | 中 |
| 重复 schema 定义 | ChangePasswordRequest(4 处)/BatchDeleteRequest(5-6 处)/Notification 系列 | 同名 BaseModel 各自内联 | `app/schemas/common.py` 单一基类 | 中 |
| **[Δ第2轮新增] 监听器配置归一化重复** | `approval_flows/listener_service.py:84-95` `_normalize_config` 与 `approval_flows/service_definitions.py:24-46` `_normalize_listener` | 两处独立实现完全相同的 6 项映射（bodyTemplate→body_template / titleTemplate / contentTemplate / userIds / targetIds→user_ids / callbackName→callback_action） | 抽到 `approval_flows/listener_normalizer.py` 单一来源 | 中（防"保存归一化"与"触发归一化"行为漂移） |

## P3：依赖与架构问题

| 问题 | 涉及模块 | 证据 | 风险 | 修复建议 |
|------|----------|------|------|----------|
| **隐式循环依赖（前端唯一硬伤）** | `packages/shared/miniapp/wechatAuth.ts` → `@hospital/api` | 运行时 import userApi，package.json 未声明，靠 hoisting 运行 | 高（pnpm 配置变化即崩） | 网络调用上移到 apps 层，或用依赖注入 |
| infrastructure 反向依赖业务层（6 处） | email/notifications/image/quota → modules 业务 | 模块级 import `app.modules.*` | 中 | infra 接收 DTO/回调，modules 主动调用 |
| 3 对后端软循环 | appointments↔waitlist、approval_flows↔leave_requests、payments↔refunds | 均延迟 import 规避 | 中 | 抽共享 service / 引入回调接口 / 事件驱动 |
| router 绕过 service | ≥10 模块 router 直接 `select().execute()` | grep router 内 SQL | 中 | 强制 router→service→models |
| 密码策略错置 | `tenants/password_policy.py` 被 4 模块跨域引用 | codegraph 确认 | 中 | 迁 `app/common/password_policy.py` |
| 上帝服务 | `schedules/service_mutation.py` 1623 行、`unified_message/service.py` 974 行 | 行数+扇入扇出 | 中 | 按子操作/channel 拆分 |
| 版本漂移 | antd v6/v5、icons v6/v5、pro-components v3/v2、react v19/v18、@typescript-eslint 5/8 | package.json | 中 | 文档化决策 / 锁版本 / 对齐 lint |

## 建议整改顺序

1. **先清 P0 高置信度、无动态入口的死代码**：`app/services/` 整目录、`schemas/error.py`、admin 3 死文件、packages/api 7 死模块、5 死依赖；根目录噪声本地删除 + gitignore。
2. **再用测试/构建/页面冒烟验证 P1**：codegen 是否被 spawn、3 个孤立页面是否后端下发、sessionRecorder 泄漏。
3. **最后处理 P2 重复实现与 P3 跨模块依赖**，避免一次性大重构：优先 BaseSchema 统一（机械重构收益最大）和 wechatAuth 隐式循环（前端唯一硬伤）。

## 删除前验证清单

- [ ] 类型检查（前端 tsc / 后端 mypy 或 import 检查）
- [ ] lint（`pnpm lint` + `ruff`）
- [ ] 单元测试（后端 `pytest`，前端 `pnpm test`）
- [ ] 构建（`pnpm build` 受影响 app）
- [ ] 核心路由访问（admin/patient-h5/doctor 关键页面）
- [ ] 小程序加载（patient-miniapp 三个包）
- [ ] 关键权限菜单（access.ts 权限键）
- [ ] 关键业务流程冒烟（预约挂号、支付、退款、审批、通知）

---

## 配套产物

- `dead-code-candidates.json` — 机器可读候选列表
- `dependency-audit.json` — 依赖审计结果
- `architecture-dependency-summary.md` — 模块依赖与循环依赖摘要

---

# 执行与调查日志（2026-06-30）

## 已执行清理（P0，全部验证通过）

| 分片 | 动作 | 验证 |
|------|------|------|
| Shard1 后端 | 删 `app/services/` 整目录；3 处 stale patch 重定向到 `app.modules.rule_engine.rule_performance_service.get_current_tenant_id`；删 `schemas/error.py`；`schemas/admin.py` 移除 8 个零引用类（保留 AdminListResponse） | test_cache_isolation.py 13 passed ✓ |
| Shard2 packages/api | 删 `export.ts`/`contact.ts`/`config.ts` + barrel 清理 | tsc 无错 ✓ |
| Shard3 admin | 删 `useFormDraft`/`errorHandler`/`formHelper`；`useResponsive` 移除 5 死 hook | 残留引用=0 ✓ |
| Shard4 依赖+卫生 | 移除 5 死依赖；删 `var/`(52MB)；`git rm --cached` 27 个误入库文件；.gitignore 补 5 条 | 变更范围干净 ✓ |

**安全护栏救回 4 项误判**：`account/useCountdown/performance/retry` 在 packages/api 内部有活跃消费者（useEmailBinding、request.ts、doctor.ts、admin.ts），正确跳过。

## 已执行架构修复（P3）

**wechatAuth 隐式循环依赖 —— 已修复并验证** ✓
- `packages/shared/src/miniapp/wechatAuth.ts` 移除运行时 `import { userApi } from '@hospital/api'`，`getProfile` 改为注入参数（依赖反转，与 ImageUpload 的 onUpload 范式一致），仅保留 `import type`。
- 6 个调用点（patient-miniapp LoginPopup/profile + miniapp-instance 4 个 Profile shell）传 `userApi.getProfile`；LoginPopup 补 userApi import。
- 验证：shared 仅余 type import（运行时循环断开），packages/shared tsc 无错。

## 调查结论（P1/P2 复核）

| 项 | 原判定 | 复核结论 | 处置 |
|----|--------|----------|------|
| `packages/codegen` | P1 死包 | **误判** — 被 `lowcode/codegen_service.py` subprocess 调用（cli-wrapper.js/dist） | **从死代码清单移除** |
| sessionRecorder 泄漏 | P1 嫌疑 | **误判** — `init` 已注册 beforeunload/pagehide/visibilitychange 兜底 flush，MAX_QUEUE_SIZE=500 防堆积；stop/forceFlush 是公开 API 非该调未调 | **无需修复** |
| BaseSchema 批量替换 | P2 高收益机械重构 | **误判** — schedule.py 等文件请求 schema 用 2 字段 ConfigDict、响应 schema 用 4 字段，是**刻意差异**；盲转会改变序列化行为 | **降级为设计重构**，需先引分层基类，**禁止盲批量** |
| patient-h5 `/guide` | P1 孤立页 | 确认 config 式路由无自动挂载 + 无内部跳转；后端 seed 的 `/pages/guide/index` 是小程序路径，与此无关 | **需产品确认**：删 or 补路由 |
| admin `dictionaries` | P1 孤立页 | 后端 `/dicts`/`/dict-options` 已就绪，前端页未挂菜单 = 半成品 | **需产品决策**：挂菜单 or 删页 |
| patient-miniapp `lowcode` | P1 孤立页 | Taro 须在 app.config pages 声明才能跳转 | **需确认后端是否下发**，是则补 pages |
| mini-appointment-miniapp | P1 重叠 app | 确认 4 页、零引用 @hospital/api/shared、完全独立 | **需产品决策**：保持独立 or 接入共享层 |

## Round 3 执行 + 紧急修复（2026-06-30，workflow 8-agent 并行）

### 已执行（验证通过）
| 项 | 动作 | 验证 |
|----|------|------|
| E1 监听器归一化 | 新建 `approval_flows/listener_normalizer.py`，`_normalize_config`/`_normalize_listener` 改为薄包装 | 70 tests passed，6 项行为一致性核对通过 |
| E2 admin 字典页挂载 | `config/routes/system.ts` 加 dictionaries 路由组 + `access.ts` 加 `canDictionary` | 路由/权限/跳转路径三处对齐，结构平衡 |
| E3 miniapp lowcode 可达 | `app.config.ts` pages 数组加 `pages/lowcode/index` | Taro 配置合法，6 页全部命中文件 |
| **紧急 P0：image 包破损修复** | workflow P4 调查发现 `infrastructure/image/__init__.py` 导出已删函数 → `import` 直接 ImportError（图片上传功能在分支上已坏）。修：`__init__.py` 删 stale 导出；`upload/router.py` 改为就地读 `SettingsService.get_by_category("image")` + 构造 `ImageProcessor`（依赖反转） | import 链恢复，44 upload/image tests passed |
| P4 infrastructure 反向耦合 | 上述修复后，infrastructure → modules 的 6 处 live 反向 import **全部清零**（5 处分支已做、image 收尾本轮完成） | grep live 反向 import = 0 |

### 已产出精确方案（5 份，待审批执行）
| 方案 | 风险 | 行为变化 | 核心做法 |
|------|------|----------|----------|
| **P1 payments↔refunds 循环** | **低** | **无** | 循环根因是一个 6 行纯函数 `_generate_out_trade_no` 错放在 PaymentService 类上。抽到 `payment_ordering.py` 模块级函数，两端 import，refunds 不再实例化 PaymentService。交叉点 B（payments→refunds 单向编排）保留 lazy import。4 文件。**最该先做。** |
| P2 approval_flows↔leave_requests 循环 | 中 | 无（注册时机变） | DIP：引擎定义 Protocol 回调接口，业务回调迁出引擎包到各业务模块自注册。引擎不再 import 业务 service。~9 文件。 |
| P3 appointments↔waitlist 循环 | 中 | **有（同步→异步）** | 事件驱动：appointments 取消发 Celery 事件，waitlist 监听递补。递补变异步（增一个调度周期延迟），需 PR 标注。7 文件。 |
| P5 request.ts 三份收敛 | 中 | 无（逐端如实参数化） | packages/api 抽 `createWebInterceptors()` 工厂，三端瘦身调用，调用点零改动。5 文件。 |

## Round 4 执行（2026-06-30，workflow 4-agent 并行架构重构）

| 方案 | 风险 | 结果 | 验证 |
|------|------|------|------|
| **P1 payments↔refunds 循环** | 低 | **done** | 抽 `payment_ordering.py` 纯函数；77 tests pass；顶层 import 双向 OK，不再 lazy import |
| **P2 approval_flows↔leave_requests 循环** | 中 | **done** | DIP：业务回调迁出引擎、业务侧自注册；89 tests pass；引擎零业务 import；两种 import 顺序无错 |
| **P3 appointments↔waitlist 循环** | 中 | **done** | 事件驱动：Celery task 异步递补；P3 自身 8 用例全绿；lint-imports 7 契约全守、core→modules 边切断 |
| **P5 request.ts 三份收敛** | 中 | **done** | `createWebInterceptors()` 工厂；packages/api + 三端 tsc 全 exit 0；零 UI 依赖；调用点零改动 |

**P3 行为变化（已标注，需 PR 说明）**：候补递补从"取消同 HTTP 响应内同步"改为"Celery 异步触发"（延迟约一个调度周期）；Celery worker 必须运行否则递补不发生。失败可见性从 cancel 调用栈 logger.warning 移至 task logger.error。`send_task` 按名投递避免 core→modules 静态依赖（保 importlinter）。

**P3 发现的附带技术修正**：任务描述要求"sync db session"，但 `WaitlistService.auto_promote` 是 async，agent 改用 `async_session_maker + loop.run_until_complete` 异步桥接（同 notification_task 范式）——功能正确性必要修正，已注明。

### 新发现的遗留测试债（非本轮引入，建议单独修）
P3 验证时暴露 7 个 pre-existing 失败（已核实非本轮改动所致）：
- 5 个 cancel 测试：`pytest.raises(ValueError)` 但 cancel() 抛 `BusinessError`（异常类型历史漂移）
- 2 个 waitlist add 测试（`service_mutation.py`）：同类 ValueError/BusinessError 不匹配

## Round 5 执行（2026-06-30，workflow 3-agent 并行收尾）

| Shard | 结果 | 验证 |
|-------|------|------|
| **S1 遗留测试修复** | done | test_appointment_cancel.py + test_waitlist.py：**34 passed / 0 failed**（7 个 ValueError→BusinessError 失败全修）。仅改测试，未碰生产；其余仍用 ValueError 的测试（生产确实抛 ValueError）正确保留 |
| **S2 ProColumns presets** | done | 新建 `admin/src/utils/columnPresets.tsx`（5 个列工厂 + overrides），改造 5 页（appointment/list、medical-record、waitlist、follow-up/tasks、follow-up/records）；admin tsc exit 0。跳过有据（queue 用 antd ColumnsType、detail 是 Descriptions、状态列各页字典不同不抹平） |
| **S3 重复 schema 收敛** | partial（护栏生效） | 新建 `schemas/common.py`（BatchDeleteRequest/SortOrderItem/SortOrderRequest），合并 cms/content 两模块；165 tests pass。**正确跳过**：ChangePasswordRequest（4 处校验严重不齐，强合并会改 400→422 错误码）、contacts/approval_flows BatchDeleteRequest（基类+错误消息差异）、StoreInfo（序列化机制不同） |

## 仍待处理（需你决策/单独排期）

> 至此所有可安全自动执行的清理项已完成。剩余项要么需产品决策、要么需设计级重构、要么有实质行为差异需逐项人工裁定：

1. **S3 跳过的重复 schema（需逐项裁定）**：ChangePasswordRequest 4 处校验不齐（doctors 版无 schema 校验、auth 版无 max_length、错误码 400 vs 422）—— 需先定"统一密码策略"再合并；contacts/approval_flows BatchDeleteRequest、StoreInfo 同理。
2. **产品决策**：A1 patient-h5 `/guide` 孤立页（删 or 补路由）、A4 mini-appointment-miniapp（独立 / 接入 / 废弃）。
3. **BaseSchema 统一（设计重构）**：已证实盲转不安全（请求/响应 schema 刻意用 2 字段 vs 4 字段 ConfigDict）。正确做法是先引 `BaseRequestSchema`（2 字段）/保留 `BaseSchema`（4 字段）分层基类，再逐类按其当前 ConfigDict 精确匹配转换。
4. **上帝服务拆分**：schedules/service_mutation.py（1623 行）、unified_message/service.py（974 行）—— 大重构，建议有明确功能触发点再做。
