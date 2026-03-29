# 预约流程功能 -- 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-03-29
> 审查目标：预约流程的逻辑流程、页面布局、操作合理性

---

## 模式选择

选定**集中调度模式**。Team Lead 统一调度三个 Explore Agent（PM / Designer / Engineer）并行收集事实，随后自行完成交叉辩论和共识裁决。

---

## Round 1 -- 事实收集

### PM Agent 事实清单（产品视角）

**1. 预约状态体系**
- 系统共定义 9 种状态：0 待支付、1 已预约、2 已签到、3 候诊中、4 就诊中、5 已完成、6 已取消、7 已过期、8 已关闭
- 状态定义来源：`packages/shared/src/constants/appointment.ts` 与 `apps/server/app/modules/appointments/common.py` 保持一致
- 前端 `STATUS_MAP`（admin 端 list.tsx 第 15-25 行）与共享常量一致

**2. 预约创建流程**
- 患者端 H5（booking/index.tsx）：选择排班 -> 选就诊人 -> 提交，无病情描述输入
- 小程序端（packageBooking/pages/booking/index.tsx）：选择排班 -> 选就诊人 -> 病情描述(选填) -> 检查重复预约 -> 提交
- H5 端缺少重复预约检查（checkDuplicate）
- H5 端无病情描述输入功能
- 小程序端有预约须知展示，H5 端没有
- Server 端 `AppointmentCreate` schema 包含 `symptom_description` 可选字段

**3. 取消预约**
- Admin 端：仅 status=0（待支付）可取消，权限要求 `appointment:cancel`
- 患者端 H5：status=1（已预约）可取消
- 患者端小程序：status=1 且未过期时可取消
- Server 端 `cancel` 方法：允许 CONFIRMED(1) 和 SIGNED(2) 状态取消
- **冲突**：Admin 端限制 status=0 才能取消，但 Server 端允许 status=1,2 取消。Admin 端对非管理员用户取消了更少的权限

**4. 爽约标记**
- Admin 端列表：仅 status=0 可标记爽约，权限要求 `appointment:update`
- 医生端 consultation 页面：已过号（EXPIRED=7）可标记爽约
- Server 端 `mark_no_show`：允许 CONFIRMED(1) 和 EXPIRED(7) 状态
- **冲突**：Admin 端爽约条件（status=0）与 Server 端（status=1,7）不一致
- 爽约标记后状态变为 CLOSED(8)，而 blackist_task 中对爽约状态判断同时用 status=7 和 status=8

**5. 取消签到**
- Admin 端：status=2 时仅超级管理员可取消签到
- Admin 端详情页同样如此
- Server 端 `cancel_sign_in`：要求 status=2，路由需要 `get_current_super_admin`
- 一致

**6. 预约统计**
- Server `AppointmentStatistics` schema：pending 字段描述为"待签到数"，实际映射 status=1（CONFIRMED）
- Admin 端统计：字段名 pending 对应的是 status=1
- `no_show` 字段映射 status=7（EXPIRED），但共享常量中 EXPIRED 是"已过期"而非"爽约"
- **语义混淆**：EXPIRED(7) 在统计中被称为 noShow，但实际在状态流转中，EXPIRED 是"过号"，CLOSED(8) 才是"爽约"

**7. 预约通知**
- 创建预约：发送站内消息（MessageService）+ 邮件事件钩子
- 取消预约：发送站内消息 + 邮件事件钩子
- 签到：邮件事件钩子（无站内消息）
- 叫号：仅 WebSocket 通知（无站内消息/短信）
- 完成就诊：站内消息 + 邮件事件钩子
- 预约提醒：Celery 定时任务（微信订阅消息），每30分钟检查
- NotificationService 中 `notify_appointment_success`、`notify_appointment_remind`、`notify_queue_call` 均为 TODO 未实现

