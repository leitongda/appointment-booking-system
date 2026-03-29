# 规则组管理功能 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-29
> 审查目标：admin 端规则组管理功能的逻辑流程、页面布局、文字描述、操作合理性，结合 Server 端接口

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 评审范围聚焦在单一功能模块（规则组设置），非全项目评审；用户需要可操作的修改意见，集中调度可快速收敛且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**功能完成度：**

- 列表页：已实现（`rule-sets.tsx`）
- 新增/编辑：已实现，共用同一表单组件（`rule-set-form.tsx`），包含 6 个 Tab（基础信息、时间口径、时间窗配置、预约策略、签到策略、容量策略）
- 删除：已实现，单条删除需输入 CONFIRM 确认
- 详情：已实现，通过抽屉（Drawer）而非独立路由
- 导入/导出：已实现（`ImportExport` 组件）
- 批量启用/禁用/删除：已实现
- 实时预览：已实现（右侧面板/抽屉）
- 规则效果预览：已实现（Modal）
- 预设模板：已实现（4 个预设：标准门诊、专家门诊、体检预约、急诊）
- 引导流程：已实现（首次访问显示 OnboardingCard）
- 完成度指示器：已实现（CoreCompletionCard）

**前后端接口对应关系：**

- 前端 API 14 个方法，后端 17 个端点（3 个性能监控接口前端未封装）
- 所有业务接口前后端完全对应
- 后端额外端点：GET /performance、GET /slow-queries、DELETE /performance/metrics（仅 super_admin）

**业务逻辑流程：**

- 创建：前端表单 → POST /rule-sets → RuleSetService.create() → 创建主记录 + 关联数据（班次类型、时间窗、3 个策略）
- 更新：PUT /rule-sets/{id} → 更新主记录 + 重建班次类型关联（删除旧的、创建新的）
- 规则组与班次类型：多对多（通过 RuleSetShiftType 中间表）
- 规则组与预约：一对多（appointments.rule_set_id → rule_sets.id）
- 规则组不直接关联门店/医生/科室，通过 ShiftType 间接关联

**文字描述与文案：**

- 列表页标题："规则组列表"
- 表单页标题：新增"新增规则组"，编辑"编辑规则组"
- 表格列标题：规则名称、优先级、班次类型、时间来源、比较精度、状态、创建时间、操作
- 表单标签约 30+ 个，多数带有 tooltip 提示文字
- 成功/失败消息使用简短中文
- 确认弹窗：删除需输入 CONFIRM，批量操作使用 Modal.confirm
- 预设模板描述完整
- 引导卡片包含 3 个步骤说明

**文案不一致事实：**

- 列表页标题"规则组列表"，表格列标题用"规则名称"（而非"规则组名称"）
- 批量启用/禁用的确认弹窗内容中标点使用不一致（有些地方有逗号，有些用句号）
- 表单中"启用状态"标签 vs 列表页"状态"列标题

### Designer — 用户视角

**页面结构与布局：**

- 列表页：PageContainer > ProTable + RuleSetPreviewDrawer
- 表单页（桌面端）：左右分栏布局（ResizableDivider），左侧表单 6 个 Tab + 右侧实时预览面板（Affix 固定）
- 表单页（移动端/平板端）：垂直布局 + 抽屉预览
- 表单页包含：OnboardingCard（首次）、Alert（非首次快速配置提示）、ProForm、FooterToolbar、RulePreviewModal、PresetModal
- 总计使用约 20+ 个 Ant Design/ProComponents 组件

**交互模式：**

- Modal 弹窗 9 处（删除确认、批量操作、预设选择、规则预览、导入）
- Popconfirm 2 处（启用/禁用切换、删除时间窗）
- Loading 状态：列表页内置 ProTable loading，表单页使用 Card loading prop，批量操作无独立 loading
- 空状态：时间窗空列表使用 Empty 组件 + "添加时间窗"按钮
- 表单验证：约 20+ 个字段有验证规则（required、min/max 范围）

**表单设计：**

- 6 个 Tab，约 33 个表单字段
- 字段类型：文本输入(3)、数字输入(8)、下拉选择(10)、开关(8)、多行文本(2)、自定义组件(OffsetInput)
- 布局：Row + Col 栅格，2~4 列
- 条件显示字段：waitlistMaxSize/waitlistPromotePolicy（候补启用时）、overbookingMax（超额启用时）、failTag（失败策略为 ALLOW_WITH_TAG 时）
- 默认值完整定义在 constants/rule-set.ts 中

