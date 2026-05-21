# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：对等协作
> 日期：2026-05-20
> 审查目标：医生排班系统完整大版本实施方案

---

## 模式选择

**选定模式：** 对等协作

**选择理由：** 三个维度权重均衡（产品、UX、工程），存在跨职能权衡需要结构化辩论（双状态机设计、拖拽可行性、停诊处置复杂度），对等模式可最大化交叉碰撞发现盲区。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约
- 现有排班模块覆盖：Schedule（排班表）、ScheduleTemplate（排班模板）、RestDay（休息日）、ScheduleSuspension（停诊）、LeaveRequest（请假/调班）、DoctorBookingSetting（预约设置）、ScheduleGenerationLog（生成日志）
- 来源：`apps/server/app/models/schedule.py`、`schedule_template.py`、`rest_day.py`、`schedule_suspension.py`、`leave_request.py`、`doctor_booking_setting.py`

**功能完成度：**
- 已实现 17 个排班端点、14 个模板端点、4 个停诊端点、4 个休息日端点
- 已实现：排班 CRUD、批量创建/停诊/恢复/删除、模板生成排班、自定义排班、排班统计（利用率趋势/医生工作量/高峰时段热力图）、可预约排班查询（含规则引擎）
- 未实现：诊室管理、号源拆分（线上/线下/预留/加号）、发布状态机、冲突检测服务、拖拽调整、批量复制、节假日管理、停诊患者处置闭环、加号审批
- 来源：`apps/server/app/modules/schedules/router.py`、`schedule_templates/router.py`

**预约与排班关联：**
- Appointment.schedule_id FK -> schedules.id，预约创建时 schedule.booked_slots += 1，取消时 -= 1
- 号源消费使用 Redis 分布式锁（锁键 `appointment:create:{schedule_id}`，超时 5s，重试 3 次）
- 无悲观锁（select_for_update），全部依赖 Redis 分布式锁 + ORM 脏检查
- 来源：`apps/server/app/modules/appointments/service_booking.py:179-260`

**停诊/休息日能力：**
- 停诊：创建时更新 schedule.status=0，支持按 schedule_ids/time_slots/全天三种粒度，自动发送停诊通知
- 休息日：doctor_ids JSON 数组（NULL 表示门店所有医生），支持日期范围，排班模块多处检查休息日
- 请假/调班：LeaveRequest 支持 stop_clinic/schedule_change 两种类型，有审核流程（pending/approved/rejected/cancelled）
- 来源：`apps/server/app/modules/schedule_suspensions/service.py:87-398`、`rest_days/router.py`

**通知渠道：**
- 5 个已注册渠道：in_app、wechat、sms、email、websocket
- 排班相关事件：schedule（websocket->in_app）、stop_clinic（wechat->sms->in_app）
- 支持渠道降级、去重（Redis 24h TTL）、用户偏好过滤、免打扰时段、重试机制（max_retries=3）
- 来源：`apps/server/app/infrastructure/notifications/dispatcher.py:46-57`

**权限体系：**
- 现有排班权限：schedule:create、schedule:update、schedule:delete（Admin）；doctor:schedule:view、doctor:schedule:edit（Doctor）
- 缺少：schedule:read（独立读权限）、schedule:publish、schedule:suspend、schedule:extra-quota、schedule:extra-quota:approve、schedule:holiday、schedule:room
- 角色体系：SUPER_ADMIN、PLATFORM_ADMIN、TENANT_ADMIN、STORE_ADMIN、DOCTOR、PATIENT
- 来源：`apps/server/app/common/role_permissions.py`、各 router.py 中 require_permission() 调用

**多租户隔离：**
- 排班相关表均有 tenant_id（schedules、schedule_templates、schedule_suspensions、rest_days、leave_requests、appointments）
- 例外：doctor_booking_settings 无 tenant_id
- 排班查询有租户过滤，但 schedule_templates 和 rest_days 的路由层无显式 tenant_id 过滤
- 来源：各模型文件、`modules/schedule_templates/router.py`、`modules/rest_days/router.py`

---

### Designer — 用户视角

