# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-04-18
> 审查目标：预约规则配置、设置、排班逻辑跨端（admin/server/小程序）优化审查

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 跨三端（admin/server/小程序）全链路审查，无单一主导领域，三个维度（产品/交互/技术）权重相当，集中调度收敛最快且输出完整度最高。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位与功能清单：**
- Admin 端排班管理含 13 个页面 + 26 个组件文件，覆盖规则设置/日历/自定义排班/休息日/停诊/统计
- Admin 端预约管理含 4 个页面（列表/队列/统计/详情）
- 规则配置在配置中心：规则组、班次类型、预约须知、医生预约设置
- 小程序端预约：4 个主页面（预约确认/结果/详情/列表）+ 扫码签到
- 医生端：今日预约、就诊管理、排班日历查看

**排班功能产品形态：**
- 创建方式：模板排班（ScheduleTemplate）+ 自定义排班（CustomSchedule）+ 停诊排班（ScheduleSuspension）
- 排班粒度：按天/按时段/按班次/按时间槽（morning/afternoon/evening）
- 排班与科室/医生/诊室：doctor_id 外键关联，department 通过医生间接关联，store_id 关联门店
- 排班状态流转：创建(1) → 预约中(booked_slots++) → 已满 → 停诊(0)

**预约规则配置项：**
- 规则组（RuleSet）：17 字段，含时间来源/时区来源/比较精度/取整模式/时钟偏差容忍度
- 时间窗（RuleWindow）：12 字段，支持 BOOK/CHECKIN/CANCEL/HOLD_RELEASE 四种动作
- 预约策略（RuleBookingPolicy）：9 字段，含用户配额/冲突策略
- 签到策略（RuleCheckinPolicy）：9 字段，含宽限期/未签到处理
- 容量策略（RuleCapacityPolicy）：8 字段，含候补/超额
- 医生预约设置（DoctorBookingSetting）：7 字段，偏移天数/范围天数/放号时间
- 规则生效范围：租户级（规则组/班次类型）→ 门店级（医生设置）→ 班次级（排班应用规则组）

**多端功能覆盖对比：**
- 排班管理仅 Admin 端（创建规则/生成排班/自定义排班/休息日/停诊）
- 预约创建：Admin + Patient-miniapp
- 取消预约：Admin + Patient（条件不同：Admin 仅 status=0，Patient 允许 status=1,2）
- 签到：Patient 扫码 + Admin 确认
- 规则配置仅 Admin 端

**预约流程完整链路：**
- 正常流程：患者选排班 → 填就诊人 → [免费→已预约] / [付费→待支付→支付→已预约] → 签到 → 候诊 → 就诊 → 完成
- 取消：Admin 仅 status=0 可取消，Patient 允许 status=1,2，Server 允许 status=1,2
- 爽约：自动(status=7) vs 手动(status=8) 状态不一致，统计仅算 status=8
- 支付超时：Celery 任务将 status=0 标记为 status=7

**已识别问题（来自历史评审，经 Round 2 交叉验证后修正）：**
- ~~P0: complete() 无前置状态检查~~ — 已修复。service_flow.py:183 有状态检查（SIGNED/SEEING）
- ~~P0: 爽约状态不一致（手动=8 vs 自动=7）~~ — 已修复。blacklist_task.py:291 自动标记也使用 NO_SHOW(8)
- ~~P0: 预约提醒任务未考虑多租户隔离~~ — 已修复。notification_task.py:133 使用 set_tenant_context + tenant_id 过滤
- P0: Admin 爽约按钮条件 — list.tsx:321 status===1 时显示爽约按钮，代码正确（已修复或误报）

### Designer — 用户视角

**页面清单与结构：**
- Admin 端排班管理：13 页面 + 9 日历子组件，总约 8000 行代码
- 小程序端预约：4 主页面，总约 1300 行代码
- 排班规则表单：13 个字段，分 3 区（基础信息/排班设置/高级设置）
- 排班日历：周视图（7天×30分钟时间轴）+ 月视图（日历格子）