**列表页设计：**

- 8 列表格，操作列 220px 宽
- 筛选条件仅 enabled（启用/禁用）一个
- 分页：默认 10 条，支持切换页大小和快速跳转
- 批量操作按钮在选中行后显示
- 非超级管理员：编辑/启用/禁用按钮灰色不可点击

**导航流程：**

- 列表 → 新增：history.push('/operations/system/rule-sets/create')
- 列表 → 编辑：history.push(`/operations/system/rule-sets/${id}/edit`)
- 表单保存成功 → 列表页
- 取消 → history.back()

**操作按钮统计：**

- 列表页 9 个按钮/操作
- 表单页 7 个按钮（含底部工具栏）
- 时间窗配置 3 个操作按钮

### Engineer — 技术视角

**数据模型：**

- 7 个模型表：RuleSet、ShiftType、RuleSetShiftType（中间表）、RuleWindow、RuleBookingPolicy、RuleCheckinPolicy、RuleCapacityPolicy
- RuleSet 17 个字段（含审计字段 4 个），默认值完整
- 关系：RuleSet 一对多 RuleWindow（CASCADE）、一对一 3 个 Policy 表
- 索引：rule_sets(enabled, priority)、rule_windows(rule_set_id, enabled)、rule_set_shift_types(shift_type_id)

**API 端点：**

- 11 个规则组 CRUD 端点 + 3 个时间窗端点 + 3 个策略端点 = 17 个
- 权限分级：普通管理员可查看/预览，超级管理员可 CRUD/启用禁用/管理时间窗和策略
- 预览端点 POST /rule-sets/preview：检查动作是否在允许时间窗口内

**Schema 定义：**

- 所有 Response Schema 使用 alias_generator=to_camel（snake_case → camelCase）
- RuleSetCreate：17 个字段，shift_type_ids 为必填（min_length=1）
- RuleSetUpdate：所有字段 Optional
- RuleWindowCreate：10 个字段

**业务逻辑（Service 层）：**

- RuleSetService 使用 Mixin 组合：QueryMixin + MutationMixin + PolicyMixin
- create()：创建主记录 + 关联数据（班次类型、时间窗、3 个策略）
- update()：更新主记录 + 重建班次类型关联（先删旧的后建新的）
- delete()：级联删除（CASCADE）
- 规则引擎：RuleEngineService，通过 shift_type_id 获取适用的规则组（enabled=True，按 priority 排序取第一个）

**前端 API 封装：**

- 14 个方法，与后端业务端点完全对应
- TypeScript 类型定义完整（10 个类型）
- 前后端字段通过 camelCase 转换保持一致

**多租户处理：**

- RuleSet.tenant_id：ForeignKey("tenants.id"), nullable=True, 有索引
- Service 层查询（get_list/get_by_id）未显式添加 tenant_id 过滤条件
- 导入功能显式使用 tenant_id 参数
- 认证层（get_current_admin）验证 admin.tenant_id 与请求上下文租户一致

---

## Round 2：辩论层

### Team Lead 交叉验证

经过对三方事实的交叉验证，以下为关键发现：

1. **前后端更新接口严重不匹配**：前端表单页将所有数据（基础信息 + 时间窗 + 3 个策略）通过单一 PUT 请求提交，但后端 `update()` 方法仅更新基本字段和班次关联，**完全忽略时间窗和策略数据**。后端设计了独立的时间窗/策略更新端点，但前端未调用。
2. **租户隔离存在数据泄露风险**：Service 层查询无任何 tenant_id 过滤，中间件仅负责识别租户而非注入过滤条件。理论上跨租户数据可被查询。
3. **RuleWindow name 字段前后端不一致**：前端 `RuleWindowConfig.tsx` 允许用户设置时间窗名称，但数据库模型和 Schema 都无 name 字段，用户配置的名称被静默丢弃。
4. **规则优先级竞争无任何提示**：规则引擎 `get_applicable_rule_set()` 按 priority 取第一个，被覆盖的规则组无任何警告。列表页无"生效状态"指示。

