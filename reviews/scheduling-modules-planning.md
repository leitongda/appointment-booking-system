# 排班系统剩余模块规划 — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-20
> 审查目标：4 个待实现排班模块的实施规划

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 4 个模块需求已明确（非探索性决策），技术方案有大量现有模式可复用（CRUD、Excel 导入导出、审批流），目标是产出可直接执行的实施计划而非设计方案。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**模块 1: 诊室管理**
- 无 schedule_rooms 模型、无迁移文件、无后端模块、无前端页面
- Schedule 模型无 room_id 字段
- 冲突检测服务已预留 `_check_room_conflict()` 方法（当前为 pass）
- 权限节点 `schedule:room` 已定义但未使用
- BatchCopyModal 中 `copyRoom` 选项已预留但为死字段

**模块 2: 排班规则设置页**
- 前端规则页面已完整实现：列表页(899行)、表单页(542行)、4 个子组件
- ScheduleTemplate 模型字段完整：weekdays(JSON)、break_times(JSON)、schedule_mode(weekly/biweekly/monthly)
- 15 个 API 端点已实现（CRUD、生成、预览、复制、历史等）
- 无"自动发布"配置项，午休通过 breakTimes 排除时间段实现
- 规则页已有：生成排班、批量添加、复制规则（同院区+跨院区）、历史记录
- 结论：排班规则设置页功能已相当完整，无需新建

**模块 3: 停诊患者处理增强**
- ScheduleSuspension 模型已有 processing_method(4种)、processing_status、affected_appointment_count 字段
- SuspensionProcessingService 已实现 4 种处置方式（auto_refund/reschedule/change_date/manual）
- 退款服务 RefundService 已实现（幂等、累计校验、并发去重）
- 停诊通知 MessageService.send_stop_clinic_notification() 已实现
- **关键缺口**：前端停诊页面(suspension.tsx)不包含处置方式选择 UI，创建停诊时不传 processing_method，导致后端不会自动触发患者处置
- schedules 模块的 batch-suspend 端点已支持 processing_method 参数

**模块 4: 批量导入/导出**
- import_export 模块已实现 5 个导入端点 + 9 个导出端点
- 排班模板导出已实现（schedule-templates），排班数据本身无导出端点
- 无排班数据导入端点
- openpyxl 和 xlrd 已在依赖中
- Excel 基础设施（import_service/export_service）已实现通用封装
- 文件存储基础设施（LocalStorage/MinIO/COS）已实现
- 排班统计页已有前端 CSV 导出（JS 生成 Blob）

**通用事实**
- 已实现排班 API 端点：30+（schedules 22+、templates 15、suspensions 7）
- 排班相关前端页面：14 个路由、5450 行代码
- 权限节点：10 个（schedule:read/create/update/delete/publish/suspend/extra-quota/holiday/room）
- 发现：`schedule:template` 权限前端引用但后端未定义；`schedule:publish` 和 `schedule:holiday` 后端定义但未使用

### Designer — 用户视角

**页面清单**
- 排班模块共 14 个路由、14 个页面组件、5450 行代码
- 日历模块 14 个组件（含 6 个弹窗/抽屉）

**弹窗模式统计**
- 4 种弹窗模式：ModalForm(ProComponents)、Modal+ProForm、Modal+Form、Drawer
- 不一致：同类弹窗使用不同模式（创建用 ModalForm vs Modal+Form）

**停诊管理页面现状**
- 仅有添加/取消/删除操作
- 无处置方式选择 UI
- 无受影响患者列表展示
- 无自动退款/转约/改期的前端交互入口

**排班规则页面现状**
- 功能完整：规则列表、3步向导表单、实时日历预览、生成排班、批量添加、复制规则、历史记录
- 无需新建

**导入导出 UI**
- 仅排班统计页有前端 CSV 导出
- 排班数据本身无导入/导出 UI

**组件一致性**
- 脱敏函数（maskName/maskPhone）在 DayDetailDrawer 和 AppointmentDetailModal 中重复实现
- 颜色常量统一使用 @/themes/scheduleColors

### Engineer — 技术视角

