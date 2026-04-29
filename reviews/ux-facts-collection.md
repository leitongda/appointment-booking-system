# 用户体验（UX）事实收集报告

**调研日期**: 2026-04-28
**项目**: appointment-booking-system
**调研范围**: admin、doctor、patient-h5、patient-miniapp 前端应用

---

## 1. 页面清单与结构

### Admin 端（机构管理后台）
- **总文件数**: 274 个 TS/TSX 文件
- **页面文件数**: 224 个
- **组件文件数**: 35 个
- **路由配置**: 458 行，包含 114 个路由条目
- **路由层级**: 4 级嵌套（一级菜单 > 二级菜单 > 三级页面 > 四级操作）
- **主要菜单分组**:
  - 仪表盘
  - 平台管理（租户、订阅计划、小程序平台）
  - 医疗服务（医生、排班、预约、患者、病历、诊费）
  - 组织架构（门店、科室、医疗配置、员工）
  - 运营中心（内容、消息、反馈、统计）
  - 系统管理（角色、配置、监控）
- **源文件位置**: `/apps/admin/config/routes.ts:1-458`

### Doctor 端（医生工作台）
- **总文件数**: 84 个 TS/TSX 文件
- **页面文件数**: 12 个
- **主要页面**: 
  - 登录、工作台、我的排班、停诊调班
  - 预约管理（今日预约、历史预约）
  - 就诊管理、病历管理（列表、填写）
  - 数据统计、预约规则、消息中心
- **源文件位置**: `/apps/doctor/.umirc.ts:53-73`

### Patient-H5 端（患者 H5）
- **总文件数**: 102 个 TS/TSX 文件
- **页面文件数**: 23 个
- **路由配置**: 20 个路由
- **主要页面**:
  - 首页、科室、医生、预约、候补、病历
  - 个人中心、患者信息、消息、反馈
  - 登录、注册、搜索、设置
- **源文件位置**: `/apps/patient-h5/.umirc.ts:37-67`

### Patient-Miniapp 端（患者小程序）
- **总文件数**: 80 个 TS/TSX 文件
- **组件框架**: Taro 3 + NutUI
- **组件类型**: View、Text、Image、Button、Checkbox、Radio 等

---

## 2. 交互模式统计

### Alert/Confirm 调用
- **Admin 端**:
  - `alert()` 原生调用: 0 次
  - `Modal.confirm()` 调用: 16 次
  - `modal.confirm()` 调用: 5 次
  - `message.success/error/warning/info` 调用: 355 次
  - 主要位置: app.tsx、utils/request.ts、各页面组件

- **Doctor 端**:
  - `Modal.confirm()` 调用: 33 次
  - `alert()` 原生调用: 0 次

- **Patient-H5 端**:
  - `Dialog.confirm()` 调用: 3 次
  - `Toast.show()` 调用: 78 次
  - `alert()` 原生调用: 0 次

- **Patient-Miniapp 端**:
  - Taro Dialog 组件调用

### Loading 状态处理
- **Admin 端**:
  - `loading` 状态变量: 83 个
  - Spin 组件使用: 31 次
  - Skeleton 组件使用: 少量
- **Doctor/Patient-H5 端**:
  - 使用 Ant Design Mobile 的 `Skeleton` 和 `SpinLoading` 组件

### 空状态处理
- **Admin 端**:
  - `Empty` 组件导入: 12 次
  - ProTable 内置空状态: 广泛使用
- **Patient-H5 端**:
  - `Empty` 组件导入: 12 次

---

## 3. 响应式设计事实

### 媒体查询
- **Admin 端**:
  - `@media` 查询: 3 次
  - 主要用于特定组件的响应式调整
- **Patient-H5 端**:
  - `@media` 查询: 33 次
  - 包含 `prefers-reduced-motion` 支持

### 固定宽度值
- **硬编码颜色值**: 587 处（`#` 开头的颜色值）
- **CSS 变量使用**: 12 处（`var(--` 语法）
- **样式文件**: Admin 端 7 个 CSS/Less 文件

### Viewport 配置
- **Admin 端 HTML 模板** (`/apps/admin/dist/index.html:5`):
  ```html
  <meta name="viewport" content="width=device-width, user-scalable=no, initial-scale=1.0, maximum-scale=1.0, minimum-scale=1.0">
  ```
- **布局模式**: Admin 使用混合布局（mix 模式，固定侧边栏）

---

## 4. 无障碍事实

### ARIA 属性
- **Admin 端**:
  - `aria-*` 属性: 6 处
  - `role` 属性: 3 处
  - `tabIndex`: 0 处
- **Patient-H5 端**:
  - `aria-*` 属性: 0 处
- **整体评估**: 无障碍属性使用较少

### 表单 Label 关联
- **Admin 端**:
  - `<label>` 标签: 4 处
  - 主要依赖 Ant Design Form 组件的自动 label 关联
- **Doctor/Patient-H5 端**:
  - 同样依赖组件库自动处理

### 图片 Alt 属性
- **Admin 端**:
  - `alt=` 属性: 4 处
  - 大量图片未设置 alt 属性