### Critic 质询

1. [Critic → Engineer] 🚨 关键 质询 1：租户隔离仅识别不过滤
   - 论据：`service_query.py` 无 tenant_id 引用。中间件设置 ContextVar，但 Service 层从未调用 `get_current_tenant_id()` 过滤查询。租户 A 的 super_admin 理论上可查询租户 B 的规则组。
   - 要求回应：Engineer
   - 裁决回应：经验证，Service 层确实缺少 tenant_id 过滤。这不是架构设计选择，而是**安全遗漏**。应在 get_list/get_by_id 中添加 tenant_id 过滤。

2. [Critic → PM/Designer] 🚨 关键 质询 2：规则优先级竞争无提示
   - 论据：`time_windows.py:27` 使用 `.order_by(RuleSet.priority.asc()).limit(1)` 取唯一规则组。用户无法知道哪些规则组正在生效、哪些被覆盖。
   - 要求回应：PM、Designer
   - 裁决回应：确认是重要业务风险。列表页需要"生效状态"指示器。

3. [Critic → Engineer] 🚨 关键 质询 3：时间窗 name 字段缺失
   - 论据：前端 `RuleWindowConfig.tsx` 有 name 输入（行 190-197），但数据库模型（`rule_set.py:85-112`）和 Schema（`rule_set.py:143-154`）均无 name 字段。
   - 要求回应：Engineer
   - 裁决回应：经验证，数据库模型和 Schema 确实都无 name 字段。前端时间窗名称输入是死字段。

4. [Critic → Engineer] 🚨 关键 质询 4：update() 不更新时间窗和策略，编辑修改被静默丢弃
   - 论据：`service_mutation.py:110-154` 的 update() 仅更新基本字段和班次关联。RuleSetUpdate Schema 也无 windows/policies 字段。前端将所有数据通过单一 PUT 提交，后端静默忽略。
   - 要求回应：Engineer
   - 裁决回应：经验证，这是**严重功能缺陷**。前端 handleSubmit 发送完整数据，后端 update() 完全忽略 windows 和 policies。

5. [Critic → PM] 质询 5：预设模板业务合理性未审查
   - 论据：急诊模板超额 999 但总容量 0（不限）语义矛盾；体检取消时间窗-172800秒（2天前）可能过严。
   - 要求回应：PM
   - 裁决回应：需业务方确认各预设参数合理性。

6. [Critic → Designer] 质询 6：完成度指示器定义不合理
   - 论据：CORE_REQUIRED_FIELDS 不含 windows 和策略，但无时间窗的规则组实际无效。
   - 要求回应：PM、Designer
   - 裁决回应：确认指示器可能误导用户，需扩展核心配置定义。

7. [Critic → Designer/Engineer] 质询 7：批量操作 loading 问题定位不准
   - 论据：Modal.confirm 的 onOk 返回 Promise 时 Ant Design 自动显示 loading。实际问题应为失败时 Modal 立即关闭无法重试。
   - 要求回应：Designer、Engineer
   - 裁决回应：Critic 正确，需修正问题描述方向。

### 独到发现

1. **前后端更新架构严重不匹配**：前端单表单提交全部数据 vs 后端分散式更新接口（主记录 + 独立时间窗/策略端点），导致编辑模式下时间窗和策略修改被静默丢弃
2. **规则组优先级竞争是隐藏的业务风险**：系统仅使用优先级最高的规则组，其他被关联但优先级低的规则组完全不生效，但无任何用户提示
3. **引导体系与实际复杂度不匹配**：3 步引导暗示简单配置，实际 6 个 Tab 33+ 字段，完成度指示器只追踪 8 个基础字段

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 裁决回应 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | 租户隔离仅识别不过滤 | 经验证为安全遗漏，非架构选择 | 是 | 升级为 P0 安全修复 |
| 2 | 规则优先级竞争无提示 | 确认为重要业务风险 | 是 | 纳入 P0 行动 |
| 3 | 时间窗 name 前后端不一致 | 确认为 bug | 是 | 纳入 P0 行动 |
| 4 | update() 静默丢弃时间窗/策略修改 | 确认为严重功能缺陷 | 是 | 升级为 P0 功能修复 |

---

## Round 3：共识层