**8. 路由重复**
- `router.py`（主路由）和 `router_query.py`（查询子路由）都注册了 `GET ""` 获取预约列表的端点
- 主路由 prefix 为 `/appointments`，query 子路由 prefix 为 `/appointments/query`
- 但 `router.py` 中 include query_router 时使用了 `prefix="/query"`
- **风险**：`GET /appointments` 和 `GET /appointments/query` 都能获取列表，逻辑重复，维护成本高

---

### Designer Agent 事实清单（用户视角）

**1. Admin 端预约列表页（list.tsx）**
- 使用 ProTable 组件，支持搜索表单（关键字、门店、医生、科室、预约日期范围、状态、创建时间范围）
- 表格列：预约编号、患者、手机号、医生、科室、预约日期、时段、排队号、状态、创建时间、操作
- 操作按钮：详情（需权限 appointment:detail）、取消（status=0，需 appointment:cancel）、爽约（status=0，需 appointment:update）、取消签到（status=2，仅超管）
- 支持导出（ImportExport 组件，无导入）
- 门店筛选仅超级管理员和多门店管理员可见
- **问题**：日期快捷选项包含"近7天"、"近30天"，与"今天"、"本周"、"本月"功能有重叠

**2. Admin 端预约详情页（detail.tsx）**
- 使用 ProDescriptions 展示基本信息（预约编号、状态、患者信息、医生信息、日期时段、排队号）
- 时间线展示（Timeline）：创建预约 -> 签到 -> 叫号 -> 完成就诊 / 已取消
- 操作：取消签到（status=2，仅超管）、返回列表
- **缺失**：
  - 无病情描述展示
  - 无签到方式展示
  - 无门店信息
  - 无症状描述
  - 取消信息（取消时间、取消原因）展示在时间线中，但不在基本信息区

**3. 患者端 H5 预约列表（patient-h5 appointment/index.tsx）**
- Tab 切换：全部、待就诊（status=1）、已完成（status=5）、已取消（status=6）
- 卡片式列表，支持下拉刷新和无限滚动加载
- 操作：待就诊(status=1) 状态下显示"取消预约"和"签到"按钮
- 点击卡片跳转详情页
- **缺失**：没有"待支付(0)"的 Tab，没有"已过期(7)"和"已关闭(8)"的分类

**4. 患者端 H5 预约详情（patient-h5 appointment/detail.tsx）**
- 渐变色状态头部
- 卡片展示：预约信息、就诊人信息、医生信息
- 就诊进度 Steps：已预约 -> 已签到 -> 就诊中 -> 已完成
- 已取消时展示取消信息卡片
- 操作：待就诊时可取消、可签到
- **问题**：Steps 中"就诊中"实际对应 status=3（WAITING 候诊中）和 status=4（SEEING 就诊中），但只展示了 4 步，缺少"候诊中"状态

**5. 患者端小程序预约详情（patient-miniapp appointment/detail.tsx）**
- 状态图标映射覆盖 status 1/2/3/5/6/7，缺少 0（待支付）和 8（已关闭）
- 操作：status=1 且未过期时可取消或扫码签到
- 签到方式为扫码签到（调用微信扫码 API）
- **差异**：小程序签到走扫码流程（scan -> select -> signIn），H5 直接调用 signIn API

**6. 医生端今日预约（doctor appointment/today.tsx）**
- 顶部统计卡片：今日预约、候诊中、就诊中、已完成
- 操作：呼叫(status=2)、完成(status=4)、过号(status=4)、病历(status=4或5)
- WebSocket 实时连接状态指示器
- **缺失**：无爽约标记功能（只能在 consultation 页面操作）

**7. 医生端就诊管理（doctor consultation/index.tsx）**
- 左栏：当前就诊患者（大头像 + 操作按钮）
- 右栏：候诊队列（List 组件）
- 底部可折叠：已过号列表
- 操作：呼叫、完成就诊、过号、重新呼叫（已过号）、标记爽约（已过号）
- 抽屉：患者历史记录
- 弹窗：复诊预约
- WebSocket 实时通知
- **完整性高**，功能覆盖全面