**页面清单与结构：**
- 13 条排班相关路由（`apps/admin/config/routes/medical-services.ts:39-58`）
- 核心页面代码量：排班规则列表 898 行、排班列表 548 行、排班日历 302 行、甘特图 529 行、排班统计 534 行
- 日历组件集：WeekView(152)、MonthView(160)、DayDetailDrawer(183)、TimeSlotCell(112)、CalendarHeader(95)、DoctorSelector(126)、StatusLegend(29)
- 医生详情页有独立排班 Tab（DoctorScheduleTab 188 行、ScheduleCalendar 197 行、ScheduleEditModal 267 行）
- 来源：`apps/admin/src/pages/schedule/` 目录

**交互模式统计：**
- 日历视图：全部自定义实现，未使用 react-big-calendar/fullcalendar 等第三方库
- 周视图：CSS Grid（`grid-template-columns: 60px repeat(7, 1fr)`），30 分钟时间轴（08:00-21:00）
- 月视图：antd Calendar 组件 + 自定义 cellRender
- 甘特图：纯 CSS flex/grid 实现
- modal.confirm 调用 7 处（删除确认、停诊确认、恢复确认等）
- Popconfirm 使用多处（取消休息日、取消停诊等）
- 来源：各页面文件

**弹窗/表单模式：**
- Modal 使用：简单信息展示/详情查看
- Drawer 使用：DayDetailDrawer(400px)、甘特图详情(400px)、停诊审核(450px)
- ModalForm（ProComponents）：新增排班、批量添加、停诊添加、从模板生成
- 步骤式表单：排班规则表单（3 步 Steps）、复制规则弹窗（2 步 Steps）
- 嵌套弹窗：ScheduleEditModal 内嵌套"添加排班"子 ModalForm
- 弹窗宽度：400px~1300px 不等
- 来源：各组件文件

**拖拽库现状：**
- @dnd-kit 已安装（core ^6.3.1、sortable ^10.0.0、modifiers ^9.0.0、utilities ^3.2.2）
- 当前仅用于医生列表排序和科室排序（SortableTable 组件）
- 排班相关页面中未使用任何拖拽功能
- 来源：`apps/admin/package.json:22-25`、`components/SortableTable/index.tsx`

**组件库现状：**
- antd ^6.3.7 + @ant-design/pro-components 3.1.12-0
- ProComponents 使用贯穿：PageContainer、ProTable、ProForm/ModalForm、全套 ProFormXxx 组件
- @ant-design/charts ^2.6.6 用于统计图表（Line/Column/Heatmap）
- dayjs ^1.11.10 日期处理、ahooks ^3.9.7 Hooks 工具库
- 来源：`apps/admin/package.json`

**设计系统/样式规范：**
- 主题色：APP_PRIMARY_COLOR = '#1677ff'（Ant Design 默认蓝）
- CSS 变量仅 4 个间距变量（global.less:30-35）
- Less 变量仅日历页面 6 个状态颜色（calendar.less:1-7）
- 大量硬编码颜色值（#1890ff、#52c41a、#722ed1、#ff4d4f、#999 等）
- antd-style ^4.1.0 CSS-in-JS 方案可用但排班页面未使用
- 来源：`apps/admin/src/themes/themeConfig.ts`、`global.less`、`calendar.less`

**响应式和布局：**
- 流式布局（contentWidth: 'Fluid'）
- 排班页面无 @media 查询（仅甘特图有 2 处：max-width:1200px 和 print）
- 日历页面无响应式适配
- 布局模式：Row/Col 栅格、CSS Grid（周视图）、固定宽度列（甘特图）
- 来源：`config/layout/runtime-settings.ts`、`gantt/gantt.less:247-275`

---

### Engineer — 技术视角

**存储层事实：**
- Schedule 模型 18 个字段，无显式唯一约束，仅 tenant_id 有索引
- ScheduleTemplate 模型 18 个字段，break_times 为 Text/JSON 存储
- RestDay.doctor_ids 为 Text/JSON 存储
- ScheduleSuspension.schedule_ids/time_slots 为 Text/JSON 存储
- DoctorBookingSetting 有唯一约束 UniqueConstraint('store_id', 'doctor_id')
- 所有排班表继承 Base + AuditMixin（created_at/updated_at/created_by/updated_by）
- 来源：各模型文件

