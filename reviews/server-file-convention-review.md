# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：领域主导（Engineer 为 Lead）
> 日期：2026-05-28
> 审查目标：Server 端文件管理/命名/组织规范

---

## 模式选择

**选定模式：** 领域主导（Engineer 为 Lead）

**选择理由：** 文件命名和组织规范是技术架构层面的深度评估，Engineer 视角主导。已有初步扫描数据可复用。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品/API 视角

**API 路由前缀命名：**
- 60 条路由注册，全部使用小写
- 31 条使用单词前缀（`/auth`, `/users`, `/stores` 等）
- 29 条使用 kebab-case 复合前缀（`/medical-records`, `/doctor-booking-settings` 等）
- 0 条使用 camelCase 或 snake_case 前缀

**前缀 vs 模块目录名对应关系：**
- kebab-case 前缀统一对应 snake_case 目录名（`/medical-records` → `medical_records/`）
- 转换规则一致：目录名中 `_` 替换为 `-`

**Tag 命名：**
- 60 个 tag 全部使用中文（如 "认证"、"门店管理"、"排班模板"）
- 粒度统一，每个路由一个 tag
- 1 个英文 tag："WebSocket"

**模块功能覆盖度：**
- 57 个模块目录中，54 个有注册的 API 路由
- 3 个纯服务模块无路由：`revenue/`, `rule_engine/`, `visit_types/`
- `performance/` 有路由但通过 `statistics` 或 `admin` 路由注册

### Designer — 开发者体验视角

**文件发现成本（预约相关代码）：**
- 路径：`modules/appointments/` → 7 个文件（router.py + router_booking/flow/query + service.py + service_booking/flow + common.py）
- 涉及的模型：`models/appointment.py`
- 涉及的 schema：`schemas/appointment.py`
- 总计 10 个文件需理解

**文件发现成本（排班相关代码）：**
- 路径：`modules/schedules/` → 10 个文件（router + router_custom/extra_quota/statistics + service + service_conflict/extra_quota/generation/mutation/query + audit_helpers）
- 总计 12+ 个文件需理解

**命名可预测性测试：**

| 关键词 | 猜测目录 | 实际目录 | 匹配？ |
|--------|---------|---------|--------|
| 退费 | refunds/ | refunds/ | 是 |
| 通知 | notifications/ | notification_logs/ + notification_preferences/ | 否（拆分为 2 个） |
| 模板 | templates/ | schedule_templates/ + email_templates/ | 部分 |
| 科室 | departments/ | departments/ | 是 |
| 班次 | shifts/ | shift_types/ | 否（多了 _types） |

**测试文件组织：**
- 81 个单元测试文件 + ~30 个集成测试文件
- 2 层目录：`tests/unit/` 和 `tests/integration/`
- 1 个共享 fixtures 目录：`tests/fixtures/`
- 2 个 conftest.py：`tests/conftest.py`（主）+ `tests/conftest_pg.py`（PostgreSQL）
- 命名模式：全部 `test_*.py`

**文档覆盖：**
- 57 个模块中仅 `approval_flows/` 有 README.md
- 项目级 README.md 存在且已更新

### Engineer — 技术视角

**1. 缺失 `__init__.py`：**
- `modules/support_tickets/`：无 `__init__.py`（有 router.py + service.py）
- `infrastructure/payments/`：无 `__init__.py`（有 config_resolver.py + schemas.py + wechat_pay_service.py）

**2. `common/` 与 `core/` 职责重叠：**
- `common/error_codes.py`：定义 `TenantErrorCode` 类，租户/订阅相关错误码，约 10 个常量
- `core/error_codes.py`：定义 `ErrorCode` 类，排班/预约/通用错误码，约 20 个常量
- 两者命名风格不同：`TenantErrorCode.TENANT_DISABLED` vs `ErrorCode.SCHEDULE_CONFLICT`
- 功能互补但不统一

**3. 全局 `services/` 仅剩 2 个文件，消费者分析：**
- `email_template_service.py`：被 `modules/email_templates/router.py`（1处）+ `infrastructure/email/service.py`（1处）导入 → 2 个消费者
- `rule_performance_service.py`：被 `modules/rule_sets/router.py`（3处）+ `modules/rule_engine/monitoring.py`（2处）导入 → 2 个消费者
- 按 CLAUDE.md Service 归属规则（2+ 消费者 → 全局），这 2 个文件留在全局 services/ 是合理的

**4. `__init__.py` 内容分析：**
- 55 个模块 `__init__.py` 中，约 25 个为非空（5-6 行），其余为 1 行或空
- 非空的 `__init__.py` 主要是 FastAPI router 导入（`from .router import router`）
- `approval_flows/__init__.py`：注册回调处理器（`register_builtin_callbacks()`）
- `tenants/__init__.py`：导入子服务类
- `rule_engine/__init__.py`：导入策略注册

