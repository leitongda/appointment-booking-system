# P2: 预设模板后端支持 + 预览优先级模拟

## Context

规则组管理系统 P0/P1 全部完成。两个 P2 任务：
1. **预设模板后端支持** — 当前4个模板硬编码在前端 constants，SaaS 多租户应有后端模板管理
2. **预览优先级模拟** — 当前预览通过 `shift_type_id` 自动选最高优先级规则组，用户看不到哪个规则组生效以及为什么

---

## 功能1：预设模板后端支持

### 设计思路

采用**渐进式方案**：后端存储预设模板，保留系统预设不可删除，支持租户自定义预设。前端从后端加载，回退到本地硬编码。

### 后端

#### 新增模型 `RuleSetPreset`

文件：`apps/server/app/models/rule_set.py`（追加）

```
RuleSetPreset:
  id           String(36) PK
  tenant_id    String(36) FK nullable  — null=全局系统预设
  name         String(100)
  description  Text nullable
  config       JSON                    — 完整规则组配置（含 windows、policies）
  is_system    Boolean default=False   — 系统预设不可删除/修改
  sort_order   Integer default=0
  + AuditMixin (created_at, updated_at, created_by, updated_by)
```

#### 新增 Schema

文件：`apps/server/app/schemas/rule_set.py`（追加）

- `RuleSetPresetBase` — name, description, config
- `RuleSetPresetCreate` — 继承 Base，含 sort_order
- `RuleSetPresetUpdate` — 全 Optional
- `RuleSetPresetResponse` — 含 id, is_system, timestamps

#### 新增路由

文件：在 `apps/server/app/modules/rule_sets/router.py` 追加预设端点

- `GET /rule-sets/presets` — 列表（含系统预设 + 当前租户预设）
- `POST /rule-sets/presets` — 创建自定义预设（超管）
- `PUT /rule-sets/presets/{id}` — 更新（仅非系统预设）
- `DELETE /rule-sets/presets/{id}` — 删除（仅非系统预设）

放在同一 router 中，避免创建新模块。服务逻辑用独立函数。

#### 种子数据

在模型文件中提供 `get_system_presets()` 函数，返回4个系统预设的完整配置（从前端常量迁移）。

首次查询时检测：如果系统预设不存在则自动初始化（lazy seed）。

### 前端

#### API 层

文件：`packages/api/src/modules/rule-set.ts`（追加）

```typescript
ruleSetApi.getPresets()           // GET /rule-sets/presets
ruleSetApi.createPreset(data)     // POST /rule-sets/presets
ruleSetApi.updatePreset(id, data) // PUT /rule-sets/presets/{id}
ruleSetApi.deletePreset(id)       // DELETE /rule-sets/presets/{id}
```

#### 常量层

文件：`apps/admin/src/constants/rule-set.ts`

- 保留现有 4 个预设作为**回退**（后端不可用时）
- 新增 `fetchPresets()` 函数优先从后端加载

#### 表单页适配

文件：`apps/admin/src/pages/system/rule-set-form.tsx`

- `PresetModal` 组件改为从后端动态加载预设列表
- 新增"保存为预设"按钮（超管可见）— 将当前表单配置保存为自定义预设

### 关键文件

| 文件 | 改动 |
|------|------|
| `apps/server/app/models/rule_set.py` | 追加 RuleSetPreset 模型 |
| `apps/server/app/schemas/rule_set.py` | 追加预设相关 Schema |
| `apps/server/app/modules/rule_sets/router.py` | 追加预设 CRUD 端点 |
| `apps/server/app/modules/rule_sets/service_query.py` | 追加预设查询 + lazy seed |
| `apps/server/app/modules/rule_sets/service_mutation.py` | 追加预设创建/更新/删除 |
| `packages/api/src/modules/rule-set.ts` | 追加预设 API |
| `apps/admin/src/constants/rule-set.ts` | 保留回退 + 导出 fetchPresets |
| `apps/admin/src/pages/system/rule-set-form.tsx` | 动态加载预设 + 保存为预设 |
| `apps/server/tests/integration/test_rule_sets_router_endpoints.py` | 追加预设相关测试 |

---

## 功能2：预览优先级模拟

### 设计思路

在现有预览功能基础上，增加"匹配规则组"信息展示，让用户看到哪个规则组被选中、有哪些候选规则组、优先级排序。

### 后端

#### 修改预览端点

文件：`apps/server/app/modules/rule_sets/router.py`

在 `RulePreviewResponse` 中新增字段：

```python
class RulePreviewResponse(BaseModel):
    book_window: WindowCheckResult
    checkin_window: WindowCheckResult
    cancel_window: WindowCheckResult
    # 新增
    matched_rule_set: Optional[RuleSetBrief] = None      # 匹配到的规则组
    candidate_rule_sets: List[RuleSetBrief] = []          # 所有候选规则组（按优先级排序）
```

`RuleSetBrief`：`{id, name, priority, enabled}`

#### 修改规则引擎查询

文件：`apps/server/app/modules/rule_engine/time_windows.py`

新增方法 `get_candidate_rule_sets()`，返回所有匹配班次类型的规则组（不仅取第一个）。

`get_applicable_rule_set()` 内部调用，保持向后兼容。

#### Schema 更新

文件：`apps/server/app/schemas/rule_set.py`

追加 `RuleSetBrief` 和更新 `RulePreviewResponse`。

### 前端

#### 预览 Modal 增强

文件：`apps/admin/src/pages/system/components/RulePreviewModal.tsx`

- 新增"匹配规则组"信息区域
- 展示匹配到的规则组名称和优先级
- 展示候选规则组列表（高亮匹配的那个）
- 如果没有匹配到规则组，显示提示

### 关键文件

| 文件 | 改动 |
|------|------|
| `apps/server/app/schemas/rule_set.py` | 更新 RulePreviewResponse |
| `apps/server/app/modules/rule_engine/time_windows.py` | 新增 get_candidate_rule_sets |
| `apps/server/app/modules/rule_sets/router.py` | 预览端点返回匹配信息 |
| `packages/api/src/modules/rule-set.ts` | 更新预览响应类型 |
| `apps/admin/src/pages/system/components/RulePreviewModal.tsx` | 展示匹配信息 |
| `apps/server/tests/integration/test_rule_sets_router_endpoints.py` | 更新预览测试 |

---

## 实施顺序

1. 功能2（预览优先级模拟）— 改动小，3-4个文件，先快速交付
2. 功能1（预设模板后端支持）— 改动大，需要模型/路由/前端全栈

## 验证

1. 后端测试：`pytest tests/integration/test_rule_sets_router_endpoints.py -v`
2. 预览验证：前端打开规则预览，确认显示匹配规则组信息
3. 预设验证：前端打开预设选择弹窗，确认从后端加载；保存当前配置为预设；创建规则组时应用预设