**排班管理交互模式：**
- 表单布局：左右分栏（左预览日历 sticky + 右表单卡片），FooterToolbar 固定操作栏
- 日历交互：周视图点击时间段 → 预约列表；月视图点击日期 → 详情抽屉
- 批量操作：批量生成/批量添加/复制规则/批量停诊/批量删除
- 生成排班：选择日期范围 + 预览班次 + 可编辑容量 + 冲突检测弹窗
- 复制规则：两步向导（编辑参数 → 选择目标医生）

**预约规则配置交互：**
- 卡片分组：Card1 基础信息 + Card2 排班设置 + Card3 排班方式 + Collapse 高级设置
- 规则冲突处理：生成前检测（checkGenerated API）→ 冲突弹窗 → 跳过/取消
- 排班权重：Alert 组件显示 停诊 > 自定义排班 > 休息日 > 普通排班

**患者端预约交互：**
- 4 步流程：选择医生/时段 → 预约确认（就诊人+预约信息+病情描述+须知）→ 支付 → 结果
- 就诊人切换：Radio.Group 单选
- 重复预约检测：checkDuplicate API → 确认弹窗
- 结果页：成功/失败状态 + 温馨提示 + 操作按钮

**Loading/空状态/错误：**
- Loading：Spin 组件包裹内容 + Button loading 属性
- 骨架屏：未使用 Skeleton 组件，首屏显示 "加载中..." 文字
- 空状态：Empty 组件
- 错误：message.error 全局提示 + 表单字段红字

**响应式设计：**
- Admin 表格：scroll={{ x: 1650 }} 横向滚动
- 日历视图：固定宽度布局
- 小程序：750rpx 基准，固定底部操作栏，主题色 CSS 变量

### Engineer — 技术视角

**数据模型：**
- Schedule：44 字段，含 doctor_id/store_id/template_id/shift_type_id/time_slot/total_slots/booked_slots/status
- ScheduleTemplate：36 字段，含 weekdays(JSON)/slot_count/slot_capacity/break_times(JSON)/schedule_mode
- Appointment：83 字段（含快照字段）
- RuleSet：17 字段，含 7 个默认口径配置项
- RuleWindow/RuleBookingPolicy/RuleCheckinPolicy/RuleCapacityPolicy：各 8-12 字段

**排班核心逻辑：**
- ScheduleService 采用组合模式：ScheduleMutationMixin + ScheduleQueryMixin + ScheduleGenerationMixin
- 冲突检测：Redis 分布式锁（租户+医生+日期+时间段粒度，10s 超时，5 次重试）
- 自动生成：Celery 任务每天凌晨 2 点，遍历活跃租户 + 启用模板，生成未来 N 天排班
- 号源计算：booked_slots 是反规范化计数字段，预约+1/取消-1，非 COUNT(*) 聚合。无周期性对账机制

**预约核心逻辑：**
- 创建校验链（9步）：排班存在性 → 排班状态 → 号源余量 → 休息日 → 规则引擎时间窗 → 预约冲突 → 容量限制 → 用户权限 → 黑名单
- 号源锁定：双层分布式锁（用户级 + 排班级），条件 UPDATE 防竞态
- 状态机：0待支付 → 1已预约 → 2已签到 → 3候诊中 → 4就诊中 → 5已完成 / 6已取消 / 7已过期 / 8已爽约
- 取消/爽约：支付退款同步处理，号源释放，候补自动递补

**规则引擎架构：**
- RuleEngineService：RuleEngineTimeWindowMixin + RuleEngineValidationMixin + RuleEnginePolicyMixin
- 规则匹配：班次类型关联规则组，取优先级最高（priority 最小）的启用规则组
- 规则无版本管理，无历史记录

