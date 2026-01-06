# 规则管理界面优化计划

## 概述

优化规则管理界面，同时提升代码质量和用户体验。保持现有标签页结构，添加批量操作功能。

## 主要问题

### 列表页 (rule-sets.tsx)
- 列定义过长（133行），应提取为常量
- 缺少批量操作功能
- 操作逻辑重复

### 表单页 (rule-set-form.tsx) - 核心问题
- **状态管理混乱**：ProForm 状态与独立状态并存
- **大量重复代码**：30+ 处重复的 onChange 模式
- **缺少表单验证**：策略字段没有验证规则
- **initialValues 庞大**：135行内联默认值

### RuleWindowConfig 组件
- 独立状态管理，未集成到 ProForm
- 重复的 onChange 处理
- 缺少字段验证

### RulePreviewModal 组件
- 预览时与当前编辑的规则组未关联
- 默认值不够智能

---

## 优化方案

### 文件结构

```
apps/admin/src/
├── constants/
│   └── rule-set.ts                       # 新增：选项和默认值
├── pages/system/
│   ├── rule-sets.tsx                     # 修改：添加批量操作
│   ├── rule-set-form.tsx                 # 修改：核心重构
│   └── components/
│       ├── RuleWindowConfig.tsx          # 修改：ProForm.List
│       ├── RulePreviewModal.tsx          # 修改：智能默认值
│       └── RuleSetTableColumns.tsx       # 新增：列定义
```

---

## 详细改动

### 1. 新建 `constants/rule-set.ts`

**目的**：集中管理所有选项和默认值

**内容**：
- 时间来源选项 (TIME_SOURCE_OPTIONS)
- 时区来源选项 (TIMEZONE_SOURCE_OPTIONS)
- 比较精度选项 (COMPARE_PRECISION_OPTIONS)
- 舍入模式选项 (ROUNDING_MODE_OPTIONS)
- 冲突策略选项 (CONFLICT_STRATEGY_OPTIONS)
- 签到状态选项 (AFTER_GRACE_STATUS_OPTIONS)
- 未签到处理选项 (NO_CHECKIN_AFTER_CLOSE_OPTIONS)
- 候补递补策略选项 (WAITLIST_PROMOTE_POLICY_OPTIONS)
- 时间窗动作类型 (WINDOW_ACTION_OPTIONS)
- 时间窗参考点 (WINDOW_REFERENCE_POINT_OPTIONS)
- 时间窗失败策略 (WINDOW_FAIL_POLICY_OPTIONS)
- 默认值配置（RULE_SET_FORM_INITIAL_VALUES 等）

---

### 2. 新建 `components/RuleSetTableColumns.tsx`

**目的**：提取列表列定义为独立模块

**内容**：
```typescript
export const getRuleSetColumns = (handlers: ColumnHandlers): ProColumns<RuleSet>[]
```

通过参数注入处理器，保持灵活性。

---

### 3. 修改 `rule-sets.tsx`

**改动**：
1. 使用 `getRuleSetColumns` 替代内联列定义
2. 添加 `rowSelection` 支持多选
3. 实现批量操作：
   - `handleBatchEnable` - 批量启用（只显示已禁用项）
   - `handleBatchDisable` - 批量禁用（只显示已启用项）
   - `handleBatchDelete` - 批量删除（仅超级管理员）
4. 批量按钮使用 `Promise.all` 并发请求

---

### 4. 修改 `rule-set-form.tsx`（核心）

**核心改动**：

1. **移除独立状态**：
   - 删除 `bookingPolicy`、`checkinPolicy`、`capacityPolicy`、`windows` 状态

2. **统一 ProForm 管理**：
   ```typescript
   // 之前
   const [bookingPolicy, setBookingPolicy] = useState({});
   <ProFormSwitch
     checked={bookingPolicy.requireAuth}
     fieldProps={{ onChange: (val) => setBookingPolicy({ ...bookingPolicy, requireAuth: val }) }}
   />

   // 之后
   <ProFormSwitch name={['bookingPolicy', 'requireAuth']} />
   ```

3. **导入常量**：
   - 替换所有内联选项为常量引用
   - 使用 `RULE_SET_FORM_INITIAL_VALUES`

4. **添加表单验证**：
   - 所有关键字段添加 `rules`
   - 使用 `tooltip` 提供条件提示

5. **改进预览功能**：
   - 传入当前表单数据：`ruleSetData={formRef.current?.getFieldsValue()}`

**预期效果**：
- 代码从 633 行减少到 380 行（-40%）
- 重复代码从 30+ 处减少到 0 处
- 统一状态管理，消除数据不一致

---

### 5. 修改 `RuleWindowConfig.tsx`

**核心改动**：

1. **使用 ProForm.List**：
   ```typescript
   <ProForm.List name="windows">
     {(fields, { add, remove }) => (
       // 动态窗口列表
     )}
   </ProForm.List>
   ```

2. **消除重复代码**：
   - 使用 `name={[field.name, 'fieldName']}` 路径
   - 移除所有 `handleUpdateWindow` 调用

3. **添加条件验证**：
   ```typescript
   <ProFormDependency name={[field.name, 'failPolicy']}>
     {({ failPolicy }) => {
       if (failPolicy === 'ALLOW_WITH_TAG') {
         return <ProFormText name={[field.name, 'failTag']} rules={[{ required: true }]} />;
       }
       return null;
     }}
   </ProFormDependency>
   ```

**预期效果**：
- 代码从 255 行减少到 180 行（-29%）
- 与主表单无缝集成

---

### 6. 修改 `RulePreviewModal.tsx`

**改动**：
1. 添加 `ruleSetData` prop 接收当前表单数据
2. 使用 `useEffect` 智能设置默认值
3. 优先使用传入的 `ruleSetData.shiftTypeIds[0]`

---

## 实施步骤

### 阶段 1：基础设施
- [ ] 创建 `constants/rule-set.ts`

### 阶段 2：列表页优化
- [ ] 创建 `components/RuleSetTableColumns.tsx`
- [ ] 修改 `rule-sets.tsx` 添加批量操作

### 阶段 3：表单页核心重构
- [ ] 修改 `rule-set-form.tsx`：导入常量，重构基础信息和时间口径
- [ ] 修改 `RuleWindowConfig.tsx`：改用 ProForm.List
- [ ] 修改 `rule-set-form.tsx`：重构策略标签（删除独立状态）
- [ ] 修改 `RulePreviewModal.tsx`：智能默认值

### 阶段 4：验收测试
- [ ] 新建规则组完整流程
- [ ] 编辑规则组完整流程
- [ ] 批量操作全场景测试

---

## 关键文件

1. **constants/rule-set.ts** - 新建，所有选项和默认值的单一来源
2. **pages/system/rule-set-form.tsx** - 核心重构，消除双重状态管理
3. **components/RuleWindowConfig.tsx** - 时间窗组件重构
4. **pages/system/rule-sets.tsx** - 列表页增强
5. **components/RuleSetTableColumns.tsx** - 新建，提取列定义

---

## 预期效果

### 代码质量
- 核心业务代码减少 40%
- 重复代码从 30+ 处减少到 0 处
- 统一状态管理

### 用户体验
- 批量操作效率提升 3-5 倍
- 完善表单验证
- 优化预览功能

### 可维护性
- 提取常量和配置
- 模块化列定义
- 遵循 ProForm 最佳实践
