# Admin 仪表盘优化计划

## Context

当前 admin 仪表盘存在以下问题：
1. **布局纯纵向排列** -- 5 个 ProCard 依次堆叠，大屏幕浪费水平空间
2. **趋势图用纯 CSS 实现** -- 没有用已安装的 `@ant-design/charts` (v2.6.6)
3. **3 个门店统计卡片有语法错误** -- AppointmentStatsCard、UserStatsCard、VisitorStatsCard 无法编译，未接入
4. **状态分布用文字 Statistic 展示** -- 没有可视化图表
5. **缺少数据维度** -- 收入趋势、时段分布、星期分布等 API 已有但未使用

## 新布局结构

```
Row 1: [核心指标] -- 6 个统计卡片 (xs=24 sm=12 lg=4)
Row 2: [预约与收入趋势 (span=16)] | [预约状态分布 饼图 (span=8)]
Row 3: [时段分布 柱状图 (span=12)] | [星期分布 柱状图 (span=12)]
Row 4: [门店专属区域] -- 条件渲染，3 个统计卡片 + 签到二维码
Row 5: [排行榜] -- 科室 TOP10 + 医生 TOP10 并排
```

## 图表方案

| 数据 | 当前 | 优化后 | 组件 |
|---|---|---|---|
| 预约趋势 (14天) | CSS 柱状图 | 面积折线图 | `Line` |
| 收入趋势 (14天) | 未展示 | 折线图 (Tab 切换) | `Line` |
| 状态分布 | 9 个 Statistic 文字 | 环形图 | `Pie` |
| 时段分布 | 未展示 | 柱状图 | `Column` |
| 星期分布 | 未展示 | 柱状图 | `Column` |

图表使用 `React.lazy` 懒加载，复用 `schedule/statistics.tsx` 的模式。

## 新增 API 调用

在现有 5 个调用基础上新增 3 个（全部并行 `Promise.allSettled`）：
- `statisticsApi.getRevenueTrend(14)` -- 收入趋势
- `statisticsApi.getTimeSlotDistribution()` -- 时段分布
- `statisticsApi.getWeekdayDistribution()` -- 星期分布

StoreSection 新增：
- `statisticsApi.getStoreDashboardStats(storeId)` -- 门店统计

## 文件变更清单

### 1. `apps/admin/src/pages/dashboard/index.tsx` -- 主仪表盘（重写）

- 懒加载 `Line`, `Column`, `Pie` from `@ant-design/charts`
- 新增 state: `revenueTrendData`, `timeSlotData`, `weekdayData`
- 扩展 `Promise.allSettled` 为 8 个调用
- CSS 柱状图 -> `Line` 面积折线图
- 状态 Statistic 网格 -> `Pie` 环形图
- 新增时段/星期分布 `Column` 柱状图
- 趋势区域用 `Tabs` 切换预约/收入
- 布局改为 Row/Col 双列结构

### 2. `apps/admin/src/pages/dashboard/components/StoreSection/index.tsx` -- 门店区域（重写）

- 新增 `storeStats` state + `useEffect` 调用 `getStoreDashboardStats`
- 导入并渲染修复后的 3 个统计卡片
- 布局: 3 个统计卡片 (span=18, 各 span=6) + 签到二维码 (span=6)

### 3. `apps/admin/src/pages/dashboard/components/StoreSection/AppointmentStatsCard.tsx` -- 修复语法错误

- 修复 import 语法 (`StatisticCard` 来自 `@ant-design/pro-components`)
- 修复组件声明 (`= () =>`)
- 修复 icon style 缺少闭合括号

### 4. `apps/admin/src/pages/dashboard/components/StoreSection/UserStatsCard.tsx` -- 修复语法错误

- 同上 import/声明修复
- 修复模板字符串语法
- 修复周环比颜色逻辑（正数绿色，负数红色）

### 5. `apps/admin/src/pages/dashboard/components/StoreSection/VisitorStatsCard.tsx` -- 完全重写

- 文件严重损坏，从头重写
- 展示今日/昨日 PV/UV + PV/UV 周环比

## 实施顺序

1. 修复 3 个 Store 统计卡片（独立文件，无依赖）
2. 重写 StoreSection/index.tsx（接入 API + 渲染卡片）
3. 重写主 dashboard/index.tsx（图表 + 新布局 + 新 API）

## 验证方式

1. `pnpm build:admin` 确认编译通过
2. `pnpm dev:admin` 启动后访问仪表盘页面，确认：
   - 6 个核心指标卡片正常显示
   - 趋势折线图有数据渲染（Tab 切换预约/收入）
   - 状态分布环形图有数据
   - 时段/星期柱状图有数据
   - 门店区域 3 个统计卡片 + 二维码正常（需有门店上下文）
   - 排行榜表格正常
3. 缩小浏览器窗口验证响应式布局（小屏单列，大屏双列）
