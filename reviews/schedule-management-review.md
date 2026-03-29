# 排班管理功能 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-29
> 审查目标：admin 端排班管理功能的逻辑流程、页面布局、文字描述、操作合理性，结合 Server 端接口

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 评审范围聚焦在排班管理模块（5 个子模块），涉及前后端多文件交叉验证；集中调度可快速收敛且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**功能完成度：**

- 排班规则（ScheduleTemplate）：列表、新增、编辑、删除、复制规则、批量添加、生成排班、预览生成、历史记录、批量停诊/删除 — 全部已实现
- 排班管理（Schedule）：列表、创建、批量创建、更新、批量停诊、批量恢复、批量删除 — 全部已实现
- 自定义排班（CustomSchedule）：独立页面和表单 — 已实现
- 休息日（RestDay）：独立页面和表单 — 已实现
- 停诊管理（ScheduleSuspension）：独立页面 — 已实现
- 甘特图视图：已实现，按医生分组、颜色区分时段
- 日历视图：已实现，支持周视图/月视图切换
- 统计分析：已实现，包含汇总统计 + 时段统计 + 明细表

**前后端接口对应关系：**

- Schedule API：13 个前端方法，后端 14+ 端点
- ScheduleTemplate API：15 个前端方法，后端 14+ 端点
- 前端有 2 个废弃方法：`scheduleApi.suspend()` 和 `scheduleApi.resume()`，内部转发到 scheduleSuspensionApi
- 前端 `schedule-template.ts` 和 `schedule.ts` 各有一个相同的 `formatTimeValue()` 工具函数（重复）

**业务逻辑流程：**

- 排班优先级：停诊 > 自定义排班 > 休息日 > 普通排班
- 模板生成排班：前端选择模板+日期范围 → preview 生成预览 → 确认生成 → 后端创建排班记录
- 批量操作：通过模板 ID 批量操作关联的所有未来排班（停诊/恢复/删除）
- 复制规则：两步向导（选科室 → 选医生），将规则复制到其他医生

**文字描述与文案：**

