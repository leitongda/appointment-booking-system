# 重构 app.tsx：主题文件归位 + 代码拆分

## Context

`apps/admin/src/app.tsx` 有 680 行，包含了主题配置、动态菜单逻辑、跨 Tab 同步、应用初始化、请求拦截器等大量非 Umi 运行时配置的代码。两个主题文件（`illustrationTheme.ts`、`shadcnTheme.ts`）散落在 `src/` 根目录，没有放在专门的文件夹中。需要将主题文件归位，并将可拆分的代码提取到对应的模块中。

## 文件变更总览

```
apps/admin/src/
  themes/                              <-- 新建文件夹
    index.ts                           <-- barrel export
    illustrationTheme.ts               <-- 从 src/ 根目录移入
    shadcnTheme.ts                     <-- 从 src/ 根目录移入
    themeConfig.ts                     <-- 新建：提取 getThemeConfig()
  utils/
    menu.ts                            <-- 新建：提取动态菜单逻辑 (~150行)
    crossTab.ts                        <-- 新建：提取跨Tab事件处理 (~80行)
    initApp.ts                         <-- 新建：提取应用初始化 (~30行)
    requestInterceptors.ts             <-- 新建：提取请求拦截器 (~65行)
  components/
    PageTransitionWrapper.tsx           <-- 新建：提取过渡动画组件 (~15行)
  constants/
    paths.ts                           <-- 新建：loginPath 常量（多处共用）
```

删除：`src/illustrationTheme.ts`、`src/shadcnTheme.ts`（已移入 `themes/`）

## 详细计划

### 1. 创建 `src/constants/paths.ts`

提取 `loginPath` 常量（被 crossTab、requestInterceptors、app.tsx 三处共用）。

```ts
export const LOGIN_PATH = '/login';
```

### 2. 创建 `src/themes/` 文件夹，移入主题文件

- `themes/illustrationTheme.ts` — 从 `src/illustrationTheme.ts` 移入，内容不变
- `themes/shadcnTheme.ts` — 从 `src/shadcnTheme.ts` 移入，内容不变
- `themes/themeConfig.ts` — 从 app.tsx 提取 `getThemeConfig()`（第 307-329 行），导入 `@/utils/spacing` 和 `antd`
- `themes/index.ts` — barrel re-export

### 3. 创建 `src/utils/menu.ts`

从 app.tsx 提取第 29-175 行：
- `DynamicMenuConfig` 接口（内部使用，不导出）
- `dynamicMenuRules` 数组（12 条规则，内部使用）
- `processMenuData()` 函数 → 导出
- `computeParentOpenKeys()` 函数 → 导出

依赖：`MenuDataItem` 类型 from `@ant-design/pro-components`

### 4. 创建 `src/utils/crossTab.ts`

从 app.tsx 提取第 183-260 行：
- `handleCrossTabEvent()` 函数 → 导出

依赖：`@hospital/shared`（多个导出）、`antd`（Modal/notification/Button）、`@umijs/max`（history）、`@/constants/paths`（LOGIN_PATH）

### 5. 创建 `src/utils/initApp.ts`

从 app.tsx 提取第 20-23 行 + 第 262-285 行：
- `apiBaseUrl` 常量 + `setBaseURL` 调用
- `initApiConfig()` 调用
- `initTracker()` 调用及配置
- `initPerformanceMonitoring()` 调用及配置

导出 `initApp()` 函数和 `apiBaseUrl`

### 6. 创建 `src/utils/requestInterceptors.ts`

从 app.tsx 提取第 614-679 行：
- `umiRequestConfig: RequestConfig` → 导出

依赖：`@umijs/max`（RequestConfig 类型）、`@hospital/shared`（token 相关）、`antd`（Modal/message）、`@/constants/paths`（LOGIN_PATH）

### 7. 创建 `src/components/PageTransitionWrapper.tsx`

从 app.tsx 提取第 290-301 行：
- `PageTransitionWrapper` 组件

### 8. 更新 `app.tsx`

- 替换 import 路径（旧主题文件 → `@/themes`）
- 添加新模块的 import
- 删除已提取的 6 个代码块
- `request` 改为 re-export：`export { umiRequestConfig as request } from '@/utils/requestInterceptors'`
- 模块顶层调用 `initApp()`
- `loginPath` 替换为 `LOGIN_PATH` from `@/constants/paths`

预计 app.tsx 从 680 行缩减到 ~250 行，只保留 Umi 运行时必需的三个导出（`rootContainer`、`getInitialState`、`layout`）+ request re-export。

### 9. 删除旧文件

- `src/illustrationTheme.ts`
- `src/shadcnTheme.ts`

## 执行顺序

1. 创建 `constants/paths.ts`（被多个新模块依赖）
2. 创建 `themes/` 文件夹及其 4 个文件
3. 创建 `utils/menu.ts`、`utils/crossTab.ts`、`utils/initApp.ts`、`utils/requestInterceptors.ts`
4. 创建 `components/PageTransitionWrapper.tsx`
5. 重写 `app.tsx`（更新 import + 删除已提取代码）
6. 删除旧的主题文件
7. 构建验证

## 验证方式

1. `cd apps/admin && pnpm build` — 确认构建通过
2. `pnpm dev:admin` — 确认开发服务器正常启动
3. 浏览器访问验证：登录、菜单展开/收起、路由切换动画、主题渲染
