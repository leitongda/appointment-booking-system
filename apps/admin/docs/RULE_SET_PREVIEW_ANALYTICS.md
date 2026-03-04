# 规则组预览埋点文档

## 概述

本文档记录了规则组管理系统中预览功能的埋点设计，用于分析用户对三种预览方式的使用情况，以及预览后的编辑行为。

## 埋点架构

- **埋点基础**: 使用 `@hospital/shared` 中的 Tracker 类
- **埋点工具**: `/apps/admin/src/utils/analytics.ts`
- **数据上报**: 批量上报到 `/api/v1/analytics/batch`
- **埋点开关**: 通过 Tracker 配置的 `enabled` 和 `enableInDev` 控制

## 埋点事件清单

### 1. 实时预览（Live Preview）

#### 1.1 实时预览打开

**事件名**: `rule_preview:live:open`

**触发时机**: 用户进入规则组编辑页，右侧实时预览面板首次渲染时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID（编辑模式）
  ruleSetName?: string;      // 规则组名称
  hasWindows?: boolean;      // 是否配置了时间窗
  hasShiftTypes?: boolean;   // 是否关联了班次类型
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 实时预览面板的打开次数
- 新建 vs 编辑规则组的预览使用率
- 配置完整性（是否有时间窗/班次类型）

#### 1.2 实时预览更新

**事件名**: `rule_preview:live:update`

**触发时机**: 用户编辑表单，实时预览面板自动更新时（节流 3 秒）

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  updateCount: number;       // 累计更新次数（每次上报）
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 实时预览的更新频率
- 用户编辑活跃度
- 平均每次编辑会话的更新次数

### 2. 规则效果预览（Modal Preview）

#### 2.1 Modal 预览打开

**事件名**: `rule_preview:modal:open`

**触发时机**: 用户点击"预览规则效果"按钮，打开预览弹窗时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- Modal 预览的使用频率
- 用户是否主动触发预览

#### 2.2 Modal 预览开始

**事件名**: `rule_preview:modal:start`

**触发时机**: 用户在 Modal 中点击"开始预览"按钮时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  shiftTypeId?: string;      // 选择的班次类型 ID
  scheduleDate?: string;     // 排班日期
  hasCurrentTime?: boolean;  // 是否指定了当前时间
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 预览配置偏好（日期、班次类型选择）
- 是否使用自定义当前时间

#### 2.3 Modal 预览成功

**事件名**: `rule_preview:modal:success`

**触发时机**: 预览请求成功返回结果时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  previewDuration: number;   // 预览耗时（毫秒）
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 预览成功率
- 平均预览响应时间

#### 2.4 Modal 预览失败

**事件名**: `rule_preview:modal:fail`

**触发时机**: 预览请求失败时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  error?: string;            // 错误信息
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 预览失败率
- 常见错误类型

### 3. 快速查看（Drawer Preview）

#### 3.1 Drawer 预览打开

**事件名**: `rule_preview:drawer:open`

**触发时机**: 用户在列表页点击规则组，打开侧边抽屉时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- Drawer 快速查看的使用频率
- 列表页的预览需求

#### 3.2 Drawer 预览关闭

**事件名**: `rule_preview:drawer:close`

**触发时机**: 用户关闭侧边抽屉时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  viewDuration: number;      // 查看时长（毫秒）
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 平均查看时长
- 查看时长分布

### 4. 编辑行为（Edit Behavior）

#### 4.1 预览前编辑状态

**事件名**: `rule_preview:edit:before`

**触发时机**: 用户点击"预览规则效果"按钮前，记录当前编辑状态

**数据字段**:
```typescript
{
  ruleSetId?: string;              // 规则组 ID
  ruleSetName?: string;            // 规则组名称
  tab: EditTabType;                // 当前 Tab
                                   // - basic: 基础信息
                                   // - time: 时间口径
                                   // - windows: 时间窗配置
                                   // - booking: 预约策略
                                   // - checkin: 签到策略
                                   // - capacity: 容量策略
  changedFields?: string[];        // 相对于初始值变化的字段
  hasWindows?: boolean;            // 是否配置了时间窗
  isPresetApplied?: boolean;       // 是否应用了预设模板
  timestamp: number;               // 时间戳
}
```

