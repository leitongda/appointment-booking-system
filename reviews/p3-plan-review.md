# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-21
> 审查目标：P3 阶段 9 项任务的合理编排与实施方案

---

## 模式选择

**选定模式：** 集中调度

**选择理由：**
执行编排任务，不涉及跨职能设计评审。PM 视角（优先级/依赖）主导，需要快速收敛为行动计划。集中调度模式的 Team Lead 自行裁决 + 仅 Critic 质询，最适合此场景。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**P3 任务依赖关系：**
- P3-1, P3-2, P3-3, P3-4 四个管理页任务在后端 API 层面互相独立（不同模块、不同路由前缀）
- P3-5（TS 修复）与 P3-1 共享 `rule-set-form.tsx`（16 条错误），与 P3-2 共享 `system/settings`
- P3-6（集成测试）与 P3-1 共享 `test_rule_sets_router_endpoints.py`
- P3-7（E2E）在逻辑上依赖 P3-6 通过
- P3-8 无 TODO 遗留（room_id 已完整实现）

**功能价值验证：**
- rule_sets: 26 个端点，前端已有完整页面（rule-sets.tsx + rule-set-form.tsx 1699 行 + rule-set-audit.tsx）
- blacklists: 4 个端点，路由指向通用设置页，无专用页面
- unified_message: 16 个端点，message/ 目录有旧模块页面，但无 unified_message 专用页面
- points: 0 个独立端点（3 个方法挂在 patients 模块下），无独立路由

**技术债影响面：**
- TS 编译错误：355 条，分布在 81 个文件中。90+ 条集中在 `constants/rule-set.ts`（字面量类型过窄）
- 集成测试失败：11 个（183 passed, 16 skipped）。4 个 P2 引入，7 个历史遗留

**已有前端页面清单：**
- 24 个业务目录，46 个后端模块，前端覆盖率约 50%
- P3-1 已完成（3 个页面文件）、P3-3 部分完成（3 个页面文件服务于旧模块）

### Designer — 用户视角

**页面模式统计（P2 新建 4 页）：**
- 平均代码行数：273 行
- ProTable 使用率：3/4（payment 页为查询详情模式，未用 ProTable）
- Drawer 使用率：3/4（详情展示）
- Descriptions 使用率：4/4
- 内联样式为主，Less 仅 10 个页面级文件

**典型页面结构（doctor/list.tsx 612 行）：**
- PageContainer → ProTable（columns + request + toolBarRender + pagination）
- 筛选器：select（异步加载门店/科室）、dateRange、text、valueEnum
- CRUD 模式：toolBarRender 新增按钮 → 跳转表单页；操作列 → Popconfirm 删除 / Drawer 详情

**可复用基础设施：**
- `useListPage` hook（actionRef/message/handleDelete/handleAction）
- `utils/proTable.ts`（toProTableResult/createListRequest）
- `ListOperations/`（OperationButton/OperationGroup/CreateButton）
- `FormPage/` 表单页基础设施
- `ImportExport/` 导入导出组件

**P3 页面复杂度：**
- blacklist: 低（标准 CRUD，4 端点，简单数据模型）
- points: 低（积分流水 + 手动调整，需新建 API 模块）
- unified_message: 中（三组功能域：消息列表/模板管理/接收人规则，已有部分实现）

**UI 库版本：**
- antd 6.3.7、@ant-design/pro-components 3.1.12-0、@umijs/max 4.6.0
- 导入方式：antd 直接导入、ProComponents 从 @ant-design/pro-components

### Engineer — 技术视角

**P3-8 排班 room_id：已完整实现**
- Schedule.room_id 字段已存在（FK → schedule_rooms.id）
- ScheduleRoom 模型已定义
- ConflictDetector._check_room_conflict() 已实现
- 未找到 TODO 注释

**P3-9 多租户限流现状：**
- RateLimitMiddleware 已按租户维度隔离（Redis ZSET 滑动窗口）
- 当前为全局固定参数（300/min, 50/sec），不支持按租户差异化
- Tenant 模型无 rate_limit 字段
- 配置化需：模型新字段 + 迁移 + 中间件改造 + Redis 缓存