**核心引擎事实：**
- 服务架构：组合模式，ScheduleService = ScheduleQueryMixin + ScheduleMutationMixin + ScheduleGenerationMixin
- 排班创建：Redis 分布式锁（锁键 `schedule:create:{doctor_id}:{date}:{time_slot}`，超时 10s，重试 5 次）
- 排班生成：模板生成 + 幂等创建（IntegrityError 兜底）+ 休息日检查
- effective_status 为动态计算属性（suspended/custom/rest_day/overridden/active），非持久化
- 号源对账定时任务：reconcile_booked_slots，比较 booked_slots 与实际活跃预约 COUNT，偏差自动修复
- 来源：`apps/server/app/modules/schedules/service.py`、`service_query.py`、`service_mutation.py`、`service_generation.py`

**并发控制机制：**
- 全部使用 Redis 分布式锁，无数据库层悲观锁（select_for_update 全库搜索为空）
- 预约创建锁：`appointment:create:{schedule_id}`，超时 5s
- 预约取消锁：`appointment:cancel:{schedule_id}`，超时 10s
- 排班创建锁：`schedule:create:{doctor_id}:{date}:{time}`，超时 10s
- 取消预约有竞态保护：条件 UPDATE `WHERE status=0` + rowcount 检测
- 来源：`apps/server/app/core/redis.py:818-862`、`service_booking.py:449-464`

**状态机事实：**
- Schedule.status 仅两个值：0（停诊）、1（正常），无复杂状态机
- ScheduleSuspension.status：0（已取消）、1（生效中）
- Appointment.status 有 9 个值（0-8），有完整流转路径
- 无事件/信号机制用于状态变更通知
- 来源：`schedule.py:36`、`schedule_suspension.py:20`、`appointments/common.py:24-32`

**数据库迁移现状：**
- 87+ 个迁移文件，命名规范 `{序号三位}_{描述}.py`
- 有数据迁移先例：083_backfill_shift_type_id_for_templates.py（原生 SQL UPDATE FROM 子查询）
- 有幂等性检查先例：082 使用 column_exists/index_exists 检查
- 最新迁移编号：086
- 来源：`apps/server/migrations/versions/`

**事务控制：**
- 无 session.begin() 显式事务，全部依赖 autocommit=False + 手动 commit/rollback
- Celery 任务使用同步引擎 get_sync_db()，每个模板独立 SessionLocal
- 排班生成任务无分布式锁保护，依赖查询去重 + IntegrityError 兜底
- 连接池：异步 pool_size=5/max_overflow=10/pool_recycle=300s
- 来源：`apps/server/app/db/session.py`、`core/config.py:41-51`、`tasks/schedule_task.py`

**测试基础设施：**
- 默认 SQLite 内存数据库 + StaticPool，function 级隔离
- PostgreSQL 集成测试通过 TEST_DATABASE_URL 环境变量启用
- 排班相关 fixtures：test_tenant、test_store、test_department、test_doctor、test_schedule、test_schedule_full、test_appointment、test_shift_type、test_rule_set
- Redis Mock：mock_redis fixture 模拟 distributed_lock/get/set/delete
- 排班单元测试 22 个（test_schedule_service.py）、排班任务测试 12 个（test_schedule_task.py）
- 来源：`apps/server/tests/conftest.py`、`tests/unit/test_schedule_service.py`、`tests/unit/test_schedule_task.py`

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 完整投票矩阵（对等协作模式）

