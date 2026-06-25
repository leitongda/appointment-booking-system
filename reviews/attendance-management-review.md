# 考勤管理功能 - 自适应评审画布

> 协作模式：集中调度
> 执行深度：深度
> 风险升级因子：授权（考勤数据访问控制）、Schema 变更（10+ 新模型）、审批流（补卡/请假审批）
> 日期：2026-06-25
> 审查目标：考勤管理功能（班次管理、签到组管理、考勤管理员、假期管理、打卡、补卡、外勤、考勤规则、我的签到记录、公司每日记录）

---

## Phase 0 审批记录

**基础复杂度：** 深度（50-80 新文件，10 个子功能，跨 4+ 模块）
**风险升级因子：** 授权、Schema 变更、审批流
**最终深度：** 深度
**协作模式：** 集中调度
**用户批准：** 已批准

---

## Round 1：事实层

### PM - 产品视角

**关键事实：**
- F-001: 项目定位为"医院预约挂号系统"，核心业务是患者预约 | 来源: CLAUDE.md | E1 | High
- F-008: 现有 ShiftType 是排班业务分类标签（OPD/CHECKUP/EXAM），无考勤时间语义 | 来源: shift_type.py:15 | E1 | High
- F-014: 现有 LeaveRequest 是医生停诊/调班申请，非员工假期管理 | 来源: leave_request.py:9-39 | E1 | High
- F-020: 现有签到是患者预约签到（appointment_checkins），非员工考勤 | 来源: service_flow.py:20-30 | E1 | High
- F-035: 系统无"员工"角色模型，Doctor 是最接近的用户 | 来源: enums/core.py:57-65 | E1 | High
- F-034: 系统无考勤相关权限码定义 | 来源: access.ts | E2 | High
- F-060: 后端 82 个模块均不包含考勤模块 | 来源: api/v1/__init__.py | E1 | High

**不确定性：** 6 项（目标用户范围、班次复用、打卡技术方案、假期独立性、存储方案、多端选择）

### Designer - 用户视角

**关键事实：**
- F-03: 签到审计日志页面展示患者签到数据，非员工考勤 | 来源: checkin-audit-logs.tsx | E1 | High
- F-04: 停诊审核页使用 ModalForm + Descriptions 模式 | 来源: leave-request/index.tsx | E1 | High
- F-11: 列表页标准模式为 PageContainer > ProTable + useListPage hook | 来源: 多个页面 | E1 | High
- F-17: 审批交互使用 ModalForm + ProFormRadio.Group（通过/拒绝）+ ProFormTextArea | 来源: leave-request | E1 | High
- F-22: admin 端无考勤相关页面 | 来源: 页面扫描 | E1 | High
- F-24: patient-miniapp 有扫码签到（checkin/scan.tsx），但为患者就诊签到 | 来源: miniapp | E1 | High
- F-27: 现有考勤相关功能分布在 organization、medical-services、system 三个分组 | 来源: 路由配置 | E1 | High

### Engineer - 技术视角

**关键事实：**
- F-1.5: 数据库不存在任何考勤相关表 | 来源: grep 搜索 | E2 | High
- F-2.2: 审批引擎支持 business_type 回调注册，可接入补卡/请假审批 | 来源: callback_registry.py | E1 | High
- F-3.3: 模块注册通过 api/v1/__init__.py 的 RouterRegistration 列表 | 来源: __init__.py | E1 | High
- F-4.3: 租户过滤在 service 层手动添加 tenant_id 条件 | 来源: leave_requests/service.py | E1 | High
- F-5.4: Redis 无考勤相关 key 前缀 | 来源: redis.py | E1 | High
- F-6.1: @hospital/api 包无考勤模块 | 来源: packages/api/src/modules/ | E1 | High

### Round 1 质量门禁

- [x] 每条事实包含来源
- [x] 每条事实标注证据级别
- [x] 零评价性词汇
- [x] 覆盖所有调研维度
- [x] 三个视角交集度：高（均确认考勤为全新功能域）

**结果：** 通过
**争议密度：** 低（<20%）
**Round 2 决策：** 降级为仅评审组

---

## Round 2：辩论层（评审组）

### 挑战者 A - 关键质询