**8. 签到流程对比**
- 小程序：扫码（scan.tsx） -> 选择预约（select.tsx，含时间窗倒计时） -> 签到成功弹窗
- H5：直接调用 signIn API（无扫码、无时间窗展示）
- Admin：无签到入口（只能取消签到）
- **体验不一致**：小程序签到体验远优于 H5

---

### Engineer Agent 事实清单（技术视角）

**1. 数据模型**
- `Appointment` 模型（appointment.py）：36+ 字段，包含快照字段（patient_name、doctor_name、department_name、doctor_title 等）
- `tenant_id` 字段 nullable=True，但迁移 043 要求 NOT NULL -- 需确认
- 支付快照字段（payment_profile_id 等 7 个字段）
- 规则快照字段（book_open_at、checkin_open_at 等 6 个字段）
- 关联关系：schedule、patient、doctor、tenant、payment_profile、payment_miniapp_instance

**2. 服务层架构**
- `AppointmentService`（service.py）通过多继承组合：`AppointmentBookingService` + `AppointmentFlowService`
- 基类 `AppointmentServiceBase`（common.py）提供查询和工具方法
- `_compat` 方法用于延迟导入，解决循环依赖问题
- 分布式锁用于创建和取消操作的并发控制（Redis distributed lock）

**3. 创建预约逻辑（service_booking.py）**
- 配额检查 -> 排班验证 -> 租户一致性校验 -> 休息日检查 -> 规则引擎检查（预约时间窗、预约冲突、容量限制） -> 用户/患者验证 -> 分布式锁内双重检查 -> 创建 -> 发通知
- 队列号使用 `func.max(queue_number) + 1` 方式生成（在锁内）
- 号源已满检查在锁内做了二次验证（refresh schedule）

**4. 状态流转逻辑（service_flow.py）**
- 签到：CONFIRMED(1) -> SIGNED(2)，含时间窗校验和签到次数限制
- 叫号：SIGNED(2) -> SEEING(4)
- 完成就诊：任意状态 -> COMPLETED(5)（无前置状态检查）
- 过号：SIGNED(2) 或 SEEING(4) -> EXPIRED(7)
- 重新叫号：EXPIRED(7) -> SEEING(4)
- 爽约：CONFIRMED(1) 或 EXPIRED(7) -> CLOSED(8)
- 取消：CONFIRMED(1) 或 SIGNED(2) -> CANCELLED(6)

**5. 状态机缺陷**
- `complete()` 方法无前置状态检查：任何状态都可被标记为"已完成"，包括已取消(6)、已过期(7)、已关闭(8)的预约
- `WAITING(3)` 状态从未在代码中被设置：状态流转中没有 CONFIRMED/SIGNED -> WAITING 的转换，该状态在共享常量中定义但未被使用
- `PENDING(0)` 状态从未在创建流程中使用：创建预约直接设为 CONFIRMED(1)，0 状态仅用于展示

**6. 爽约/黑名单状态不一致**
- `mark_no_show` 将状态设为 CLOSED(8)
- `blacklist_task.py` 爽约自动标记任务将过期预约设为 status=7（第 235-236 行：`appointment.status = 7`）
- 同一任务的黑名单检查使用 `Appointment.status == 8` 统计爽约次数
- 即：自动爽约标记设为 7(EXPIRED)，手动爽约标记设为 8(CLOSED)，统计时只算 8

**7. API 响应构造**
- `router.py` 和 `router_query.py` 中多处手动构造 `AppointmentResponse`，代码重复（约 30 行 x 5 处）
- `get_today_appointments` 直接返回字典而非 Pydantic model
- 列表接口在 for 循环中逐个构造响应对象，无批量转换

**8. 通知机制**
- WebSocket 通知：创建预约通知医生、签到通知医生、叫号通知医生、完成通知医生、过号通知医生
- 站内消息：创建、取消、完成就诊时发送
- 邮件事件钩子：创建、取消、签到、叫号、完成、爽约时触发
- 微信订阅消息：预约提醒（Celery 定时任务）
- 短信通知：仅停诊通知（NotificationService），其他场景未实现
- 叫号通知（notify_queue_call）标记为 TODO