> Critic 发现了 4 个关键质询（超出上限 3 个，但均经代码验证确认，全部纳入裁决）

### ✅ 共识项（共 19 项）

#### P0：立即执行

1. **[安全] Service 层添加 tenant_id 过滤**（成本：4h，负责：Engineer）
   - **结论：** Critic 验证确认：service_query.py 无任何 tenant_id 引用，中间件仅设置 ContextVar 不注入过滤。跨租户数据可被查询，是**安全遗漏**而非架构选择。
   - **行动：** 在 get_list/get_by_id 中调用 `get_current_tenant_id()` 添加 tenant_id 过滤条件

2. **[功能缺陷] 修复 update() 不更新时间窗和策略**（成本：6h，负责：Engineer）
   - **结论：** 前端 handleSubmit 将 windows/policies 一起提交，后端 update() 仅更新基本字段和班次关联，**静默丢弃时间窗和策略修改**。这是严重功能缺陷。
   - **行动方案 A（推荐）：** 扩展 RuleSetUpdate Schema 支持 windows/policies，在 update() 中同步更新关联数据
   - **行动方案 B：** 前端改为调用分散式更新接口（主记录 PUT + 独立策略 PUT）
   - 建议采用方案 A，保持前端提交逻辑不变，后端补全 update 逻辑

3. **[Bug] 修复时间窗 name 字段前后端不一致**（成本：2h，负责：Engineer）
   - **结论：** 前端 RuleWindowConfig.tsx 有 name 输入，但数据库模型和 Schema 都无 name 字段
   - **行动：** 在数据库模型、Schema（Create/Update/Response）中添加 name 字段，或删除前端 name 输入（二选一，建议前者）

4. **[业务风险] 列表页增加"生效状态"指示**（成本：3h，负责：Designer + Engineer）
   - **结论：** 规则引擎按 priority 取唯一规则组，被覆盖的规则组完全不生效但无任何提示
   - **行动：** 列表页增加"生效中"/"已被覆盖"状态标签，需要后端提供冲突检测接口或前端批量判断

5. **列表页缺少班次类型筛选**（成本：2h，负责：Designer + Engineer）
   - **结论：** 后端已支持 shift_type_id 过滤参数，前端未暴露此功能
   - **行动：** 列表页搜索栏增加"班次类型"下拉筛选

6. **前端路由权限拦截**（成本：2h，负责：Engineer）
   - **结论：** 非 super_admin 可通过 URL 直接访问编辑页面
   - **行动：** 前端路由层增加 canSuperAdmin 权限检查

7. **统一列标题"规则组名称"**（成本：0.5h，负责：Designer）
   - **结论：** 与页面标题和表单标签不一致

8. **删除 rule-set-form.tsx.backup 文件**（成本：0.5h，负责：Engineer）
   - **结论：** 备份文件残留在代码仓库中，应使用 Git 管理版本

#### P1：本轮迭代

9. **时间口径 Tab 说明优化**（成本：3h，负责：Designer + PM）
   - **行动：** 添加顶部说明卡片 + 将 tooltip 改为始终可见的 help 文本

10. **批量操作失败处理优化**（成本：2h，负责：Engineer）
    - **结论：** Critic 纠正：问题不是缺少 loading（Ant Design 自动处理），而是失败时 Modal 立即关闭用户无法重试
    - **行动：** 修改 onOk 回调，失败时阻止 Modal 关闭

11. **编辑模式增加预设模板入口**（成本：3h，负责：Designer + Engineer）

12. **引导体系重新设计**（成本：4h，负责：PM + Designer）
    - **结论：** Critic 指出引导与实际复杂度严重不匹配，不是"增加第 4 步"能解决的。完成度指示器定义也不合理（不含时间窗和策略）
    - **行动：** (1) 扩展引导步骤覆盖策略配置 (2) 扩展 CORE_REQUIRED_FIELDS 包含至少 1 个时间窗 (3) 添加保存前校验（无时间窗时警告）

13. **保存后行为优化**（成本：2h，负责：Engineer）
    - **行动：** 创建成功跳转编辑页，编辑成功停留在当前页

14. **统一删除确认弹窗文案**（成本：1h，负责：PM + Designer）

15. **编辑页加载失败优雅降级**（成本：2h，负责：Engineer）