**分析指标**:
- 预览时的配置完整度
- 用户最常修改的字段
- 预设模板的使用率

#### 4.2 预览后编辑状态

**事件名**: `rule_preview:edit:after`

**触发时机**: 用户预览后返回编辑页并保存时

**数据字段**:
```typescript
{
  ruleSetId?: string;              // 规则组 ID
  ruleSetName?: string;            // 规则组名称
  tab: EditTabType;                // 当前 Tab
  changedFields?: string[];        // 相对于预览前变化的字段
  hasWindows?: boolean;            // 是否配置了时间窗
  timestamp: number;               // 时间戳
}
```

**分析指标**:
- **预览后修改比例**: `changedFields.length > 0` 的占比
- 用户在预览后最常调整的字段
- 预览对编辑决策的影响

#### 4.3 编辑页退出 Tab

**事件名**: `rule_preview:edit:exit_tab`

**触发时机**: 用户切换 Tab 时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  tab: EditTabType;          // 离开的 Tab
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 用户最常使用的 Tab
- Tab 切换顺序
- 在哪个 Tab 退出页面（了解用户关注点）

#### 4.4 编辑保存

**事件名**: `rule_preview:edit:save`

**触发时机**: 用户点击保存按钮时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  tab: EditTabType;          // 当前 Tab
  hasWindows?: boolean;      // 是否配置了时间窗
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 保存操作的 Tab 分布
- 配置完整度对保存的影响

#### 4.5 编辑取消

**事件名**: `rule_preview:edit:cancel`

**触发时机**: 用户点击取消按钮时

**数据字段**:
```typescript
{
  ruleSetId?: string;        // 规则组 ID
  ruleSetName?: string;      // 规则组名称
  tab: EditTabType;          // 当前 Tab
  timestamp: number;         // 时间戳
}
```

**分析指标**:
- 取消操作的 Tab 分布
- 放弃编辑的原因分析

## 核心分析问题

### 预览方式使用频率

1. **实时预览 vs Modal 预览 vs Drawer 预览**
   - 哪种预览方式使用最多？
   - 用户是否同时使用多种预览方式？
   - 不同预览方式的场景差异

2. **实时预览的活跃度**
   - 平均每次编辑会话触发多少次更新？
   - 用户是否频繁查看实时预览？

3. **Modal 预览的使用模式**
   - 预览成功率如何？
   - 预览响应时间是否影响使用体验？
   - 用户是否多次调整参数重新预览？

### 预览后修改比例

1. **预览对编辑决策的影响**
   - 有多少用户在预览后修改了配置？
   - 预览后修改的字段主要是什么？
   - 预览是否帮助用户发现配置问题？

2. **预览前后的配置变化**
   - 预览前后的字段变化对比
   - 用户是否根据预览结果调整时间窗？
   - 预览是否影响策略配置？

### 用户关注点

1. **Tab 使用情况**
   - 用户最常在哪个 Tab 进行编辑？
   - 用户在哪个 Tab 退出页面（说明这是他们最关注的）？
   - Tab 切换的常见路径是什么？

2. **配置完整度**
   - 有多少用户配置了时间窗？
   - 有多少用户关联了班次类型？
   - 配置完整的规则组是否更倾向于保存？

## 数据查询示例

### 查询实时预览使用率

```sql
SELECT
  COUNT(DISTINCT session_id) as total_sessions,
  COUNT(DISTINCT CASE WHEN event_name = 'rule_preview:live:open' THEN session_id END) as live_preview_sessions,
  CAST(COUNT(DISTINCT CASE WHEN event_name = 'rule_preview:live:open' THEN session_id END) AS FLOAT) / COUNT(DISTINCT session_id) as usage_rate
FROM analytics_events
WHERE event_name IN ('rule_preview:live:open', 'page_view')
  AND page_path = '/system/rule-sets/create'
  AND created_at >= NOW() - INTERVAL '7 days';
```