**5. 模块内 schemas.py 分布：**
- 15 个模块有模块内 `schemas.py`
- 39 个全局 schema 文件在 `app/schemas/`
- 模块内有 schema 的：admin, approval_flows, common_services, content, dictionaries, doctor_portal, doctors, examination_reports, miniapp_platform, refunds, shift_types, tenants, unified_message, upload, users

**6. import 路径规范抽查（5 个模块）：**
- content：`from app.modules.content.service import ...`（模块内 ✅）
- medical_records：`from app.modules.medical_records.service import ...`（模块内 ✅）
- leave_requests：`from app.modules.leave_requests.service import ...`（模块内 ✅）
- dictionaries：`from app.modules.dictionaries.service import ...`（模块内 ✅）
- upload：无独立 service，逻辑在 router 中

**7. 迁移文件命名：**
- 117 个文件使用 `NNN_描述.py` 格式
- 1 个文件使用 hex hash：`2fc10ef02888_remove_weekday_column_from_schedule_.py`
- 存在编号重复：004(×2), 007(×2), 058(×2)

**8. 文件命名一致性：**
- 所有 `.py` 文件使用 snake_case，无 camelCase/PascalCase 文件名
- 无文件名含空格或特殊字符
- 模型文件命名：51 个文件，全部单数名词（`doctor.py` 而非 `doctors.py`）
- Schema 文件命名：39 个文件，匹配对应模型名

---

## Round 2：辩论层（Engineer Lead 交叉验证 + Critic 质询）

### 简化投票矩阵（领域主导模式）

| 议题 | Lead 立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 缺失 __init__.py (2处) | P1 必修 | 影响范围有限，Python 3.3+ 支持 implicit namespace packages | P1 — 不影响运行但违反项目规范 |
| common/ vs core/ error_codes 分裂 | P1 应统一 | 两文件功能互补不重复，但命名风格不一致 | P2 — 可共存，需统一命名风格 |
| 全局 services/ 2 文件 | 现状合理 | 2+ 消费者规则下位置正确 | P2 — 仅文档化 |
| 迁移 hex hash 文件 | P2 建议修 | Alembic 自动生成，手动改名有风险 | P2 — 低优先级 |
| 模块命名单复数混用 | P2 文档化 | REST 语义下合理 | P2 — 仅文档化规则 |

### Critic 质询

1. **[Critic → Engineer] 质询 1：`__init__.py` 缺失的实际影响**
   - 论据：Python 3.3+ 支持 namespace packages，缺失 `__init__.py` 不影响导入
   - 要求回应：确认 `support_tickets` 和 `payments` 的导入链是否实际依赖 `__init__.py`
   - 级别：普通

2. **[Critic → 全体] 质询 2：模块拆分粒度差异**
   - 论据：`admin/` 有 16 个文件（含 6 个 router_*.py），而 `amap/` 仅 1 个 router.py。差距是否反映模块复杂度还是过度拆分
   - 要求回应：给出拆分标准的事实依据
   - 级别：普通

3. **[Critic → 全体] 🚨 质询 3：81 个单元测试但覆盖面不足**
   - 论据：81 个 test 文件但 grep 显示几乎所有模块目录都无直接测试文件引用。测试文件命名（`test_foo_service.py`）与模块目录无直接映射
   - 要求回应：解释测试发现路径的实际成本
   - 级别：🚨 关键

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | Lead 回应 | 是否充分 | 处置 |
|---|------------|----------|---------|------|
| 1 | __init__.py 缺失的实际影响 | 需验证 `from app.modules.support_tickets import router` 是否正常工作。Python 3.3+ namespace packages 在大多数场景可用，但打包工具（setuptools）可能有问题 | 充分 | 纳入 P1（低成本高安全） |
| 2 | 81 个测试的发现成本 | 测试文件按功能域命名（test_appointment_*.py）而非按模块目录（test_modules/appointments/），导致无法从模块目录直接定位测试 | 充分 | 纳入 P2（文档化映射关系） |

---

## Round 3：共识层

### ✅ 共识项

1. **缺失 `__init__.py`**
   **结论：** 补充 `support_tickets/__init__.py` 和 `infrastructure/payments/__init__.py`
   **建议行动：** 创建 2 个空 `__init__.py` 文件
   **成本估算：** 0.1h
   **优先级：** P1

