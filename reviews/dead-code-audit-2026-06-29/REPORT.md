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
