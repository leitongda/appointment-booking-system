# 排班系统增强：排班模板-规则组关联 + ShiftType 抽离

## Context

排班模板（ScheduleTemplate）和规则组（RuleSet）目前仅通过 `shift_type_id` 间接关联。排班模板定义"怎么排班"，规则组定义"怎么预约"，两者通过班次类型（ShiftType）桥接。这导致：

1. **无法为模板指定专属规则** — 规则匹配只能通过 shift_type 级联（doctor > department > store > tenant），无法让某模板直接绑定特定规则组
2. **ShiftType 定义位置不合理** — ShiftType 是共享概念（排班模板、排班记录、规则组都用），但定义在 `rule_set.py` 内
3. **容量字段语义不清** — 排班模板的 `slot_capacity`（每班次号源数）和规则组的 `total_capacity`（预约限制）在 UI 上容易混淆

本次改动包含 4 个独立任务，可并行执行。

---

## 任务 1：ScheduleTemplate 增加 `rule_set_id`（2h）

### 目标
允许排班模板可选关联一个规则组。排班生成时，Schedule 记录继承 `rule_set_id`；规则引擎在匹配时优先检查直接绑定的规则组，未命中再走 shift_type 级联。

### 1.1 Alembic 迁移（103）
- 文件：`apps/server/migrations/versions/103_add_rule_set_id_to_schedule_templates.py`
- `add_column('schedule_templates', Column('rule_set_id', String(36), ForeignKey('rule_sets.id'), nullable=True, comment='关联规则组ID'))`
- `create_index('idx_schedule_templates_rule_set_id', 'schedule_templates', ['rule_set_id'])`
- `add_column('schedules', Column('rule_set_id', String(36), ForeignKey('rule_sets.id'), nullable=True, comment='关联规则组ID'))`
- `create_index('idx_schedules_rule_set_id', 'schedules', ['rule_set_id'])`

### 1.2 模型更新
- **`apps/server/app/models/schedule_template.py`**:
  - 添加 `rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True, index=True, comment="关联规则组ID")`
  - 添加 `rule_set = relationship("RuleSet", backref="schedule_templates")`（注意：RuleSet 已有 `appointments` backref，这里用不同名称）
- **`apps/server/app/models/schedule.py`**:
  - 添加 `rule_set_id = Column(String(36), ForeignKey("rule_sets.id"), nullable=True, index=True, comment="关联规则组ID")`

### 1.3 Schema 更新
- **`apps/server/app/schemas/schedule_template.py`**:
  - `ScheduleTemplateBase`: 添加 `rule_set_id: Optional[str] = Field(None, description="关联规则组ID")`
  - `ScheduleTemplateUpdate`: 添加 `rule_set_id: Optional[str]`
  - `ScheduleTemplateResponse`: 添加 `rule_set_id: Optional[str]` + `rule_set_name: Optional[str]`
  - `ScheduleTemplateCopyRequest`: 添加 `rule_set_id: Optional[str]`
  - `ScheduleTemplateCrossStoreCopyRequest`: 添加 `rule_set_id: Optional[str]`

### 1.4 服务层更新
- **`apps/server/app/modules/schedule_templates/service_mutation.py`**:
  - create/update 方法中处理 `rule_set_id` 字段
  - 校验：如果 `rule_set_id` 非空，验证该 RuleSet 存在且 `enabled=True`
- **`apps/server/app/modules/schedule_templates/service_generation.py`**:
  - `_generate_from_template_internal` 中，创建 Schedule 时赋值 `rule_set_id=template.rule_set_id`

### 1.5 规则引擎更新（核心）
- **`apps/server/app/modules/rule_engine/time_windows.py`**:
  - `check_action_window` 方法修改匹配逻辑：
    ```
    1. 如果 schedule.rule_set_id 存在 → 直接查该 RuleSet
    2. 如果该 RuleSet 匹配（enabled, 未删除, shift_type 匹配）→ 使用它
    3. 否则回退到现有 shift_type 级联逻辑
    ```
  - `get_applicable_rule_set` 方法：先检查 `schedule.rule_set_id`，有则直接查询，否则走 `get_candidate_rule_sets`
  - `get_candidate_rule_sets` 方法：不需要修改（回退路径）

### 1.6 缓存层更新
- **`apps/server/app/modules/rule_engine/cache.py`**:
  - `get_rule_sets_v2` / `set_rule_sets_v2` 增加 `rule_set_id` 参数支持直接缓存查找
  - 缓存 key 格式：当有 `rule_set_id` 时直接缓存 `rule:{tenant_id}:direct:{rule_set_id}`

### 1.7 前端更新
- **`packages/api/src/modules/schedule-template.ts`**:
  - `ScheduleTemplateCreateData` / `ScheduleTemplateUpdateData`: 添加 `ruleSetId?: string`