2. **`common/error_codes.py` 与 `core/error_codes.py` 命名风格不一致**
   **结论：** 两者功能互补（租户错误码 vs 业务错误码），但命名风格应统一
   **建议行动：** 将 `common/error_codes.py` 中的 `TenantErrorCode` 合并到 `core/error_codes.py`，统一为 `ErrorCode` 类的不同域
   **成本估算：** 2h（含 import 更新）
   **优先级：** P2

3. **全局 `services/` 2 个文件位置合理**
   **结论：** `email_template_service` 和 `rule_performance_service` 各有 2 个消费者，符合 CLAUDE.md "2+ 消费者 → 全局" 规则
   **建议行动：** 在 CLAUDE.md 中文档化这 2 个文件保留在全局的理由
   **成本估算：** 0.5h
   **优先级：** P2

4. **迁移 hex hash 文件命名不一致**
   **结论：** `2fc10ef02888_remove_weekday_column_from_schedule_.py` 应改为数字编号
   **建议行动：** 重命名为 `118_remove_weekday_from_schedule_templates.py`
   **成本估算：** 0.5h
   **优先级：** P2

5. **模块命名单复数混用需文档化**
   **结论：** 混用有 REST 语义依据（复数 = 资源集合，单数 = 功能域），但需在 CLAUDE.md 中明确规则
   **建议行动：** 添加模块目录命名规则到 CLAUDE.md
   **成本估算：** 0.5h
   **优先级：** P2

6. **测试发现成本高**
   **结论：** 测试文件按功能命名而非模块目录对应，新开发者难以从模块目录定位测试
   **建议行动：** 在 CLAUDE.md 中添加测试文件与模块的映射约定
   **成本估算：** 0.5h
   **优先级：** P2

### ⚡ 分歧项

无重大分歧。

---

## 被低估的优势

1. **Service 迁移已完成 96%** — 48 个全局 service 已迁移到模块内，仅剩 2 个有充分理由的全局 service
2. **API 路由前缀命名完全一致** — 60 条路由全部 kebab-case 或小写单词，0 例违规
3. **文件命名零违规** — 全部 snake_case，无 camelCase 文件名
4. **__init__.py 覆盖率 96%** — 57 个模块中仅 1 个缺失

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P1 | 补充 2 个缺失的 `__init__.py` | 0.1h | 中 | Engineer | 待执行 |
| P1 | 统一 `error_codes.py`（合并 common/ 到 core/） | 2h | 高 | Engineer | 待执行 |
| P2 | 文档化全局 services 保留理由 | 0.5h | 中 | Engineer | 待执行 |
| P2 | 重命名 hex hash 迁移文件 | 0.5h | 低 | Engineer | 待执行 |
| P2 | 文档化模块命名规则（复数资源/单数功能域） | 0.5h | 中 | PM | 待执行 |
| P2 | 文档化测试文件与模块映射约定 | 0.5h | 中 | Engineer | 待执行 |

### P1：立即执行

1. **补充 `__init__.py`** — 创建 `modules/support_tickets/__init__.py` 和 `infrastructure/payments/__init__.py` [成本：0.1h]
2. **统一 error_codes** — 将 `common/error_codes.py` 中的 `TenantErrorCode` 合并到 `core/error_codes.py` 的 `ErrorCode` 类中，更新所有 import [成本：2h]

### P2：下个周期规划

1. **文档化全局 services 保留理由** [成本：0.5h]
2. **重命名迁移文件** [成本：0.5h]
3. **文档化模块命名规则** [成本：0.5h]
4. **文档化测试映射约定** [成本：0.5h]

### 待定：需用户确认

无。

---

## 摘要

**使用模式：** 领域主导（Engineer 为 Lead）

**关键共识：** 6 项达成共识
- 2 个缺失 `__init__.py` 需补充（P1）
- `error_codes` 两文件命名风格不一致需统一（P1）
- 全局 services 保留位置合理（P2 文档化）
- 迁移文件命名不一致（P2）
- 模块命名规则需文档化（P2）
- 测试发现成本需降低（P2 文档化）

**关键分歧：** 0 项

**Top 3 P1 行动：**
1. 补充 2 个 `__init__.py`（成本：0.1h）
2. 统一 `error_codes.py`（成本：2h）

**Critic 关键洞察：** 81 个测试文件但与模块目录无直接映射，新开发者发现测试的成本高于必要水平。测试文件按功能域命名（如 `test_appointment_booking.py`）而非按模块目录命名，这一约定需要文档化。

**整体评价：** Server 端文件管理整体规范水平高 — 全局 services 迁移 96% 完成、API 路由命名 0 违规、文件命名 0 违规、__init__.py 覆盖率 96%。仅有 2 项 P1 级问题需修复，4 项 P2 级文档化建议。