**API 设计：**
- 排班：/schedules（CRUD + 批量操作 + 停诊/恢复）+ /schedule-templates + /custom-schedules
- 预约：/appointments（创建/取消/签到/叫号/完成/爽约/统计）
- 规则：/rule-sets（CRUD + 启用/禁用/预览 + 时间窗/策略子资源）
- 权限：get_current_admin + require_permission + get_store_filter + tenant_context 中间件

**模块耦合：**
- 预约模块依赖：schedule/rule_engine/messages/payments/refunds/waitlist
- 排班模块依赖：doctor/rest_day/messages/redis
- 规则引擎独立模块，被预约模块引用
- 无循环依赖，使用组合模式降低耦合

**前端 API：**
- packages/api/src/modules/：schedule.ts + appointment.ts + rule-set.ts
- camelCase ↔ snake_case 自动转换
- 无特殊缓存机制

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 简化投票矩阵（集中调度模式）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| Admin 取消按钮仅 status=0 | 前后端不一致，需修复前端 | 🚨 要求验证代码事实 | **确认问题** — list.tsx:313 限制 status=0，后端支持 1,2 |
| complete() 无前置检查 | ~~历史问题~~ 已修复 | 🚨 要求验证 | **已修复** — service_flow.py:183 有状态检查 |
| 爽约状态不一致 7 vs 8 | ~~历史问题~~ 已修复 | 要求验证 | **已修复** — 自动/手动均用 NO_SHOW(8) |
| Celery 多租户隔离 | 已修复 | 🚨 要求全面审查 | **已修复** — 所有任务均有 tenant_context + tenant_id 过滤 |
| 号源计算无缓存性能 | 非关键瓶颈（非 COUNT 查询） | 🚨 性能被低估 | **风险可控** — booked_slots 是字段非聚合，但缺乏对账 |
| 规则引擎无版本管理 | 真实问题，SaaS 审计需要 | 普通质询 | **确认问题** — 无 audit trail |
| Schedule 44 字段模型 | 偏大但尚可管理 | 普通质询 | **观察** — 可拆分但非紧急 |
| 排班自动生成串行执行 | 扩展性隐患 | 普通质询 | **确认问题** — 大租户量时需并行化 |
| Admin 骨架屏缺失 | 体验瑕疵 | 普通质询 | **确认问题** — 首屏 Loading 文字体验差 |

### 独到发现

1. **booked_slots 一致性风险**：该字段通过代码逻辑 +1/-1 维护，但无数据库约束（如 CHECK 约束）和周期性对账。如果极端情况下（进程崩溃、锁超时）出现不一致，没有自动修复机制。
2. **排班自动生成顺序敏感**：schedule_task.py 串行遍历租户，单个租户失败不影响其他租户（独立 try/catch），但总执行时间与租户数线性增长。
3. **Admin 端取消按钮 vs 详情页操作不统一**：列表页取消仅 status=0，但详情页可能有其他操作入口。管理员的取消权限路径不清晰。

### Critic 质询

1. [Critic → 全体] Admin 取消逻辑三端不一致是否真实？
   - 论据：PM 声称 Admin 仅 status=0 可取消，违反管理员权限高于用户的常理
   - 要求回应：提供三端代码证据
   - 级别：🚨 关键

2. [Critic → 全体] 号源计算无缓存的性能影响
   - 论据：高并发抢号场景下可能成为瓶颈
   - 要求回应：提供 booked_slots 的计算方式和锁竞争分析
   - 级别：🚨 关键

