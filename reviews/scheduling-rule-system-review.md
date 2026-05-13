# appointment-booking-system — 自适应多智能体研究画布

> 协作模式：对等协作
> 日期：2026-05-11
> 审查目标：排班规则体系（排班模板、规则组、医生预约设置、排班生成、例外管理、可预约查询）

---

## 模式选择

**选定模式：** 对等协作

**选择理由：** 用户明确要求对等协作模式。排班规则体系涉及产品（入口收敛、运营体验）、设计（表单增强、交互流）、工程（数据模型、链路打通、冲突检测）三方深度交叉，适合充分碰撞后收敛。

---

## Round 1：事实层（只写事实，不评价）

### PM — 产品视角

**功能完成度：**

1. **排班模板** — 已实现
   - CRUD、批量生成、预览生成、自定义容量生成、复制（同医生/跨门店） — `schedule_templates/router.py:77-831`
   - 班次类型绑定已实现：模型字段 `shift_type_id`（`schedule_template.py:19`），创建时校验非空（`service_mutation.py:45`）

2. **规则组** — 已实现
   - CRUD、启用/禁用、时间窗管理、策略管理（预约/签到/容量）、预设模板、规则预览、性能监控、审计日志 — `rule_sets/router.py:1-902`
   - Scope 字段支持：模型含 `store_id`, `department_id`, `doctor_id`（`rule_set.py:60-62`）

3. **医生预约设置** — 部分实现（配置存在但未被患者端读取）
   - CRUD、状态管理、已配置医生列表 — `doctor_booking_settings/router.py:20-192`
   - 患者端可预约查询未使用该配置：`get_available()` 仅用 `days` 参数，不读 `booking_start_offset` / `booking_range_days` / `release_time`
   - 调用方仅限自身 router 和租户清理服务

4. **排班生成** — 已实现
   - 模板→排班转换，`shift_type_id` 已写入 Schedule 记录（`service_generation.py:157,231`）
   - 休息日检查、规则校验调用 — `service_generation.py:23-100`
   - 去重仅精确匹配（同医生、同日期、同开始结束时间），无部分重叠检测 — `service_generation.py:352-361`

5. **例外管理** — 已实现
   - 休息日：模型 `rest_day.py`，排班生成和可预约查询均检查
   - 停诊：模型 `schedule_suspension.py`，批量停诊
   - 自定义排班：`template_id` 为 None 标识，可预约查询优先显示

6. **患者端可预约查询** — 部分实现
   - 日期范围过滤、容量检查、休息日过滤、自定义排班优先 — `service_query.py:164-213`
   - 规则引擎已调用：`rule_engine.check_action_window(s, 'BOOK', now)` — `router.py:723-741`
   - 未读取医生预约设置

**模块间数据流：**

- 排班模板 → 排班生成：`shift_type_id`, `store_id`, `department_id`, `doctor_id`, 时间段、容量等字段均传递 — `service_generation.py:374-389`
- 规则引擎 → 可预约查询：规则引擎在 `router.py:723-741` 被调用，计算 `booking_open_at` / `booking_close_at` / `booking_status`
- 医生预约设置 → 可预约查询：**断裂**，无读取逻辑
- 例外 → 可预约查询：休息日过滤（`service_query.py:186-195`），停诊过滤（`status == 0`），自定义排班优先

**权限与隔离：**

- `doctor_booking_settings` 所有接口均有 `get_current_admin` + `require_permission` + `get_store_filter`/`check_store_access` — `router.py:20-192`
- 对比 `schedules/router.py`、`doctors/router.py`，权限模式一致
- 租户过滤：查询条件添加 `WHERE tenant_id = ?` — `service_query.py:24-26`

**配置校验：**

- 排班模板创建校验：名称/门店/医生/科室/班次类型/星期/时间非空，结束>开始，排除时段不越界不重叠 — `service_mutation.py:37-226`
- 医生-门店-科室归属校验已实现：`service_mutation.py:76-81`
- 排班生成去重：仅精确匹配，无部分重叠检测

### Designer — 用户视角

**页面清单与路由：**

排班规则相关页面分布：

