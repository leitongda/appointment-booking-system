# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-29
> 审查目标：排班管理功能的逻辑流程、页面布局、操作合理性
> 项目：排班管理功能

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 排班管理是系统核心业务模块，横跨前端 UI/UX、后端 API、数据模型、定时任务多个层面，需要全栈视角的统一分析。集中调度模式可确保评审结论的一致性和行动项的可执行性。

---

## Round 1：事实层（只写事实，不评价）

### PM Agent — 产品视角

**模块定位与路由：**
- 排班管理位于 admin 端 `/medical-services/schedule` 下，权限标识 `canSchedule`
- 共 12 个路由（含 4 个隐藏表单路由），默认重定向到排班规则页
- 子模块：排班规则设置、排班列表、排班日历、排班甘特图、自定义排班、休息日设置、停诊管理、排班统计

**功能完成度清单：**

| 子模块 | 页面文件 | 状态 | 关键功能 |
|---|---|---|---|
| 排班规则列表 | rule/index.tsx | 已实现 | CRUD、批量生成、预览生成（含自定义容量）、复制规则到多医生、生成历史、批量删除/停诊 |
| 排班规则表单 | rule/form.tsx | 已实现 | 基础信息+排班设置+排班方式+高级设置（排除时间段）、左侧实时日历预览 |
| 排班日历 | calendar/index.tsx | 已实现 | 周视图+月视图切换、医生选择器、日期详情抽屉、预约详情弹窗、创建预约弹窗、请求去重 |
| 排班列表 | detail/index.tsx | 已实现 | 多维度筛选、批量停诊/恢复/删除、新增排班弹窗 |
| 甘特图 | gantt/index.tsx | 已实现 | 按医生分组、周视图导航、预约进度条、停诊/休息日标记、详情抽屉 |
| 自定义排班列表 | custom.tsx | 已实现 | 列表展示、生效班次查询 |
| 自定义排班表单 | custom-form.tsx | 已实现 | 级联选择（门店->科室->医生）、动态时段配置（添加/复制/删除）、日期范围 |
| 休息日列表 | rest-day.tsx | 已实现 | 列表展示、取消/删除 |
| 休息日表单 | rest-day-form.tsx | 已实现 | 门店级/医生级休息日设置 |
| 停诊管理 | suspension.tsx | 已实现 | 停诊记录CRUD、动态加载可选排班（支持按时段停诊或全天停诊） |
| 排班统计 | statistics.tsx | 已实现 | 按门店月份查询、汇总统计+明细表格 |

**前后端接口对应关系：**
- 前端调用 `scheduleApi`、`scheduleTemplateApi`、`customScheduleApi`、`restDayApi`、`scheduleSuspensionApi` 共 5 个 API 模块
- 后端 `/schedules` 路由提供：列表、详情、创建、批量创建、更新、批量停诊、批量恢复、批量删除、获取可预约排班、排班统计 — 共 10 个端点
- 前端 `scheduleApi.suspend` 和 `scheduleApi.resume` 标记为 @deprecated，内部转发到 `scheduleSuspensionApi`
- 未发现未实现的前端功能或废弃的后端接口

**核心业务规则（代码级事实）：**
- 排班权重：停诊 > 自定义排班 > 休息日设置 > 普通排班（在列表页 Alert 和表单页 Alert 中均有说明）
- 排班模式枚举：weekly、month_week_1~5、year_odd_week、year_even_week
- 预约类型枚举：urgent、normal、expert、medical_insurance、self_pay
- 时段标识：使用 morning/afternoon/evening（数据库注释中还遗留 AM/PM 字样）
- 休息日模型：支持日期范围 + 门店级/医生级，doctor_ids 为 JSON 数组存储

**消息文案体系：**
- 独立文件 `utils/message.ts`，共 35 条消息，覆盖所有操作场景
- 所有页面统一引用 `ScheduleMessages` 对象

---

### Designer Agent — 用户视角

**页面结构与布局：**