| 议题 | PM | Designer | Engineer | Critic 质询 | 共识？ |
|------|-----|----------|----------|-------------|--------|
| 号源拆分（线上/线下/预留/加号） | +1（核心竞争力） | +1（TimeSlotCell 仅显示聚合数字） | +1，32-40h | 质询2：必要性未论证 | ✅ 3/3 |
| 发布状态机（draft/published） | +1（无法先排班再统一发布） | +1（缺少草稿预览安全感） | +1，20-24h | 质询2：当前二态是否够用 | ✅ 3/3 |
| 停诊患者处置闭环 | +1（用户留存关键路径） | +1（患者无一键改约路径） | +1 且高优先级，24-28h | -- | ✅ 3/3 |
| 多租户隔离修复 | +1（安全漏洞） | +1（跨租户数据泄露） | +1，应为 P0，4-6h | 质询4：严重性被低估 | ✅ 3/3（优先级分歧） |
| Schedule 复合唯一约束 | +1（数据完整性底线） | +1（视觉混乱） | +1 交叉发现，3-4h | 质询5：实际重复风险未评估 | ✅ 3/3 |
| 拖拽排班调整 | +1（杀手级体验差异） | +1（@dnd-kit 已安装） | +1 但成本高，36-44h | -- | ✅ 3/3 |
| 冲突检测服务 | +1 | -- | +1 但可降优先级，16-20h | -- | ⚠️ 2/3 |
| 排班生成任务锁 | -- | +1（进度反馈缺失） | +1 交叉发现，2-3h | -- | ✅ 2/2 |
| 硬编码颜色/设计系统 | +1（品牌定制能力） | +1（三种蓝色不一致） | +1 但低优先级，8-12h | -- | ✅ 3/3 |
| 响应式适配 | 反驳（桌面端有意取舍） | +1（移动端不可用） | 反驳（不建议投入） | -- | ⚠️ 1/3 |
| 自定义日历组件 | -- | 发现（未用第三方库） | 反驳（正确选择） | 质询6：为何呈现为负面 | ⚠️ 0/3 |
| 通知降级 UX | +1 交叉发现（短信内容等价性） | -- | -- | -- | 新增 |
| 权限体系扩展 | +1 交叉发现（商业化基础） | +1 交叉发现（权限颗粒度不足） | -- | -- | ✅ 2/2 |
| 连接池调优 | -- | -- | +1 交叉发现，1h | -- | 新增 |
| effective_status 性能 | -- | -- | +1 交叉发现，8-12h | -- | 新增 |

### 独到发现

1. **号源拆分的产品必要性被三方遗漏**（PM 交叉发现）：当前 total_slots 无法区分线上/线下/预留渠道，这是"全栈医院预约挂号系统"定位的核心缺失
2. **键盘导航完全缺失**（Designer 交叉发现）：排班页面有 ARIA 属性但无键盘交互（onKeyDown 等），屏幕阅读器用户无法操作，合规性风险
3. **三种蓝色混用**（Designer 交叉发现）：#1677ff（antd 主题蓝）、#1890ff（旧版 antd 蓝）、#2196F3（Material 蓝）在同一页面出现
4. **Schedule 模型无复合唯一约束**（Engineer 交叉发现）：Redis 锁有超时，数据库层唯一约束是最终防线，3-4h 可修复
5. **排班生成任务无分布式锁**（Engineer 交叉发现）：快速连续点击可能触发并发生成，2-3h 可修复
6. **连接池偏保守**（Engineer 交叉发现）：pool_size=5/max_overflow=10 在高并发排班场景下可能成为瓶颈，1h 可调
7. **effective_status N+1 性能隐患**（Engineer 交叉发现）：50 条排班 × 每条独立计算状态 = 大量额外查询，8-12h 可优化
8. **停诊工作流断裂**（Designer 交叉发现）：患者收到通知后无一键改约路径，需手动重新预约
9. **号源对账对用户不可见**（Designer 交叉发现）：reconcile_booked_slots 自动修复偏差但用户无感知

### Critic 质询

1. [Critic → 全体] 质询 1：PM 声称 doctor_booking_settings "未被读取"，但代码显示 `get_available()` 已通过 `_get_booking_setting()` 完整读取了 booking_start_offset/booking_range_days/release_time。PM 的断言与代码事实矛盾。
   - 要求回应：PM / Engineer
   - 级别：普通

2. [Critic → 全体] 质询 2：三方对 9 项"未实现"功能的判断标准不一致，且未提供用户调研/运营反馈/工单数据来支撑必要性。发布状态机、拖拽调整、号源拆分是否是假设性需求？
   - 要求回应：PM
   - 级别：普通

3. [Critic → 全体] 质询 3：Engineer 将全部并发控制描述为"无悲观锁、全部依赖 Redis"，过度简化。预约创建/取消/排班创建三层锁已覆盖最高频写操作，表述暗示存在系统性缺陷。
   - 要求回应：Engineer
   - 级别：普通

4. [Critic → 全体] 质询 4：doctor_booking_settings 无 tenant_id 是真实的多租户隔离缺陷，但三方均未评估严重性。通过 JOIN Store 间接过滤依赖 store 租户归属始终正确，无法防止跨租户 store_id 引用攻击。
   - 要求回应：PM / Engineer
   - 级别：普通

