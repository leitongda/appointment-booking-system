# 规则组预览埋点清单

## 已完成的工作

### 1. 埋点工具函数创建

**文件**: `/apps/admin/src/utils/analytics.ts`

**功能**:
- 定义了所有埋点事件常量
- 实现了 13 个埋点函数
- 提供了辅助函数（时间戳、字段对比等）

**埋点事件**:
```typescript
const RULE_PREVIEW_EVENTS = {
  LIVE_PREVIEW_OPEN: 'rule_preview:live:open',
  LIVE_PREVIEW_UPDATE: 'rule_preview:live:update',
  MODAL_PREVIEW_OPEN: 'rule_preview:modal:open',
  MODAL_PREVIEW_START: 'rule_preview:modal:start',
  MODAL_PREVIEW_SUCCESS: 'rule_preview:modal:success',
  MODAL_PREVIEW_FAIL: 'rule_preview:modal:fail',
  DRAWER_PREVIEW_OPEN: 'rule_preview:drawer:open',
  DRAWER_PREVIEW_CLOSE: 'rule_preview:drawer:close',
  EDIT_BEFORE_PREVIEW: 'rule_preview:edit:before',
  EDIT_AFTER_PREVIEW: 'rule_preview:edit:after',
  EDIT_EXIT_TAB: 'rule_preview:edit:exit_tab',
  EDIT_SAVE: 'rule_preview:edit:save',
  EDIT_CANCEL: 'rule_preview:edit:cancel',
};
```

### 2. 实时预览埋点集成

**文件**: `/apps/admin/src/components/rule-set-visualization/RuleSetLivePreview.tsx`

**埋点位置**:
- 组件首次挂载时触发 `LIVE_PREVIEW_OPEN`
- 表单数据变化时触发 `LIVE_PREVIEW_UPDATE`（节流 3 秒）

**收集数据**:
```typescript
{
  ruleSetId?: string;
  ruleSetName?: string;
  hasWindows?: boolean;
  hasShiftTypes?: boolean;
  updateCount?: number;
  timestamp: number;
}
```

### 3. Modal 预览埋点集成

**文件**: `/apps/admin/src/pages/system/components/RulePreviewModal.tsx`

**埋点位置**:
- Modal 打开时触发 `MODAL_PREVIEW_OPEN`
- 点击"开始预览"按钮时触发 `MODAL_PREVIEW_START`
- 预览成功时触发 `MODAL_PREVIEW_SUCCESS`
- 预览失败时触发 `MODAL_PREVIEW_FAIL`

**收集数据**:
```typescript
{
  ruleSetId?: string;
  ruleSetName?: string;
  shiftTypeId?: string;
  scheduleDate?: string;
  hasCurrentTime?: boolean;
  previewDuration?: number;
  error?: string;
  timestamp: number;
}
```

### 4. Drawer 预览埋点集成

**文件**: `/apps/admin/src/components/rule-set-visualization/RuleSetPreviewDrawer.tsx`

**埋点位置**:
- 抽屉打开时触发 `DRAWER_PREVIEW_OPEN`
- 抽屉关闭时触发 `DRAWER_PREVIEW_CLOSE`

**收集数据**:
```typescript
{
  ruleSetId?: string;
  ruleSetName?: string;
  viewDuration?: number;
  timestamp: number;
}
```

### 5. 编辑行为埋点集成

**文件**: `/apps/admin/src/pages/system/rule-set-form.tsx`

**埋点位置**:
- 点击"预览规则效果"按钮前触发 `EDIT_BEFORE_PREVIEW`
- 预览后保存时触发 `EDIT_AFTER_PREVIEW`
- Tab 切换时触发 `EDIT_EXIT_TAB`
- 保存时触发 `EDIT_SAVE`
- 取消时触发 `EDIT_CANCEL`

**收集数据**:
```typescript
{
  ruleSetId?: string;
  ruleSetName?: string;
  tab: EditTabType;
  changedFields?: string[];
  hasWindows?: boolean;
  isPresetApplied?: boolean;
  timestamp: number;
}
```

### 6. 埋点文档创建