| 路由 | 页面 | 行数 | 导航层级 |
|------|------|------|---------|
| `/organization/medical-config/rule-sets` | 规则组管理 | 274 | 组织架构 > 医疗配置 |
| `/organization/medical-config/rule-sets/create, /:id/edit` | 规则组表单 | 1578 | hideInMenu |
| `/organization/medical-config/shift-types` | 班次类型管理 | 139 | 组织架构 > 医疗配置 |
| `/medical-services/doctor/booking-setting` | 预约设置列表 | - | 医疗服务 > 医生管理 |
| `/medical-services/doctor/booking-setting/create, /:id/edit` | 预约设置表单 | 249 | hideInMenu |
| `/medical-services/schedule/rule` | 排班规则设置 | 885 | 医疗服务 > 排班管理 |
| `/medical-services/schedule/rule/create, /:id/edit` | 排班规则表单 | 511 | hideInMenu |

导航入口分布在 **4 个不同的一级/二级菜单**，无统一的"排班规则中心"入口。

**前后端字段对比：**

1. **规则组表单**：前端有 `name`, `priority`, `shiftTypeIds`, `enabled`, `description` + 时间口径/时间窗/策略等字段。**后端支持但前端未暴露**：`storeId`, `departmentId`, `doctorId`（scope 字段） — `rule-set-form.tsx:419-876`
2. **排班模板表单**：前端有门店/科室/医生/星期/时间/班次数/班次人数/排除时段。**后端支持但前端未暴露**：`shiftTypeId`（班次类型字段） — `schedule/rule/form.tsx:317-420`
3. **医生预约设置表单**：门店/医生/偏移天数/范围天数/放号时间 — 前后端一致

**交互模式：**

- Modal.confirm 用于批量操作确认（启用/禁用/删除/停诊）和生成排班前重复检测
- Loading 状态：表单页使用 state 或 Card loading，列表页使用 ProTable 内置
- 空状态：均依赖 ProTable 默认空状态
- 成功/失败反馈：统一使用 `message.success/error`

**预览功能：**

- 规则组表单：有实时预览面板（`RuleSetLivePreview`）和规则效果预览弹窗（`RulePreviewModal`）
- 排班模板表单：有日历预览（`RulePreviewCalendar`），实时预览排班效果
- 医生预约设置表单：无预览功能

**表单校验：**

- 规则组表单：所有 Tab 字段有 required + 范围校验；跨字段校验仅"未配置时间窗时确认"
- 排班模板表单：必填校验 + 步骤式校验；时间格式校验仅 HH:mm 格式；**无班次类型必填校验（字段缺失）**
- 医生预约设置：必填 + 范围校验 + 医生重复校验 + 门店-医生级联

**门店/科室维度支持：**

| 页面 | 门店 | 科室 |
|------|------|------|
| 规则组表单 | 不支持 | 不支持 |
| 排班模板表单 | 支持（下拉选择） | 支持（级联选择） |
| 医生预约设置 | 支持（下拉选择） | 不支持（隐含在医生中） |

### Engineer — 技术视角

**数据模型：**

- `ScheduleTemplate.shift_type_id`：`String(36), ForeignKey("shift_types.id"), nullable=True, index=True` — `schedule_template.py:19`
- `Schedule.shift_type_id`：`String(36), ForeignKey("shift_types.id")` — `schedule.py`
- `RuleSet` scope 字段：`store_id`, `department_id`, `doctor_id`（均可选，为空表示上级级）— `rule_set.py:60-62`
- `DoctorBookingSetting`：`store_id`, `doctor_id`, `booking_start_offset`, `booking_range_days`, `release_time` — `doctor_booking_setting.py`
- RuleSet ↔ ShiftType：多对多（`rule_set_shift_types` 关联表）

**规则引擎链路：**

- 匹配优先级：医生级 > 科室级 > 门店级 > 租户级 — `time_windows.py:45`
- 匹配核心：通过 `shift_type_id` + scope 字段匹配，按 `priority` 排序
- 调用位置：排班生成时校验（`service_generation.py:79-106`）、可预约查询时计算时间窗（`router.py:723-741`）
- Redis 缓存机制存在

**排班生成链路：**

- `shift_type_id` 从模板传递到 Schedule 记录 — `service_generation.py:157,231`
- 去重条件：`doctor_id` + `schedule_date` + `start_time` + `end_time` 精确匹配 — `service_generation.py:352-361`
- 兜底：数据库唯一约束 IntegrityError

**可预约查询链路：**

