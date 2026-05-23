# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：集中调度
> 日期：2026-05-23
> 审查目标：医疗服务模块（admin 端 + server 端）— 功能/字段/逻辑/业务/操作补充机会

---

## 模式选择

**选定模式：** 集中调度

**选择理由：** 综合评审无明确主导领域，集中调度可快速收敛且输出完整度最高。Round 2 仅启动 Critic，交叉评审由 Team Lead 自行完成。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**产品定位：**
- 项目定位：全栈医院预约挂号系统，SaaS 多租户架构，支持多门店/分院、多科室、多医生排班预约
- 医疗服务模块路由定义：`apps/admin/config/routes/medical-services.ts:15-119`
- 医疗服务包含 7 个子模块：医生管理、排班管理、预约管理、患者管理、病历管理、检查报告、诊费管理

**功能完成度：**

| 子模块 | admin 页面 | server API | 状态 |
|--------|-----------|-----------|------|
| 医生管理 - 列表/新增/编辑/详情/预约设置/诊费 | 已实现 | 已实现 | 完整 |
| 排班管理 - 规则/列表/日历/甘特图/自定义/休息日/停诊/审核/加号/诊室/统计 | 已实现 | 已实现 | 完整 |
| 预约管理 - 列表/签到队列/统计/详情/候补 | 已实现 | 已实现 | 完整 |
| 患者管理 - 患者列表/详情/就诊卡列表/详情 | 已实现 | 已实现 | 完整 |
| 病历管理 | admin 端仅查看 | server 端完整 CRUD | **admin 端只读** |
| 检查报告 | admin 端查看+删除 | server 端完整（含上传） | **admin 端无上传** |
| 诊费管理 - 类型/模板 | 已实现 | 已实现 | 完整 |

**数据模型（server 端）：**

| 模型 | 文件 | 字段数 | 关键字段 |
|------|------|--------|---------|
| Doctor | `models/doctor.py` | 30+ | name, phone, title, specialty, introduction, department_id, store_id, tenant_id |
| Schedule | `models/schedule.py` | 20+ | doctor_id, schedule_date, start_time, end_time, online_quota, offline_quota, reserved_quota, extra_quota, fee, schedule_status |
| Appointment | `models/appointment.py` | 30+ | user_id, patient_id, doctor_id, schedule_id, status, queue_number, payment_*, refund_*, reminder_* |
| MedicalRecord | `models/medical_record.py` | 15+ | appointment_id, patient_id, doctor_id, chief_complaint, diagnosis, treatment, prescription |
| ExaminationReport | `models/examination_report.py` | 12 | record_id, appointment_id, patient_id, doctor_id, report_type, file_* |
| ConsultationFeeType | `models/consultation_fee.py` | 7 | store_id, name, code, description, sort_order, status |
| ConsultationFeeTemplate | `models/consultation_fee.py` | 4 | fee_type_id, initial_fee, follow_up_fee |
| StoreFeeTemplate | `models/consultation_fee.py` | 5 | store_id, fee_type_id, initial_fee, follow_up_fee |
| DoctorConsultationFee | `models/consultation_fee.py` | 7 | doctor_id, store_id, department_id, fee_type_id, initial_fee, follow_up_fee |
| CommonService | `models/common_service.py` | 11 | tenant_id, store_id, name, code, icon, link_type, link_url, department_id |
| HealthReminder | `models/common_service.py` | 10 | tenant_id, store_id, reminder_type, name, content, tips, recommended_interval |
| WaitlistEntry | `models/waitlist.py` | 12 | user_id, patient_id, schedule_id, status, position, priority |
| LeaveRequest | `models/leave_request.py` | 14 | doctor_id, request_type, schedule_id, stop_date, reason, status |

**API 端点清单（医疗服务相关）：**

| 模块 | router 文件 | 端点数 | 认证方式 |
|------|------------|--------|---------|
| common_services | `modules/common_services/router.py` | 3 | get_current_user (可选) |
| medical_records | `modules/medical_records/router.py` | 7 | get_current_user_or_admin |
| examination_reports | `modules/examination_reports/router.py` | 7 | get_current_user_or_admin |
| consultation_fees | `modules/consultation_fees/router.py` | 15+ | get_current_admin |
| doctors | `modules/doctors/router.py` | 10+ | get_current_admin |
| schedules | `modules/schedules/router.py` + 4 子路由 | 20+ | get_current_admin |
| appointments | `modules/appointments/router.py` + 3 子路由 | 15+ | get_current_admin / get_current_user |
| waitlist | `modules/waitlist/` | 5+ | get_current_admin / get_current_user |
| leave_requests | `modules/leave_requests/` | 5+ | get_current_admin |