5. [Critic → 全体] 质询 5：Schedule 模型无唯一约束，三方均提到了但未评估实际数据重复风险。当 time_slot 为空时锁键 `schedule:create:{doctor_id}:{date}:None` 可能无法精确区分不同时间段排班。
   - 要求回应：Engineer
   - 级别：普通

6. [Critic → Designer] 质询 6：自定义日历组件被呈现为隐含负面发现，但未评估替代方案。WeekView 152 行 + MonthView 160 行体量不大，antd Calendar + 自定义 cellRender 可能是更合理的选择。
   - 要求回应：Designer
   - 级别：普通

7. [Critic → 全体] 质询 7：三方均未引用 2026-05-11 的 scheduling-rule-system-review 结论。之前标记的 P0 项（如 doctor_booking_settings 接入可预约查询）代码显示已完成，本次方案范围需要重新评估。
   - 要求回应：PM / Engineer
   - 级别：普通

8. [Critic → PM] 质询 8：方案缺少竞品对比。号源拆分、发布状态机、拖拽排班在同类 SaaS 医疗预约系统中是标配还是高级功能？缺乏外部参照无法判断是否过度设计。
   - 要求回应：PM
   - 级别：普通

9. [Critic → 全体] 质询 9：三方忽略了系统核心优势——effective_status 五态计算、号源对账任务、通知渠道降级链、排班生成幂等性、请求去重机制。这些已有能力是否已部分覆盖"未实现"功能需求？
   - 要求回应：PM / Designer / Engineer
   - 级别：普通

### 🚨 Critic 关键质询追踪

Critic 选择不标记任何关键质询。理由：所有问题属于"信息准确性和论证充分性"层面，未达到"根本性逻辑缺陷或重大遗漏"阈值。

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| -- | 无关键质询 | -- | -- | -- |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：多租户隔离修复**
   **结论：** doctor_booking_settings 无 tenant_id 是真实安全漏洞，templates/rest_days 路由层缺少显式租户过滤是防御性缺口。3/3 方同意。
   **建议行动：** doctor_booking_settings 加 tenant_id 字段+迁移；路由层加显式租户过滤；schedule_suspensions 路由层同样检查。
   **成本估算：** 4-6h（Engineer）
   **优先级：** P0

2. **议题：Schedule 复合唯一约束**
   **结论：** 无数据库层唯一约束，Redis 锁超时后可能产生重复排班。3/3 方同意。
   **建议行动：** 新增 UniqueConstraint(doctor_id, schedule_date, start_time, end_time) + 迁移 + IntegrityError 处理。
   **成本估算：** 3-4h（Engineer）
   **优先级：** P0

3. **议题：排班生成任务分布式锁**
   **结论：** Celery 任务无锁保护，快速连续点击可能触发并发生成。2/2 方同意。
   **建议行动：** Celery 任务入口加 Redis 分布式锁（复用现有模式）。
   **成本估算：** 2-3h（Engineer）
   **优先级：** P0

4. **议题：停诊患者处置闭环**
   **结论：** 当前停诊仅发通知，无自动改约/退号/推荐其他医生的闭环。3/3 方同意，且 Engineer 标记为高优先级。
   **建议行动：** schedule_suspensions 增强（suspension_type/processing_method/processing_status），支持自动退号退款、转约、改期、人工处理，异步处置+通知。
   **成本估算：** 24-28h（Engineer）
   **优先级：** P1（依赖发布状态机）

5. **议题：发布状态机**
   **结论：** 当前 Schedule.status 仅 0/1 无法表达草稿/已发布/已停诊等状态。3/3 方同意。
   **建议行动：** 新增 schedule_status 字段（draft/published/booking/full/suspended/finished/withdrawn），保留旧 status 兼容。
   **成本估算：** 20-24h（Engineer）
   **优先级：** P1（号源拆分和停诊处置的前置依赖）

6. **议题：号源拆分（线上/线下/预留/加号）**
   **结论：** total_slots 无法区分渠道来源，是产品定位的核心缺失。3/3 方同意。
   **建议行动：** Schedule 新增 online_quota/offline_quota/reserved_quota/extra_quota 字段，预约/取消/对账逻辑改造。
   **成本估算：** 32-40h（Engineer）
   **优先级：** P1（依赖发布状态机）