1. **排班规则列表** (rule/index.tsx, 803行)
   - 顶部：日期信息 Alert（当前日期、本月第几周、奇偶周）
   - 主体：ProTable 列表，14列，横向滚动 1650px
   - 操作列：Dropdown 菜单（生成排班、编辑、复制规则、历史记录、删除排班、批量停诊、删除规则）
   - 工具栏：生成排班(N)、批量添加、新增规则
   - 弹窗：GenerateScheduleModal（两阶段：设置->预览/直接生成）、BatchAddModal、HistoryLogsModal、CopyRuleModal

2. **排班规则表单** (rule/form.tsx, 450行)
   - 布局：Row + Col (12:12)，左侧日历预览 + 右侧表单
   - 表单分区：基础信息（Card）、排班设置（Card）、排班方式（Card）、高级设置（Collapse）
   - 底部：FooterToolbar 固定底部

3. **排班日历** (calendar/index.tsx, 267行)
   - 顶部：DoctorSelector（科室->医生级联 + 头像展示）
   - 中间：CalendarHeader（视图切换 + 日期导航 + 刷新）
   - 主体：MonthView（Ant Design Calendar + 自定义 cellRender）或 WeekView（时间轴网格）
   - 抽屉/弹窗：DayDetailDrawer、AppointmentDetailModal、CreateAppointmentModal

4. **排班甘特图** (gantt/index.tsx, 548行)
   - 顶部：筛选器（门店、科室、医生、日期范围、周导航）
   - 图例：上午/下午/晚上/停诊/休息日
   - 主体：自定义 CSS 甘特图（非第三方组件），按医生分行，按日期分列
   - 详情：右侧 Drawer

5. **排班列表** (detail/index.tsx, 522行)
   - 搜索栏：门店、日期、科室、医生
   - 主体：ProTable，支持批量选择
   - 批量操作：批量停诊、批量恢复、批量删除
   - 新增排班弹窗

6. **排班统计** (statistics.tsx, 313行)
   - 查询条件 Card：门店 + 月份选择
   - 统计汇总 Card：总号源、总预约、预约率、排班天数
   - 时段统计 Card：上午/下午/晚间分栏
   - 排班明细 Table：按日期+医生分组

7. **停诊管理** (suspension.tsx, 347行)
   - ProTable 列表
   - 添加弹窗：门店->医生->日期 三级联动后动态显示排班 Checkbox 列表
   - 不选排班则全天停诊

8. **自定义排班** (custom.tsx, 277行 + custom-form.tsx, 329行)
   - 列表页：生效班次查询（独立 Card）+ 排班列表
   - 表单页：FormPage 组件包裹，动态时段配置

**交互模式观察：**
- 级联选择模式普遍使用：科室->医生、门店->科室->医生
- 门店权限：非超管只显示关联门店，多处重复实现此逻辑
- 删除/停诊操作普遍使用 Popconfirm 确认
- 批量操作在 ProTable 工具栏中按选中状态动态显示

---

### Engineer Agent — 技术视角

**数据模型：**
- `Schedule` 模型：15个字段，核心字段 doctor_id、schedule_date、time_slot、start_time、end_time、total_slots、booked_slots、status、appointment_type、template_id
- `ScheduleSuspension` 模型：7个字段，store_id、doctor_id、title、suspension_date、schedule_ids(JSON)、time_slots(JSON)、status
- `RestDay` 模型：store_id、doctor_ids(JSON数组)、start_date、end_date、reason、status
- `ScheduleTemplate` 模型：doctor_id、store_id、department_id、weekdays、appointment_type、start_time、end_time、slot_count、slot_capacity、schedule_mode、break_times、status
- 多租户支持：所有模型均有 tenant_id 字段，查询层使用 `get_current_tenant_id()` 过滤