**诊室管理 — 存储层**
- Schedule 模型无 room_id，需新增字段 + 迁移
- 冲突检测服务 `_check_room_conflict()` 已预留但为 pass
- CRUD 模式参考：DepartmentService（get_by_id/get_list/create/update/delete + 租户隔离）
- 迁移最新版本：098，命名规范：三位数字前缀 + 描述

**排班规则 — 配置存储**
- ScheduleTemplate 模型已完整，无独立 service 文件（逻辑在 service_mutation 和 schedule_task 中）
- SystemSetting 模型支持门店级覆盖，预定义分类含 booking/hospital 等
- 排班自动任务每天凌晨 2:00 使用 Celery chord 执行

**停诊患者处理 — 事务链路**
- create() 流程：创建记录 → 更新排班状态 → commit → 发送通知 → 患者处置
- 通知和处置在 commit 之后，失败仅 logger.warning
- 预约取消+退款在同一事务中（atomic），微信调用失败触发回滚
- RefundService 有 5 重防退错机制

**批量导入/导出 — 技术依赖**
- openpyxl/xlrd 已有，无 pandas
- Excel 基础设施已实现通用封装
- batch_create 在 service_mutation.py 中已实现
- Celery 配置：软超时 5min、硬超时 10min、3 个队列
- 文件存储：LocalStorage/MinIO/COS 三种后端

**通用技术事实**
- Schedule 模型 25 个字段，含唯一索引 uix_schedule_doctor_date_time
- 冲突检测 6 项（医生时间/诊室/午休/节假日/休息日/医生状态）
- 分布式锁：异步版 tenant_distributed_lock + 同步版 SyncRedisCache.acquire_lock
- 排班状态机 7 个状态、11 条合法转换路径

---

## Round 2：辩论层

### 交叉评论投票矩阵（集中调度简化版）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 诊室管理作为独立模块 CRUD | 低成本增量添加，P2 | 质询 3：缺少业务场景数据 | P2 — 有预留点但非阻塞，成本低可顺手做 |
| 排班规则页无需新建 | 功能已完整 | 质询 1：可能与 rule_sets 语义不同 | 共识 — 规则页已满足需求，修复权限 bug 即可 |
| 停诊处理前端缺口是 P0 | 后端框架在但前端未接入 | 质询 2/6：reschedule 是伪实现 + 无补偿机制 | P0 — 需补全后端实现 + 前端接入 + 补偿机制 |
| 排班导出优先于导入 | 统计页 CSV 已存在 | 质询 5：导入比导出更紧迫 | P1 — 导出复用现有基础设施，导入需新建 |

### 独到发现

1. 停诊处置后端已完整实现但前端未接入 — 这是"功能存在但不可用"的典型案例
2. 排班规则页功能已相当完整，"排班规则设置页"需求实际上已被满足
3. 诊室管理是增量添加（新增表 + Schedule 加字段），不破坏现有功能
4. 导出可复用现有 Excel 基础设施，导入需额外设计验证和冲突处理

### Critic 质询

1. [Critic → 全体] 质询 1：排班规则页"已完整"结论过于武断
   - 论据：排班模板 vs 排班规则 vs rule_sets 语义可能不同；schedule:template 权限 bug
   - 级别：普通

2. [Critic → 全体] 质询 2：停诊处置 4 种方式中 reschedule/change_date 是伪实现
   - 论据：仅追加 remark 文本，无状态转换、无业务流程、前端零接入
   - 级别：🚨 关键

3. [Critic → 全体] 质询 3：诊室管理缺少业务场景数据
   - 论据：无用户场景数据，可能价值很低
   - 级别：🚨 关键

4. [Critic → 全体] 质询 4：忽略了项目已有的工程优势
   - 论据：测试覆盖好、冲突架构可扩展、Excel 基础设施完善
   - 级别：普通

5. [Critic → 全体] 质询 5：排班统计页已有 CSV 导出，导入更紧迫
   - 论据：导出需求部分满足，导入完全缺失
   - 级别：普通

6. [Critic → 全体] 质询 6：停诊处置事务链路无补偿机制
   - 论据：通知/处置在 commit 后执行，失败仅 logger.warning，pending 状态永久悬挂
   - 级别：🚨 关键

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 2 | 停诊处置 reschedule/change_date 是伪实现 | Engineer 确认：仅 remark 追加，无状态转换 | 是 | 纳入 P0 计划 |
| 3 | 诊室管理缺少业务场景 | PM：大版本计划已定义，预留点密集 | 部分 — 无实际用户数据 | 纳入 P2 计划（低成本） |
| 6 | 停诊处置无补偿机制 | Engineer：pending 状态永久悬挂 | 是 | 纳入 P0 计划 |