**文件**: `/apps/admin/docs/RULE_SET_PREVIEW_ANALYTICS.md`

**内容**:
- 埋点架构说明
- 详细的事件清单（13 个事件）
- 数据字段定义
- 核心分析问题
- 数据查询示例
- 埋点开关配置

## 埋点功能特性

### 性能优化
- **节流处理**: 实时预览更新采用 3 秒节流，避免频繁上报
- **批量上报**: 利用现有 Tracker 的批量上报机制
- **异步上报**: 所有埋点调用都是异步的，不影响用户体验

### 数据完整性
- **规则组标识**: 所有事件都包含规则组 ID 和名称
- **时间戳**: 所有事件都包含精确时间戳
- **上下文信息**: 记录配置状态、变化字段等上下文

### 开发友好
- **类型安全**: 完整的 TypeScript 类型定义
- **开关控制**: 支持开发环境关闭埋点
- **调试模式**: 支持 debug 模式输出日志

## 可回答的分析问题

### 预览方式使用频率
1. 实时预览 vs Modal 预览 vs Drawer 预览的使用率
2. 实时预览的平均更新频率
3. Modal 预览的成功率和响应时间
4. Drawer 预览的平均查看时长

### 预览对编辑的影响
1. **预览后修改比例**: 多少用户在预览后修改了配置？
2. 预览前后最常修改的字段
3. 预览是否帮助用户发现配置问题

### 用户行为模式
1. 用户最常在哪个 Tab 进行编辑？
2. 用户在哪个 Tab 退出页面？
3. Tab 切换的常见路径
4. 预设模板的使用率

### 配置完整度
1. 有多少用户配置了时间窗？
2. 有多少用户关联了班次类型？
3. 配置完整的规则组是否更倾向于保存？

## 文件清单

### 新增文件
1. `/apps/admin/src/utils/analytics.ts` - 埋点工具函数
2. `/apps/admin/docs/RULE_SET_PREVIEW_ANALYTICS.md` - 埋点文档
3. `/apps/admin/docs/ANALYTICS_CHECKLIST.md` - 本清单文件

### 修改文件
1. `/apps/admin/src/components/rule-set-visualization/RuleSetLivePreview.tsx`
2. `/apps/admin/src/components/rule-set-visualization/RuleSetPreviewDrawer.tsx`
3. `/apps/admin/src/pages/system/components/RulePreviewModal.tsx`
4. `/apps/admin/src/pages/system/rule-set-form.tsx`

## 使用说明

### 开发环境
默认关闭埋点。如需开启，修改 `apps/admin/src/app.tsx`:
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
默认开启埋点，无需额外配置。

### 验证埋点
1. 打开浏览器开发者工具
2. 在 Console 中查看埋点日志（需开启 debug 模式）
3. 在 Network 中查看 `/api/v1/analytics/batch` 请求

## 注意事项

1. **埋点不影响功能**: 所有埋点调用都有错误处理，埋点失败不会影响正常功能
2. **隐私保护**: 不记录敏感数据，仅记录配置元数据
3. **性能考虑**: 节流和批量上报机制确保埋点不影响性能
4. **数据准确性**: 预览后修改对比基于表单快照，确保数据一致性

## 后续优化方向

1. 根据埋点数据优化预览组件的交互设计
2. 分析预览耗时，优化性能
3. 基于用户使用频率调整预览功能的优先级
4. 根据修改比例评估预览功能的实际价值
5. 添加更多维度的埋点（如错误类型、配置复杂度等）

## 验证清单

- [x] 创建埋点工具函数
- [x] 集成实时预览埋点
- [x] 集成 Modal 预览埋点
- [x] 集成 Drawer 预览埋点
- [x] 集成编辑行为埋点
- [x] 创建埋点文档
- [x] 创建埋点清单
- [x] 修复 TypeScript 类型问题
- [x] 验证埋点功能完整性

## 统计数据

- **埋点事件数量**: 13 个
- **埋点函数数量**: 13 个
- **修改文件数量**: 4 个
- **新增文件数量**: 3 个
- **文档页数**: 2 个
- **代码行数**: 约 450 行
