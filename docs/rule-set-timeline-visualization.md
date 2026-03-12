# 时间轴可视化组件使用指南

## 概述

时间轴可视化组件用于直观显示规则组中时间窗的时间关系，帮助用户理解"提前7天开放、班次开始前1小时截止"等复杂的时间配置。

## 组件列表

### 1. RuleSetTimeline

**位置**: `apps/admin/src/components/rule-set-visualization/RuleSetTimeline.tsx`

**功能**: 基于 Ant Design Timeline 的垂直/水平时间轴展示组件

**使用示例**:

```tsx
import { RuleSetTimeline } from '@/components/rule-set-visualization';

<RuleSetTimeline
  windows={windows}
  direction="vertical"
  compact={false}
  shiftStart={shiftStart}
  shiftEnd={shiftEnd}
/>
```

**参数说明**:
- `windows`: RuleWindow[] - 时间窗配置数组
- `direction`: 'vertical' | 'horizontal' - 时间轴方向，默认 'vertical'
- `compact`: boolean - 是否使用紧凑模式，默认 false
- `shiftStart`: Date - 班次开始时间（可选）
- `shiftEnd`: Date - 班次结束时间（可选）

**特性**:
- 按动作类型（预约、签到、取消、释放）分组显示
- 显示相对于班次时间的开放和截止偏移
- 计算并显示实际时间点（如 08:00）
- 提供友好的人类可读描述（如"班次开始时间提前7天开放"）

### 2. WindowTimelineCard

**位置**: `apps/admin/src/components/rule-set-visualization/WindowTimelineCard.tsx`

**功能**: 单个时间窗的详细时间轴卡片组件

**使用示例**:

```tsx
import { WindowTimelineCard } from '@/components/rule-set-visualization';

<WindowTimelineCard
  window={window}
  shiftStart={shiftStart}
  shiftEnd={shiftEnd}
  compact={false}
  highlightOnHover={true}
/>
```

**参数说明**:
- `window`: RuleWindow - 单个时间窗配置
- `shiftStart`: Date - 班次开始时间
- `shiftEnd`: Date - 班次结束时间（可选）
- `compact`: boolean - 是否使用紧凑模式，默认 false
- `highlightOnHover`: boolean - 鼠标悬停时是否高亮，默认 true

**特性**:
- 可视化展示开放时间 → 参考点 → 截止时间的关系
- 使用不同颜色区分开放（绿色）和截止（橙色）
- 显示实际时间范围
- 提供友好的时间描述
- 支持鼠标悬停交互效果

### 3. 在时间窗配置中集成

**位置**: `apps/admin/src/components/RuleWindowConfig.tsx`

**功能**: 在规则组表单的时间窗配置 Tab 中集成了时间轴可视化

**使用方法**:
1. 在规则组表单页面，切换到"时间窗配置" Tab
2. 点击右上角的"显示时间轴"按钮
3. 时间轴将显示在时间窗配置表单下方
4. 当添加或修改时间窗时，时间轴会实时更新

**显示内容**:
- 所有已启用的时间窗
- 每个时间窗的开放和截止偏移
- 基于默认班次时间（8:00）的实际时间计算
- 按动作类型分组的友好描述

## 时间格式化

### formatOffset 函数

将秒数偏移转换为人类可读格式：

```typescript
import { formatOffset } from '@/utils/ruleSetFormatter';

formatOffset(-604800); // "提前7天"
formatOffset(-3600);   // "提前1小时"
formatOffset(1800);    // "延后30分钟"
formatOffset(null);    // "不限制"
```

### 实际时间计算

使用 `calculateWindowTime` 函数计算实际时间点：

```typescript
import { calculateWindowTime } from '@/utils/ruleSetFormatter';

const shiftStart = new Date('2024-01-01T08:00:00');
const openTime = calculateWindowTime(
  'SHIFT_START',  // 参考点
  -604800,        // 提前7天（秒）
  shiftStart      // 班次开始时间
);
// 结果: 2023-12-25T08:00:00
```

## 视觉设计

### 颜色方案

- **预约时间窗**: 蓝色 (#1890ff)
- **签到时间窗**: 绿色 (#52c41a)
- **取消时间窗**: 橙色 (#fa8c16)
- **释放时间窗**: 紫色 (#722ed1)

### 开放/截止颜色

- **开放时间**: 绿色背景 (#f6ffed)，绿色边框 (#b7eb8f)
- **截止时间**: 橙色背景 (#fff7e6)，橙色边框 (#ffd591)
- **不限制**: 灰色文字，∞ 符号

## 响应式设计

时间轴组件完全支持响应式设计：

- **移动端** (< 768px): 使用紧凑模式，字体和间距减小
- **平板** (768px - 1024px): 适度调整布局
- **桌面** (> 1024px): 完整显示所有信息

## 示例场景

### 场景1: 门诊预约规则

```
预约时间窗:
- 开放: 班次开始时间提前7天
- 截止: 班次开始时间前1小时

时间轴显示:
[绿色] 提前7天 (12-25 08:00)
[蓝色] 班次开始时间
[橙色] 提前1小时 (01-01 07:00)
```

### 场景2: 签到规则

```
签到时间窗:
- 开放: 预约创建时间延后0秒（立即）
- 截止: 班次开始时间延后30分钟

时间轴显示:
[绿色] 预约时立即
[蓝色] 班次开始时间
[橙色] 延后30分钟 (08:30)
```

## 最佳实践

1. **总是提供 shiftStart 参数**: 这样可以计算并显示实际时间点，提高可读性
2. **使用友好的描述**: 组件会自动生成人类可读的时间描述
3. **合理使用紧凑模式**: 在空间有限时使用 `compact={true}`
4. **颜色编码**: 利用颜色区分不同类型的操作和时间点
5. **实时更新**: 在表单中集成时，确保数据变化时实时更新时间轴

## 故障排除

### 时间轴不显示

- 检查是否传递了 `windows` 数组
- 确保至少有一个时间窗的 `enabled` 属性为 `true`

### 时间显示不正确

- 检查 `shiftStart` 和 `shiftEnd` 是否为有效的 Date 对象
- 验证 `openOffsetSec` 和 `closeOffsetSec` 的单位是秒

### 样式问题

- 确保导入了组件的样式文件
- 检查父容器是否有足够的宽度和高度

## 未来改进

- [ ] 支持自定义时间范围（如显示跨多天的时间窗）
- [ ] 添加时间轴缩放功能
- [ ] 支持时间窗冲突检测和警告
- [ ] 添加时间轴导出功能（PNG/SVG）
- [ ] 支持多语言时间描述