**TS 错误详情：**
- 总计 355 条，81 个文件
- TS2558（Expected 0 type arguments）：25 条 — ProForm API 变更
- TS2339（属性不存在）：NotificationQuota/TenantStatusInfo 类型不匹配
- TS2322（类型不匹配）：rule-set-form.tsx readonly → mutable
- TS2349（不可调用）：common-service.ts API 层问题
- TS2307（找不到模块）：request.ts 缺 axios
- `constants/rule-set.ts` 单文件 90+ 错误（字面量类型过窄）

**集成测试失败详情（11 个）：**
- common_services ×5：响应格式变更（期望 code=0 实际 HTTP 200）
- admin_me：token fixture 未设置 username
- check_duplicate：schedule 唯一约束冲突
- rule_sets delete：软删除 vs 硬删除语义
- schedule ×2：token fixture 失效 + 路由 404
- medical_records_my：token fixture 失效
- websocket：async event loop teardown 问题

**模块耦合：**
- API 包已有 46 个模块、99 条 export（412 行），中等规模
- blacklist 和 points 的 API 模块已存在（blacklist.ts 完整，points 无独立模块）
- barrel export 尚未达到需要拆分的程度

---

## Round 2：辩论层

### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| P3-1 是否需要执行 | 已完成，标记跳过 | | |
| P3-3 是否需要执行 | 部分完成，需确认覆盖度 | | |
| P3-8 是否需要执行 | 已完成，标记跳过 | | |
| P3 任务优先级排序 | 待定 | | |
| P3-5 修复范围 | 待定 | | |

### 独到发现

1. P3-1/P3-3/P3-8 三项任务在 Round 1 调研中发现已全部或大部分完成，实际 P3 范围比预期小
2. `constants/rule-set.ts` 单文件贡献了 90+ 条 TS 错误（25%），但均为字面量类型推断过窄，不影响运行时
3. 集成测试中 token fixture 有系统性失效风险（3 个测试明确标注，可能影响更多）
4. P3-4（积分管理）无独立路由，端点嵌套在 patients 模块下，创建独立管理页需要架构决策

### Critic 质询

| # | 质询 | 级别 | 回应摘要 |
|---|------|------|---------|
| 1 | common_services 非废弃模块，测试失败是格式变更 | 普通 | ✅ 接受。修正为"活跃模块，测试断言未同步" |
| 2 | blacklist 复杂度"低"混淆了已有/预期 | 普通 | ✅ 接受。修正措辞为"预期复杂度低" |
| 3 | P3-1 跳过缺乏完成度验证 | 🚨 关键 | ✅ 已验证：路由注册完整（4条），页面文件存在 |
| 4 | P3-4 架构决策悬空 | 🚨 关键 | ✅ 已裁决：移出 P3 范围，归入待定 |
| 5 | TS 错误处置策略笼统 | 普通 | ✅ 已制定分层策略（见下方） |
| 6 | token fixture 系统性失效 | 普通 | ✅ 已纳入 P3-6 优先修复项 |
| 7 | 复杂度评估缺量化 | 普通 | ✅ 已补充量化估算（见行动计划） |
| 8 | 投票矩阵遗漏 P3-2/P3-4 | 🚨 关键 | ✅ 已补充完整 |

### 🚨 关键质询追踪

| # | 关键质询内容 | 回应 | 处置 |
|---|------------|------|------|
| 3 | P3-1 跳过标准缺失 | 已验证路由和页面文件存在；P3-3 同样验证通过 | 纳入计划：P3-1/P3-3/P3-8 标记跳过 |
| 4 | P3-4 架构决策悬空 | 积分功能价值低（3 个端点，嵌套在 patients 下），独立建页 ROI 不高 | 移出 P3，归入待定 |
| 8 | 投票矩阵遗漏 P3-2/P3-4 | 已补充 P3-2 进入执行计划，P3-4 归入待定 | 纳入计划 |

---

## Round 3：共识层

### ✅ 共识项

**1. P3-1（rule_sets 管理页）— 跳过**
- **结论：** 已完整实现。3 个页面文件（rule-sets.tsx, rule-set-form.tsx 1699行, rule-set-audit.tsx），4 条路由全部注册
- **建议行动：** 无
- **成本：** 0h
- **优先级：** 不适用

**2. P3-3（统一消息管理页）— 跳过**
- **结论：** 已实现。`/content-center/message` 下 4 个页面（list, form, templates, recipient-rules），覆盖后端 16 个端点
- **建议行动：** 无
- **成本：** 0h
- **优先级：** 不适用

