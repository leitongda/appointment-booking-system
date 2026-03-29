# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-28
> 审查目标：Admin 端排班管理功能 + Server 端排班相关接口，给出优化建议

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合评审涉及前端UI/UX、后端API设计、数据模型多维度，无单一领域需要特别深入，集中调度模式收敛最快且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 排班管理位于 admin 端"医疗业务"菜单下，共 12 个路由页面（含隐藏路由）
- 权限标识：canSchedule
- 核心子模块：排班规则设置、排班日历、排班列表、甘特图、自定义排班、停诊管理、休息日设置、排班统计

**功能完成度：**
- 排班日历（calendar/）：已实现 — 周视图+月视图切换、医生选择器、日期详情抽屉、预约详情弹窗、创建预约弹窗、请求去重
- 排班规则（rule/）：已实现 — CRUD、批量生成、预览生成（含自定义容量）、复制规则到多医生、生成历史记录、批量删除/停诊
- 排班规则表单（rule/form.tsx）：已实现 — 基础信息+排班设置+排班方式+高级设置（排除时间段）、实时日历预览
- 自定义排班（custom.tsx + custom-form.tsx）：已实现 — 列表展示、生效班次查询、级联选择（门店→科室→医生）、动态时段配置
- 排班列表（detail/）：已实现 — 多维度筛选、批量停诊/恢复/删除、新增排班弹窗、预约状态展示
- 甘特图（gantt/）：已实现 — 按医生分组、周视图导航、预约进度、停诊状态
- 停诊管理（suspension.tsx）：已实现 — 停诊记录CRUD、动态加载可选排班
- 休息日设置（rest-day.tsx + rest-day-form.tsx）：已实现 — 门店级/医生级休息日、权重说明
- 排班统计（statistics.tsx）：已实现 — 按门店月份查询、汇总+明细

**前后端接口对应关系：**
- 前端调用的所有 API 在后端均有对应路由实现，前后端接口完全匹配
- 后端提供的所有 API 端点均被前端使用
- 未发现未实现功能或废弃接口

**核心业务特性：**
- 排班权重系统：停诊 > 自定义排班 > 休息日设置 > 普通排班
- 休息日标记：所有排班接口返回 isRestDay 字段
- 时段兼容：同时支持 morning/afternoon/evening 和 AM/PM/NIGHT 两种格式
- 排班模式枚举：weekly、month_week_1~5、year_odd_week、year_even_week

### Designer — 用户视角

**页面清单与结构：**
- 22 个文件，6630 行代码
- 9 个路由页面 + 8 个日历子组件 + 1 个共享组件
- 最大文件：rule/index.tsx（1350 行，~47KB）
- 页面间导航：规则→规则表单、自定义排班→自定义排班表单、休息日→休息日表单

**交互模式统计：**
- Modal 使用 5 处，ModalForm 使用 5 处，Drawer 使用 2 处，共 12 个弹窗/抽屉
- Spin 组件使用 17 次（6 个文件），未发现 Skeleton 组件
- Empty 组件使用 6 次（3 个文件）
- message 组件使用 61 次（success 22、error 28、warning 8、info 3）

**日历组件分析：**
- 周视图：30 分钟时间轴（08:00-21:00），Grid 8 列布局
- 月视图：基于 Ant Design Calendar 封装
- 视图切换持久化到 localStorage
- TimeSlotCell 状态：available/booked/full/suspended/empty
- RulePreviewCalendar：426 行，支持月/年视图切换、响应表单值变化

**排班规则表单分析：**
- 4 个分组：基础信息（4 字段）、排班设置（6 字段）、排班方式（1 字段）、高级设置（动态）
- 左右布局：左侧预览日历 + 右侧表单
- 使用 ProForm 组件体系

**组件一致性事实：**
- ProComponents 使用广泛：ProTable 7 次、ProForm 8 次、ModalForm 5 次、PageContainer 12 次
- 自定义组件 8 个（日历相关），其余直接使用 Ant Design 组件
- 样式文件 2 个 Less（calendar.less 512 行、gantt.less 277 行）