**API 端点清单（router.py，624行）：**
- GET `/schedules` — 列表查询，支持医生/门店/日期/状态筛选，内置休息日判断
- GET `/schedules/statistics` — 按门店+月份统计，分别查询普通排班和自定义排班
- GET `/schedules/available/{doctor_id}` — 可预约排班，集成规则引擎（预约窗口检查、紧急程度判定）
- GET `/schedules/{schedule_id}` — 详情，含休息日判断
- POST `/schedules` — 创建，使用租户隔离分布式锁
- POST `/schedules/batch` — 批量创建
- PUT `/schedules/{schedule_id}` — 更新
- POST `/schedules/batch-suspend` — 批量停诊
- POST `/schedules/batch-resume` — 批量恢复
- POST `/schedules/batch-delete` — 批量删除（跳过有预约的）

**Service 层结构：**
- `ScheduleService` 通过 Mixin 拆分：`ScheduleQueryMixin`（查询）、`ScheduleMutationMixin`（变更）、`ScheduleGenerationMixin`（生成）
- 排班创建使用 `RedisCache.tenant_distributed_lock`，锁粒度：租户+医生+日期+时间段
- 自定义排班（template_id=NULL）可覆盖普通排班（前提是无预约）
- 停诊服务 `ScheduleSuspensionService`：创建停诊时自动更新排班状态，取消时自动恢复

**定时任务：**
- `auto_generate_schedules_task`：每天凌晨2点，遍历所有活跃租户，按模板生成排班
- `generate_schedules_for_template`：手动触发单模板生成
- 每个租户、每个模板使用独立事务，失败不影响其他
- 支持失败告警 Webhook

**Schema 层：**
- `ScheduleBase` -> `ScheduleCreate` / `ScheduleBatchCreate` / `ScheduleUpdate`
- `ScheduleResponse`：含 doctor_name、department_name、store_name、is_rest_day
- `AvailableScheduleResponse`：扩展 booking_status、capacity_percent、urgency_level
- 使用 Pydantic `alias_generator=to_camel` 做 camelCase 转换

**安全机制：**
- 所有管理端点需要 `get_current_admin` 认证
- 门店过滤：`get_store_filter` + `check_store_access`
- 权限控制：`require_permission("schedule:create/update/delete")`
- 租户隔离：所有查询条件包含 tenant_id

**前端共享常量：**
- `packages/shared/src/constants/schedule.ts`（618行）：包含时段、状态、星期、预约类型、排班模式的所有映射和工具函数
- 时间均分算法：`splitTimeRange` 和 `splitTimeRangeWithBreaks` 支持排除时间段
- 排班预览：`generateSchedulePreview` 和 `shouldGenerateSchedule` 用于前端预览

---

## Round 2：交叉辩论

### 交叉验证矩阵

| 验证维度 | PM 发现 | Designer 发现 | Engineer 发现 | 一致性 |
|---|---|---|---|---|
| 功能完整性 | 8个子模块全部已实现 | 所有页面均有完整UI | 所有API端点已实现且被前端使用 | 完全一致 |
| 排班权重 | Alert明确展示权重 | 列表页和表单页均有提示 | 后端代码中自定义排班覆盖普通排班逻辑已实现 | 一致 |
| 时段格式 | morning/afternoon/evening | UI统一使用中文标签 | Schema中注释残留AM/PM，实际存储小写格式 | 发现矛盾：注释不一致 |
| 门店权限 | 多处重复过滤逻辑 | 多页面重复实现非超管过滤 | 后端 get_store_filter 统一处理 | 发现重复 |
| 休息日 | 接口返回 isRestDay | 日历/甘特图展示休息日标记 | router.py 内联休息日查询逻辑（N+1风险） | 逻辑一致但有性能问题 |

### Critic Agent — 质询与发现

**质询 1：排班列表页的"新增排班"弹窗功能是否与排班规则/自定义排班功能重叠？**
- 事实：`detail/index.tsx` 的 ModalForm 支持直接创建单条排班（选择科室->医生->日期->时段->号源）
- 事实：`custom-form.tsx` 也支持创建排班，但更丰富（支持多时段、日期范围、预约类型等）
- 事实：后端 `POST /schedules` 端点是统一的创建入口
- 结论：存在功能重叠，简单新增弹窗无法设置时间区间，也无法设置预约类型（虽然字段存在但UI未提供选择）