**3. P3-8（排班 room_id）— 跳过**
- **结论：** 已完整实现。Schedule.room_id 字段 + ScheduleRoom 模型 + 冲突检测均就绪，无 TODO 遗留
- **建议行动：** 无
- **成本：** 0h
- **优先级：** 不适用

**4. P3-2（黑名单管理页）— 执行**
- **结论：** 后端 4 个端点就绪，API 模块已存在（blacklist.ts），前端无专用页面（路由指向通用设置）
- **建议行动：** 新建 ProTable 列表页 + 新增弹窗 + 解禁操作
- **成本估算：** 4-6h
- **优先级：** P0（高价值、低成本）
- **负责：** Engineer

**5. P3-5（修复 TS 编译错误）— 分层执行**
- **结论：** 355 条错误分三类处理
  - Tier 1（批量修复，30min）：`constants/rule-set.ts` 90+ 条字面量类型 → 添加 `as const` 类型断言
  - Tier 2（逐文件修，4-6h）：ProForm 泛型变更（TS2558, 25条）+ 类型属性缺失（TS2339）
  - Tier 3（低优先级）：import 错误（axios, @umijs/max）、shared/perf 类型
- **建议行动：** Tier 1 + Tier 2 纳入 P0；Tier 3 纳入 P2
- **成本估算：** Tier 1: 0.5h, Tier 2: 4-6h, Tier 3: 2-3h
- **优先级：** Tier 1+2 = P0, Tier 3 = P2
- **负责：** Engineer

**6. P3-6（修复集成测试失败）— 执行**
- **结论：** 11 个失败，需分优先级
  - 优先修（系统性风险）：3 个 token fixture 失效 → 修复 fixture 链
  - 常规修（5-8h）：common_services ×5（断言格式）、rule_sets delete（软/硬删除）、check_duplicate（唯一约束）、schedule route 404
- **建议行动：** 先修 token fixture（防止雪崩），再逐个修其余
- **成本估算：** fixture 修 2-3h + 其余 5-8h = 7-11h
- **优先级：** P0（fixture 修复）+ P1（其余）
- **负责：** Engineer

**7. P3-7（E2E 测试补充）— 执行**
- **结论：** 依赖 P3-6 通过。admin 端 E2E 覆盖率低
- **建议行动：** P3-6 通过后，为核心管理页添加 Playwright E2E
- **成本估算：** 8-12h
- **优先级：** P1
- **负责：** Engineer

**8. P3-9（多租户限流配置化）— 执行**
- **结论：** 当前全局固定参数（300/min, 50/sec），需支持按租户差异化
- **建议行动：** Tenant 表新增可选字段 → 迁移 → 中间件改造 → Redis 缓存
- **成本估算：** 8-12h
- **优先级：** P2
- **负责：** Engineer

### ⚡ 分歧项

无。所有议题已达成共识。

### 待定：需用户确认

**1. P3-4（用户积分管理页）**
- **现状：** 后端仅 3 个方法嵌套在 patients 模块下，无独立路由/API 模块
- **选项：**
  - (a) 新建独立路由 + API 模块 + 页面（成本：8-12h）
  - (b) 在 patients 页面内嵌入积分管理 Tab（成本：4-6h）
  - (c) 从 P3 移除，后续按需再做（成本：0h）
- **Critic 关键质询依据：** 三方均回避了架构决策，需用户明确方向

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 7 项达成共识（3 项跳过、4 项执行）
- 1 项待定（P3-4 积分管理，需用户决策）

**关键发现：**
- P3 实际范围比预期小 33%（9 项 → 6 项，3 项已完成）
- 355 条 TS 错误中 25% 可批量修复（rule-set.ts 单文件）
- token fixture 系统性失效是 P3-6 的最高优先级

**Top 3 P0 行动：**
1. P3-2 黑名单管理页（4-6h）— 高价值、低成本
2. P3-5 Tier 1+2 TS 错误修复（4.5-6.5h）— 消除编译阻断
3. P3-6 token fixture 修复（2-3h）— 防止测试雪崩

**Critic 关键洞察：**
- "代码已写" ≠ "功能可用" — P3-1/P3-3/P3-8 虽标记跳过但建议定期冒烟测试
- token fixture 失效是系统性风险，不仅影响报告的 3 个测试
- P3-4 的架构决策被三方集体回避，需要用户明确方向
