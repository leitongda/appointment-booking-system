# 字典功能实施计划

## Context

系统内存在 46 个 Python Enum 类和大量前端硬编码常量（shared/constants、admin/constants、16+ 处页面内联定义），且多处存在重复定义。当前系统没有任何数据字典管理功能。需要：
1. 为 admin 端添加字典管理功能（通用字典引擎）
2. 将系统内适合迁移的硬编码数据迁移到字典管理
3. 消除枚举/常量的重复定义问题

完整分析画布：`reviews/dictionary-feature-review.md`

---

## 第一阶段：字典基础设施（P0）

### 1.1 后端字典模型 + 迁移

**文件：**
- `apps/server/app/models/dict_type.py` — 字典类型模型
- `apps/server/app/models/dict_item.py` — 字典项模型
- `apps/server/app/models/__init__.py` — 注册新模型
- `apps/server/migrations/versions/110_create_dict_tables.py` — Alembic 迁移

**模型设计：**
```python
# dict_type.py
class DictType(Base, AuditMixin):
    __tablename__ = "dict_types"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String(50), nullable=False, comment="字典类型编码")
    name = Column(String(100), nullable=False, comment="字典类型名称")
    description = Column(String(500), nullable=True, comment="描述")
    status = Column(Integer, default=1, comment="状态 1=启用 0=禁用")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    __table_args__ = (UniqueConstraint("code", "tenant_id", name="uq_dict_type_code_tenant"),)

# dict_item.py
class DictItem(Base, AuditMixin):
    __tablename__ = "dict_items"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    dict_type_id = Column(String(36), ForeignKey("dict_types.id"), nullable=False, index=True)
    label = Column(String(200), nullable=False, comment="显示标签")
    value = Column(String(100), nullable=False, comment="字典值")
    sort_order = Column(Integer, default=0, comment="排序")
    status = Column(Integer, default=1, comment="状态 1=启用 0=禁用")
    extra = Column(JSON, nullable=True, comment="扩展数据（颜色、图标等）")
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=True, index=True)
    __table_args__ = (UniqueConstraint("dict_type_id", "value", "tenant_id", name="uq_dict_item_value_tenant"),)
```

**参考实现：** `apps/server/app/models/shift_type.py`（ShiftType 模式）

### 1.2 后端字典模块（router + service + schemas）

**文件：**
- `apps/server/app/modules/dictionaries/__init__.py`
- `apps/server/app/modules/dictionaries/router.py` — 字典类型 CRUD + 字典项 CRUD
- `apps/server/app/modules/dictionaries/service.py` — 字典服务（含 Redis 缓存）
- `apps/server/app/modules/dictionaries/schemas.py` — Pydantic 请求/响应模型
- `apps/server/app/api/v1/__init__.py` — 注册路由

**API 设计：**
```
管理 API（admin 端）:
  GET    /api/v1/dicts                    — 字典类型列表（分页）
  POST   /api/v1/dicts                    — 创建字典类型
  PUT    /api/v1/dicts/{id}               — 更新字典类型
  DELETE /api/v1/dicts/{id}               — 删除字典类型（软删除/禁用）
  GET    /api/v1/dicts/{type_id}/items    — 字典项列表
  POST   /api/v1/dicts/{type_id}/items    — 创建字典项
  PUT    /api/v1/dicts/{type_id}/items/{item_id} — 更新字典项
  DELETE /api/v1/dicts/{type_id}/items/{item_id} — 删除字典项（软删除/禁用）
  PUT    /api/v1/dicts/{type_id}/items/sort — 批量排序

公开查询 API（三端共用）:
  GET    /api/v1/dict-options/{type_code}         — 按类型编码获取已启用的字典项
  GET    /api/v1/dict-options/batch?codes=xxx,yyy — 批量获取多个类型的字典项
```

**认证模式：**
- 管理 API：`Depends(get_current_admin)` + `Depends(require_permission("system:dict"))` （参考 `apps/server/app/modules/shift_types/router.py`）
- 公开查询 API：`Depends(get_current_account)` 或无认证（根据字典类型决定）

**参考实现：**
- `apps/server/app/modules/shift_types/router.py` — CRUD 路由模式
- `apps/server/app/modules/shift_types/service.py` — Service 类模式
- `apps/server/app/common/permission_deps.py` — 权限控制模式

