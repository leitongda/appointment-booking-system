# appointment-booking-system — Server 端结构优化计划审查

> 协作模式：领域主导（Engineer 主导）
> 日期：2026-05-28
> 审查目标：Server 端结构优化计划 (`.claude/plans/server-server-project-name-scalable-shell.md`)

---

## 模式选择

**选定模式：** 领域主导（Engineer 主导）

**选择理由：** 技术架构计划的深度审查，Engineer 视角需要最深（enum 迁移风险、import 循环、模块拆分正确性），PM 和 Designer 提供迁移影响范围和开发者体验辅助视角。

---

## Round 1：事实层

### PM — 产品视角

**迁移影响范围：**
- Phase 1 涉及 ~60 个文件（44 个 to_camel + 8 组 enum + constants）
- Phase 2 涉及 56 个模块（大部分只需确认，无需改动）
- Phase 3 涉及 2 个遗留文件（email_template_service.py, rule_performance_service.py）

**执行顺序依赖：**
- Phase 1 内部 to_camel 和 enum 迁移无依赖，可并行
- Phase 2 的 Tier 1-4 无跨 Tier 依赖，各 Tier 内部可并行
- Phase 3 依赖 Phase 2 完成后再执行

**回滚策略事实：**
- 计划中未描述回滚方案
- enum 迁移使用 re-export 兼容但未指定兼容期时长
- 无 feature flag 控制新旧路径切换

**CI/CD 影响：**
- 5 个 GitHub Actions 工作流受影响（test.yml 直接相关）
- 无 pre-commit hooks
- 迁移过程中 lint（Ruff + flake8）可能产生新 import 警告

### Designer — 用户视角

**目录可发现性：**
- 当前 app/ 下 14 个顶层目录，计划新增 enums/ + constants/ 后变为 16 个
- `app/common/`（认证工具）vs `app/enums/`（枚举）vs `app/constants/`（常量）vs `app/utils/`（工具函数）的边界需要明确文档
- RoleType 在 `app/common/auth_types.py:10`，计划迁到 `app/enums/user.py`，两者职责边界不明确

**Import 路径一致性：**
- 当前 `from app.common.xxx` 259 次, `from app.core.xxx` 95 次, `from app.models.xxx` 869 次, `from app.schemas.xxx` 195 次
- 计划新增 `from app.enums.xxx` 和 `from app.constants.xxx` 两种变体
- to_camel 当前 0 处正确引用 `from app.schemas.response import to_camel`，44 处本地重复定义

**命名冲突风险：**
- `enums/common.py` 与 `modules/*/common.py` 同名但不同层级，无直接冲突
- `enums/appointment.py` 与 `modules/appointments/common.py` 职责需划分（enum vs 基类 vs 常量）
- `enums/user.py` 中 RoleType 从 `common/auth_types.py` 迁出后，该文件仍保留 AccountInfo 等数据类

### Engineer — 技术视角

**1. Enum 迁移事实：**
- 8 组重复 enum（models/ 和 schemas/ 各一份）
- 12+ 个仅 schemas/ 中的 enum
- core/ 中 EventType, WSMessageType；common/ 中 RoleType；tasks/ 中 ReminderLevel
- unified_message/schemas.py 有 7 个 enum
- 模块内 Dict 常量：APPOINTMENT_STATUS, CHECKIN_METHOD
- NotificationChannel 在两个文件中重复；EventType 在 core/ 和 schemas/ 中重复

**2. to_camel 统一事实：**
- 权威定义：schemas/response.py:7-10
- 44 处重复全部实现一致（无变体）
- 0 个文件已正确引用

**3. Service 组合模式：**
- Mixin 读写分离：doctors, stores, rule_sets, schedule_templates, waitlist
- Mixin 领域分离：appointments, schedules, consultation_fees
- 跨模块依赖：AppointmentService → MessageServiceCompat, RuleEngineService, SettingsService

**4. 计划遗漏：**
- APPOINTMENT_STATUS dict vs enum 选择未明确
- Pydantic ConfigDict 重复（40+ 文件）未涉及
- EventType、WSMessageType、ReminderLevel、unified_message 7 个 enum 未列入

---

## Round 2：辩论层

### 简化投票矩阵（领域主导模式）