- **`apps/admin/src/pages/schedule/template/form.tsx`**（或等效表单页面）:
  - 添加规则组选择器（可选），显示当前租户下启用的规则组列表
  - Tooltip 说明："指定规则组后，该模板生成的排班将使用此规则组的预约/签到/取消策略，而非按班次类型自动匹配"

### 1.8 测试
- 文件：`apps/server/tests/unit/test_rule_engine.py` — 补充：
  - 测试 `schedule.rule_set_id` 直接命中场景
  - 测试 `rule_set_id` 指向已禁用规则组时回退到级联逻辑
  - 测试 `rule_set_id` 为空时走原有级联逻辑
- 文件：`apps/server/tests/unit/test_schedule_template_service.py` — 补充：
  - 测试 create/update 传入 `rule_set_id`
  - 测试生成排班时 `rule_set_id` 被继承到 Schedule

---

## 任务 2：规则组页面增加"关联排班模板"列表（2h）

### 目标
在规则组详情页显示关联的排班模板列表，方便管理员了解哪些排班模板在使用该规则组。

### 2.1 Schema 更新
- **`apps/server/app/schemas/rule_set.py`**:
  - 新增 `ScheduleTemplateBrief` 模型：
    ```python
    class ScheduleTemplateBrief(BaseModel):
        id: str
        name: str
        doctor_name: Optional[str] = None
        department_name: Optional[str] = None
        store_name: Optional[str] = None
        shift_type_name: Optional[str] = None
        status: Optional[int] = 1
    ```
  - `RuleSetDetailResponse` 添加 `schedule_templates: List[ScheduleTemplateBrief] = []`

### 2.2 服务层更新
- **`apps/server/app/modules/rule_sets/service_query.py`**:
  - `get_by_id` 方法（或对应的详情查询）：查询关联的排班模板
    ```python
    from app.models.schedule_template import ScheduleTemplate
    templates_result = await db.execute(
        select(ScheduleTemplate)
        .where(ScheduleTemplate.rule_set_id == rule_set.id)
        .order_by(ScheduleTemplate.name)
    )
    ```
  - 组装 `ScheduleTemplateBrief` 列表（JOIN doctor/department/store 获取名称）

### 2.3 路由更新
- **`apps/server/app/modules/rule_sets/router.py`**:
  - GET /{id} 端点返回数据中包含 `schedule_templates` 列表（无需新增端点，扩展现有详情接口）

### 2.4 前端更新
- **`apps/admin/src/pages/system/rule-set-form.tsx`**（或等效详情页）:
  - 在规则组详情中添加"关联排班模板"卡片/表格区域
  - 使用 ProTable 或简单列表展示模板名称、医生、科室、状态
  - 点击模板名称可跳转到排班模板编辑页

### 2.5 API 层更新
- **`packages/api/src/modules/rule-set.ts`**:
  - `RuleSetDetail` 类型添加 `scheduleTemplates?: ScheduleTemplateBrief[]`

### 2.6 测试
- 文件：`apps/server/tests/unit/test_rule_set_service.py` — 补充：
  - 测试详情接口返回关联模板列表
  - 测试无关联模板时返回空列表
  - 测试多模板关联时按名称排序

---

## 任务 3：ShiftType 独立为 models/shift_type.py（1h）

### 目标
将 ShiftType 从 `models/rule_set.py` 抽离到独立文件 `models/shift_type.py`，使其职责更清晰。保持向后兼容（`rule_set.py` 中保留 re-export）。

### 3.1 新建模型文件
- **`apps/server/app/models/shift_type.py`**（新建）:
  ```python
  """班次类型模型"""
  from sqlalchemy import Column, String, Boolean, Text, ForeignKey
  from sqlalchemy.orm import relationship
  from app.db.base import Base, AuditMixin
  import uuid

  class ShiftType(Base, AuditMixin):
      """班次类型表"""
      __tablename__ = "shift_types"

      id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
      code = Column(String(50), unique=True, nullable=False, comment="类型代码: OPD/CHECKUP/EXAM/NURSING/SPECIAL")
      name = Column(String(100), nullable=False, comment="类型名称")
      description = Column(Text, comment="描述")
      enabled = Column(Boolean, nullable=False, default=True, comment="是否启用")
      tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True, comment="租户ID")

      schedules = relationship("Schedule", backref="shift_type")
      rule_sets = relationship("RuleSet", secondary="rule_set_shift_types", back_populates="shift_types")
  ```

### 3.2 更新 rule_set.py（保持兼容）
- **`apps/server/app/models/rule_set.py`**:
  - 删除 `ShiftType` 类定义（第 21-34 行）
  - 在文件顶部添加 re-export：
    ```python
    from app.models.shift_type import ShiftType  # backward compat re-export
    ```
  - `RuleSet.shift_types` relationship 不变（SQLAlchemy 通过字符串 "ShiftType" 解析）