**竞品功能对比：**

| 功能 | 微医/好大夫 | 本项目 | 备注 |
|------|-----------|--------|------|
| 在线问诊（图文/视频） | 有 | doctor.online_consult_enabled 字段存在，无独立问诊流程 | 字段预留，未实现流程 |
| 智能分诊/导诊 | 有 | 无 | C 端平台功能，SaaS 工具不适用 |
| 排班日历视图 | 有 | 有（calendar + gantt） | |
| 候补排队 | 部分有 | 有（waitlist） | |
| 电子处方 | 有 | MedicalRecord.prescription 字段存在，无独立处方模块 | 字段预留 |
| 检查检验报告 | 有 | 有（examination_reports） | |
| 诊后随访 | 有 | 无 | |
| 医生评价/评分 | 有 | 无 | |
| 复诊提醒 | 有 | VisitTypeService 存在，但仅配置级 | |
| 多渠道通知 | 有 | 有（unified_message 模块） | |
| 医保/商保对接 | 有 | 无 | |
| 排班冲突检测 | N/A | 有（service_conflict.py） | |
| 号源拆分 | 部分有 | 有（online/offline/reserved/extra） | |
| 诊费三级配置 | 部分有 | 有（全局/门店/医生） | |

### Designer — 用户视角

**页面清单与结构：**

| 子模块 | 页面文件 | 组件数 |
|--------|---------|--------|
| 医生管理 | `pages/doctor/` | 11 个文件 |
| 排班管理 | `pages/schedule/` | 35 个文件 |
| 预约管理 | `pages/appointment/` | 4 个文件 |
| 患者管理 | `pages/user/` + `pages/patient/` | 4 个文件 |
| 病历管理 | `pages/medical-record/` | 1 个文件 |
| 检查报告 | `pages/examination-report/` | 1 个文件 |
| 诊费管理 | `pages/system/` | 3 个文件 |
| 停诊审核 | `pages/leave-request/` | 1 个文件 |
| 候补队列 | `pages/waitlist/` | 1 个文件 |

**交互模式统计：**
- 日历组件支持拖拽排班（DraggableScheduleCell + DroppableTimeSlot）
- 排班日历支持月视图（MonthView）和周视图（WeekView）
- 有 BatchCopyModal（批量复制排班）、ImportModal（导入排班）
- 有 CreateAppointmentModal（管理员创建预约）
- 有 ExtraQuotaModal（加号申请）
- 有 ListPageSkeleton 骨架屏组件

**组件使用一致性：**
- 统一使用 ProTable、ProForm、Modal、Drawer
- 日历组件为自定义实现
- 有 RuleWindowConfig 排班时段配置组件

**操作按钮与权限：**
- 路由级权限：canDoctor, canSchedule, canAppointment, canPatient, canMedicalRecord, canConsultationFee, canLeaveRequest, canClinicalOperations
- 页面内按钮级权限：通过路由级 access + 组件内 useAccess 实现（examination-report 有 isSuperAdmin 判断，doctor/form 有 canSuperAdmin 控制）

### Engineer — 技术视角

**存储层事实：**

| 模型 | 软删除 | 审计字段 | 唯一约束 |
|------|--------|---------|---------|
| Doctor | deleted_at | AuditMixin | tenant_id+username, tenant_id+phone |
| Schedule | 无 | AuditMixin | doctor_id+schedule_date+start_time+end_time |
| Appointment | 无 | AuditMixin | appointment_no |
| MedicalRecord | 无 | AuditMixin | record_no |
| ExaminationReport | 无 | AuditMixin | 无 |
| ConsultationFeeType | 无 | AuditMixin | store_id+code |
| WaitlistEntry | 无 | 自定义时间戳 | 无 |
| LeaveRequest | 无 | AuditMixin | 无 |

**业务逻辑事实：**

| 模块 | service 文件 | 方法数 | 复杂度 |
|------|-------------|--------|--------|
| doctors | service.py + service_mutation.py + service_query.py | 15+ | 中 |
| schedules | 6 个 service 文件 | 30+ | 高 |
| appointments | 3 个 service 文件 | 20+ | 高 |
| medical_records | service.py | 7 | 低 |
| examination_reports | service.py | 6 | 低 |
| consultation_fees | 4 个 service 文件 | 15+ | 中 |
| waitlist | service.py | 5+ | 中 |
| leave_requests | service.py | 5+ | 中 |