7. **议题：拖拽排班调整**
   **结论：** 3/3 方同意价值高，但 Engineer 评估成本 36-44h。
   **建议行动：** @dnd-kit 实现二维网格拖拽 + 后端 drag-adjust API + 冲突实时检查。
   **成本估算：** 36-44h（Engineer）
   **优先级：** P2

8. **议题：排班生成任务锁 + 连接池调优**
   **结论：** 低成本高价值的工程改进。2/2 方同意。
   **建议行动：** Celery 任务加锁 2-3h；连接池 pool_size/max_overflow 调优 1h。
   **成本估算：** 3-4h（Engineer）
   **优先级：** P0

### ⚡ 分歧项

1. **议题：响应式适配（移动端）**
   **各方立场：**
   - PM：反驳，桌面端管理后台有意不做移动端，患者端才是移动场景
   - Designer：+1，移动端查看排班是合理需求，当前完全不可用
   - Engineer：反驳，不建议投入，0h
   **裁决/建议：** 管理端排班日历不做响应式（PM+Engineer 立场），但可考虑独立的"医生端排班查看"轻量页面（Designer 关注点）。
   **决策依据：** 排班管理是桌面端高信息密度操作，移动适配 ROI 低。

2. **议题：自定义日历组件 vs 第三方库**
   **各方立场：**
   - Designer：发现（隐含建议引入第三方库）
   - Engineer：反驳，自定义实现是正确选择（1111 行，体量可控），引入 fullcalendar 40-50h
   - Critic：质疑为何呈现为负面发现
   **裁决/建议：** 维持自定义实现。但拖拽功能实现时需评估是否引入 fullcalendar 的拖拽能力（Engineer 提示）。
   **决策依据：** 当前体量可控，但拖拽场景可能逆转成本天平。

---

## 被低估的优势

1. **effective_status 五态计算**：动态状态机比持久化状态更灵活，批量加载休息日和自定义排班后内存计算避免 N+1（但有性能隐患需优化）
2. **号源对账定时任务**：reconcile_booked_slots 自动修复 booked_slots 偏差，是防御性设计
3. **通知渠道降级链**：5 渠道注册 + 降级策略 + Redis 去重 + 免打扰时段 + 重试机制，是成熟基础设施
4. **排班生成幂等性**：模板生成 + IntegrityError 兜底 + 每模板独立事务
5. **Redis 分布式锁三层保护**：预约创建/取消/排班创建三层锁覆盖最高频写操作

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 多租户隔离修复（doctor_booking_settings 加 tenant_id + 路由层租户过滤） | 4-6h | 高（安全） | Engineer | 待执行 |
| P0 | Schedule 复合唯一约束 | 3-4h | 高（数据完整性） | Engineer | 待执行 |
| P0 | 排班生成任务分布式锁 | 2-3h | 高（并发安全） | Engineer | 待执行 |
| P0 | 连接池调优 | 1h | 中（性能） | Engineer | 待执行 |
| P1 | 发布状态机（schedule_status 字段 + 状态流转） | 20-24h | 高 | Engineer | 待执行 |
| P1 | 停诊患者处置闭环 | 24-28h | 高 | Engineer + PM | 待执行 |
| P1 | 号源拆分（online/offline/reserved/extra quota） | 32-40h | 高 | Engineer | 待执行 |
| P1 | 权限体系扩展（8 个新权限节点） | 8-10h | 中 | Engineer | 待执行 |
| P1 | 硬编码颜色统一为设计 token | 8-12h | 中 | Designer + Engineer | 待执行 |
| P2 | 拖拽排班调整 | 36-44h | 高 | Engineer + Designer | 待执行 |
| P2 | 冲突检测服务 | 16-20h | 中 | Engineer | 待执行 |
| P2 | effective_status 性能优化（批量预计算+缓存） | 8-12h | 中 | Engineer | 待执行 |
| P2 | 通知降级 UX（短信内容等价性） | 4-6h | 中 | PM + Engineer | 待执行 |
| 待定 | 键盘无障碍合规 | 16-20h | 中 | Designer + Engineer | 需用户确认 |
| 待定 | 节假日管理模块 | 16-20h | 中 | PM + Engineer | 需用户确认 |
| 待定 | 日历组件抽象层（未来复用） | 8-12h | 低 | Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **多租户隔离修复** — doctor_booking_settings 加 tenant_id 字段（Alembic 迁移）+ 路由层为 schedule_templates/rest_days/schedule_suspensions 加显式租户过滤。成本 4-6h，负责：Engineer。
2. **Schedule 复合唯一约束** — 新增 UniqueConstraint(tenant_id, doctor_id, schedule_date, start_time, end_time)，迁移文件 + service 层 IntegrityError 处理。成本 3-4h，负责：Engineer。
3. **排班生成任务分布式锁** — Celery 任务入口加 Redis 锁（复用 `schedule:generate:{template_id}` 模式）。成本 2-3h，负责：Engineer。
4. **连接池调优** — pool_size 从 5 调到 10，max_overflow 从 10 调到 20。成本 1h，负责：Engineer。