**质询 2：停诊管理模块与排班列表的批量停诊是否冲突？**
- 事实：排班列表的批量停诊直接修改 Schedule.status=0
- 事实：停诊管理创建 ScheduleSuspension 记录，同时修改 Schedule.status=0
- 事实：排班列表的恢复操作标记为 @deprecated，实际转发到 scheduleSuspensionApi
- 结论：存在两条停诊路径，一条不创建停诊记录（直接改状态），一条创建停诊记录。恢复时只查找停诊记录，可能导致通过排班列表直接停诊的排班无法通过停诊管理恢复

**质询 3：排班统计的日期范围查询是否存在数据重复计算？**
- 事实：`get_schedule_statistics` 端点先查询 store_id 下的所有医生排班（第1步），再查询同门店 template_id=NULL 的排班（第2步）
- 事实：第1步没有 store_id 过滤条件（只过滤了 doctor_id IN doctor_map），而第2步使用了 store_id
- 结论：如果医生从其他门店借调，第1步可能包含非本门店排班数据

**质询 4：甘特图的分页加载策略在大数据量下是否可靠？**
- 事实：甘特图页面分页加载所有排班数据，pageSize=100，通过 Promise.all 并发请求剩余页
- 事实：如果某一周有 500+ 条排班（多医生场景），将产生 5+ 次并发请求
- 结论：虽然功能正确，但用户体验上加载较慢，且内存中保存全量数据

**质询 5：排班规则表单的"排班预览"组件是否真正与后端生成逻辑一致？**
- 事实：前端使用 `generateSchedulePreview` 纯前端计算预览日期列表
- 事实：后端使用 `should_generate_schedule` + `split_time_range_with_breaks` 生成实际排班
- 事实：两套逻辑分别在前端 `packages/shared` 和后端 `app/utils/schedule_utils.py` 中独立实现
- 结论：存在前后端逻辑不一致的风险。前端 `getDateInfo` 的周数计算方式（`Math.ceil(date.getDate() / 7)`）与后端 ISO 周可能不同

### 投票矩阵

| 发现项 | PM 投票 | Designer 投票 | Engineer 投票 | Critic 质询 | 优先级 |
|---|---|---|---|---|---|
| 停诊双路径不一致 | 重要 | 中等 | 严重 | 确认存在 | P0 |
| 统计接口数据可能重复 | 重要 | N/A | 严重 | 确认存在 | P0 |
| 门店权限过滤逻辑重复 | 中等 | 中等 | 重要 | 可提取公共 Hook | P1 |
| 排班规则预览前后端逻辑不一致 | 重要 | 重要 | 严重 | 需验证 | P1 |
| 新增排班弹窗功能不完整 | 重要 | 重要 | 中等 | 与自定义排班重叠 | P1 |
| Schema 注释 AM/PM 遗留 | 低 | N/A | 重要 | 文档债务 | P2 |
| 日历页面只能选单医生 | 中等 | 重要 | N/A | 设计限制 | P2 |
| 甘特图全量加载性能 | 中等 | 中等 | 重要 | 数据量大时有风险 | P2 |

---

## Round 3：共识收敛

### 裁决原则
- P0：数据正确性或业务逻辑缺陷，必须修复
- P1：影响用户体验或代码质量，建议本轮修复
- P2：优化建议，可排入后续迭代

### 共识项（7项，全员一致）

1. **停诊操作存在双路径**（P0）：排班列表直接停诊不创建 ScheduleSuspension 记录，导致无法通过停诊管理恢复
2. **统计接口第1步查询缺少 store_id 过滤**（P0）：可能导致跨门店数据混入
3. **门店权限过滤在 5+ 个组件中重复实现**（P1）：应提取公共 Hook
4. **排班规则预览依赖前端独立计算的周数逻辑**（P1）：与后端可能不一致
5. **排班列表新增排班弹窗缺少预约类型选择**（P1）：与自定义排班功能部分重叠
6. **Schema 注释中遗留 AM/PM 字样**（P2）：实际使用小写 morning/afternoon/evening
7. **甘特图全量加载在大量排班时有性能风险**（P2）