**安全机制事实：**
- 所有端点均有认证
- medical_records 创建/更新要求 doctor_id
- examination_reports 上传/删除要求 doctor_id
- 数据隔离：通过 tenant_id
- 操作日志：middleware/operation_log.py

**缓存和性能事实：**
- medical_records service 层使用 joinedload 显式加载关联（覆盖了 model 的默认 lazy loading）
- examination_reports model 上使用 lazy="selectin"
- 其他模型依赖 service 层显式加载

---

## Round 2：辩论层

### 交叉评论投票矩阵

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| 竞品对比标准 | PM 选微医/好大夫作为竞品 | 竞品选择不公平（SaaS 工具 vs C 端平台） | 接受 Critic 质询，调整对标范围 |
| WaitlistEntry 无 AuditMixin | Engineer 标为缺陷 | 可能是有意设计（自定义时间戳更精确） | 接受 Critic，非缺陷 |
| 按钮级权限未检查 | Designer 标为待办 | 代码中已存在权限控制 | 接受 Critic，非缺陷 |
| admin 端病历只读 | PM 标为"已实现" | 粒度不够，应区分"可查看"和"可操作" | 接受 Critic，需细化 |
| 病历硬删除 | 三方均未发现 | 无权限校验的物理删除是合规风险 | 接受 Critic，P0 修复 |
| N+1 问题 | Engineer 标为"可能有" | service 层已处理，未经验证 | 接受 Critic，非缺陷 |
| 停诊受影响预约数 | 三方均未发现 | 字符串筛选整数字段，永远为 0 | 接受 Critic，P0 bug |
| 病历与预约状态联动 | 三方均未发现 | 不检查预约状态即可创建病历 | 接受 Critic，需补充校验 |
| 检查报告详情显示裸 ID | Designer 未发现 | Drawer 显示 UUID 而非可读信息 | 接受 Critic，P1 优化 |
| medical_records 跨模块依赖 | Engineer 未分析 | router 直接调用 examination_reports service | 非紧急，P2 重构 |

### Critic 质询

1. **[Critic -> 全体] 质询 1: PM 的竞品对比标准不公平**
   - 论据: 项目是 B 端 SaaS 工具，对标 C 端平台型产品（微医/好大夫）不恰当
   - 级别: 普通 — 裁决：调整对标范围，聚焦 SaaS 工具类竞品

2. **[Critic -> 全体] 质询 2: WaitlistEntry 无 AuditMixin 是有意设计**
   - 论据: 自定义时间戳（created_at/promoted_at/cancelled_at）比 AuditMixin 更精确
   - 级别: 普通 — 裁决：认同，非缺陷

3. **[Critic -> 全体] 质询 3: 按钮级权限已存在**
   - 论据: examination-report 有 isSuperAdmin 判断，doctor/form 有 canSuperAdmin
   - 级别: 普通 — 裁决：认同，Designer 遗漏

4. **[Critic -> 全体] 质询 4: admin 端病历只读需要细化**
   - 论据: PM 将"病历管理"标为"已实现"，但 admin 端只能查看不能操作
   - 级别: 普通 — 裁决：接受，需评估是否需要 admin 端病历操作

5. **[Critic -> 全体] 质询 5: 病历硬删除无权限校验**
   - 论据: MedicalRecordService.delete() 物理删除且不校验操作者身份
   - 级别: 普通 — 裁决：**P0 修复**

6. **[Critic -> 全体] 质询 6: N+1 问题未经验证**
   - 论据: medical_records service 层已使用 joinedload，Engineer 未检查
   - 级别: 普通 — 裁决：认同，非缺陷

7. **[Critic -> 全体] 质询 7: _count_affected_appointments 字符串筛选整数字段**
   - 论据: Appointment.status 是 Integer，用字符串筛选永远为空
   - 级别: 普通 — 裁决：**P0 bug 修复**

8. **[Critic -> 全体] 质询 8: 病历与预约状态未联动**
   - 论据: 不检查预约状态即可创建病历
   - 级别: 普通 — 裁决：P1 补充校验

9. **[Critic -> 全体] 质询 9: 检查报告详情显示裸 ID**
   - 论据: Drawer 显示 UUID 而非可读信息
   - 级别: 普通 — 裁决：P1 优化

10. **[Critic -> 全体] 质询 10: medical_records 跨模块依赖**
    - 论据: router 直接调用 examination_reports service
    - 级别: 普通 — 裁决：P2 重构

### 独到发现（Critic 遗漏发现）