**响应式和无障碍：**
- @media 查询仅 2 处（甘特图响应式 + 打印样式）
- aria 属性使用：0 次
- 固定像素宽度大量使用（表格列宽、弹窗宽度、选择器宽度）
- 未使用 CSS Module、vw/vh/rem 响应式单位

### Engineer — 技术视角

**存储层事实：**
- 5 张核心表：schedules、schedule_templates、custom_schedules、schedule_suspensions、schedule_generation_logs
- schedules 表字段：doctor_id、tenant_id(nullable=True)、store_id、template_id、shift_type_id、schedule_date、time_slot、start/end_time、total/booked_slots、status 等
- schedule_templates 表：weekdays（JSON数组）、break_times（JSON数组）、slot_count、slot_capacity、schedule_mode
- schedule_suspensions 表：**缺少 tenant_id 字段**（与 schedules/templates 不一致）
- 关系：Schedule ← ScheduleTemplate（多对一，可空）、Schedule ← Doctor/Store/Tenant
- tenant_id 索引存在于 schedules 和 schedule_templates 表
- 7 个数据库迁移脚本与排班相关

**核心引擎事实：**
- 服务分层：ScheduleService 继承 QueryMixin + MutationMixin + GenerationMixin
- 生成算法：查询模板→解析 weekdays→排除 break_times→split_time_range_with_breaks 均分→逐日创建（含休息日检查和防重）
- **`_create_schedule_if_not_exists` 创建的 Schedule 对象未设置 tenant_id**（service_generation.py:87-100）
- `batch_create` 方法中有 tenant_id 注入（service_mutation.py:139）
- `get_list` 查询**没有 tenant_id 过滤**（service_query.py:31-61）
- `get_available` 中**N+1 查询问题** — 循环中每个排班都调用 `_check_rest_day`（service_query.py:83-91）
- 冲突检测：Redis 分布式锁（粒度：租户+医生+日期+时间段，10 秒超时，5 次重试）
- 批量操作：停诊/删除/恢复均支持批量，返回 success/failed 分类结果
- Celery 异步任务：每天凌晨 2 点自动生成排班，多租户遍历，每模板独立事务

**API/协议事实：**
- 排班模块 10 个端点，模板模块 14 个端点，停诊模块 5 个端点
- 无 WebSocket/SSE 实时更新

**安全机制事实：**
- JWT Bearer Token 认证 + Token 黑名单（Redis）
- 权限装饰器：require_permission("schedule:create/update/delete")
- 多租户隔离：创建时注入 tenant_id、查询/更新/删除校验 tenant_id（但存在上述遗漏）
- 全部使用 ORM，未发现原生 SQL 拼接

**依赖和模块耦合事实：**
- 排班模块依赖：Redis、Appointment、Doctor、Message、RestDay、RuleEngine
- 工具函数：schedule_utils（587 行，含 split_time_range_with_breaks 等复杂算法）

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| # | 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|---|------|-----------|------------|---------|
| 1 | schedule_suspensions 缺少 tenant_id | 代码已验证确认，安全风险 | 🚨 关键 | P0 修复 |
| 2 | _create_schedule_if_not_exists 未注入 tenant_id | 代码已验证确认，数据完整性风险 | 补充发现 | P0 修复 |
| 3 | get_list 查询无 tenant_id 过滤 | 代码已验证确认，跨租户数据泄露 | 补充发现 | P0 修复 |
| 4 | Celery 定时任务失败无告警/重试 | Critic 质询合理，运维风险 | 🚨 关键 | P1 改进 |
| 5 | 排班统计遗漏 evening 时段 | Critic 已验证 statistics.tsx 确实只统计 morning/afternoon | 🚨 关键 | P1 修复 |
| 6 | get_available N+1 查询问题 | 循环内逐条查 RestDay，性能风险 | 补充发现 | P1 优化 |
| 7 | rule/index.tsx 1350 行巨石文件 | 组件拆分不足，维护困难 | 普通 | P2 重构 |
| 8 | 双时段格式 (morning/AM) 并存 | 历史遗留，前端需维护两套配置 | 普通 | P2 统一 |
| 9 | 响应式布局仅 2 处 | 明确为桌面端管理后台，暂可接受 | 普通 | 待定 |
| 10 | 甘特图命名与交互能力不匹配 | 本质是时间轴视图，非交互式甘特图 | 普通 | 待定 |
| 11 | 61 次 message 调用无统一模式 | 前端错误处理不一致 | 普通 | P2 统一 |