**9. Celery 定时任务**
- 预约提醒：每30分钟执行，检查 N 小时内待就诊的预约
- 爽约自动标记：检查已过期排班但未签到的预约
- 黑名单自动释放：到期自动解除
- 预约提醒任务未考虑多租户隔离（无 tenant_id 过滤）

---

## Round 2 -- 交叉辩论

### 交叉验证矩阵

| # | 发现点 | PM 确认 | Designer 确认 | Engineer 确认 | 严重程度 |
|---|--------|---------|--------------|--------------|---------|
| F1 | Admin 爽约操作条件（status=0）与 Server 端（status=1,7）不一致 | Y | Y | Y | P0 |
| F2 | `complete()` 无前置状态检查 | - | - | Y | P0 |
| F3 | WAITING(3) 状态从未被设置 | Y | Y | Y | P1 |
| F4 | PENDING(0) 状态从未被使用 | Y | Y | Y | P1 |
| F5 | 路由重复（GET /appointments 列表） | - | - | Y | P1 |
| F6 | 爽约状态不一致（手动=8 vs 自动=7 vs 统计只算8） | Y | - | Y | P0 |
| F7 | Admin 详情页缺少病情描述、门店信息展示 | Y | Y | - | P1 |
| F8 | H5 端缺少重复预约检查 | Y | - | Y | P1 |
| F9 | H5 端无病情描述输入 | Y | - | Y | P2 |
| F10 | 通知服务多个方法 TODO 未实现 | Y | - | Y | P1 |
| F11 | 预约提醒任务未考虑多租户隔离 | - | - | Y | P0 |
| F12 | API 响应构造代码重复 | - | - | Y | P2 |
| F13 | AppointmentStatistics 字段名 pending 映射 status=1，语义混淆 | Y | - | Y | P1 |
| F14 | H5 签到无时间窗展示 | - | Y | Y | P2 |
| F15 | 医生端 Dashboard status===3 对应 WAITING 而非 SEEING | - | - | Y | P1 |

### Critic Agent 质询

**Q1: F1 是否真的是 P0？**
> Admin 端对"爽约"按钮的显示条件是 `record.status === 0`（待支付），而非"已预约"。如果管理员需要对一个已预约但未支付的患者标记爽约，确实合理。但通常场景是对已预约(status=1)或已过号(status=7)标记爽约。当前 Admin 端的条件 `status === 0` 几乎不可能被满足（创建时就是 status=1），这意味着 Admin 端的爽约功能实际上无法使用。
> **裁决：P0**。功能完全不可用。

**Q2: F6 状态不一致的影响范围？**
> 自动爽约标记任务把 status 设为 7(EXPIRED)，但 EXPIRED 的语义是"已过期/过号"。后续黑名单统计只查 status=8。这意味着：自动爽约标记的患者不会被计入爽约次数，黑名单形同虚设。
> **裁决：P0**。黑名单功能失效。

**Q3: F2 complete() 无前置状态检查的实际风险？**
> 如果管理员误操作对已取消的预约点"完成就诊"，状态会直接变成 COMPLETED(5)。这在业务上是不可接受的。
> **裁决：P0**。数据一致性风险。

**Q4: F11 预约提醒任务未考虑多租户隔离的风险？**
> 在多租户环境下，定时任务遍历所有预约时没有按 tenant_id 过滤。如果租户 A 的微信配置被用于发送租户 B 的预约提醒，会导致信息泄露和跨租户数据暴露。
> **裁决：P0**。多租户数据安全风险。

### 独到发现