- `GET /schedules/available/{doctor_id}` 流程：`get_available()` 获取排班 → 规则引擎计算时间窗 → 容量判断
- 时间范围：纯 `days` 参数（默认 14 天），不使用 `booking_start_offset` / `booking_range_days`
- 规则引擎已调用：`rule_engine.check_action_window(s, 'BOOK', now)` — `router.py:723-741`
- 未读取 `doctor_booking_settings` 表

**权限与隔离：**

- `doctor_booking_settings/router.py` 所有接口有完整鉴权 — 7 个接口全部覆盖
- `GET /schedules/available/{doctor_id}` 是患者端公开接口，无管理员认证
- 租户过滤：`WHERE tenant_id = ?`，通过 `get_current_tenant_id()` 获取

**数据迁移：**

- `082_add_shift_type_to_schedule_templates.py`：新增 `shift_type_id` 列到 `schedule_templates` 表，幂等性设计
- 本地改动已包含模型变更

**依赖和耦合：**

- 排班模板 → 排班生成：单向依赖，清晰
- 规则引擎是底层服务，被排班生成和可预约查询调用，不反向依赖
- `doctor_booking_setting_service` 仅被自身 router 和租户清理服务调用，不被排班模块使用
- 无循环依赖

---

## Round 2：辩论层

### 交叉评论投票矩阵

#### 完整投票矩阵（对等协作模式）

| 议题 | PM | Designer | Engineer | Critic 质询 | 共识？ |
|------|-----|----------|----------|-------------|--------|
| 导航入口分散（4个菜单） | +1 (P2) | +1 | +1 (低优先级) | 普通质询：需验证是否为有意设计 | ✅ 共识 |
| 前端缺失 scope 字段（store/dept/doctor） | +1 (P0) | +1 (阻断性) | +1 (4-6h) | — | ✅ 共识 |
| 前端缺失 shiftTypeId 字段 | +1 (P0) | +1 (阻断性) | +1 (2-4h) | — | ✅ 共识 |
| doctor_booking_settings 未被可预约查询读取 | +1 (P0) | +1 (核心失效) | +1 (8-12h) | — | ✅ 共识 |
| 排班生成仅精确匹配去重，无重叠检测 | +1 (P1) | +1 (数据质量风险) | +1 (6-8h) | — | ✅ 共识 |
| 建立"排班规则中心"统一入口 | +1 (P2，需数据支撑) | +1 | +1 (40-60h，第三阶段) | 普通质询：需产品论证 | ✅ 共识 |
| 增加排班生成前冲突预览 | — | +1 (关键决策点) | +1 (10-15h) | — | ✅ 共识 |
| 原始分析 vs 实际代码严重不符 | +1 (方案规模需重评) | — | +1 (第一阶段高估) | 🚨 关键：需用户确认本地改动状态 | 待定 |
| 方案规模 vs 实际待修复范围 | +1 (重评工作量) | — | +1 (21-33h 非原估) | 🚨 关键：第一阶段大部分已完成 | 待定 |
| 遗漏患者端视角 | 未覆盖 | 未覆盖 | 未覆盖 | 🚨 关键：三方均聚焦管理端 | 待定 |
| 权限已完整（原始分析有误） | +1 (基础要求非差异化) | +1 | +1 | — | ✅ 共识 |
| 数据迁移：历史数据缺 shift_type_id | — | — | 交叉发现 (3-5h) | — | ✅ 新发现 |
| Redis 缓存一致性 | — | — | 交叉发现 (3-4h) | — | ✅ 新发现 |
| 批量操作"盲确认"无影响范围提示 | — | 交叉发现 | — | — | ✅ 新发现 |

图例：
- ✅ = +1（同意）
- ❌ = 反驳（不同意）
- ⚡ = Critic 质询（Critic 不参与投票，仅对议题发起质询）
- 🤝 = 2/3 或 3/3 同意（共识，基于 PM/Designer/Engineer 三方投票）
- ⚠️ = ≤1/3 同意（分歧）

### 独到发现