---

## Round 3：共识层

### ✅ 共识项

1. **议题：排班规则设置页无需新建**
   **结论：** 当前排班模板管理页已覆盖规则列表、3步向导表单、实时预览、生成排班、批量添加、复制规则、历史记录等全部功能。"排班规则设置页"需求已被满足。
   **建议行动：** 修复 `schedule:template` 权限 bug（前端引用但后端未定义），无需新建页面。
   **成本估算：** 1h（添加权限定义）
   **优先级：** P2

2. **议题：批量导入复用现有 Excel 基础设施**
   **结论：** ImportService/ExcelExportService 已通用封装，openpyxl 已有，batch_create 已实现。新增排班导入/导出端点成本低。
   **建议行动：** 新增排班数据导出端点 + 导入端点 + 前端入口。
   **成本估算：** 导出 4h + 导入 8h = 12h
   **优先级：** P1

3. **议题：诊室管理是低成本增量添加**
   **结论：** CRUD 模式可参考 DepartmentService，冲突检测已预留，权限已定义。新增 schedule_rooms 表 + Schedule 加 room_id 字段 + 激活 _check_room_conflict。
   **建议行动：** 作为独立 CRUD 模块实现，不阻塞其他模块。
   **成本估算：** 12h（模型2h + 迁移2h + 服务4h + 路由2h + 前端2h）
   **优先级：** P2

### ⚡ 分歧项

1. **议题：停诊处置增强的范围和深度**
   **各方立场：**
   - PM：4 种处置方式已实现，前端接入即可
   - Designer：前端需新增处置方式选择、受影响患者列表、处置状态展示
   - Engineer：reschedule/change_date 仅是 remark 追加，需补全实际业务流程
   **裁决：** 接受 Critic 质询 2 的判断 — reschedule/change_date 是伪实现，需补全。同时接受质询 6 — 需要补偿机制。
   **决策依据：** "追加 remark 文本"不等于"转约/改期完成"，用户期望的是实际业务流程闭环。

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 停诊处置：前端接入处置方式选择 UI | 6h | 高 | Engineer+Designer | 待执行 |
| P0 | 停诊处置：补全 reschedule/change_date 业务流程 | 12h | 高 | Engineer | 待执行 |
| P0 | 停诊处置：补偿机制（定时任务扫描 pending 状态） | 4h | 高 | Engineer | 待执行 |
| P1 | 批量导出排班数据（后端 Excel 端点 + 前端按钮） | 4h | 中 | Engineer | 待执行 |
| P1 | 批量导入排班数据（后端端点 + Excel 解析 + 冲突处理 + 前端） | 8h | 中 | Engineer | 待执行 |
| P2 | 诊室管理（schedule_rooms CRUD + Schedule.room_id + 冲突检测激活） | 12h | 中 | Engineer | 待执行 |
| P2 | 修复 schedule:template 权限 bug | 1h | 低 | Engineer | 待执行 |
| 待定 | 排班规则页与 rule_sets 模块关系梳理 | 4h | 待定 | PM | 需用户确认 |

### P0：立即执行（停诊患者处理闭环）

**P0-1. 停诊前端接入处置方式选择 UI（6h）**
- 前端 `suspension.tsx` 添加停诊弹窗增强：
  - 新增"处置方式"字段（Radio.Group: 自动退号退款/转约其他医生/改期其他时间/人工处理）
  - 新增"受影响预约"预览区域（调用 `GET /{id}/affected-count`）
  - 停诊列表新增 `processing_status` 和 `affected_appointment_count` 列
  - 操作列新增"查看处置结果"按钮
- 调用 `POST /schedule-suspensions` 时传入 `processing_method`
- 负责：Engineer（API 对接）+ Designer（UI 交互）