**质询 1（关键）：考勤功能目标用户范围不明确**
- 论据：系统无"员工"角色，Account 仅支持 Admin/Doctor/User 三种扩展
- 误报验证：5 问均可回答，考勤是日常运营需求，每日触发
- 级别：**关键**

### 挑战者 B - 替代方案

**设计决策 1：路由分组**
| 方案 | 路径 | 优势 | 风险 |
|------|------|------|------|
| A. organization 下 | /organization/attendance | 与员工管理同组 | 已有 4 个子模块，拥挤 |
| B. operations 下 | /content-center/attendance | 运营管理语义 | URL 前缀不匹配 |
| C. 新建一级分组 | /attendance | 独立清晰，体量足够 | 需调整菜单顺序 |

**设计决策 2：考勤班次**
| 方案 | 说明 | 优势 | 风险 |
|------|------|------|------|
| A. 独立新建 | attendance_shifts 表 | 职责清晰，不污染排班 | 两套"班次"概念 |
| B. 扩展 ShiftType | 新增时间字段 | 减少概念 | 影响排班模块 |
| C. 关联引用 | attendance_shifts.shift_type_id | 支持关联 | 配置复杂 |

**设计决策 3：假期管理**
| 方案 | 说明 | 优势 | 风险 |
|------|------|------|------|
| A. 独立新建 | attendance_leave_requests 表 | 业务隔离 | 两套"请假"概念 |
| B. 扩展 LeaveRequest | 新增 request_type | 复用审批 | 审批回调混乱 |
| C. 共享审批，独立模型 | 新表 + approval_flows 回调 | 架构清晰 | 需新建回调 |

**设计决策 4：打卡验证**
| 方案 | 说明 | 优势 | 风险 |
|------|------|------|------|
| A. 仅 GPS | navigator.geolocation | 简单 | 可被模拟，室内精度差 |
| B. GPS+WiFi MAC | 辅助验证 | 增加安全性 | iOS 11+/Android 10+ 禁止获取 MAC |
| C. GPS+WiFi SSID+设备 | SSID + device_id | 可行 | 隐私合规 |
| D. 可配置化 | 规则中配置验证方式 | 灵活 | 初始仅支持 GPS |

### 审计者 - 一致性检查

1. **模型命名**：使用 `attendance_xxx` 前缀，避免与 appointment check-in 冲突
2. **租户隔离**：所有考勤模型必须包含 `tenant_id`（nullable=True, index=True）
3. **权限命名**：遵循 `attendance:module:action` 格式
4. **Schema 归属**：领域专属放模块内，跨模块复用放全局

### Round 2 质量门禁

- [x] 每个反驳附带理由
- [x] 评审组完成误报抑制检查
- [x] 关键质询标记：1 条
- [x] 争议密度已计算：低

**结果：** 通过
**Round 3 决策：** 直接裁决

---

## Round 3：共识层

### 裁决（Team Lead）

**决策 1：路由分组 → 方案 C（新建一级分组"考勤"）**
- 理由：10 个子功能体量足够独立，避免污染现有分组
- 路径：`/attendance/*`
- 菜单位置：在 organization 和 operations 之间

**决策 2：考勤班次 → 方案 A（独立新建 attendance_shifts）**
- 理由：ShiftType 是排班分类标签（OPD/CHECKUP/EXAM），语义完全不同；独立模型职责清晰
- 新模型字段：id, tenant_id, name, code, start_time, end_time, break_start, break_end, grace_minutes, late_threshold_minutes, early_threshold_minutes, is_flexible, enabled

**决策 3：假期管理 → 方案 C（共享审批，独立模型）**
- 理由：现有 LeaveRequest 面向医生停诊/调班，业务流程完全不同；复用 approval_flows 引擎但独立业务表
- 新模型：attendance_leave_requests + attendance_leave_types + attendance_leave_balances
- 审批回调：注册 business_type="attendance_leave"

**决策 4：打卡验证 → 方案 D（可配置化）+ 初始仅支持 GPS**
- 理由：WiFi MAC 在 iOS 11+/Android 10+ 不可行；GPS SSID 可后续迭代；可配置化支持灵活扩展
- 初始实现：GPS 定位 + 允许半径配置

