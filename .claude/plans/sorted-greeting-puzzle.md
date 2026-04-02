# Admin-v2 多主题切换系统 (inspired by tweakcn)

## Context

admin-v2 已完成初始搭建，当前仅支持 light/dark 模式切换 (ThemeToggle + next-themes)。用户希望参考 tweakcn.com，支持多种预设主题 (颜色方案) 切换，不只是暗色/亮色。

**核心思路**: 将 "颜色主题" (color theme) 与 "明暗模式" (light/dark) 解耦。明暗模式继续用 next-themes；颜色主题通过 JS 动态注入 CSS 变量实现。

## 架构设计

### 两层主题模型

| 层 | 控制什么 | 持久化 | 实现 |
|---|---|---|---|
| 明暗模式 | light / dark / system | next-themes (localStorage) | 已有，不变 |
| 颜色主题 | primary/accent/border 等色值 | localStorage `admin-v2-theme` | 新增 |

选择颜色主题时，同时提供该主题的 light 和 dark CSS 变量集。切换明暗模式时，自动使用当前主题对应的暗/亮色值。

### 文件结构

```
src/
  themes/
    registry.ts          # 主题注册表: ThemePreset[] + lookup
    presets/
      index.ts           # 汇总导出所有预设
      default.ts         # 默认 (zinc/neutral)
      blue.ts
      green.ts
      rose.ts
      orange.ts
      violet.ts
      catppuccin.ts
      vercel.ts
      nature.ts
      tangerine.ts
    theme-context.tsx     # ThemeProvider + useThemePreset hook
    apply-theme.ts        # applyTheme() 将 CSS 变量写入 :root
  components/
    ThemeToggle.tsx       # 改造: 明暗 + 颜色主题选择器
    ThemeSwitcher.tsx     # 新增: 颜色主题弹出面板 (色块网格)
```

### 主题数据结构

```typescript
interface ThemePreset {
  name: string;           // 唯一标识: "default", "blue", "catppuccin"
  label: string;          // 显示名: "默认", "蓝色", "Catppuccin"
  cssVars: {
    light: Record<string, string>;  // oklch 值
    dark: Record<string, string>;
  };
}
```

### 运行时主题应用 (apply-theme.ts)

```typescript
function applyTheme(preset: ThemePreset, mode: 'light' | 'dark') {
  const root = document.documentElement;
  const vars = preset.cssVars[mode];
  Object.entries(vars).forEach(([key, value]) => {
    root.style.setProperty(`--${key}`, value);
  });
}
```

切换主题/明暗模式时调用 applyTheme，将对应 CSS 变量写入 :root 行内样式。

### ThemeContext (theme-context.tsx)

- `ThemeProvider` 包裹在 next-themes `ThemeProvider` 内部
- 读取 localStorage `admin-v2-theme` (默认 "default")
- 提供 `themeName`, `setTheme(name)` 给子组件
- 监听 next-themes 的 `resolvedTheme` 变化，自动调用 `applyTheme()`

### ThemeSwitcher 组件

- 点击 Header 的调色板图标弹出 Popover
- 显示主题色块网格 (圆形色块 + 名称)
- 当前选中的主题有勾选标记
- 选择后立即应用并持久化

### ThemeToggle 改造

保留 Sun/Moon 明暗切换按钮不变，在其旁边新增调色板按钮 (打开 ThemeSwitcher)。

## 预设主题 (10 个)

| name | label | 主色调 |
|---|---|---|
| default | 默认 | 中性灰 (当前 zinc) |
| blue | 蓝色 | oklch 蓝色调 |
| green | 绿色 | oklch 绿色调 |
| rose | 玫瑰 | oklch 粉红调 |
| orange | 橙色 | oklch 暖橙调 |
| violet | 紫罗兰 | oklch 紫色调 |
| catppuccin | Catppuccin | 紫粉柔和 |
| vercel | Vercel | 极简黑白 |
| nature | 自然 | oklch 森林绿 |
| tangerine | 蜜柑 | oklch 暖橙色 |

每个预设包含完整的 light + dark CSS 变量集 (background, foreground, primary, secondary, muted, accent, destructive, border, input, ring, card, popover, sidebar 系列, chart 系列, radius)。

## 实施步骤

### Step 1: 主题注册表和预设数据
- 新建 `src/themes/` 目录
- 创建 `src/themes/presets/` 下 10 个预设文件
- 创建 `src/themes/registry.ts` (主题注册表 + lookup 函数)

### Step 2: 主题应用逻辑
- 新建 `src/themes/apply-theme.ts` - applyTheme() 函数

### Step 3: ThemeContext
- 新建 `src/themes/theme-context.tsx` - ThemePresetProvider + useThemePreset
- 在 App.tsx 中包裹 ThemePresetProvider

### Step 4: ThemeSwitcher 组件
- 新建 `src/components/ThemeSwitcher.tsx` - 颜色主题选择面板
- 改造 `src/components/ThemeToggle.tsx` - 加入调色板按钮

### Step 5: Header 集成
- 更新 `AppHeader.tsx` - 放置调色板按钮

### Step 6: globals.css 调整
- 移除 `:root` 和 `.dark` 中的硬编码 CSS 变量 (改由 JS 注入)
- 保留 `@theme inline` 和 `@layer base` 不变
- 添加 fallback: 在 `:root` 保留 default 主题的值作为初始加载闪烁防护

## 关键文件

| 文件 | 操作 |
|---|---|
| `src/themes/presets/*.ts` | 新建 |
| `src/themes/registry.ts` | 新建 |
| `src/themes/apply-theme.ts` | 新建 |
| `src/themes/theme-context.tsx` | 新建 |
| `src/components/ThemeSwitcher.tsx` | 新建 |
| `src/components/ThemeToggle.tsx` | 修改 |
| `src/layout/AppHeader.tsx` | 修改 |
| `src/App.tsx` | 修改 (添加 ThemePresetProvider) |
| `src/globals.css` | 修改 (保留 fallback 变量) |

## 验证

1. `pnpm dev:admin-v2` 启动
2. 登录后点击 Header 调色板图标
3. 切换 10 种预设主题，验证颜色即时生效
4. 切换明暗模式，验证暗色主题也正确应用
5. 刷新页面，验证主题选择持久化
6. 验证 sidebar、card、button 等组件颜色正确跟随