1. **产品宣称 vs 实际功能的错位**（PM 交叉发现）：后端支持班次类型和 scope 字段但前端不可配置，等同于功能不存在。影响销售承诺兑现。
2. **完整配置路径断裂**（PM 交叉发现）：运营要为"张医生专家门诊配置提前7天放号"，需走 4 步但步骤2前端不支持、步骤3配置无效，用户目标无法达成。
3. **多租户规则串扰风险**（PM 交叉发现）：规则引擎的租户隔离需验证，避免租户A的规则影响租户B。
4. **批量操作"盲确认"**（Designer 交叉发现）：批量启用/禁用/删除/停诊的确认弹窗不展示影响范围，违背"知情决策"原则。
5. **历史数据迁移需求**（Engineer 交叉发现）：现有排班模板 shift_type_id 为 nullable，历史数据无班次类型，规则引擎无法匹配历史排班。
6. **Redis 缓存失效逻辑**（Engineer 交叉发现）：规则引擎有缓存，修改规则组后缓存失效时机未明确。
7. **患者端权限域跨越**（Engineer 交叉发现）：接入 doctor_booking_settings 到可预约查询需要考虑权限域问题（管理端配置 vs 患者端读取）。

### Critic 质询

1. [Critic → 全体] 🚨 **质询 1：原始问题 vs 实际代码严重不符**
   - 论据：用户原始 5 个问题中，问题1/2/4/5 的核心部分在代码中已不存在。可能因本地未提交改动已修复。
   - 要求回应：PM / Engineer
   - 级别：🚨 关键

2. [Critic → PM] 🚨 **质询 2：方案规模 vs 实际待修复范围**
   - 论据：第一阶段"打通主链路"的大部分工作已在本地改动中完成，方案可能过度设计。
   - 要求回应：PM
   - 级别：🚨 关键

3. [Critic → 全体] 🚨 **质询 3：遗漏患者端视角**
   - 论据：三方均聚焦管理端，未评估患者端预约体验问题和 doctor_booking_settings 断裂对患者的影响。
   - 要求回应：PM / Designer
   - 级别：🚨 关键

4. [Critic → PM] 质询 3：doctor_booking_settings 定位模糊
   - 论据：短期保留 vs 并入规则组无明确取舍和时间表
   - 级别：普通

5. [Critic → Designer/PM] 质询 4：缺失"排班规则中心"的用户研究支撑
   - 论据：分散式导航是否为有意设计？合并后权限模型如何处理？
   - 级别：普通

6. [Critic → PM/Engineer] 质询 5：竞品对比标准缺失
   - 论据：无竞品分析，无法判断方案复杂度是否合理
   - 级别：普通

7. [Critic → 全体] 质询 6：缺失系统优势评估
   - 论据：三方聚焦缺陷，未评估已有优势（规则引擎灵活性、预览功能、多租户隔离）
   - 级别：普通

8. [Critic → Engineer/PM] 质询 7：缺少触发频率和影响范围数据
   - 论据：所有问题均无频率/范围数据，优先级缺乏定量支撑
   - 级别：普通

### 🚨 Critic 关键质询追踪

| # | 关键质询内容 | 三方回应摘要 | 回应是否充分 | 处置 |
|---|------------|------------|------------|------|
| 1 | 原始问题 vs 实际代码不符 | PM/Engineer 均确认代码已修复，但未明确区分"已提交"和"未提交本地改动" | 否（需用户确认本地改动状态） | 待定：需用户确认 |
| 2 | 方案规模 vs 实际待修复范围 | PM 重评优先级，Engineer 估算第一阶段实际 21-33h（含前端补字段+接入+权限+迁移） | 部分（需用户确认哪些本地改动可提交） | 待定：需用户确认 |
| 3 | 遗漏患者端视角 | 三方 Round 1 未覆盖，Round 2 PM 部分回应"患者端 always use days=14" | 否（无系统性患者端评估） | 待定：需用户确认 |

---

## Round 3：共识层

### ✅ 共识项

1. **前端规则组表单增加 scope 字段（store_id/department_id/doctor_id）**
   - 结论：后端已支持三级 scope，前端未暴露导致运营只能配租户级通用规则
   - 建议行动：前端表单增加门店/科室/医生级联选择器，含校验和编辑态回显
   - 成本估算：4-6h（Engineer）
   - 负责角色：Designer（交互设计）+ Engineer（实现）
   - 优先级：P0