**P0-2. 补全 reschedule/change_date 业务流程（12h）**
- `reschedule` 方式增强：
  - 将受影响预约状态改为 `rescheduled`
  - 生成转约待办记录（可复用 appointment 状态机）
  - 通知患者选择同一科室的其他医生
  - 支持管理员手动指定转约目标医生
- `change_date` 方式增强：
  - 将受影响预约状态改为 `rescheduled`
  - 通知患者选择同一医生的其他日期
  - 支持管理员手动指定目标日期
- 预约模型新增 `rescheduled_from_appointment_id` 字段（追溯来源）
- 负责：Engineer

**P0-3. 停诊处置补偿机制（4h）**
- 新增 Celery 定时任务 `check_pending_suspension_processing`：
  - 每 30 分钟扫描 `processing_status=pending` 且创建时间 > 30 分钟的停诊记录
  - 自动重试处置（最多 3 次）
  - 超过重试次数标记为 `failed` 并发送告警通知
  - 路由到 `scheduled` 队列
- 负责：Engineer

### P1：本轮迭代（批量导入/导出）

**P1-1. 排班数据导出（4h）**
- 后端：`GET /data/export/schedules` 端点
  - 参数：doctor_id、date_range、schedule_status
  - 格式：Excel（复用 ExcelExportService）
  - 工作表：排班明细 + 汇总统计
  - 权限：schedule:read
- 前端：排班列表页/日历页添加"导出"按钮
- 负责：Engineer

**P1-2. 排班数据导入（8h）**
- 后端：`POST /data/import/schedules` 端点
  - 格式：Excel（复用 ImportService）
  - 字段映射：医生姓名→doctor_id、日期、时段、号源等
  - 验证：冲突检测（复用 ScheduleConflictService.batch_check_conflicts）
  - 冲突策略：跳过/覆盖/报告
  - 异步处理：大量数据走 Celery 任务
- 前端：排班列表页添加"导入"按钮 + Upload 组件
- 提供导入模板下载（复用 router_template.py 模式）
- 负责：Engineer

### P2：下个周期规划

**P2-1. 诊室管理（12h）**
- 模型：新增 `schedule_rooms` 表（参照大版本计划字段定义）
- 迁移：099 — 创建表 + Schedule 加 room_id 字段 + 回填
- 服务：`ScheduleRoomService` CRUD（参考 DepartmentService）
- 冲突检测：激活 `_check_room_conflict()` 方法
- 路由：`/schedule-rooms` CRUD 端点，权限 `schedule:room`
- 前端：诊室管理页面 + 日历卡片显示诊室
- 负责：Engineer

**P2-2. 修复 schedule:template 权限 bug（1h）**
- `apps/server/app/common/role_permissions.py` 的 `ADMIN_SCHEDULE_PERMISSIONS` 添加 `schedule:template`
- 负责：Engineer

### 待定：需用户确认

1. **排班规则页与 rule_sets 模块关系梳理（4h）**
   - 当前排班模板（ScheduleTemplate）和规则集（RuleSet）是两套独立系统
   - 是否需要统一或建立关联？需 PM 确认业务意图

---

## 被低估的优势

1. Excel 基础设施（ImportService/ExportService）已通用封装，新增导入导出成本极低
2. 冲突检测架构可扩展（单条+批量，6 项检查），诊室冲突只需激活预留方法
3. 分布式锁体系完善（异步+同步），停诊补偿机制可直接复用
4. 测试基础扎实（6 个排班单元测试文件 + 3 个集成测试文件）

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 3 项达成共识（排班规则页无需新建、导入复用现有基础设施、诊室管理低成本增量）

**关键分歧：**
- 1 项需裁决（停诊处置增强范围）— 裁决结果：接受 Critic 判断，补全实际业务流程

**Top 3 P0 行动：**
1. 停诊前端接入处置方式选择 UI（6h）
2. 补全 reschedule/change_date 业务流程（12h）
3. 停诊处置补偿机制（4h）

**Critic 关键洞察：**
- 停诊处置的真实状态是"后端框架搭好，但只有 auto_refund 有实质性实现，其余三种是伪实现" — 这改变了整个 P0 的范围
- 诊室管理缺少业务场景数据支撑 — 但因实施成本低（12h），仍建议作为 P2 推进
- 停诊处置事务链路无补偿机制 — pending 状态永久悬挂是数据一致性风险