3. [Critic → 全体] 多租户 Celery 隔离是否全面
   - 论据：仅关注通知任务，其他任务未审计
   - 要求回应：全面审查所有异步任务
   - 级别：🚨 关键

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | Admin 取消按钮 status=0 限制 | list.tsx:313 确认前端限制 status=0，后端 service_booking.py:492 支持 1,2 | 是 | 纳入计划 — 修复前端取消按钮条件 |
| 2 | 号源计算性能 | booked_slots 是模型字段非聚合查询，有分布式锁保护 | 是 | 风险可控 — 补充对账机制即可 |
| 3 | Celery 多租户隔离 | 所有 6 个任务文件均已使用 set_tenant_context + tenant_id 过滤 | 是 | 已修复，无需行动 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：Admin 端取消预约按钮条件过严**
   **结论：** list.tsx:313 仅对 status=0（待支付）显示取消按钮，但后端 service_booking.py:492 支持 CONFIRMED(1) 和 SIGNED(2) 的取消。管理员无法从列表页取消已确认的预约，需进入详情页或使用其他入口。
   **建议行动：** 扩展 Admin 取消按钮条件为 status ∈ {0, 1}，增加取消原因必填
   **成本估算：** 2h（前端改动 + 后端权限校验）
   **优先级：** P0

2. **议题：booked_slots 缺乏对账机制**
   **结论：** booked_slots 是反规范化字段，通过代码 +/-1 维护。虽然创建和取消路径都有分布式锁保护，但没有数据库约束（如 `CHECK (booked_slots >= 0)`）和周期性对账任务。极端情况下（进程崩溃、锁超时后重入）可能出现偏差。
   **建议行动：** 1) 添加数据库 CHECK 约束 `booked_slots >= 0`；2) 添加周期性对账 Celery 任务，每天凌晨用 COUNT(appointment) 与 booked_slots 比对
   **成本估算：** 4h（约束 + 对账任务）
   **优先级：** P0

3. **议题：规则引擎无版本管理和审计追踪**
   **结论：** RuleSet 及其子资源（时间窗、策略）的变更没有版本记录。多租户 SaaS 系统中，规则变更的追溯和回滚是合规要求。当前仅有 updated_at 时间戳。
   **建议行动：** 添加 rule_set_audit_log 表，记录每次变更的 before/after 快照
   **成本估算：** 8h（模型 + service 层记录 + 查询 API）
   **优先级：** P1

4. **议题：Admin 骨架屏缺失**
   **结论：** 排班日历、排班列表等高频页面使用 Spin + "加载中..." 文字，首屏体验差。无 Skeleton 组件使用。
   **建议行动：** 为排班日历和列表页添加 Skeleton 骨架屏
   **成本估算：** 3h
   **优先级：** P1

5. **议题：排班自动生成任务串行执行**
   **结论：** schedule_task.py 串行遍历所有活跃租户生成排班。当租户数量增长时，总执行时间线性增长。当前每租户独立事务 + try/catch，单租户失败不影响其他。
   **建议行动：** 将租户级别的排班生成改为独立 Celery 子任务（chord 或 group），实现并行化
   **成本估算：** 6h
   **优先级：** P2

6. **议题：规则配置学习成本高**
   **结论：** 规则组含 7 个口径配置项 + 时间窗 + 3 种策略，配置界面信息密度高。排班规则表单 13 字段 + 高级折叠区。对非技术管理员有使用门槛。
   **建议行动：** 1) 为规则配置页添加配置向导（按场景引导）；2) 添加规则效果预览（已有 preview API，前端未充分使用）
   **成本估算：** 12h
   **优先级：** P2

### ⚡ 分歧项

1. **议题：Schedule 44 字段是否需要拆分**
   **各方立场：**
   - PM：功能完整，字段多但对应业务需求
   - Designer：不影响用户感知
   - Engineer：44 字段偏大，热冷字段混杂（如 timezone/status 字段 vs 快照字段），可拆分核心排班 + 扩展信息
   **裁决/建议：** 当前暂不拆分。可观察性能指标，如果排班表查询成为瓶颈再拆分。
   **决策依据：** 拆分的 ROI 不明确，当前无性能数据支撑。

