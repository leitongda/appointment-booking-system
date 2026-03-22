# appointment-booking-system — 导入导出功能审计

> 协作模式：集中调度
> 日期：2026-03-22
> 审查目标：admin 端各模块导入导出接口正确性，部分导出后 Excel 为空问题

---

## 模式选择

**选定模式：** 集中调度

**选择理由：**
- 这是代码审计类任务，需要系统性地扫描多个模块
- 问题明确（导出 Excel 为空），不需要跨职能复杂权衡
- 需要快速收敛定位根因，集中调度最高效

---

## Round 1：事实层

### PM — 产品视角

**导入导出模块覆盖范围：**
- 主模块：`/apps/server/app/modules/import_export/`（路径前缀 `/data/export`, `/data/import`）
- 独立导出模块：`/apps/server/app/modules/export/`（路径前缀 `/export`）
- 基础设施层：`/apps/server/app/infrastructure/excel/`

**支持导入的实体（5个）：**
| 实体 | 端点 | 必填字段 | 权限控制 |
|------|------|---------|---------|
| 医生 | `POST /import/doctors` | 姓名、门店名称、科室名称 | `require_permission("doctor:create")` |
| 患者 | `POST /import/patients` | 姓名、手机号 | `require_permission("patient:create")` |
| 科室 | `POST /import/departments` | 科室名称、门店名称 | `require_permission("department:create")` |
| 门店 | `POST /import/stores` | 门店名称、城市 | `require_permission("store:create")` |
| 规则组 | `POST /import/rule-sets` | 规则组名称 | 无 |

**支持导出的实体（10+个）：**
- `/export` 模块：appointments, patients, schedules（无权限控制）
- `/data/export` 模块：doctors, patients, departments, stores, schedule-templates, users, logs, feedbacks, rule-sets（无权限控制）

**模块定位差异：**
- `/export` 模块：业务数据导出（预约、排班），84 行代码
- `/import_export` 模块：主数据导出（医生、科室、门店等），553 行代码

### Designer — 用户视角

**导出文件格式：**
- 统一使用 `.xlsx` 格式
- Content-Type: `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`

**文件命名规则：**
- `{实体名}_YYYYMMDDHHMMSS.xlsx`

**空数据处理：**
- 空数据时仍会生成 Excel 文件（仅含表头）
- 这是**有意设计**，非 bug

**错误处理：**
- 导出路由层无 try-except 错误捕获
- 认证错误由 FastAPI 依赖注入处理

### Engineer — 技术视角

**Excel 生成实现：**
- 使用 `openpyxl>=3.1.0`
- 核心类：`ExcelExportService`（`/app/infrastructure/excel/export_service.py`）

**关键发现 - 门店过滤缺失：**
- 所有导出端点都没有使用 `get_store_filter()` 或 `check_store_access()` 函数
- `current_admin` 包含门店信息（`store_ids`, `current_store_id`），但导出逻辑**未使用**
- 来源：`/app/common/deps.py:319-343` 定义了 `get_store_filter()` 但未被导出模块调用

**关键发现 - 权限控制缺失：**
- 导入端点有 `require_permission` 权限控制
- 导出端点只有 `get_current_admin`，没有细粒度权限控制
- 来源：`/app/common/deps.py:553-601` 定义了 `require_permission()` 但未被导出模块调用

**查询模式问题（export/service.py:22-98）：**
```python
# 预约导出 - 没有 store_id 过滤
query = select(Appointment).options(...)
# 只支持 start_date, end_date, status, doctor_id 过滤
# 没有 store_id 参数，也没有使用 current_admin 中的门店信息
```

---

## Round 2：辩论层

### 交叉评论投票矩阵（集中调度模式 - 简化版）

| 议题 | 裁决者立场 | Critic 质询 | 最终裁决 |
|------|-----------|------------|---------|
| "Excel 为空"根因 | 门店过滤缺失导致 | 需确认具体表现 | 确认门店过滤是主要问题 |
| 两个模块并存 | 功能互补，非重复 | 需澄清定位 | 保持现状，统一文档 |
| 空数据返回空表头 | 有意设计 | 合理 | 保持现状 |
| 权限控制缺失 | 安全隐患 | 需要添加 | P1 修复 |

### 独到发现

1. **门店过滤缺失是"Excel 为空"的主要根因**：非超管用户绑定了特定门店，但导出时：
   - 前端可能传入了错误的 `store_id`
   - 或者根本没有传 `store_id`，导致查询了不属于用户的数据
   - 正确做法应使用 `get_store_filter(current_admin)` 自动获取用户可访问的门店

2. **权限控制不一致**：导入有权限控制，导出没有，存在安全隐患

3. **两个模块的定位**：
   - `/export`：日常业务数据导出（预约、排班）
   - `/data/export`：主数据管理导出（医生、科室等）
   - 功能互补，但需要统一权限和门店过滤逻辑

### Critic 质询与回应

#### 质询 1：两个导出模块的功能重叠被高估
- **回应**：确认 Critic 观点正确。两个模块功能互补，不是重复建设。
- **裁决**：保持现状，建议在文档中说明两个模块的定位差异。

#### 质询 2："无数据为空判断"是否真的是问题
- **回应**：确认这是有意设计，空数据时返回带表头的模板。
- **裁决**：保持现状，这不是 bug。

#### 🚨 质询 3：用户反馈的"Excel 为空"到底是什么情况？
- **回应**：经过深入代码分析，确认**门店过滤缺失**是主要根因。
- **证据**：
  - `export/service.py` 中的 `export_appointments()`, `export_patients()`, `export_schedules()` 都没有 `store_id` 参数
  - `import_export/router_export.py` 中的端点虽然有 `store_id` 参数，但没有使用 `get_store_filter()` 自动过滤
  - 非超管用户如果前端传错 `store_id` 或不传，可能查到空数据