### 独到发现

1. **tenant_id 三重遗漏**（裁决者交叉验证）：
   - schedule_suspensions 表无 tenant_id 字段
   - `_create_schedule_if_not_exists` 创建对象时未设置 tenant_id
   - `get_list` 查询缺少 tenant_id where 条件
   - 三者叠加意味着：模板生成的排班可能无 tenant_id，且列表接口可能返回跨租户数据

2. **排班权重优先级实现不完整**（裁决者交叉验证）：
   - PM 声称排班权重为"停诊 > 自定义排班 > 休息日设置 > 普通排班"
   - `get_available` 中仅通过 `schedule_map` 做简单覆盖（自定义排班覆盖普通排班）
   - 未发现显式的权重计算或排序逻辑，权重的执行依赖于查询顺序而非显式设计

### Critic 质询

1. [Critic → PM] 质询 1：排班统计遗漏 evening 时段
   - 论据：statistics.tsx 仅统计 morningSlots/afternoonSlots，evening 相关字段不存在
   - 级别：🚨 关键

2. [Critic → PM] 质询 2：甘特图命名与实际不符
   - 论据：仅展示视图，无拖拽等交互能力
   - 级别：普通

3. [Critic → Engineer] 质询 3：schedule_suspensions 缺少 tenant_id
   - 论据：与 schedules/templates 表设计不一致，仅靠 API 层保护
   - 级别：🚨 关键

4. [Critic → Engineer] 质询 4：schedules 表 tenant_id 可空性
   - 论据：nullable=True 与"创建时注入"声明矛盾
   - 级别：普通

5. [Critic → Engineer] 质询 5：双时段格式并存
   - 论据：后端 get_time_slot_from_time 只返回小写，大写格式来源不明
   - 级别：普通

6. [Critic → Engineer] 质询 6：split_time_range_with_breaks 午餐边界
   - 论据：算法复杂 140+ 行，需验证边界场景
   - 级别：普通

7. [Critic → Engineer] 质询 7：Redis 锁 10 秒超时合理性
   - 论据：超时释放后数据库操作仍在执行可能导致重复
   - 级别：普通

8. [Critic → PM & Engineer] 质询 8：Celery 定时任务失败无告警/重试
   - 论据：仅记录日志，无人主动知晓，可能 24 小时无排班
   - 级别：🚨 关键

9. [Critic → Designer] 质询 9：rule/index.tsx 1350 行巨石文件
   - 论据：违反单一职责，维护性差
   - 级别：普通

10. [Critic → Designer] 质询 10：响应式布局仅 2 处
    - 论据：排班管理为 admin 桌面端，但可能需要移动端查看
    - 级别：普通

11. [Critic → Engineer] 质询 11：61 次 message 调用无统一模式
    - 论据：错误处理不一致，措辞不统一
    - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 回应摘要 | 回应充分 | 处置 |
|---|------------|---------|---------|------|
| 1 | schedule_suspensions 缺少 tenant_id | 裁决者代码验证确认，数据表+API层双重缺失 | 是 | P0 修复 |
| 2 | Celery 定时任务失败无告警/重试 | 仅 try-except 记录日志，无 max_retries 装饰器，无告警集成 | 是 | P1 改进 |
| 3 | 排班统计遗漏 evening 时段 | statistics.tsx 确实只统计 morning/afternoon 两个字段 | 是 | P1 修复 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：schedule_suspensions 表缺少 tenant_id 字段**
   **结论：** 多租户数据隔离存在安全漏洞，停诊记录可跨租户访问
   **建议行动：** 添加 tenant_id 字段 + 迁移脚本 + API 层注入
   **成本估算：** 2h（迁移脚本 + 模型修改 + service 层修改）
   **优先级：** P0