### 1.3 前端字典 API 模块

**文件：**
- `packages/api/src/modules/dict.ts` — 字典 API 封装
- `packages/api/src/index.ts` — 导出 dictApi

**参考实现：** `packages/api/src/modules/shift-type.ts`

### 1.4 前端字典缓存层

**文件：**
- `packages/shared/src/utils/dictCache.ts` — 字典缓存工具（localStorage + TTL）
- `apps/admin/src/hooks/useDict.ts` — 字典数据 hook

**缓存策略：**
- localStorage 存储，TTL 30 分钟
- 页面加载时先读缓存，后台异步刷新
- 字典管理页面操作成功后清除相关缓存

### 1.5 admin 端路由注册

**文件：**
- `apps/admin/config/routes/system.ts` — 新增 `/system/dictionaries` 路由

**路由配置：**
```typescript
{
  path: '/system/dictionaries',
  name: '字典管理',
  component: '@/pages/system/dictionaries',
  access: 'canSystemManagement',
}
```

---

## 第二阶段：admin 端字典管理页面（P0）

### 2.1 字典类型列表页

**文件：** `apps/admin/src/pages/system/dictionaries/index.tsx`

**UI 方案：**
- ProTable 列表展示字典类型（code、name、description、status、操作）
- 使用 `useListPage` + `createListRequest` + `ListOperations` 统一风格
- 操作列：编辑、字典项管理、启用/禁用、删除（Popconfirm）
- 支持按 name/code 搜索

**参考实现：** `apps/admin/src/pages/system/shift-types.tsx`（最简洁的 CRUD 示例）

### 2.2 字典项管理页

**文件：** `apps/admin/src/pages/system/dictionaries/items.tsx`

**UI 方案：**
- 顶部显示字典类型信息（名称、编码、描述）
- ProTable 列表展示字典项（label、value、sort_order、status、操作）
- 支持新增、编辑（ModalForm）、启用/禁用、删除（禁用而非物理删除）
- 后续迭代支持拖拽排序（SortableTable 组件）

**参考实现：** `apps/admin/src/pages/system/consultation-fee-types.tsx` + `apps/admin/src/pages/system/shift-type-form.tsx`

### 2.3 表单组件

**文件：**
- `apps/admin/src/pages/system/dictionaries/components/DictTypeForm.tsx` — 字典类型表单（ModalForm）
- `apps/admin/src/pages/system/dictionaries/components/DictItemForm.tsx` — 字典项表单（ModalForm）

---

## 第三阶段：第一批数据迁移（P0）— 11 项纯显示类字典

**迁移清单（不参与业务逻辑判断，纯前端显示配置）：**

| 字典编码 | 当前分布 | 涉及文件 |
|---------|---------|---------|
| doctor_title | shared/constants/user.ts:40 | 医生职称 |
| education | admin/constants/index.ts:50, admin/pages/doctor/form.tsx:32 | 学历（消除重复） |
| id_card_type | admin/pages/user/detail.tsx:43, patient-h5/pages/profile/patient/edit.tsx:18 | 证件类型 |
| patient_relationship | shared/constants/user.ts:59, admin/pages/user/detail.tsx:35 | 就诊人关系（消除重复） |
| notice_type | admin/constants/formFields.ts:10 | 公告类型 |
| news_type | admin/constants/formFields.ts:19 | 新闻类型 |
| banner_link_type | admin/constants/formFields.ts:28 | 轮播图链接类型 |
| banner_position | admin/constants/formFields.ts:37 | 轮播图位置 |
| booking_notice_type | admin/pages/system/booking-notice.tsx:13 | 预约须知类型 |
| doctor_page_style | admin/pages/doctor/form.tsx:26 | 医生页面风格 |
| processing_method | admin/pages/schedule/suspension.tsx:54 | 停诊处置方式 |

**迁移步骤：**
1. 数据库 seed：编写 Alembic 数据迁移脚本，将枚举值插入 dict_types + dict_items
2. 后端 schemas：将上述字典对应的 Pydantic 字段从枚举改为 `str` 类型
3. 前端常量：将 hardcoded options 改为从字典 API 获取（使用 `useDict` hook）
4. 清理重复定义：删除 admin 页面内联的重复常量