1. **病历物理删除无权限校验** — `service.py:199-207`，对比 examination_reports 有 doctor_id 校验
2. **_count_affected_appointments 字符串筛选整数** — `leave_requests/service.py:236`，永远返回 0
3. **MedicalRecordCreate status 默认值问题** — 默认为 2（已完成），无法创建草稿
4. **检查报告详情显示裸 ID** — `examination-report/index.tsx:307-310`
5. **CommonService/HealthReminder 被 PM 遗漏** — 属于医疗服务数据基础设施
6. **admin 端病历缺少新增/编辑/删除** — server API 已有，admin 端未对接
7. **visit_date 硬编码 datetime.now()** — `service.py:71`，无法补录历史病历
8. **examination_reports 查询依赖 model lazy 策略** — 与 medical_records 的显式 joinedload 做法不一致

---

## Round 3：共识层

### ✅ 共识项

1. **议题：病历硬删除改为软删除 + 权限校验**
   **结论：** MedicalRecordService.delete() 应改为软删除（添加 deleted_at 字段），并增加权限校验（仅创建医生或管理员可删除）
   **建议行动：** 添加 deleted_at 字段到 MedicalRecord 模型，修改 delete 方法为软删除，增加 doctor_id 或 admin 权限校验
   **成本估算：** 4h（模型迁移 1h + service 修改 2h + 测试 1h）
   **优先级：** P0

2. **议题：_count_affected_appointments bug 修复**
   **结论：** Appointment.status 是 Integer 字段，leave_requests/service.py:236 使用字符串筛选导致永远返回 0
   **建议行动：** 将 `['pending', 'confirmed']` 改为对应的整数值 `[0, 1]`
   **成本估算：** 1h（修改 + 测试）
   **优先级：** P0

3. **议题：检查报告详情 Drawer 显示可读信息**
   **结论：** 当前显示 UUID，应显示关联实体名称并支持跳转
   **建议行动：** 修改 Drawer 组件，加载关联的 appointment/patient/doctor/record 名称，添加链接
   **成本估算：** 3h（API 返回关联名称 1h + 前端 Drawer 修改 2h）
   **优先级：** P1

4. **议题：admin 端病历管理补充操作能力**
   **结论：** 当前 admin 端病历只能查看，server API 已有完整 CRUD。需评估是否需要 admin 端操作
   **建议行动：** 添加 admin 端病历编辑和删除功能（创建仍由医生端负责）
   **成本估算：** 6h（编辑表单 3h + 删除确认 1h + 权限控制 2h）
   **优先级：** P1

5. **议题：病历创建校验预约状态**
   **结论：** 当前不检查预约状态即可创建病历，应限制为"就诊中"或"已完成"的预约
   **建议行动：** 在 MedicalRecordService.create() 中增加预约状态校验
   **成本估算：** 2h（校验逻辑 1h + 测试 1h）
   **优先级：** P1

6. **议题：visit_date 支持调用方指定**
   **结论：** 当前硬编码为 datetime.now()，无法补录历史病历
   **建议行动：** 在 MedicalRecordCreate schema 中添加 visit_date 字段，从关联预约获取或由调用方指定
   **成本估算：** 1h（schema 修改 + service 修改）
   **优先级：** P1

7. **议题：MedicalRecordCreate status 默认值改为草稿**
   **结论：** 默认为 2（已完成）不合理，应默认为 1（草稿）
   **建议行动：** 修改 schema 默认值为 1
   **成本估算：** 0.5h
   **优先级：** P1

### ⚡ 分歧项

1. **议题：admin 端是否需要病历创建功能**
   **各方立场：**
   - PM：需要，机构管理员应能代医生补录病历
   - Designer：需要，但应限制为特殊情况（医生离职/账号异常）
   - Engineer：谨慎，病历创建关联医生身份，admin 代建需明确操作人
   **裁决/建议：** 暂不实现 admin 端创建，仅实现编辑和删除。如果未来有需求再扩展
   **决策依据：** 病历创建涉及医生专业判断，admin 端代建可能引发责任归属问题

2. **议题：medical_records router 直接调用 examination_reports service 是否需要重构**
   **各方立场：**
   - Engineer：应抽取共享查询层解耦
   - PM：当前功能正常，重构收益不大
   **裁决/建议：** P2 级别，当前不影响功能，后续有新需求时再重构
   **决策依据：** 重构成本 > 当前维护成本，且两个模块的耦合是业务上的合理关联

---

## 被低估的优势