| 议题 | 裁决者(Engineer)立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| Enum 迁移范围不完整 | 确认遗漏 +10-15% 工作量 | 🚨 调研范围不足 | 补充扫描步骤，扩大 Phase 1 范围 |
| APPOINTMENT_STATUS 应转 IntEnum | **反驳**：保持 dict | — | 保持 dict，不转 enum |
| to_camel 统一 | +1 但需注意依赖瓶颈 | 🚨 可能成为依赖瓶颈 | 统一但仍允许 modules 内部使用 |
| BaseSchema 基类 | 新增建议（计划未涉及） | — | 纳入 Phase 1.5 |
| Phase 1 可并行 | 部分反驳：Git 冲突风险 | — | 拆子阶段串行执行 |
| 回滚方案 | 反驳 PM：风险极高 | — | 增加回滚方案 |
| enums vs constants 边界 | +1 边界需文档化 | 边界不清 | 在 CLAUDE.md 定义分类指南 |
| 无循环 import 风险 | +1 静态分析无风险 | 🚨 无运行时验证 | 增加运行时验证步骤 |
| Phase 2 "只需确认" | — | 过于乐观 | Tier 1-2 改为"抽查"而非逐个确认 |
| 架构优势被忽略 | — | 三方都忽略 | 补充保留策略说明 |

### 独到发现

1. **Dict 常量与 Enum 的本质区别**：APPOINTMENT_STATUS 的值是 Integer（数据库映射），100% 使用 dict 访问模式，转为 IntEnum 无收益却有风险。CHECKIN_METHOD 的值是字符串，更符合 StrEnum 语义。
2. **to_camel 重复可能是有意设计**：当前 44 处本地定义实现了模块独立性，任何文件可以独立运行不依赖 response.py。统一后牺牲了这种独立性换取 DRY。
3. **跨模块 Service 依赖需要分级处理**：MessageServiceCompat 已有兼容层（低风险）、SettingsService 是配置读取（中风险）、RuleEngineService 是业务逻辑耦合（高风险，暂不动）。

### Critic 质询

1. [Critic → 全体] "无循环 import 风险"结论证据不充分——仅有静态分析，无运行时验证
   - 级别：🚨 关键
2. [Critic → 全体] to_camel 集中化可能成为依赖瓶颈——44 个文件依赖 response.py
   - 级别：🚨 关键
3. [Critic → 全体] 计划遗漏 7+ 个 enum——调研范围不足
   - 级别：🚨 关键
4. [Critic → 全体] enums vs constants 边界不清——开发者无法判断放哪
   - 级别：普通
5. [Critic → 全体] Phase 2 "大部分只需确认"过于乐观
   - 级别：普通
6. [Critic → 全体] 三方忽略了当前架构优势
   - 级别：普通
7. [Critic → 全体] SQLAlchemy Column(Enum(MyEnum)) 可能需要特殊处理
   - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 回应摘要 | 回应是否充分 | 处置 |
|---|------------|----------|------------|------|
| 1 | "无循环 import 风险"证据不充分 | Engineer 补充：Python import 机制下，enums/ 不依赖任何模块，单向依赖不存在循环条件。但同意增加运行时 pytest 验证。 | 是 | 纳入计划：Phase 1 后增加 import 验证测试 |
| 2 | to_camel 集中化依赖瓶颈 | Engineer 承认风险但认为可控：response.py 是纯函数无副作用，变更概率极低。Critic 提出的"44 个文件同时依赖"实际上是当前 869 个文件依赖 models/ 的子集。 | 是 | 纳入计划：统一后增加 BaseSchema 基类降低直接依赖 |
| 3 | 遗漏 7+ 个 enum | Engineer 确认遗漏，补充了完整清单：unified_message 7 个 + EventType + WSMessageType + ReminderLevel。 | 是 | 纳入计划：Phase 1 前增加全量 enum 扫描 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：** Enum 迁移范围需扩大
   **结论：** 计划遗漏了 unified_message/schemas.py 7 个 enum、core/ 2 个 enum、tasks/ 1 个 enum。Phase 1 需先执行全量 enum 扫描。
   **建议行动：** 在 Phase 1 前增加 `grep -rn "class.*Enum" app/` 全量扫描步骤，确保无遗漏。
   **成本估算：** 0.5h（扫描 + 列表）
   **优先级：** P0

2. **议题：** APPOINTMENT_STATUS 保持 dict 格式
   **结论：** 数据库 Integer 映射 + 100% dict 访问模式 + API 数字值契约，转为 IntEnum 风险大于收益。保持 dict，迁到 `constants/appointment.py`。
   **建议行动：** 修改计划——APPOINTMENT_STATUS 不转 enum，移入 constants/。CHECKIN_METHOD 可转 StrEnum。
   **成本估算：** 0h（保持现状）
   **优先级：** P0