2. **前端排班模板表单增加班次类型选择器**
   - 结论：后端 shift_type_id 已存在且必填校验已实现，但前端无选择器，功能不可达
   - 建议行动：前端表单增加班次类型下拉选择器，设为必填，关联已有班次类型数据
   - 成本估算：2-4h（Engineer）
   - 负责角色：Designer + Engineer
   - 优先级：P0

3. **doctor_booking_settings 接入可预约查询链路**
   - 结论：配置表完整但未被读取，放号设置 100% 场景失效，是核心功能断裂
   - 建议行动：修改 get_available() 逻辑读取医生预约设置，用 booking_start_offset/booking_range_days/release_time 替代硬编码 days=14
   - 成本估算：8-12h（Engineer），含边界情况处理和测试
   - 负责角色：Engineer
   - 优先级：P0

4. **排班生成增加时间段重叠检测**
   - 结论：当前仅精确匹配去重，部分重叠场景（如 9:00-12:00 vs 10:00-14:00）会产生冲突排班
   - 建议行动：实现时间段重叠检测算法，替代/补充现有精确匹配
   - 成本估算：6-8h（Engineer）
   - 负责角色：Engineer
   - 优先级：P1

5. **增加排班生成前冲突预览**
   - 结论：当前批量生成排班是"盲操作"，运营无法预知冲突，违背预防优于修复原则
   - 建议行动：生成前预览新增/跳过/冲突排班数量和详情
   - 成本估算：10-15h（Engineer）
   - 负责角色：PM（定义预览信息结构）+ Designer（交互设计）+ Engineer（实现）
   - 优先级：P1

6. **历史数据迁移：为现有排班模板补 shift_type_id**
   - 结论：shift_type_id 为 nullable，历史模板无班次类型，规则引擎无法匹配历史排班
   - 建议行动：编写数据迁移脚本，按门店/科室/时间段推断默认班次类型
   - 成本估算：3-5h（Engineer）
   - 负责角色：Engineer
   - 优先级：P1

7. **Redis 缓存失效逻辑确认**
   - 结论：规则引擎使用 Redis 缓存，修改规则组后缓存失效时机未明确
   - 建议行动：确认缓存失效策略，修改规则组/班次类型时主动清除缓存
   - 成本估算：3-4h（Engineer）
   - 负责角色：Engineer
   - 优先级：P1

8. **建立"排班规则中心"统一入口**
   - 结论：4 个分散入口增加认知负担和操作中断，但需产品论证 ROI
   - 建议行动：先增加页面间快速跳转按钮（低成本），后续基于用户行为数据决定是否重构导航
   - 成本估算：快速跳转 4-6h，完整重构 40-60h（Engineer）
   - 负责角色：PM + Designer + Engineer
   - 优先级：P2

### ⚡ 分歧项

1. **doctor_booking_settings 最终定位：保留独立 vs 并入规则组**
   - 各方立场：
   - PM：短期保留独立但进入主链路，后续评估并入
   - Designer：无明确立场
   - Engineer：独立表接入成本更低（8-12h），并入规则组需额外 16-24h 重构
   - 裁决/建议：短期保留独立，打通主链路后观察运营使用情况再决定
   - 决策依据：先让功能生效，再考虑架构优化

2. **导航重构的时机和深度**
   - 各方立场：
   - PM：需用户行为数据支撑，建议先埋点
   - Designer：高优先级，严重影响体验
   - Engineer：功能未打通前统一入口无意义，放第三阶段
   - 裁决/建议：先做页面间快速跳转（P2），完整重构放第三阶段
   - 决策依据：功能优先于体验，打通主链路是前置条件

---

## 被低估的优势

