# 响应式迁移指南

## 概述

admin 端已通过 antd Grid（Row/Col）实现基础响应式（1560 处使用）。
本次补充了响应式工具 Hook 和 CSS 工具类，用于处理 antd Grid 无法覆盖的场景。

## 工具清单

### Hook 工具（`@/utils/useResponsive`）

```tsx
import { useResponsive, useResponsiveCols, useResponsiveValue } from '@/utils/useResponsive';

// 断点检测
const { isMobile, isTablet, isDesktop, breakpoint, width } = useResponsive();

// 响应式列数
const cols = useResponsiveCols({ xs: 1, sm: 2, md: 3, lg: 4 });

// 响应式值
const padding = useResponsiveValue({ xs: 8, md: 16, lg: 24 });
const showSidebar = useResponsiveValue({ xs: false, lg: true });
```

### 组件工具（`@/components/Responsive`）

```tsx
import { ResponsiveContainer, ResponsiveGrid, ResponsiveStats, ShowOn, HideOn } from '@/components/Responsive';

// 响应式容器（移动端限宽居中）
<ResponsiveContainer maxWidth={1200}>
  <Content />
</ResponsiveContainer>

// 响应式网格（自动调整列数）
<ResponsiveGrid cols={{ xs: 1, sm: 2, md: 3, lg: 4 }}>
  <Card>1</Card>
  <Card>2</Card>
</ResponsiveGrid>

// 响应式统计卡片（手机2列→桌面5列）
<ResponsiveStats>
  <StatisticCard />
  <StatisticCard />
</ResponsiveStats>

// 条件显示
<ShowOn breakpoints={['lg', 'xl', 'xxl']}>
  <DesktopSidebar />
</ShowOn>
<HideOn breakpoints={['xs', 'sm']}>
  <DesktopOnlyContent />
</HideOn>
```

### CSS 工具类（`@/styles/responsive.less`）

```less
@import '@/styles/responsive.less';

// 显示/隐藏
<div className="responsive-hide-mobile">桌面端显示</div>
<div className="responsive-hide-desktop">移动端显示</div>

// 布局
<div className="responsive-padding">响应式内边距</div>
<div className="responsive-grid">响应式网格</div>
<div className="stats-grid">统计卡片网格</div>
<div className="responsive-table-container">表格水平滚动容器</div>
<div className="responsive-toolbar">工具栏（移动端垂直排列）</div>
```

## 断点定义

| 断点 | 宽度 | 场景 |
|------|------|------|
| xs | <576px | 手机 |
| sm | ≥576px | 大手机/小平板 |
| md | ≥768px | 平板 |
| lg | ≥992px | 小桌面 |
| xl | ≥1200px | 桌面 |
| xxl | ≥1600px | 大桌面 |

## 迁移优先级

### P0：ProTable 水平滚动（防止移动端溢出）

```tsx
// ❌ 错误：表格在移动端溢出
<ProTable columns={columns} />

// ✅ 正确：添加 scroll 配置
<ProTable
  columns={columns}
  scroll={{ x: 1200 }}  // 根据列总宽度设置
/>
```

**需修改的页面**：所有使用 ProTable 的列表页（约 30+ 个）

### P1：统计卡片响应式

```tsx
// ❌ 错误：固定 6 列，移动端挤压
<Row gutter={[16, 16]}>
  <Col span={4}><StatisticCard /></Col>
  ...
</Row>

// ✅ 正确：使用响应式断点
<Row gutter={[16, 16]}>
  <Col xs={12} sm={8} lg={4}><StatisticCard /></Col>
  ...
</Row>

// 或使用 ResponsiveStats 组件
<ResponsiveStats>
  <StatisticCard />
  ...
</ResponsiveStats>
```

### P2：表单响应式

```tsx
// ✅ 使用 responsive-form 类
<div className="responsive-form">
  <Form layout="vertical">
    <Form.Item label="名称"><Input /></Form.Item>
  </Form>
</div>
```

### P3：工具栏响应式

```tsx
// ✅ 使用 responsive-toolbar 类
<div className="responsive-toolbar">
  <Button>操作1</Button>
  <Button>操作2</Button>
</div>
```

## 当前状态

- ✅ 响应式工具建立（Hook + 组件 + CSS）
- ✅ dashboard 页面已使用 antd Grid 响应式
- ✅ 1560 处使用 antd Grid（Row/Col）
- ⏳ ProTable scroll 配置待补（约 30+ 页面）
- ⏳ 移动端表单布局待优化
- ⏳ 移动端工具栏待优化

## 注意事项

1. **antd Grid vs CSS 媒体查询**：优先使用 antd Grid 的 `xs/sm/md/lg/xl` 属性，它通过 JavaScript 实现响应式，比 CSS 媒体查询更灵活
2. **ProTable scroll**：所有列表页必须配置 `scroll={{ x: ... }}`，防止移动端表格溢出
3. **min-width: 0**：在 flex/grid 子元素上添加 `min-width: 0`，防止内容撑破容器
4. **测试**：修改后用浏览器 DevTools 测试 375px（手机）、768px（平板）、1200px（桌面）三个宽度