16. **规则组与排班规则关系说明**（成本：1.5h，负责：PM）

17. **预设模板参数业务审查**（成本：1h，负责：PM）
    - **结论：** Critic 指出急诊模板超额 999 + 总容量 0 语义矛盾，体检取消时间窗-2天可能过严
    - **行动：** 与业务方确认各预设模板参数合理性

#### P2：下个周期

18. **列表页统计信息**（成本：1h，负责：Designer）
19. **隐藏低价值列（时间来源/比较精度）**（成本：1h，负责：Designer）

### ⚡ 分歧项

1. **议题：时间口径 Tab 是否应该默认折叠/高级模式**
   **裁决：** 保持平铺但增加顶部说明卡片 + 字段下方 help 文本
   **决策依据：** 可发现性优于简洁性

---

## 被低估的优势

1. **完成度指示器设计**：虽然定义需扩展，但概念本身有价值
2. **实时预览面板**：表单右侧可视化反馈，降低理解门槛
3. **预设模板系统**：覆盖常见场景，显著降低首次配置门槛
4. **埋点追踪完善**：关键行为均有埋点，有利于后续优化决策
5. **删除确认需输入 CONFIRM 文本**：防止误删的安全措施

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 |
|--------|------|------|------|------|
| **P0** | **Service 层添加 tenant_id 过滤（安全修复）** | **4h** | **极高** | **Engineer** |
| **P0** | **修复 update() 不更新时间窗和策略** | **6h** | **极高** | **Engineer** |
| **P0** | **修复时间窗 name 前后端不一致** | **2h** | **高** | **Engineer** |
| **P0** | 列表页增加"生效状态"指示 | 3h | 高 | Designer + Engineer |
| **P0** | 列表页增加班次类型筛选 | 2h | 高 | Designer + Engineer |
| **P0** | 前端路由权限拦截 | 2h | 高 | Engineer |
| **P0** | 统一列标题"规则组名称" | 0.5h | 高 | Designer |
| **P0** | 删除备份文件 | 0.5h | 高 | Engineer |
| P1 | 时间口径 Tab 说明优化 | 3h | 高 | Designer + PM |
| P1 | 批量操作失败处理优化 | 2h | 高 | Engineer |
| P1 | 编辑模式增加预设模板入口 | 3h | 中 | Designer + Engineer |
| P1 | 引导体系重新设计 | 4h | 高 | PM + Designer |
| P1 | 保存后行为优化 | 2h | 高 | Engineer |
| P1 | 统一删除确认弹窗文案 | 1h | 中 | PM + Designer |
| P1 | 编辑页加载失败优雅降级 | 2h | 中 | Engineer |
| P1 | 规则组与排班规则关系说明 | 1.5h | 中 | PM |
| P1 | 预设模板参数业务审查 | 1h | 中 | PM |
| P2 | 列表页统计信息 | 1h | 低 | Designer |
| P2 | 隐藏低价值列 | 1h | 低 | Designer |

**P0 总计成本：20h** | **P1 总计成本：18.5h** | **P2 总计成本：2h**

### 待定：需用户确认

（无 — 所有关键质询已逐条回应）

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 19 项达成共识（P0: 8 项, P1: 9 项, P2: 2 项）

**关键分歧：** 1 项（时间口径 Tab 折叠 vs 平铺，已裁决：保持平铺+增加说明）

**Top 5 P0 行动（按紧迫度排序）：**
1. Service 层添加 tenant_id 过滤（4h）— 跨租户数据泄露风险
2. 修复 update() 不更新时间窗和策略（6h）— 编辑修改被静默丢弃
3. 修复时间窗 name 字段前后端不一致（2h）— 用户配置的名称丢失
4. 列表页增加"生效状态"指示（3h）— 规则优先级竞争无提示
5. 前端路由权限拦截 + 班次类型筛选 + 文案统一 + 清理备份（5h）

**Critic 关键洞察：**
- Critic 将 Round 1 的"架构选择"判断推翻为"安全遗漏"，经代码验证确认
- Critic 发现了 Round 1 三方都遗漏的严重功能缺陷（update 静默丢弃数据）
- Critic 纠正了"批量操作缺少 loading"的问题定位（实际问题为失败时 Modal 关闭无法重试）

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无 | | | |