**决策 5：目标用户 → 覆盖 Admin + Doctor，不引入新角色**
- 理由：系统当前仅有 Admin/Doctor/User 三种角色，考勤覆盖前两者即可；User（患者）无考勤需求
- 考勤主体通过 account_id 关联统一账号表

### 共识项

| # | 议题 | 结论 | 严重度 | 证据 |
|---|------|------|--------|------|
| 1 | 路由分组 | 新建 /attendance 一级分组 | P2 | E3 |
| 2 | 考勤班次 | 独立新建 attendance_shifts | P2 | E1 |
| 3 | 假期管理 | 独立模型 + 共享审批引擎 | P2 | E1 |
| 4 | 打卡验证 | 可配置化，初始 GPS | P2 | E3 |
| 5 | 目标用户 | Admin + Doctor | P1 | E1 |
| 6 | 模型命名 | attendance_xxx 前缀 | P3 | E1 |
| 7 | 租户隔离 | 全部包含 tenant_id | P1 | E1 |
| 8 | 权限命名 | attendance:module:action | P3 | E1 |
| 9 | Schema 归属 | 领域专属放模块内 | P3 | E2 |

### Open Risks

1. **考勤数据量增长**：每日打卡记录 + 每日统计可能产生大量数据，需设计清理和归档策略
2. **隐私合规**：GPS 定位和设备信息收集需符合《个人信息保护法》，需在 UI 中明确告知并获取同意

---

## 被低估的优势

1. 审批引擎（approval_flows）已具备通用审批能力，补卡/请假审批可通过 business_type 回调无缝接入
2. 统一账号体系（Account + AccountAdmin/AccountDoctor）已支持多角色，考勤主体可直接关联 account_id
3. 排班模板（ScheduleTemplate）已包含 start_time/end_time/break_times，考勤班次可参考其数据结构
4. packages/api 的 Taro 适配器已就绪，小程序端打卡无需额外适配工作

---

## 行动计划（按杠杆率排序）

### P1：架构决策（本轮必须确认）

| # | 行动 | 杠杆率 | 工程成本 | 风险降低 | 负责 |
|---|------|--------|---------|---------|------|
| 1 | 确认考勤主体范围（Admin + Doctor） | 最高 | Low | High | PM |
| 2 | 确认考勤模型设计（attendance_xxx 体系） | 最高 | Low | High | Engineer |

### P2：核心实现（按阶段分批）

**阶段一：基础框架（~30h）**

| # | 行动 | 工程成本 | 风险降低 | 杠杆率 | 负责 |
|---|------|---------|---------|--------|------|
| 3 | Alembic 迁移：创建考勤核心表（attendance_shifts, attendance_groups, attendance_records, attendance_rules） | Medium | High | 高 | Engineer |
| 4 | 后端模块：班次管理 CRUD（attendance_shifts/router.py + service.py + schemas.py） | Medium | Medium | 中 | Engineer |
| 5 | 后端模块：签到组管理 CRUD（attendance_groups/router.py + service.py） | Medium | Medium | 中 | Engineer |
| 6 | 后端模块：考勤规则配置（attendance_rules/router.py + service.py） | Medium | High | 高 | Engineer |
| 7 | 路由注册：api/v1/__init__.py 添加考勤模块 + 前端路由配置 | Low | Medium | 高 | Engineer |

**阶段二：打卡核心（~40h）**

| # | 行动 | 工程成本 | 风险降低 | 杠杆率 | 负责 |
|---|------|---------|---------|--------|------|
| 8 | 后端模块：打卡 API（GPS 定位验证 + 迟到/早退/旷工判定逻辑） | High | High | 中 | Engineer |
| 9 | 后端模块：补卡申请 + 审批回调（接入 approval_flows） | Medium | Medium | 中 | Engineer |
| 10 | 后端模块：外勤打卡 | Medium | Low | 低 | Engineer |
| 11 | 小程序/H5 端：打卡页面（GPS 定位 + 调用打卡 API） | High | High | 中 | Engineer |

**阶段三：统计与展示（~30h）**