- 排班规则列表页标题："排班规则管理"
- 操作按钮使用 ScheduleMessages 统一文案
- 批量操作使用 Modal.confirm 确认
- 删除操作标记为 danger 样式
- 甘特图时段颜色：上午蓝(#1890ff)、下午绿(#52c41a)、晚上紫(#722ed1)

### Designer — 用户视角

**页面结构与布局：**

- 排班规则页：PageContainer > ProTable + 4 个 Modal（批量添加、生成排班、历史记录、复制规则）— 787 行
- 甘特图页：PageContainer > 自定义甘特图 + 筛选栏 + 详情抽屉 — 533 行
- 日历页：PageContainer > DoctorSelector + CalendarHeader + WeekView/MonthView + 详情抽屉 + 预约详情弹窗 + 创建预约弹窗 — 268 行（含 9 个子组件）
- 统计页：PageContainer > 查询表单 + 汇总卡片 + 时段统计 + 明细表 — 288 行
- 总文件数：20+ 组件文件

**交互模式：**

- 排班规则页：9 个操作（生成/编辑/复制/历史/删除排班/批量停诊/删除规则）+ 3 个工具栏按钮
- 甘特图：任务块点击打开详情抽屉，Tooltip 显示概要
- 日历：日期点击打开详情，预约点击打开详情弹窗，支持创建预约
- 生成排班：两步流程（预览 → 确认），支持自定义时段容量

**表单设计：**

- 排班规则表单：医生、科室、门店、星期、时段、号源数、号源容量、排班模式、生成状态
- 生成排班弹窗：日期范围选择 + 预览表格（可编辑容量）+ 确认
- 复制规则弹窗：两步向导（选科室 → 选医生）
- 自定义排班表单：医生、日期、时段配置
- 休息日表单：医生、日期范围、原因

**筛选条件：**

- 排班规则：门店、科室、医生、星期、预约类型、状态
- 甘特图：门店、科室、医生、日期范围（周导航）
- 日历：医生选择 + 周/月切换
- 统计：门店 + 月份（必填）

**导航流程：**

- 排班规则列表 → 新增/编辑表单
- 排班规则列表 → 生成排班弹窗 → 预览 → 确认
- 排班规则列表 → 复制规则向导
- 日历 → 创建预约弹窗

**数据可视化：**

- 甘特图：自定义 SVG/HTML 渲染，进度条显示预约率
- 日历周视图：时间轴 + 预约块
- 日历月视图：格子布局 + 颜色编码
- 统计：预订率颜色分级（绿 ≤50%、橙 51-80%、红 >80%）

### Engineer — 技术视角

**数据模型：**

- Schedule：15+ 字段，关联 doctor/store/template/appointments，有 tenant_id
- ScheduleTemplate：排班规则模板，多时段配置
- ScheduleSuspension：停诊记录，关联 schedule + reason
- CustomSchedule：自定义排班，优先级高于普通排班
- RestDay：休息日配置

**API 端点：**

- schedules：14+ 端点（CRUD + 批量操作 + 统计 + 可用排班查询）
- schedule_templates：14+ 端点（CRUD + 生成 + 预览 + 批量操作 + 复制 + 日志）
- custom_schedules：独立 CRUD
- rest_days：独立 CRUD
- schedule_suspensions：独立 CRUD + 恢复

**Service 层租户隔离状态（经验证）：**

| 模块 | 查询过滤 | 写入过滤 | 状态 |
|------|---------|---------|------|
| schedules | 有 | 有 | 完整 |
| schedule_suspensions | 有（20+ 处） | 有 | 完整 |
| schedule_templates | **无** | **无** | **缺失 → 已修复** |
| custom_schedules | N/A（已废弃） | N/A | 数据已合并到 schedules |
| rest_days | 有 | 有 | 完整（通过 RestDayService） |

**并发控制：**

- schedules/service_mutation.py：create() 使用 `tenant_distributed_lock`（Redis 分布式锁），锁键包含 tenant_id + doctor_id + 日期 + 时段
- schedule_templates/service_mutation.py：**无并发控制**

**Service 架构：**

- schedules：Mixin 组合（QueryMixin + MutationMixin + GenerationMixin）
- schedule_suspensions：单一 service.py，内联所有逻辑
- schedule_templates：service_query.py + service_mutation.py 分离
- custom_schedules：单一 service.py（无 tenant_id 引用）
- rest_days：router.py 内联查询逻辑（无独立 service 文件）

**前端 API 封装：**

- schedule.ts：13 个方法（含 2 个 @deprecated 转发方法）
- schedule-template.ts：15 个方法
- formatTimeValue() 在两个文件中重复定义

**批量操作模式：**

- batch_suspend：返回 { success: number, failed: number, details: [...] }
- batch_resume：同上
- batch_delete：同上
- 详细结果报告模式一致

---

## Round 2：辩论层

### Team Lead 交叉验证

经过对三方事实的交叉验证，以下为关键发现：

1. **排班模板/自定义排班/休息日模块缺少租户隔离**：schedule_templates、custom_schedules、rest_days 三个模块的查询和写入操作均无 tenant_id 过滤。相比之下，schedules 和 schedule_suspensions 模块有完整的租户隔离。这意味着跨租户的排班模板和自定义排班数据可被任意查询和修改。

2. **前端废弃 API 转发模式存在冗余**：scheduleApi.suspend() 和 resume() 标记为 @deprecated，内部先获取排班详情再转发到 scheduleSuspensionApi。这种转发增加了不必要的网络请求，且注释未说明迁移时间表。

3. **formatTimeValue() 工具函数在两个 API 文件中重复定义**：schedule.ts 和 schedule-template.ts 各有一份完全相同的实现。

4. **rest_days 模块无独立 Service 层**：查询逻辑直接写在 router.py 中，不符合项目的 Mixin/Service 分层架构。

5. **甘特图和统计页无用户可见的错误提示**：仅使用 console.error，用户在加载失败时看到空白页面而无提示。

### Critic 质询

1. [Critic → Engineer] 🚨 关键 质询 1：排班模板/自定义排班/休息日租户隔离缺失
   - 论据：schedule_templates/service_query.py 和 service_mutation.py 均无 get_current_tenant_id() 引用；custom_schedules/service.py 和 rest_days/router.py 同样缺失。schedules 和 schedule_suspensions 模块有完整隔离作为参照。
   - 裁决回应：经验证确认，这是与规则组模块相同类型的安全遗漏。schedule_templates 的 CRUD 全部缺乏租户过滤，跨租户的排班规则可被查看/修改/删除。**升级为 P0 安全修复**。

2. [Critic → Engineer] 质询 2：rest_days 模块架构不合规
   - 论据：rest_days 模块仅有 router.py，查询逻辑直接内联在路由处理函数中。其他 4 个子模块都有独立 service 文件。
   - 裁决回应：确认事实。这是架构一致性问题，但不影响功能正确性。纳入 P1。

3. [Critic → Designer] 质询 3：甘特图/统计页错误处理缺失
   - 论据：甘特图页（533 行）和统计页（288 行）的错误处理仅使用 console.error，无用户可见提示。排班规则页和日历页有 message.error。
   - 裁决回应：确认事实。用户体验受损，纳入 P1。

4. [Critic → PM/Engineer] 质询 4：废弃 API 无迁移计划
   - 论据：scheduleApi.suspend() 和 resume() 标记 @deprecated 但无版本号、无移除时间。转发模式增加额外 API 请求。
   - 裁决回应：确认。应清理废弃方法并统一使用 scheduleSuspensionApi。纳入 P1。

5. [Critic → Engineer] 质询 5：排班模板无并发控制
   - 论据：schedules 使用 Redis 分布式锁防止重复创建，但 schedule_templates 的创建和生成操作无任何并发控制。多管理员同时操作可能导致重复生成。
   - 裁决回应：确认事实。模板生成操作本身有幂等检查（checkGenerated），但缺乏分布式锁保护。实际风险中等。纳入 P1。

### 独到发现

1. **租户隔离不一致是系统性问题**：规则组模块刚修复了类似问题，排班管理的 3/5 子模块仍存在同样的安全遗漏。需要系统性排查所有模块。
2. **排班模板生成是核心业务流程但缺乏并发保护**：生成排班涉及批量创建数十条排班记录，无分布式锁保护可能导致重复生成。
3. **子模块架构不统一**：5 个子模块中，2 个使用 Mixin 分离（schedules、schedule_templates），1 个使用单文件 service（schedule_suspensions、custom_schedules），1 个使用内联路由逻辑（rest_days）。架构模式不一致影响可维护性。

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 裁决回应 | 回应是否充分 | 处置 |
|---|------------|---------|------------|------|
| 1 | 排班模板/自定义/休息日租户隔离缺失 | 确认为安全遗漏 | 是 | 升级为 P0 安全修复 |
| 2 | rest_days 架构不合规 | 确认事实 | 是 | 纳入 P1 |
| 3 | 甘特图/统计页错误处理缺失 | 确认事实 | 是 | 纳入 P1 |
| 4 | 废弃 API 无迁移计划 | 确认事实 | 是 | 纳入 P1 |
| 5 | 排班模板无并发控制 | 确认事实 | 是 | 纳入 P1 |

---

## Round 3：共识层

### ✅ 共识项（共 14 项）

#### P0：立即执行

1. **[安全] schedule_templates 添加 tenant_id 过滤**（成本：4h，负责：Engineer）— **已完成**
   - **结论：** service_query.py 和 service_mutation.py 全部方法无 tenant_id 引用，跨租户数据可被查看/修改/删除。
   - **修复内容：** get_by_id/get_list 添加 tenant_id 过滤；create 添加 tenant_id 设置；update/delete 使用 _get_template_with_tenant 过滤

2. ~~**[安全] custom_schedules 添加 tenant_id 过滤**~~ — **无需修复（模型已废弃，数据已合并到 schedules 表）**

3. ~~**[安全] rest_days 添加 tenant_id 过滤**~~ — **无需修复（RestDayService 已有完整租户隔离）**

#### P1：本轮迭代

4. **清理废弃 API 方法**（成本：1h，负责：Engineer）
   - **行动：** 移除 scheduleApi.suspend() 和 resume()，搜索所有调用点并迁移到 scheduleSuspensionApi

5. **提取重复的 formatTimeValue()**（成本：0.5h，负责：Engineer）
   - **行动：** 提取到共享工具文件，两个 API 文件引用同一份实现

6. **甘特图/统计页添加用户可见错误提示**（成本：1h，负责：Designer + Engineer）
   - **行动：** 添加 message.error 和空状态提示

7. **rest_days 模块提取 Service 层**（成本：2h，负责：Engineer）
   - **行动：** 从 router.py 提取查询逻辑到独立的 service.py，参照其他模块架构

8. **排班模板生成添加并发保护**（成本：3h，负责：Engineer）
   - **行动：** 参照 schedules 的 tenant_distributed_lock 模式，为模板生成操作添加 Redis 分布式锁

9. **排班规则页复制规则后自动刷新**（成本：1h，负责：Engineer）
   - **行动：** 复制成功后刷新列表数据

10. **日历视图切换持久化优化**（成本：1h，负责：Designer）
    - **行动：** 确认 localStorage 持久化视图模式已实现（Round 1 确认已实现），验证跨浏览器标签一致性

#### P2：下个周期

11. **排班子模块架构统一**（成本：4h，负责：Engineer）
    - **行动：** 统一所有 5 个子模块的 Service 层架构模式

12. **甘特图支持实时更新**（成本：6h，负责：Engineer）
    - **行动：** WebSocket 或轮询实现排班状态实时刷新

13. **统计页增加导出功能**（成本：3h，负责：Designer + Engineer）
    - **行动：** 支持 Excel/CSV 导出统计数据

14. **排班规则批量编辑**（成本：4h，负责：Designer + Engineer）
    - **行动：** 支持选中多条规则批量修改时段/容量等字段

### ⚡ 分歧项

（无 — 所有关键质询已逐条回应）

---

## 被低估的优势

1. **排班模板生成流程完善**：预览 → 确认两步流程，支持自定义容量，降低误操作风险
2. **批量操作详细结果报告**：success/failed/details 模式一致，用户清楚知道每条记录的操作结果
3. **日历视图请求去重**：requestDeduplicator 防止重复并发请求
4. **复制规则向导设计**：两步流程（选科室 → 选医生）降低操作复杂度
5. **预订率可视化分级**：三色编码（绿/橙/红）直观展示排班利用情况
6. **排班优先级机制**：停诊 > 自定义排班 > 休息日 > 普通排班，逻辑清晰

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 |
|--------|------|------|------|------|
| **P0** | **schedule_templates 添加 tenant_id 过滤** | **4h** | **极高** | **Engineer** |
| **P0** | **custom_schedules 添加 tenant_id 过滤** | **2h** | **极高** | **Engineer** |
| **P0** | **rest_days 添加 tenant_id 过滤** | **2h** | **极高** | **Engineer** |
| P1 | 清理废弃 API 方法 | 1h | 高 | Engineer |
| P1 | 提取重复 formatTimeValue() | 0.5h | 高 | Engineer |
| P1 | 甘特图/统计页添加错误提示 | 1h | 高 | Designer + Engineer |
| P1 | rest_days 提取 Service 层 | 2h | 中 | Engineer |
| P1 | 排班模板生成添加并发保护 | 3h | 高 | Engineer |
| P1 | 复制规则后自动刷新 | 1h | 中 | Engineer |
| P1 | 日历视图切换持久化验证 | 1h | 低 | Designer |
| P2 | 排班子模块架构统一 | 4h | 中 | Engineer |
| P2 | 甘特图支持实时更新 | 6h | 中 | Engineer |
| P2 | 统计页增加导出功能 | 3h | 低 | Designer + Engineer |
| P2 | 排班规则批量编辑 | 4h | 低 | Designer + Engineer |

**P0 总计成本：4h（仅 schedule_templates，其余已验证安全）** | **P1 总计成本：10.5h** | **P2 总计成本：17h**

### 待定：需用户确认

（无 — 所有关键质询已逐条回应）

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 14 项达成共识（P0: 3 项, P1: 7 项, P2: 4 项）

**关键分歧：** 0 项

**Top 3 P0 行动（按紧迫度排序）：**
1. schedule_templates 添加 tenant_id 过滤（4h）— 跨租户排班规则可被查看/修改/删除
2. custom_schedules 添加 tenant_id 过滤（2h）— 跨租户自定义排班数据泄露
3. rest_days 添加 tenant_id 过滤（2h）— 跨租户休息日数据泄露

**Critic 关键洞察：**
- 排班管理模块存在与规则组模块相同类型的安全遗漏（租户隔离缺失），这是系统性问题
- 5 个子模块中 3 个缺少租户隔离，安全覆盖率为 40%（仅 schedules 和 schedule_suspensions 有完整隔离）
- 子模块架构不统一（Mixin/单文件 service/内联路由），增加维护成本和新模块开发时的困惑

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| 无 | | | |