---

## 第四阶段：第二批数据迁移（P1）— 10 项有状态流转字典

| 字典编码 | 当前分布 | 注意事项 |
|---------|---------|---------|
| feedback_type | 后端 models/feedback.py, shared/types/feedback.ts | schemas 层枚举改 str |
| support_ticket_type | 后端 models/support_ticket.py | 同上 |
| support_ticket_priority | 后端 models/support_ticket.py | 同上 |
| message_type | 后端 models/message.py, admin/pages/message/ | 消除多处重复 |
| email_template_type | 后端 models/email_template.py, admin/constants/formFields.ts | 12 种类型 |
| notification_event_type | 后端 unified_message/schemas.py | 通知事件 |
| recipient_rule_type | 后端 unified_message/schemas.py | 接收人规则 |
| send_mode | admin/pages/message/form.tsx:18 | 消息发送模式 |
| appointment_source | shared/constants/appointment.ts:46 | 预约来源 |
| extra_quota_type | 后端 schemas/extra_quota.py, admin/pages/schedule/ | 加号类型 |

---

## 第五阶段：第三批数据迁移（P2）— 2 项深度耦合字典

| 字典编码 | 当前分布 | 注意事项 |
|---------|---------|---------|
| appointment_type | shared/constants/schedule.ts:65, 后端 75 处引用 | 需重构排班任务逻辑 |
| default_time_periods | shared/constants/schedule.ts:192 | 保留 SystemSetting 的门店级覆盖 |

**此阶段需要：**
- 排班任务生成逻辑增加 fallback 策略（字典 API 不可用时使用默认值）
- 保留 Python 枚举作为 fallback，字典仅作前端配置来源

---

## 待用户确认

1. **患者端和小程序端是否需要接入字典 API？** — 当前计划仅覆盖 admin 端，患者端和小程序端仍使用 shared/constants 中的硬编码值。如需统一，额外成本约 8h。

---

## 验证方案

1. **后端验证：**
   - `cd apps/server && pytest tests/unit/` — 运行单元测试
   - `alembic upgrade head` — 验证迁移脚本
   - 手动测试字典 CRUD API（curl 或 Swagger UI）

2. **前端验证：**
   - `pnpm dev:admin` — 启动 admin 端
   - 访问 `/system/dictionaries` 验证字典管理页面
   - 验证字典项的新增、编辑、启用/禁用、排序
   - 验证其他页面的下拉框从字典 API 获取数据

3. **集成验证：**
   - 在字典管理中新增一种"公告类型"，验证内容管理页面的公告类型下拉框是否更新
   - 禁用某个字典项，验证已使用该值的页面是否正常显示

---

## 关键文件清单

**后端新增：**
- `apps/server/app/models/dict_type.py`
- `apps/server/app/models/dict_item.py`
- `apps/server/app/modules/dictionaries/router.py`
- `apps/server/app/modules/dictionaries/service.py`
- `apps/server/app/modules/dictionaries/schemas.py`
- `apps/server/migrations/versions/110_create_dict_tables.py`
- `apps/server/migrations/versions/111_seed_dict_data.py`

**后端修改：**
- `apps/server/app/models/__init__.py` — 注册新模型
- `apps/server/app/api/v1/__init__.py` — 注册路由
- `apps/server/app/schemas/feedback.py` — 枚举改 str（第一批迁移时）
- 其他 schema 文件（按迁移批次）

**前端新增：**
- `packages/api/src/modules/dict.ts`
- `packages/shared/src/utils/dictCache.ts`
- `apps/admin/src/hooks/useDict.ts`
- `apps/admin/src/pages/system/dictionaries/index.tsx`
- `apps/admin/src/pages/system/dictionaries/items.tsx`
- `apps/admin/src/pages/system/dictionaries/components/DictTypeForm.tsx`
- `apps/admin/src/pages/system/dictionaries/components/DictItemForm.tsx`

**前端修改：**
- `packages/api/src/index.ts` — 导出 dictApi
- `apps/admin/config/routes/system.ts` — 新增路由
- 各页面的 hardcoded options 改为 useDict hook（按迁移批次）