1. **F16**: `service_booking.py` 第 296 行使用 `print()` 而非 `logger` 记录候补递补失败，不符合日志规范
2. **F17**: `common.py` 的 `get_list` 方法对 department_id 的处理是通过科室名称过滤（先查科室名再用 `department_name == dept_name` 过滤），如果两个科室同名会导致错误匹配
3. **F18**: `router_flow.py` 中 `call`、`complete`、`pass`、`recall`、`no_show` 端点都重复了"获取预约 -> 检查门店权限 -> 执行操作"的模式，但没有统一的装饰器或中间件
4. **F19**: 医生端 `today.tsx` 从 `localStorage` 获取 doctorId，如果用户清除缓存或换设备会导致功能失效
5. **F20**: 患者端 H5 签到使用 `checkin_method: 'PHONE'`，但 `router_flow.py` 的签到端点默认值为 `'MANUAL'`，语义不一致

---

## Round 3 -- 共识收敛

### Team Lead 裁决

经过三轮分析，共识别 **20 个发现项**，其中：

- **共识项**：16 项（三个 Agent 交叉确认）
- **分歧项**：0 项（无实质分歧，仅有不同视角的补充）
- **独到发现**：4 项（Critic Agent 额外发现 F16-F20）

### 行动计划

#### P0 -- 必须立即修复（影响核心业务逻辑或数据安全）

| # | 行动项 | 描述 | 成本估算 | 负责角色 |
|---|--------|------|---------|---------|
| P0-1 | 修复 Admin 端爽约操作条件 | 将 `list.tsx` 中 `record.status === 0` 改为 `record.status === 1`，增加 status=7（已过号）条件。与 Server 端 `mark_no_show` 允许的 CONFIRMED(1) 和 EXPIRED(7) 对齐 | 0.5h | 前端 |
| P0-2 | 修复 `complete()` 状态前置检查 | 在 `service_flow.py` 的 `complete()` 方法中增加前置状态检查，仅允许 SEEING(4) 状态完成就诊 | 0.5h | 后端 |
| P0-3 | 修复爽约状态不一致 | 将 `blacklist_task.py` 中自动爽约标记的 `appointment.status = 7` 改为 `appointment.status = 8`（CLOSED），与手动爽约一致。确保黑名单统计正确 | 1h | 后端 |
| P0-4 | 预约提醒任务增加多租户隔离 | 在 `notification_task.py` 的 `send_appointment_reminder_task` 中增加 tenant_id 过滤，或遍历活跃租户逐个处理 | 2h | 后端 |
| P0-5 | 统一爽约状态语义 | 全局梳理：EXPIRED(7) 仅用于"过号"，CLOSED(8) 用于"爽约"。更新 `AppointmentStatistics` 中 `no_show` 字段映射为 status=8 | 2h | 全栈 |

#### P1 -- 应尽快修复（影响功能完整性或可维护性）

| # | 行动项 | 描述 | 成本估算 | 负责角色 |
|---|--------|------|---------|---------|
| P1-1 | 清理 WAITING(3) 状态 | 要么在叫号前增加"候诊中"状态转换（SIGNED -> WAITING -> SEEING），要么从状态定义中移除。当前该状态无任何代码设置它 | 2h | 后端 |
| P1-2 | 清理 PENDING(0) 状态 | 如果无支付流程，从状态定义和 UI 中移除"待支付"状态；如果有，需实现支付逻辑 | 4h | 全栈 |
| P1-3 | 去重路由 | 将 `router.py` 中的 `GET ""` 列表端点迁移到 `router_query.py`，删除主路由中的重复实现 | 1h | 后端 |
| P1-4 | Admin 详情页补充信息 | 增加病情描述、门店名称、签到方式、取消原因（独立区块）的展示 | 2h | 前端 |
| P1-5 | H5 端增加重复预约检查 | 在 `patient-h5/booking/index.tsx` 提交前调用 `appointmentApi.checkDuplicate` | 1h | 前端 |
| P1-6 | 实现通知服务 TODO | 实现 `NotificationService` 中的 `notify_appointment_success`、`notify_appointment_remind`、`notify_queue_call` | 4h | 后端 |
| P1-7 | 修复统计字段语义 | 将 `AppointmentStatistics.pending` 重命名或调整映射，使 pending 映射真正的"待确认"而非"已预约" | 1h | 全栈 |
| P1-8 | 修复医生端 Dashboard 状态判断 | `dashboard/index.tsx` 第 45 行 `a.status === 3` 应改为 `a.status === 4`（SEEING）才对应"正在就诊" | 0.5h | 前端 |