3. **议题：** 新增 BaseSchema 基类
   **结论：** 40+ 文件重复 ConfigDict(alias_generator=to_camel, ...)，应创建 `schemas/base.py` 统一。
   **建议行动：** 创建 BaseSchema 基类，作为 Phase 1.5 补充任务。
   **成本估算：** 2h（创建基类 + 更新 40 个文件）
   **优先级：** P1

4. **议题：** Phase 1 拆子阶段串行执行
   **结论：** enum 迁移和 to_camel 统一虽无技术依赖，但会修改相同文件产生 Git 冲突。
   **建议行动：** Phase 1.1 创建 enums/ + constants/ → Phase 1.2 迁移 enum → Phase 1.3 统一 to_camel → Phase 1.4 清理。
   **成本估算：** 0h（调整执行顺序）
   **优先级：** P0

5. **议题：** 增加回滚方案
   **结论：** 当前无回滚方案、无兼容期、无 feature flag。对于渐进式重构风险过高。
   **建议行动：** 定义 2 周兼容期（re-export 保留），Phase 1 后运行全量测试验证。
   **成本估算：** 1h（编写兼容层 + 测试）
   **优先级：** P0

6. **议题：** enums/common.py 重命名避免混淆
   **结论：** `enums/common.py` 与 `modules/*/common.py` 同名可能误导开发者。
   **建议行动：** 重命名为 `enums/general.py` 或按领域拆分（不使用 common.py）。
   **成本估算：** 0h（命名调整）
   **优先级：** P1

7. **议题：** 在 CLAUDE.md 中定义目录边界
   **结论：** enums/constants/common/utils 的边界需要文档化。
   **建议行动：** 补充分类指南到 CLAUDE.md。
   **成本估算：** 0.5h
   **优先级：** P1

### ⚡ 分歧项

1. **议题：** to_camel 本地定义是否是有意设计
   **各方立场：**
   - Critic：44 处本地定义可能是为了模块独立性，不应贸然统一
   - Engineer：统一后 response.py 成为依赖点，但纯函数风险可控
   - Designer：统一后 IDE 跳转更方便
   **裁决：** 统一。理由——response.py 是纯函数无副作用，44 处重复的维护成本（如果 to_camel 逻辑需要调整）远大于集中化的风险。同时创建 BaseSchema 基类作为主要使用入口，减少对 to_camel 的直接依赖。
   **决策依据：** DRY 原则 + BaseSchema 基类降低直接依赖

2. **议题：** Phase 2 Tier 1-2 的处理方式
   **各方立场：**
   - PM：大部分"只需确认"
   - Critic：过于乐观
   **裁决：** Tier 1（12 个仅 router）确实无需改动。Tier 2（22 个 router + service）改为"抽查 5-8 个确认模式合规"，不需要逐个检查。
   **决策依据：** 成本收益平衡——22 个模块全部检查的 ROI 不如抽查 + 测试覆盖

3. **议题：** 跨模块 Service 依赖的处理时机
   **各方立场：**
   - Engineer：需要在 Phase 2 中评估
   - PM：Phase 3 依赖 Phase 2
   **裁决：** 跨模块依赖不在本次重构范围内。当前 compat 模式工作良好，强行标准化可能引入风险。仅记录为已知技术债务。
   **决策依据：** 最小变更原则 + compat 层已隔离风险

---

## 被低估的优势