1. **规则引擎的灵活性和优先级机制**：四级匹配（医生>科室>门店>租户）+ Redis 缓存 + 性能监控，架构设计成熟
2. **预览功能**：规则组和排班模板均有实时预览面板和效果预览弹窗，交互体验良好
3. **多租户隔离完整性**：权限、租户过滤、门店隔离全面实现
4. **后端校验的完善程度**：医生归属校验、排除时段重叠/越界校验均已实现，质量高于三方初始预期
5. **模型设计的扩展性**：RuleSet 的 scope 字段、ScheduleTemplate 的 shift_type_id 关联、多对多关系设计均预留了扩展空间

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 前端排班模板增加班次类型选择器 | 2-4h | 高：打通规则引擎核心链路 | Designer+Engineer | |
| P0 | 前端规则组表单增加 scope 字段 | 4-6h | 高：释放后端三级 scope 能力 | Designer+Engineer | |
| P0 | doctor_booking_settings 接入可预约查询 | 8-12h | 高：放号设置 100% 场景失效→生效 | Engineer | |
| P1 | 历史数据迁移补 shift_type_id | 3-5h | 中：历史排班规则匹配 | Engineer | |
| P1 | 排班生成增加时间段重叠检测 | 6-8h | 中：数据质量保障 | Engineer | |
| P1 | Redis 缓存失效逻辑确认 | 3-4h | 中：规则修改后及时生效 | Engineer | |
| P1 | 排班生成前冲突预览 | 10-15h | 中：运营效率提升 | PM+Designer+Engineer | |
| P2 | 页面间快速跳转按钮 | 4-6h | 中：降低导航分散影响 | Designer+Engineer | |
| P2 | 医生预约设置表单增加预览 | 3-4h | 低：配置信心提升 | Designer+Engineer | |
| P2 | 统一"排班规则中心"页面 | 40-60h | 中：长期体验优化 | PM+Designer+Engineer | |
| 待定 | 确认本地改动提交策略 | 0.5h | 高：决定实际待做范围 | 用户 | |
| 待定 | 患者端体验系统性评估 | 8-16h | 待评估 | PM+Designer | |

### P0：立即执行（高价值、低成本）

1. **前端排班模板增加班次类型选择器**（2-4h）— 后端已支持，纯前端工作，打通规则引擎核心匹配链路
2. **前端规则组表单增加 scope 字段**（4-6h）— 后端已支持，释放门店/科室/医生三级规则配置能力
3. **doctor_booking_settings 接入可预约查询**（8-12h）— 核心功能从 100% 失效恢复为生效

**P0 合计：14-22h（约 2-3 个工作日）**

### P1：本轮迭代（高价值、中等成本）

1. **历史数据迁移补 shift_type_id**（3-5h）— 确保历史排班也能命中规则
2. **排班生成增加时间段重叠检测**（6-8h）— 消除"幽灵排班"风险
3. **Redis 缓存失效逻辑确认**（3-4h）— 规则修改后及时生效
4. **排班生成前冲突预览**（10-15h）— 运营从"盲操作"变为"知情决策"

**P1 合计：22-32h（约 3-4 个工作日）**

### P2：下个周期规划（中等价值、较高成本）

1. **页面间快速跳转按钮**（4-6h）— 低成本缓解导航分散问题
2. **医生预约设置表单增加预览**（3-4h）— 补齐交互一致性
3. **统一"排班规则中心"页面**（40-60h）— 需产品论证和用户研究后执行

### 待定：需用户确认

1. **确认本地改动提交策略**：当前本地改动已包含 shift_type_id 模型变更、迁移脚本、权限修复等。需确认这些改动是否可直接提交，这将决定实际待做范围。
2. **患者端体验系统性评估**：Critic 指出三方均遗漏患者端视角。建议评估 doctor_booking_settings 断裂对患者预约体验的实际影响。
3. **原始分析中"已修复问题"的处理**：用户原始 5 个问题中，问题1（鉴权）、2（shift_type_id）、4（校验）、5（生成写入）已在本地改动中修复。方案中针对这些的改造项可标记为已完成。

---

## 摘要

**使用模式：** 对等协作

**关键共识：**
- 10 项达成共识（含 3 项 P0、4 项 P1、3 项 P2）

**关键分歧：**
- 2 项需要决策者介入（doctor_booking_settings 最终定位、导航重构时机）

**Top 3 P0 行动：**
1. 前端排班模板增加班次类型选择器（2-4h）
2. 前端规则组表单增加 scope 字段（4-6h）
3. doctor_booking_settings 接入可预约查询链路（8-12h）

**Critic 关键洞察：**
1. 用户原始 5 个问题中 4 个已在本地未提交改动中修复，方案规模需重新评估
2. 患者端视角被三方完全遗漏，doctor_booking_settings 断裂对患者体验的影响未经评估
3. 第一阶段实际工作量约 21-33h（含前端补字段+接入+权限+迁移），远低于原方案暗示的规模

---

## 附录：模式切换日志

| 时间 | 从 | 到 | 原因 |
|------|-----|-----|------|
| — | — | — | 未切换 |