### 3.3 更新 models/__init__.py
- **`apps/server/app/models/__init__.py`**:
  - 修改导入：`from app.models.shift_type import ShiftType`
  - 保留从 `rule_set` 导入其余模型不变

### 3.4 更新直接导入站点（推荐改为新路径，但旧路径通过 re-export 仍可用）

以下文件当前从 `app.models.rule_set` 导入 ShiftType，**推荐**改为从 `app.models.shift_type` 导入，但不强制（re-export 保证兼容）：

| 文件 | 当前导入 |
|------|---------|
| `modules/shift_types/service.py:11` | `from app.models.rule_set import ShiftType` |
| `modules/rule_sets/service_query.py:18` | `from app.models.rule_set import ... ShiftType` |
| `modules/rule_engine/time_windows.py:11` | `from app.models.rule_set import RuleSet, RuleWindow, ShiftType` |
| `modules/schedule_templates/service_generation.py:50` | `from app.models.rule_set import ShiftType` |
| `modules/schedule_templates/service_mutation.py:35` | `from app.models.rule_set import ShiftType` |
| `modules/import_export/service_rule_set_import.py:10` | `from app.models.rule_set import ... ShiftType` |
| `tests/conftest.py:34` | `from app.models.rule_set import RuleSet, ShiftType` |
| `tests/unit/test_rule_engine.py:20` | `from app.models.rule_set import ... ShiftType` |
| `tests/unit/test_rule_set_service.py:19` | `from app.models.rule_set import ... ShiftType` |
| `tests/unit/test_rule_set_permissions.py:12` | `from app.models.rule_set import RuleSet, ShiftType` |
| `tests/integration/test_rule_sets_router_endpoints.py:18` | `from app.models.rule_set import ShiftType` |
| `scripts/init_default_rule_set.py:20` | `from app.models.rule_set import ... ShiftType` |

**策略**：先只做 re-export（零风险），后续可逐步迁移导入路径。本次不改导入路径，避免大规模文件变更。

### 3.5 测试
- 运行全量测试确认无回归：`cd apps/server && pytest tests/unit/ -v`

---

## 任务 4：容量字段 UI 标注区分（1h）

### 目标
在前端明确区分两个容易混淆的容量概念：
- **排班模板 `slotCapacity`**：每班次可预约号源数（物理容量，如"上午可挂 30 个号"）
- **规则组 `totalCapacity`**：预约策略中的总容量限制（运行时约束，0=不限制）

### 4.1 排班模板表单
- **`apps/admin/src/pages/schedule/template/form.tsx`**（或等效表单）:
  - `slotCapacity` 字段添加 tooltip：
    ```
    每个班次可生成的号源数量。例如设置为 10，则该班次可接受 10 个预约。
    注意：此为号源物理上限。如需限制预约频率，请在规则组的容量策略中配置。
    ```
  - 字段 label 保持"每班次号源数"不变

### 4.2 规则组容量策略表单
- **`apps/admin/src/pages/system/rule-set-form.tsx`**（容量策略 Tab）:
  - `totalCapacity` 字段添加 tooltip：
    ```
    运行时预约容量限制。0 表示不限制（使用排班本身的号源数）。
    此限制优先级高于排班的号源数，可用于临时调整某类排班的可预约量。
    ```

### 4.3 排班日历页
- **`apps/admin/src/pages/schedule/calendar/index.tsx`**:
  - 号源列显示改为两行或带标注：
    - 主显示：`已预约/总号源`（来自 Schedule.total_slots / booked_slots）
    - 副标注：如有关联规则组且 `total_capacity > 0`，显示小字"规则限制: {total_capacity}"

---

## 验证计划

1. **迁移验证**：`cd apps/server && alembic upgrade head` — 确认 103 迁移成功
2. **单元测试**：`cd apps/server && pytest tests/unit/test_rule_engine.py tests/unit/test_rule_set_service.py tests/unit/test_schedule_template_service.py -v`
3. **回归验证**：`cd apps/server && pytest tests/unit/ -v` — 确认 ShiftType 抽离不破坏现有功能
4. **前端构建**：`pnpm build:admin` — 确认类型无误
5. **手动验证**：
   - 创建排班模板时可选关联规则组
   - 规则组详情页显示关联的排班模板
   - 规则引擎优先使用模板指定的规则组
   - 容量字段 tooltip 正确显示

## 预估总工时

| 任务 | 预估 | 风险 |
|------|------|------|
| 1. rule_set_id 关联 | 2h | 中 — 规则引擎改动需谨慎 |
| 2. 规则组关联模板列表 | 2h | 低 — 纯展示 |
| 3. ShiftType 抽离 | 1h | 低 — re-export 保证兼容 |
| 4. 容量 UI 标注 | 1h | 低 — 纯 UI |
| **合计** | **6h** | |