1. **modules/ 域聚合架构**：56 个模块的 router + service 内聚设计，使业务修改范围可控，是项目的核心架构优势。
2. **Mixin 服务组合模式**：DoctorService(QueryMixin, MutationMixin) 模式比传统继承更灵活，已被多个模块验证有效。
3. **compat 兼容层设计**：跨模块依赖通过 compat 层隔离，支持渐进式迁移。
4. **to_camel 本地定义的容错性**：即使 response.py 出问题，各模块仍可独立工作（但维护成本过高，仍建议统一）。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 全量 enum 扫描 + 补充遗漏清单 | 0.5h | 消除遗漏 | Engineer | 待执行 |
| P0 | APPOINTMENT_STATUS 保持 dict，不转 IntEnum | 0h | 避免数据库兼容性问题 | Engineer | 待执行 |
| P0 | Phase 1 拆子阶段（1.1→1.2→1.3→1.4） | 0h | 避免 Git 冲突 | Engineer | 待执行 |
| P0 | 增加 2 周兼容期 + 全量测试验证 | 1h | 回滚安全网 | Engineer | 待执行 |
| P1 | 创建 BaseSchema 基类 + 更新 40 文件 | 2h | 消除 ConfigDict 重复 | Engineer | 待执行 |
| P1 | enums/common.py 重命名为 enums/general.py | 0h | 避免命名混淆 | Engineer | 待执行 |
| P1 | CLAUDE.md 补充 enums/constants/common/utils 边界指南 | 0.5h | 开发者可发现性 | Designer | 待执行 |
| P1 | Phase 2 Tier 1-2 改为抽查模式 | 0h | 降低执行成本 | PM | 待执行 |
| P2 | 跨模块 Service 依赖记录为技术债务 | 0.5h | 长期规划 | Engineer | 待执行 |
| P2 | pre-commit hook 检查 import 路径规范 | 1h | 预防性质量 | Engineer | 待执行 |
| 待定 | RoleType 是否从 common/auth_types.py 迁到 enums/user.py | 0.5h | 需确认边界 | 全体 | 需用户确认 |

### P0：立即执行

1. **全量 enum 扫描**：`grep -rn "class.*Enum" app/ --include="*.py"` 覆盖 core/, common/, tasks/, modules/ 子目录，补充遗漏清单
2. **APPOINTMENT_STATUS 决策**：保持 dict 格式，迁到 `constants/appointment.py`；CHECKIN_METHOD 可转 StrEnum
3. **Phase 1 子阶段化**：1.1 创建目录 → 1.2 enum 迁移 → 1.3 to_camel 统一 → 1.4 清理
4. **兼容期定义**：re-export 保留 2 周，Phase 1 后 `pytest tests/ -x` 全量验证

### P1：本轮迭代

1. **BaseSchema 基类**：创建 `schemas/base.py`，消除 40+ 处 ConfigDict 重复
2. **命名优化**：`enums/common.py` → 按领域拆分，不使用 common.py
3. **边界文档**：CLAUDE.md 增加 enums/constants/common/utils 分类指南
4. **Phase 2 策略调整**：Tier 1-2 改为抽查，不逐个检查

### P2：下个周期

1. **技术债务记录**：跨模块 Service 依赖图 + 优先级评估
2. **pre-commit hook**：import 路径规范检查

### 待定：需用户确认

1. **RoleType 迁移**：从 `common/auth_types.py` 迁到 `enums/user.py`？auth_types.py 中还有 AccountInfo 等数据类，迁移后该文件职责变化

---

## 摘要

**使用模式：** 领域主导（Engineer 主导）

**关键共识：**
- 7 项达成共识

**关键分歧：**
- 3 项需要权衡裁决（to_camel 统一策略、Phase 2 执行方式、跨模块依赖处理时机）

**Top 3 P0 行动：**
1. 全量 enum 扫描补充遗漏（0.5h）
2. APPOINTMENT_STATUS 保持 dict 不转 IntEnum（0h）
3. Phase 1 拆子阶段 + 增加兼容期（1h）

**Critic 关键洞察：**
- 计划的调研范围不够（遗漏 10+ 个 enum），建议先全量扫描再制定迁移清单
- to_camel 44 处重复可能是刻意设计（模块独立性），统一需权衡维护成本 vs 集中化风险
- 当前架构（域聚合 + Mixin 组合 + compat 隔离）是有意的设计取舍，不是"需要修复的问题"

---

## 附录：对原计划的修订建议

| 原计划章节 | 修订内容 |
|-----------|---------|
| Phase 1 enum 迁移 | 扩大范围：增加 unified_message 7 个 + core 2 个 + tasks 1 个 |
| Phase 1 APPOINTMENT_STATUS | 从"转 enum"改为"保持 dict，移入 constants/" |
| Phase 1 | 新增 Phase 1.5：创建 BaseSchema 基类 |
| Phase 1 执行顺序 | 拆为 1.1→1.2→1.3→1.4 子阶段串行执行 |
| Phase 1 | 新增：2 周兼容期 + 全量测试验证 |
| Phase 2 Tier 1-2 | 从"逐个确认"改为"抽查 5-8 个" |
| Phase 2 | 移除跨模块 Service 依赖处理（记录为技术债务） |
| enums/common.py | 重命名，不使用 common.py |
| 全文 | 补充 CLAUDE.md 边界分类指南 |