2. **议题：号源查询是否需要 Redis 缓存**
   **各方立场：**
   - PM：患者端高并发查询号源时可能成为瓶颈
   - Designer：号源展示延迟影响用户决策
   - Engineer：booked_slots 是字段读取非聚合查询，数据库单行读取性能足够。引入缓存带来一致性问题。
   **裁决/建议：** 暂不引入 Redis 缓存。已通过 booked_slots 反规范化字段避免聚合查询。后续如出现性能问题，可在患者端号源列表 API 层增加短期缓存（5-10s TTL）。
   **决策依据：** 当前架构已足够支撑。缓存一致性复杂度高于收益。

---

## 被低估的优势

1. **分布式锁设计完善**：预约创建使用双层锁（用户级 + 排班级），取消使用条件 UPDATE 防竞态，支付回调有重入保护。锁粒度合理（10s 超时，5 次重试）。
2. **Celery 多租户隔离已全面实现**：6 个异步任务文件全部使用 set_tenant_context + tenant_id 过滤，每租户独立事务 + try/catch。历史评审标记的问题已全部修复。
3. **规则引擎架构灵活**：RuleSet + 4 类策略 + 时间窗的设计，支持从预约/签到/取消/号源锁定等多维度的灵活配置，SaaS 场景下可扩展性强。
4. **排班模板复制功能**：支持将一个医生的排班规则复制到多个医生（两步向导），大幅减少批量配置工作量。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | Admin 取消按钮条件扩展 | 2h | 高 | Engineer | 待执行 |
| P0 | booked_slots 对账机制 | 4h | 高 | Engineer | 待执行 |
| P1 | 规则审计日志 | 8h | 高 | Engineer | 待执行 |
| P1 | Admin 骨架屏 | 3h | 中 | Designer | 待执行 |
| P2 | 排班生成并行化 | 6h | 中 | Engineer | 待执行 |
| P2 | 规则配置向导 | 12h | 中 | PM+Designer | 待执行 |
| 待定 | Schedule 模型拆分 | 16h | 待定 | Engineer | 需性能数据 |

### P0：立即执行（高价值、低成本）

1. **Admin 取消按钮条件扩展**（2h）：修改 list.tsx 取消按钮条件为 `status === 0 || status === 1`，增加取消原因弹窗（参考患者端取消流程）
2. **booked_slots 对账机制**（4h）：a) 添加 `CHECK (booked_slots >= 0)` 数据库约束；b) 新增 Celery 对账任务，比对 COUNT(active_appointments) 与 booked_slots

### P1：本轮迭代（高价值、中等成本）

1. **规则审计日志**（8h）：新增 rule_set_audit_log 表，记录变更前后快照，提供查询 API
2. **Admin 骨架屏**（3h）：为排班日历、排班列表、预约列表添加 Skeleton 骨架屏

### P2：下个周期规划（中等价值、较高成本）

1. **排班生成并行化**（6h）：将租户级排班生成改为独立 Celery 子任务，使用 chord/group 并行执行
2. **规则配置向导**（12h）：添加按场景引导的规则配置向导，增强预览功能

### 待定：需用户确认

1. **Schedule 模型拆分**（16h）：需先收集性能数据，确认是否为瓶颈

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 6 项达成共识（2 项 P0 + 2 项 P1 + 2 项 P2）

**关键分歧：**
- 2 项需要决策者介入（Schedule 拆分 + 号源缓存），均已裁决暂不执行

**Top 3 P0 行动：**
1. Admin 取消按钮条件扩展（2h）— 前端 status=0 限制过严
2. booked_slots 对账机制（4h）— 缺乏一致性保障

**Critic 关键洞察：**
- 历史评审标记的 4 个 P0 问题中，3 个已修复（complete() 状态检查、爽约状态统一、Celery 多租户隔离），仅 Admin 取消按钮仍需修复
- Critic 质疑的号源计算性能问题经代码验证后风险可控（字段读取非聚合查询）
- Critic 要求的多租户全面审查确认所有 6 个异步任务均已正确隔离

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| | | | |