**P0 总成本：10-14h**

### P1：本轮迭代（高价值、中等成本）

1. **发布状态机** — Schedule 新增 schedule_status 枚举字段，保留旧 status 兼容，实现草稿→发布→预约中→已满/已结束流转。成本 20-24h，负责：Engineer。
2. **停诊患者处置闭环** — schedule_suspensions 增强，支持自动退号退款/转约/改期/人工处理，异步处置+通知。成本 24-28h，负责：Engineer + PM。
3. **号源拆分** — Schedule 新增 online/offline/reserved/extra quota 字段，预约/取消/对账逻辑改造。成本 32-40h，负责：Engineer。
4. **权限体系扩展** — 新增 8 个权限节点 + 角色默认分配。成本 8-10h，负责：Engineer。
5. **设计 token 统一** — 提取 CSS 变量，替换硬编码颜色，建立状态色规范。成本 8-12h，负责：Designer + Engineer。

**P1 总成本：92-114h**

### P2：下个周期规划（中等价值、较高成本）

1. **拖拽排班调整** — @dnd-kit 二维网格拖拽 + drag-adjust API + 冲突检查。成本 36-44h，负责：Engineer + Designer。
2. **冲突检测服务** — 医生时间冲突/诊室冲突/午休覆盖/节假日检查。成本 16-20h，负责：Engineer。
3. **effective_status 性能优化** — 批量预计算 + 缓存层。成本 8-12h，负责：Engineer。
4. **通知降级 UX** — 短信内容与微信消息等价性保障。成本 4-6h，负责：PM + Engineer。

**P2 总成本：64-82h**

### 待定：需用户确认

1. **键盘无障碍合规** — 排班页面 ARIA 属性+键盘导航完善。成本 16-20h。理由：中国 GB/T 37668-2019 合规要求需确认是否适用。
2. **节假日管理模块** — schedule_holidays 表 + 法定/院内/调休类型 + 排班生成时跳过。成本 16-20h。理由：当前 rest_days 已覆盖基本需求，节假日是否为独立模块需确认。
3. **日历组件抽象层** — 提取通用日历组件供患者端/诊室占用等场景复用。成本 8-12h。理由：目前仅排班日历使用，复用场景不明确。

---

## 摘要

**使用模式：** 对等协作

**关键共识：**
- 8 项达成共识（3/3 或 2/2 同意）
- P0 安全/数据完整性修复 4 项（10-14h）
- P1 核心功能增强 5 项（92-114h）

**关键分歧：**
- 2 项需要决策者介入（响应式适配、自定义日历 vs 第三方库）
- 已裁决：管理端不做响应式，维持自定义日历

**Top 3 P0 行动：**
1. 多租户隔离修复（4-6h）— doctor_booking_settings 加 tenant_id + 路由层租户过滤
2. Schedule 复合唯一约束（3-4h）— 防止重复排班的数据完整性底线
3. 排班生成任务分布式锁（2-3h）— 防止并发生成的并发安全

**Critic 关键洞察：**
- 9 条质询中 0 条标记为关键，说明方案方向正确但论证需要加强
- 最有影响力的质询：doctor_booking_settings 已接入可预约查询（PM 断言与代码矛盾）、9 项"未实现"功能的必要性未提供用户数据支撑
- 系统已有优势被低估：effective_status 五态计算、号源对账任务、通知降级链、Redis 三层锁保护

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