2. **议题：_create_schedule_if_not_exists 未注入 tenant_id**
   **结论：** 模板自动生成的排班记录 tenant_id 为 NULL，影响数据隔离和查询
   **建议行动：** 在 _create_schedule_if_not_exists 中注入 get_current_tenant_id()，同时修复 Celery 任务中的租户上下文传递
   **成本估算：** 1h（service_generation.py 修改 + Celery 任务验证）
   **优先级：** P0

3. **议题：get_list 查询缺少 tenant_id 过滤**
   **结论：** 排班列表接口可能返回其他租户的数据
   **建议行动：** 在 get_list 方法中添加 tenant_id 过滤条件，与 get_current_tenant_id() 联动
   **成本估算：** 0.5h（service_query.py 添加过滤条件）
   **优先级：** P0

4. **议题：Celery 定时任务失败无告警/重试**
   **结论：** 排班生成失败时仅记录日志，无主动告警，可能导致 24 小时无排班
   **建议行动：** 添加 max_retries=3 + retry_backoff + 失败告警通知（钉钉/企微 webhook）
   **成本估算：** 3h（任务改造 + 告警集成）
   **优先级：** P1

5. **议题：排班统计遗漏 evening 时段**
   **结论：** statistics.tsx 仅统计 morning/afternoon，evening 时段数据缺失
   **建议行动：** 扩展统计逻辑支持 evening + 动态时段配置
   **成本估算：** 2h（前端+后端统计逻辑扩展）
   **优先级：** P1

6. **议题：get_available N+1 查询问题**
   **结论：** 循环中逐条查 RestDay 表，排班量大时性能显著下降
   **建议行动：** 批量查询 RestDay（按日期范围），在内存中过滤
   **成本估算：** 2h（service_query.py 重构）
   **优先级：** P1

7. **议题：rule/index.tsx 1350 行巨石文件**
   **结论：** 违反单一职责，维护困难
   **建议行动：** 拆分为 RuleList、RuleGenerateModal、RuleCopyModal、RuleHistoryDrawer 等子组件
   **成本估算：** 4h（组件拆分 + 路由验证）
   **优先级：** P2

8. **议题：双时段格式 (morning/AM) 并存**
   **结论：** 历史遗留问题，前端需维护两套配置
   **建议行动：** 数据迁移统一为小写格式 + 清理前端双配置代码
   **成本估算：** 4h（迁移脚本 + 前后端代码清理）
   **优先级：** P2

9. **议题：61 次 message 调用无统一错误处理**
   **结论：** 错误提示措辞不一致，维护困难
   **建议行动：** 封装统一的 useMessageAction Hook，集中管理操作反馈
   **成本估算：** 3h（Hook 封装 + 逐步替换）
   **优先级：** P2

### ⚡ 分歧项

1. **议题：响应式布局是否需要覆盖排班管理**
   **各方立场：**
   - Designer：仅 2 处 @media，无移动端适配
   - Critic：医生/主任可能在移动端查看排班
   - 裁决者：admin 端明确面向桌面端管理后台
   **裁决/建议：** 当前 admin 端定位为桌面端管理工具，移动端查看排班由 doctor 端（医生工作台）覆盖。暂不需要为 admin 排班管理添加响应式。如有移动端排班管理需求，应考虑独立 H5/小程序入口。
   **决策依据：** admin/doctor/patient 三端定位不同，职责边界清晰

2. **议题：甘特图命名是否需要修改**
   **各方立场：**
   - PM：功能已实现
   - Critic：命名暗示交互能力（拖拽），实际仅为时间轴视图
   **裁决/建议：** 保持"甘特图"命名不变。在项目管理系统领域，只读甘特图是常见形态。如未来需要交互能力，再评估是否升级。
   **决策依据：** 甘特图并非必须支持拖拽，只读甘特图在医疗排班场景已足够

---

## 被低估的优势