### 分歧项（2项）

1. **排班日历是否需要支持多医生视图**
   - Designer：认为单医生视图限制较大，多医生对比是常见需求
   - PM：当前甘特图已支持多医生视图，日历定位为单医生详细视图，两者互补
   - 裁决：保持现状，日历为单医生详细视图，甘特图为多医生概览视图（P2 不急迫）

2. **排班统计是否需要增加导出功能**
   - PM：未在需求中提出
   - Designer：统计页面缺少导出按钮
   - 裁决：排入后续迭代，标记为 P2

### 行动计划

#### P0 — 必须修复（2项）

**P0-1：统一停诊操作路径**
- 问题：排班列表的批量停诊/单条停诊直接修改 status，不创建 ScheduleSuspension 记录
- 影响范围：
  - `apps/admin/src/pages/schedule/detail/index.tsx` — handleSuspend、handleBatchSuspend
  - `packages/api/src/modules/schedule.ts` — suspend/batchSuspend 方法
  - `apps/server/app/modules/schedules/router.py` — batch-suspend 端点
- 方案：排班列表的停诊操作全部改为调用 `scheduleSuspensionApi.create()`，与停诊管理使用同一路径
- 后端 batch-suspend 端点应创建 ScheduleSuspension 记录
- 成本估算：2天（前端 0.5天 + 后端 1天 + 测试 0.5天）
- 负责角色：后端工程师 + 前端工程师

**P0-2：修复统计接口 store_id 过滤缺失**
- 问题：`get_schedule_statistics` 第1步查询只有 `doctor_id IN doctor_map` 条件，缺少 `store_id` 过滤
- 影响范围：
  - `apps/server/app/modules/schedules/router.py` 第226-236行
- 方案：在普通排班查询中增加 `Schedule.store_id == store_id` 条件
- 成本估算：0.5天
- 负责角色：后端工程师

#### P1 — 建议修复（3项）

**P1-1：提取门店权限过滤公共 Hook**
- 问题：门店过滤逻辑在 5+ 个组件中重复（rule/index.tsx、rule/form.tsx、detail/index.tsx、gantt/index.tsx、suspension.tsx、custom.tsx、custom-form.tsx、rest-day-form.tsx）
- 方案：创建 `useStoreWithPermission` 自定义 Hook，封装门店加载和权限过滤
- 成本估算：1.5天（Hook 开发 0.5天 + 各组件迁移 0.5天 + 测试 0.5天）
- 负责角色：前端工程师

**P1-2：对齐排班规则预览的前后端周数计算逻辑**
- 问题：前端 `getDateInfo` 使用 `Math.ceil(date.getDate() / 7)` 计算月内周数，后端 `should_generate_schedule` 使用 Python 的 `isoweekday` 和类似逻辑
- 方案：统一使用 ISO 周计算；增加后端预览接口（POST `/schedule-templates/preview-generate` 已存在，前端应调用后端接口而非纯前端计算）
- 成本估算：1天（前端调用后端预览接口替代纯前端计算 0.5天 + 测试 0.5天）
- 负责角色：前端工程师

**P1-3：排班列表新增排班弹窗补充预约类型和时间区间**
- 问题：新增排班弹窗只有 科室->医生->日期->时段->号源，缺少预约类型、具体时间区间
- 方案：参考自定义排班表单，在 ModalForm 中增加预约类型 Select 和 开始/结束时间 TimePicker
- 成本估算：1天
- 负责角色：前端工程师

#### P2 — 后续迭代（3项）