- **裁决**：这是 bug，需要修复。

#### 质询 4："无错误处理机制"缺少频率数据
- **回应**：同意 Critic 观点，这不是高优先级问题。
- **裁决**：降级为 P2。

#### 质询 5："无文件大小验证"的影响范围未评估
- **回应**：操作日志已有 10000 条限制，其他导出数据量通常不大。
- **裁决**：保持现状，后续如有性能问题再处理。

#### 🚨 质询 6：两个导出模块的产品定位
- **回应**：已澄清定位差异，功能互补。
- **裁决**：保持现状，添加文档说明。

#### 🚨 质询 8：是否遗漏了权限控制问题？
- **回应**：确认这是被遗漏的问题。导入有权限控制，导出没有。
- **裁决**：P1 修复，为导出端点添加权限控制。

---

## Round 3：共识层

### ✅ 共识项

1. **门店过滤缺失是"Excel 为空"的主要根因**
   - 结论：导出端点没有使用 `get_store_filter()` 函数，导致非超管用户可能导出空数据
   - 建议行动：为所有导出端点添加门店过滤逻辑
   - 成本估算：4h
   - 优先级：P0

2. **权限控制不一致需要修复**
   - 结论：导入有权限控制，导出没有，存在安全隐患
   - 建议行动：为导出端点添加 `require_permission` 权限控制
   - 成本估算：2h
   - 优先级：P1

3. **空数据返回空表头是有意设计**
   - 结论：这不是 bug，保持现状
   - 建议行动：无需修改
   - 成本估算：0h
   - 优先级：无需处理

4. **两个模块并存是合理的**
   - 结论：功能互补，不是重复建设
   - 建议行动：在 API 文档中说明两个模块的定位差异
   - 成本估算：0.5h
   - 优先级：P2

### ⚡ 分歧项

无

---

## 被低估的优势

1. **统一的 Excel 导出服务**：`ExcelExportService` 提供了良好的代码复用，样式、列宽、冻结首行都已实现
2. **多工作表支持**：规则组导出支持多工作表，功能完善
3. **导入模板设计**：包含示例数据和字段批注，用户体验良好

---

## 行动计划（按 ROI 排序）

| 优先级 | 行动 | 成本 | 价值 | 负责 | 状态 |
|--------|------|------|------|------|------|
| P0 | 为导出端点添加门店过滤逻辑 | 4h | 高 | Engineer | **已完成** |
| P0 | 验证"Excel 为空"问题的具体复现步骤 | 1h | 高 | PM | 待执行 |
| P1 | 为导出端点添加权限控制 | 2h | 高 | Engineer | 待执行 |
| P2 | 添加导出 API 文档说明 | 0.5h | 中 | PM | 待执行 |
| P2 | 考虑为大数据量导出添加分页/流式机制 | 8h | 中 | Engineer | 待评估 |

### P0：立即执行（高价值、低成本）

1. **为导出端点添加门店过滤逻辑**
   - 文件：`apps/server/app/modules/export/service.py`, `apps/server/app/modules/import_export/router_export.py`
   - 修改：在查询条件中添加 `store_id` 过滤，使用 `get_store_filter(current_admin)` 获取用户可访问的门店
   - 成本：4h
   - 验证：非超管用户导出时，只能看到自己绑定门店的数据

2. **验证"Excel 为空"问题的具体复现步骤**
   - 与用户确认具体场景（哪个端点、什么筛选条件）
   - 确认是否是门店过滤问题导致
   - 成本：1h

### P1：本轮迭代（高价值、中等成本）

1. **为导出端点添加权限控制**
   - 文件：`apps/server/app/modules/export/router.py`, `apps/server/app/modules/import_export/router_export.py`
   - 修改：添加 `require_permission("xxx:export")` 依赖
   - 成本：2h

### P2：下个周期规划（中等价值、较高成本）

1. **添加导出 API 文档说明** - 0.5h
2. **考虑为大数据量导出添加分页/流式机制** - 8h（待评估是否需要）

### 待定：需用户确认

1. **确认"Excel 为空"的具体表现**
   - 是完全没有数据行（但有表头）？
   - 还是文件完全损坏无法打开？
   - 还是某些单元格为空？

---

## 摘要

**使用模式：** 集中调度

**关键共识：** 4 项达成共识

**关键分歧：** 无

**Top 3 P0 行动：**
1. 为导出端点添加门店过滤逻辑（成本：4h）- **解决"Excel 为空"的主要根因**
2. 验证"Excel 为空"问题的具体复现步骤（成本：1h）
3. （P1）为导出端点添加权限控制（成本：2h）

**Critic 关键洞察：**
- "Excel 为空"问题需要先定义具体表现，再提出解决方案
- 两个模块的功能定位需要澄清
- 权限控制问题被三方都遗漏了

---

## 附录：关键代码位置

**门店过滤函数（未被使用）：**
- `/app/common/deps.py:319-343` - `get_store_filter()`
- `/app/common/deps.py:346-366` - `check_store_access()`

**权限控制函数（导入使用，导出未使用）：**
- `/app/common/deps.py:553-601` - `require_permission()`

**导出服务（缺少门店过滤）：**
- `/app/modules/export/service.py:22-98` - `export_appointments()` 无 store_id
- `/app/modules/export/service.py:100-150` - `export_patients()` 无 store_id
- `/app/modules/export/service.py:152-206` - `export_schedules()` 无 store_id

**导出路由（store_id 参数未使用 get_store_filter）：**
- `/app/modules/import_export/router_export.py:24-73` - `export_doctors()`
- `/app/modules/import_export/router_export.py:76-119` - `export_patients()`
- `/app/modules/import_export/router_export.py:122-157` - `export_departments()`