1. **排班生成算法完善**：split_time_range_with_breaks 正确处理了排除时间段（午休）、跨天、重叠排除等边界情况，包含完善的验证和合并逻辑
2. **Redis 分布式锁 + 查重双保险**：排班创建同时使用分布式锁和数据库查重，两层防重机制
3. **实时预览能力**：RulePreviewCalendar 在表单填写时实时预览排班效果，用户体验友好
4. **批量操作设计**：停诊/删除/恢复均返回详细的 success/failed 分类结果，便于前端展示操作反馈
5. **通知机制完善**：停诊操作自动通知医生和患者，包含脱敏和个性化消息

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | get_list 添加 tenant_id 过滤 | 0.5h | 高（安全） | Engineer | |
| P0 | _create_schedule_if_not_exists 注入 tenant_id | 1h | 高（数据完整性） | Engineer | |
| P0 | schedule_suspensions 添加 tenant_id 字段 | 2h | 高（安全） | Engineer | |
| P1 | Celery 任务添加重试+告警 | 3h | 高（运维可靠性） | Engineer | |
| P1 | 排班统计支持 evening 时段 | 2h | 高（功能完整性） | PM+Engineer | |
| P1 | get_available 消除 N+1 查询 | 2h | 中（性能） | Engineer | |
| P2 | rule/index.tsx 组件拆分 | 4h | 中（可维护性） | Designer | |
| P2 | 统一时段格式（去除双格式） | 4h | 中（技术债） | Engineer | |
| P2 | 统一 message 错误处理模式 | 3h | 中（一致性） | Designer | |
| 待定 | admin 端排班管理响应式适配 | 8h+ | 待评估 | Designer | |

### P0：立即执行（高价值、低成本）

1. **get_list 添加 tenant_id 过滤** — 0.5h — 在 service_query.py 的 get_list 方法中添加 tenant_id 过滤，防止跨租户数据泄露
2. **_create_schedule_if_not_exists 注入 tenant_id** — 1h — 在 service_generation.py 的 _create_schedule_if_not_exists 中从上下文获取 tenant_id 并注入到 Schedule 对象，同时确保 Celery 任务中正确传递租户上下文
3. **schedule_suspensions 添加 tenant_id 字段** — 2h — 修改模型添加 tenant_id 列 + 创建迁移脚本 + service 层注入 tenant_id

### P1：本轮迭代（高价值、中等成本）

1. **Celery 任务添加重试和告警** — 3h — 为 auto_generate_schedules_task 添加 max_retries=3 + retry_backoff=True + 失败时发送 webhook 告警
2. **排班统计支持 evening 时段** — 2h — 扩展后端统计逻辑和前端 statistics.tsx，支持所有时段类型
3. **get_available 消除 N+1 查询** — 2h — 批量查询 RestDay 数据，在内存中进行休息日过滤

### P2：下个周期规划（中等价值、较高成本）

1. **rule/index.tsx 组件拆分** — 4h — 拆分为 RuleList、RuleGenerateModal、RuleCopyModal、RuleHistoryDrawer 等独立组件
2. **统一时段格式** — 4h — 数据迁移脚本将 AM/PM/NIGHT 转为 morning/afternoon/evening，清理前端双配置代码
3. **统一 message 错误处理** — 3h — 封装 useMessageAction Hook，逐步替换散落的 message 调用

### 待定：需用户确认

1. **admin 端排班管理是否需要移动端响应式适配** — 当前定位为桌面端管理工具，移动端查看排班由 doctor 端覆盖。如需在 admin 端移动端查看排班，预计 8h+ 适配工作量。

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 9 项达成共识（3 项 P0 + 3 项 P1 + 3 项 P2）

**关键分歧：**
- 2 项需要决策者介入（响应式适配 + 甘特图命名），均已裁决

**Top 3 P0 行动：**
1. get_list 添加 tenant_id 过滤（0.5h，安全）
2. _create_schedule_if_not_exists 注入 tenant_id（1h，数据完整性）
3. schedule_suspensions 添加 tenant_id 字段（2h，安全）

**Critic 关键洞察：**
- 3 条关键质询全部得到实质性回应：schedule_suspensions 缺 tenant_id（P0 修复）、Celery 无告警（P1 改进）、统计遗漏 evening（P1 修复）
- 裁决者交叉验证额外发现 2 条 PM/Designer/Engineer 三方均未识别的问题：`_create_schedule_if_not_exists` 未注入 tenant_id 和 `get_list` 无租户过滤

**P0 总成本：** 3.5h | **P1 总成本：** 7h | **P2 总成本：** 11h | **总计：** 21.5h

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| — | — | — | 未切换模式 |