**P2-1：修复 Schema 注释中 AM/PM 遗留**
- 问题：`schedule.py` Schema 注释中有多处 "AM上午/PM下午" 遗留
- 方案：统一更新注释为 "morning上午/afternoon下午/evening晚间"
- 成本估算：0.5天
- 负责角色：后端工程师

**P2-2：甘特图加载优化**
- 问题：甘特图全量加载排班数据，数据量大时性能有风险
- 方案：引入虚拟滚动或后端聚合接口（返回按医生+日期+时段聚合的数据，而非逐条排班）
- 成本估算：3天
- 负责角色：全栈工程师

**P2-3：排班统计导出功能**
- 问题：统计页面缺少数据导出能力
- 方案：增加 Excel 导出按钮，复用后端统计接口数据
- 成本估算：2天
- 负责角色：前端工程师

---

## 独到发现

1. **排班创建的分布式锁粒度设计合理**：使用 `租户+医生+日期+时间段` 作为锁粒度，既保证幂等性又避免不同租户/不同医生互相阻塞
2. **停诊通知机制完整**：停诊时自动通知医生和受影响的患者，且通知失败不影响停诊操作（try/catch 隔离）
3. **请求去重机制**：排班日历使用 `requestDeduplicator` 避免并发相同请求，这是少见的前端性能优化
4. **排班生成的事务隔离**：Celery 任务中每个租户、每个模板使用独立事务，避免单点失败导致全局回滚

---

## 附录

### 文件清单

**前端页面（12个）：**
- `apps/admin/src/pages/schedule/rule/index.tsx` — 排班规则列表
- `apps/admin/src/pages/schedule/rule/form.tsx` — 排班规则表单
- `apps/admin/src/pages/schedule/calendar/index.tsx` — 排班日历
- `apps/admin/src/pages/schedule/calendar/components/MonthView.tsx` — 月视图
- `apps/admin/src/pages/schedule/calendar/components/WeekView.tsx` — 周视图
- `apps/admin/src/pages/schedule/calendar/components/DoctorSelector.tsx` — 医生选择器
- `apps/admin/src/pages/schedule/calendar/components/DayDetailDrawer.tsx` — 日期详情抽屉
- `apps/admin/src/pages/schedule/gantt/index.tsx` — 排班甘特图
- `apps/admin/src/pages/schedule/detail/index.tsx` — 排班列表
- `apps/admin/src/pages/schedule/custom.tsx` — 自定义排班列表
- `apps/admin/src/pages/schedule/custom-form.tsx` — 自定义排班表单
- `apps/admin/src/pages/schedule/suspension.tsx` — 停诊管理
- `apps/admin/src/pages/schedule/rest-day.tsx` — 休息日列表
- `apps/admin/src/pages/schedule/rest-day-form.tsx` — 休息日表单
- `apps/admin/src/pages/schedule/statistics.tsx` — 排班统计
- `apps/admin/src/pages/schedule/utils/message.ts` — 消息文案

**后端文件（8个）：**
- `apps/server/app/modules/schedules/router.py` — 排班路由（624行）
- `apps/server/app/modules/schedules/service_query.py` — 查询服务
- `apps/server/app/modules/schedules/service_mutation.py` — 变更服务
- `apps/server/app/modules/schedules/service_generation.py` — 生成服务
- `apps/server/app/modules/schedule_suspensions/service.py` — 停诊服务
- `apps/server/app/models/schedule.py` — 排班模型
- `apps/server/app/models/schedule_suspension.py` — 停诊模型
- `apps/server/app/tasks/schedule_task.py` — 定时任务
- `apps/server/app/schemas/schedule.py` — 排班 Schema

**共享包（2个）：**
- `packages/api/src/modules/schedule.ts` — 前端 API 封装
- `packages/shared/src/constants/schedule.ts` — 共享常量和工具函数

### 总成本估算

| 优先级 | 项数 | 总工时 |
|---|---|---|
| P0 | 2 | 2.5天 |
| P1 | 3 | 3.5天 |
| P2 | 3 | 5.5天 |
| **合计** | **8** | **11.5天** |