#### P2 -- 后续优化（提升用户体验或代码质量）

| # | 行动项 | 描述 | 成本估算 | 负责角色 |
|---|--------|------|---------|---------|
| P2-1 | H5 端增加病情描述输入 | 在 `patient-h5/booking/index.tsx` 增加 Textarea 组件 | 1h | 前端 |
| P2-2 | H5 签到增加时间窗展示 | 参考小程序端 `select.tsx` 的倒计时和时间窗展示逻辑 | 3h | 前端 |
| P2-3 | API 响应构造去重 | 提取 `AppointmentResponse.from_appointment()` 工厂方法，消除 5 处重复的响应构造代码 | 2h | 后端 |
| P2-4 | 统一叫号通知 | 实现 `notify_queue_call` 方法，叫号时向患者发送小程序订阅消息 | 3h | 后端 |
| P2-5 | 修复日志规范 | 将 `service_booking.py` 第 296 行的 `print()` 替换为 `logger.warning()` | 0.2h | 后端 |
| P2-6 | 修复科室过滤逻辑 | 改用 department_id 外键关联过滤替代 department_name 文本匹配 | 1h | 后端 |
| P2-7 | 统一签到方式常量 | H5 使用 'PHONE'，默认为 'MANUAL'，需统一语义并文档化 | 0.5h | 全栈 |
| P2-8 | 医生端 doctorId 获取方式 | 从 localStorage 改为从 API 或 auth token 中获取 doctorId | 1h | 前端 |

---

## 摘要

### 总览
- **共识项**：16 项
- **分歧项**：0 项
- **独到发现**：4 项（F16-F20）
- **总发现数**：20 项

### Top 5 P0 行动项

| # | 行动项 | 影响 | 成本 |
|---|--------|------|------|
| P0-1 | Admin 爽约按钮条件错误（status=0 应为 1,7） | 爽约功能完全不可用 | 0.5h |
| P0-2 | complete() 无前置状态检查 | 任何状态都可被标记完成，数据一致性风险 | 0.5h |
| P0-3 | 爽约状态不一致（手动8 vs 自动7） | 黑名单统计失效，跨租户数据风险 | 1h |
| P0-4 | 预约提醒任务无多租户隔离 | 跨租户信息泄露 | 2h |
| P0-5 | 爽约状态语义全局统一 | 统计数据错误、状态含义混乱 | 2h |

**P0 总成本估算：5.5 人时**

### Critic 关键洞察

1. **Admin 爽约功能实际完全不可用**：显示条件 `status === 0`（待支付）在当前流程中永远不会满足，因为预约创建时直接设为 CONFIRMED(1)。这是一个"写了但用不了"的功能。

2. **黑名单系统形同虚设**：自动爽约标记（Celery 任务）将 status 设为 7，但黑名单统计只查 status=8。自动标记的爽约记录完全不会被计入爽约次数，黑名单永远不会自动触发。

3. **状态 3（候诊中）是"幽灵状态"**：在全端代码中定义并展示，但没有任何代码路径会设置该状态。状态机实际上只有 0-2, 4-8 的流转，3 从未参与。

4. **多租户安全盲区**：预约提醒 Celery 任务直接查全库预约发微信消息，完全绕过了 `TenantContextMiddleware`。在 SaaS 环境下，这意味着租户 A 可能收到租户 B 的患者通知。

---

*画布结束。本评审基于 2026-03-29 的代码快照，涵盖 admin/patient-h5/patient-miniapp/doctor 四端及 server 全部预约相关模块。*