| # | 行动 | 工程成本 | 风险降低 | 杠杆率 | 负责 |
|---|------|---------|---------|--------|------|
| 12 | 后端模块：假期管理（类型 + 额度 + 申请 + 审批） | Medium | Medium | 中 | Engineer |
| 13 | 后端模块：每日考勤统计（Celery 定时任务聚合） | Medium | Medium | 中 | Engineer |
| 14 | 前端页面：admin 考勤管理页面（班次/签到组/规则/假期/考勤管理员） | High | High | 中 | Designer + Engineer |
| 15 | 前端页面：我的签到记录（doctor 端 + admin 端） | Medium | Medium | 中 | Designer + Engineer |
| 16 | 前端页面：公司每日记录（admin 端，ProTable + 统计卡片） | Medium | Medium | 中 | Designer + Engineer |
| 17 | 权限配置：access.ts + init_permissions.py 添加考勤权限 | Low | Medium | 高 | Engineer |
| 18 | API 包：packages/api 添加考勤模块类型和方法 | Low | Low | 中 | Engineer |

### P3：后续迭代

1. 打卡验证增强：WiFi SSID 验证、设备指纹绑定
2. 考勤报表导出（Excel）
3. 考勤异常告警（Celery 定时检测 + 通知）
4. 考勤数据归档策略
5. 考勤与排班联动（排班自动生成考勤班次）

---

## 数据模型设计（裁决结果）

### 核心模型（阶段一）

```
attendance_shifts（考勤班次）
  id, tenant_id, name, code, start_time, end_time
  break_start, break_end, grace_minutes
  late_threshold_minutes, early_threshold_minutes
  is_flexible, enabled, created_at, updated_at

attendance_groups（签到组）
  id, tenant_id, name, description
  check_method (gps/wifi/device), location_lat, location_lng
  location_radius, wifi_ssid, enabled
  created_at, updated_at

attendance_group_members（签到组成员）
  id, group_id, account_id, tenant_id

attendance_records（打卡记录）
  id, tenant_id, account_id, shift_id, group_id
  check_date, check_in_time, check_out_time
  check_in_location, check_out_location
  check_in_device, check_out_device
  status (normal/late/early/absent/leave/field_work)
  late_minutes, early_minutes, work_hours
  created_at

attendance_rules（考勤规则）
  id, tenant_id, name, description
  late_policy, early_policy, absent_policy
  overtime_policy, flexible_window
  enabled, created_at, updated_at
```

### 扩展模型（阶段二）

```
attendance_leave_types（假期类型）
  id, tenant_id, name, code, paid, default_days, enabled

attendance_leave_balances（假期余额）
  id, tenant_id, account_id, leave_type_id, year, total_days, used_days

attendance_leave_requests（假期申请）
  id, tenant_id, account_id, leave_type_id
  start_date, end_date, duration_days, reason
  status, reviewer_id, review_comment, reviewed_at

attendance_supplement_requests（补卡申请）
  id, tenant_id, account_id, record_id, supplement_time
  reason, status, reviewer_id, review_comment

attendance_field_work（外勤记录）
  id, tenant_id, account_id, date, start_time, end_time
  location, reason, status, reviewer_id

attendance_stat_daily（每日统计）
  id, tenant_id, account_id, date, shift_id
  scheduled_in, scheduled_out, actual_in, actual_out
  status, late_minutes, early_minutes, work_hours, overtime_hours
```

---

## 摘要

**使用模式：** 集中调度
**执行深度：** 深度
**风险升级：** 授权 + Schema 变更 + 审批流

**关键共识：** 9 项
**关键分歧：** 0 项
**Open Risks：** 2 项

**Top 3 行动（按杠杆率）：**
1. 确认考勤主体范围（Admin + Doctor）— PM 裁决
2. 确认考勤模型设计（attendance_xxx 体系）— Engineer 设计
3. 创建考勤核心表 Alembic 迁移 — Engineer 实现

**评审组关键洞察：**
- 考勤管理是全新功能域，与现有排班/签到/请假模块业务语义完全不同
- 审批引擎（approval_flows）可无缝接入补卡/请假审批，无需重新实现
- 打卡验证建议可配置化，初始仅支持 GPS，后续迭代扩展 WiFi/设备验证
- 路由建议新建一级分组"考勤"，保持功能独立性