### 查询预览后修改比例

```sql
SELECT
  COUNT(*) as total_previews,
  COUNT(CASE WHEN jsonb_array_length(extra_data->'changedFields') > 0 THEN 1 END) as modified_after_preview,
  CAST(COUNT(CASE WHEN jsonb_array_length(extra_data->'changedFields') > 0 THEN 1 END) AS FLOAT) / COUNT(*) as modification_rate
FROM analytics_events
WHERE event_name = 'rule_preview:edit:after'
  AND created_at >= NOW() - INTERVAL '7 days';
```

### 查询用户最常使用的 Tab

```sql
SELECT
  extra_data->>'tab' as tab,
  COUNT(*) as exit_count,
  CAST(COUNT(*) AS FLOAT) / SUM(COUNT(*)) OVER() as percentage
FROM analytics_events
WHERE event_name = 'rule_preview:edit:exit_tab'
  AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY extra_data->>'tab'
ORDER BY exit_count DESC;
```

### 查询 Modal 预览成功率

```sql
SELECT
  COUNT(CASE WHEN event_name = 'rule_preview:modal:success' THEN 1 END) as success_count,
  COUNT(CASE WHEN event_name = 'rule_preview:modal:fail' THEN 1 END) as fail_count,
  CAST(COUNT(CASE WHEN event_name = 'rule_preview:modal:success' THEN 1 END) AS FLOAT) /
    NULLIF(COUNT(CASE WHEN event_name = 'rule_preview:modal:success' THEN 1 END) +
           COUNT(CASE WHEN event_name = 'rule_preview:modal:fail' THEN 1 END), 0) as success_rate
FROM analytics_events
WHERE event_name IN ('rule_preview:modal:success', 'rule_preview:modal:fail')
  AND created_at >= NOW() - INTERVAL '7 days');
```

## 埋点开关配置

### 开发环境

在开发环境中默认关闭埋点，如需开启，修改 `apps/admin/src/app.tsx`：

```typescript
initTracker({
  platform: 'admin',
  apiBaseUrl: API_BASE_URL,
  enabled: true,
  enableInDev: true,  // 开启开发环境埋点
  debug: true,        // 开启调试日志
});
```

### 生产环境

生产环境默认开启埋点，关闭调试日志：

```typescript
initTracker({
  platform: 'admin',
  apiBaseUrl: API_BASE_URL,
  enabled: true,
  enableInDev: false,  // 生产环境不受此参数影响
  debug: false,        // 关闭调试日志
});
```

## 注意事项

1. **埋点性能**: 实时预览更新已做节流处理（3 秒），避免频繁上报
2. **隐私保护**: 不记录敏感数据，仅记录配置元数据
3. **数据准确性**: 预览后修改的对比基于表单快照，确保数据一致性
4. **错误处理**: 埋点失败不影响正常功能使用

## 后续优化方向

1. 根据埋点数据优化预览组件的交互设计
2. 分析预览耗时，优化性能
3. 基于用户使用频率调整预览功能的优先级
4. 根据修改比例评估预览功能的实际价值

## 相关文件

- 埋点工具: `/apps/admin/src/utils/analytics.ts`
- 实时预览组件: `/apps/admin/src/components/rule-set-visualization/RuleSetLivePreview.tsx`
- Modal 预览组件: `/apps/admin/src/pages/system/components/RulePreviewModal.tsx`
- Drawer 预览组件: `/apps/admin/src/components/rule-set-visualization/RuleSetPreviewDrawer.tsx`
- 编辑页面: `/apps/admin/src/pages/system/rule-set-form.tsx`
- Tracker 基础类: `/packages/shared/src/analytics/tracker.ts`