1. **排班系统完备度高** — 号源拆分（线上/线下/预留/加号）、冲突检测、规则引擎、日历甘特图、拖拽排班、批量操作，功能深度超过多数竞品
2. **诊费三级配置** — 全局模板 → 门店覆盖 → 医生覆盖，灵活性高
3. **候补队列机制** — 自动提升、优先级排序、位置追踪，是差异化功能
4. **规则快照机制** — Appointment 模型存储预约时的规则快照（book_open_at 等），保证历史预约行为可追溯
5. **三级提醒策略** — 24h/2h/30min 三级提醒，且通过字段标记避免重复发送

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 病历硬删除改软删除 + 权限校验 | 4h | 高（合规+数据安全） | Engineer | 待执行 |
| P0 | _count_affected_appointments bug 修复 | 1h | 高（停诊审核功能失效） | Engineer | 待执行 |
| P1 | 检查报告详情 Drawer 显示可读信息 | 3h | 中（用户体验） | Engineer + Designer | 待执行 |
| P1 | admin 端病历编辑+删除 | 6h | 中（运营效率） | Engineer + Designer | 待执行 |
| P1 | 病历创建校验预约状态 | 2h | 中（数据一致性） | Engineer | 待执行 |
| P1 | visit_date 支持调用方指定 | 1h | 中（补录场景） | Engineer | 待执行 |
| P1 | MedicalRecordCreate status 默认值改草稿 | 0.5h | 低（语义正确） | Engineer | 待执行 |
| P2 | medical_records 与 examination_reports 解耦 | 4h | 低（可维护性） | Engineer | 待评估 |
| P2 | 检查报告 admin 端上传功能 | 4h | 中（运营效率） | Engineer + Designer | 待评估 |
| 待定 | 医生评价/评分系统 | 16h+ | 待定（需产品决策） | PM + Engineer | 需用户确认 |
| 待定 | 诊后随访模块 | 16h+ | 待定（需产品决策） | PM + Engineer | 需用户确认 |
| 待定 | 在线问诊流程（图文/视频） | 40h+ | 待定（需产品决策） | PM + Designer + Engineer | 需用户确认 |

### P0：立即执行（高价值、低成本）

1. **病历硬删除改软删除 + 权限校验** — MedicalRecord 模型添加 deleted_at 字段，delete() 改为软删除，增加 doctor_id 或 admin 权限校验。医疗合规要求病历保存，物理删除不可接受。成本 4h。
2. **_count_affected_appointments bug 修复** — leave_requests/service.py:236 将字符串 `['pending', 'confirmed']` 改为整数 `[0, 1]`。当前停诊审核无法显示受影响预约数。成本 1h。

### P1：本轮迭代（高价值、中等成本）

1. **检查报告详情 Drawer 显示可读信息** — 修改 Drawer 显示关联实体名称而非 UUID，添加跳转链接。成本 3h。
2. **admin 端病历编辑+删除** — 补充 admin 端对病历的编辑和删除操作（创建仍由医生端负责）。成本 6h。
3. **病历创建校验预约状态** — 在 create() 中限制只有"就诊中"或"已完成"的预约可创建病历。成本 2h。
4. **visit_date 支持调用方指定** — schema 添加 visit_date 字段，从关联预约获取或调用方传入。成本 1h。
5. **MedicalRecordCreate status 默认值改草稿** — 默认值从 2 改为 1。成本 0.5h。

### P2：下个周期规划（中等价值、较高成本）

1. **medical_records 与 examination_reports 解耦** — 抽取共享查询层。成本 4h。
2. **检查报告 admin 端上传功能** — admin 端添加检查报告上传入口。成本 4h。

### 待定：需用户确认

1. **医生评价/评分系统** — 需产品决策是否纳入 SaaS 工具范围。成本 16h+。
2. **诊后随访模块** — 需产品决策是否作为标准功能。成本 16h+。
3. **在线问诊流程** — doctor.online_consult_enabled 字段已预留，但完整问诊流程（图文/视频）成本 40h+，需产品决策。

---

## 摘要

**使用模式：** 集中调度

**关键共识：**
- 7 项达成共识（P0: 2 项, P1: 5 项）

**关键分歧：**
- 2 项需要决策者介入（admin 端病历创建、模块解耦）

**Top 3 P0 行动：**
1. 病历硬删除改软删除 + 权限校验（4h）— 合规+数据安全
2. _count_affected_appointments bug 修复（1h）— 停诊审核功能失效
3. （P1 首选）检查报告详情 Drawer 显示可读信息（3h）— 用户体验

**Critic 关键洞察：**
- 病历物理删除无权限校验是合规风险，三方均未发现
- 停诊审核的受影响预约数永远为 0（字符串筛选整数字段 bug）
- 检查报告详情显示裸 UUID，信息展示质量低于病历详情
- visit_date 硬编码为当前时间，无法补录历史病历