### 减少动画支持
- **Patient-H5 端**:
  - `prefers-reduced-motion` 支持: 4 处
  - 位置: `/apps/patient-h5/src/global.css`
  ```css
  @media (prefers-reduced-motion: reduce) {
    *, ::before, ::after {
      /* 禁用动画 */
    }
  }
  ```

---

## 5. 组件一致性事实

### UI 组件库使用
- **Admin 端**:
  - Ant Design 5 基础组件: 714 处导入
  - ProComponents (ProTable/ProForm): 64 处
  - 主要组件: Table、Form、Modal、Drawer、Button、Input、Select

- **Doctor 端**:
  - Ant Design 5 + ProComponents
  - 与 Admin 端保持一致

- **Patient-H5 端**:
  - Ant Design Mobile: 78 处导入
  - 主要组件: NavBar、Toast、Dialog、Empty、Skeleton、PullToRefresh

- **Patient-Miniapp 端**:
  - Taro 原生组件 + NutUI
  - 主要组件: View、Text、Image、Button

### 自定义组件
- **Admin 端组件库** (`/apps/admin/src/components/`):
  - AuthButton、ConfirmModal、FormPage、HeaderActions
  - ImageUpload、ListOperations、MapLocationPicker
  - RuleSetVisualization（规则集可视化组件套件）
  - TenantSwitcher、TenantStatusBanner

### 样式管理
- **Admin 端**:
  - 内联样式: 656 处 (`style=`)
  - CSS 类名: 18 处 (`className=`)
  - Tailwind CSS: 未使用

- **Patient-H5 端**:
  - Tailwind CSS: 已集成
  - 全局样式: global.css、theme.css
  - Google Fonts: Inter、Calistoga、JetBrains Mono

---

## 6. 输入方式事实

### 表单输入组件
- **Admin 端**:
  - 表单组件导入: 42 处
  - Input、Select、DatePicker、Radio、Checkbox 等
  - `autoComplete` 属性: 15 处

### 快捷键支持
- **Admin 端**:
  - `onKeyDown/onKeyUp/onKeyPress`: 0 处
  - 无快捷键绑定

### 自动补全
- **Admin 端**:
  - `autoComplete` 属性使用: 15 处
  - 主要用于表单输入的浏览器自动补全控制

---

## 7. 组件复用情况

### 通用组件统计
- **Admin 端**: 35 个自定义组件
- **组件库依赖**: 高度依赖 Ant Design 生态系统
- **组件使用 vs 原生元素**: 组件库组件占主导（714 处导入）

### 样式复用
- **CSS 变量 vs 硬编码**:
  - 硬编码颜色: 587 处
  - CSS 变量: 12 处
  - 比例: 约 98% 硬编码 vs 2% 变量

---

## 8. 移动端优化

### Patient-H5 端
- **触摸优化**: viewport 禁止用户缩放
- **下拉刷新**: PullToRefresh 组件使用
- **无限滚动**: InfiniteScroll 组件使用
- **手势支持**: SwipeAction 组件（消息列表滑动操作）

### Patient-Miniapp 端
- **原生性能**: Taro 框架编译为原生小程序
- **组件**: 使用 NutUI 移动端组件库

---

## 9. 性能优化事实

### 代码分割
- **Admin 端**:
  - 使用 `depPerChunk` 策略
  - 分组: antd-lib、pro-components-lib、charts-lib、react-lib、utils-lib、vendors
  - 最小分包大小: 50KB
  - Gzip 压缩: 生产环境启用

### 懒加载
- **Admin 端**:
  - 所有路由组件使用 `React.lazy()` 懒加载
  - 图表库使用异步加载（`chunks: 'async'`）

---

## 10. 国际化
- **Admin 端**: layout 配置 `locale: false`
- **Doctor 端**: layout 配置 `locale: false`
- **Patient-H5 端**: 无国际化配置
- **结论**: 当前不支持多语言

---

## 11. 主题系统
- **Admin 端**:
  - 主题色: `#722ED1` (紫色)
  - 主题模式: `navTheme: 'light'`
  - 布局: `layout: 'mix'` (混合模式)

- **Patient-H5 端**:
  - 支持主题切换
  - Tailwind CSS 集成
  - 自定义主题变量

- **Patient-Miniapp 端**:
  - 支持主题切换
  - Taro 主题系统

---

## 12. 错误处理
- **Admin 端**:
  - 统一错误处理: `/apps/admin/src/utils/errorHandler.ts`
  - 使用 Ant Design 的 App 组件全局提示
  - 请求拦截: `/apps/admin/src/utils/request.ts`

- **Patient-H5 端**:
  - Toast 和 Dialog 提示
  - 请求拦截器统一处理

---

## 数据来源汇总

| 项目 | 文件数 | 页面数 | 组件数 | 路由数 |
|------|--------|--------|--------|--------|
| Admin | 274 | 224 | 35 | 114 |
| Doctor | 84 | 12 | - | 12 |
| Patient-H5 | 102 | 23 | - | 20 |
| Patient-Miniapp | 80 | - | - | - |

**总计**: 540 个前端文件，259 个页面，35 个自定义组件，146 个路由
