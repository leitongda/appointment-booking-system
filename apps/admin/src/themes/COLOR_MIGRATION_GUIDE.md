# 颜色 Token 迁移指南

## 概述

本项目正在从硬编码颜色值迁移到 CSS 变量 + antd token 系统。
新代码**必须使用 token**，旧代码逐步迁移。

## Token 系统

### CSS 变量（自定义组件）

定义在 `apps/admin/src/themes/color-tokens.less`，自动引入。

```less
/* ❌ 错误：硬编码 */
color: #1677ff;
background: #f5f5f5;

/* ✅ 正确：使用 CSS 变量 */
color: var(--color-primary);
background: var(--color-bg-layout);
```

### antd Token（antd 组件）

定义在 `apps/admin/src/themes/themeConfig.ts`，通过 `useToken()` hook 使用。

```tsx
import { theme } from 'antd';

const { token } = theme.useToken();

// ❌ 错误
<Button style={{ color: '#1677ff' }} />

// ✅ 正确
<Button style={{ color: token.colorPrimary }} />
```

## 常用颜色映射表

| 硬编码值 | CSS 变量 | antd Token | 用途 |
|---------|----------|------------|------|
| `#1677ff` | `var(--color-primary)` | `token.colorPrimary` | 主色 |
| `#999` | `var(--color-text-tertiary)` | `token.colorTextTertiary` | 辅助文字 |
| `#666` | `var(--color-text-secondary)` | `token.colorTextSecondary` | 次要文字 |
| `#333` | `var(--color-text)` | `token.colorText` | 主要文字 |
| `#ff4d4f` | `var(--color-error)` | `token.colorError` | 错误/危险 |
| `#52c41a` | `var(--color-success)` | `token.colorSuccess` | 成功 |
| `#faad14` | `var(--color-warning)` | `token.colorWarning` | 警告 |
| `#f5f5f5` | `var(--color-bg-layout)` | `token.colorBgLayout` | 布局背景 |
| `#f0f0f0` | `var(--color-border-secondary)` | `token.colorBorderSecondary` | 次要边框 |
| `#d9d9d9` | `var(--color-border)` | `token.colorBorder` | 边框 |
| `#fff` | `var(--color-white)` | `token.colorBgContainer` | 白色背景 |

## 业务颜色

| 硬编码值 | CSS 变量 | 用途 |
|---------|----------|------|
| `#722ed1` | `var(--color-afternoon)` | 下午班次 |
| `#fa8c16` | `var(--color-evening)` | 晚间班次 |
| `#13c2c2` | `var(--color-queue)` | 排队状态 |

## 迁移步骤

### 1. 查找硬编码颜色

```bash
# 统计文件中的硬编码颜色
grep -n "#[0-9a-fA-F]\{3,6\}" src/pages/xxx/index.tsx
```

### 2. 替换为 CSS 变量

```bash
# 批量替换常用颜色
sed -i '' \
  -e "s/color: '#999'/color: 'var(--color-text-tertiary)'/g" \
  -e "s/color: '#1677ff'/color: 'var(--color-primary)'/g" \
  -e "s/color: '#52c41a'/color: 'var(--color-success)'/g" \
  src/pages/xxx/index.tsx
```

### 3. 验证

- 确认页面颜色无变化
- 确认无语法错误
- 运行 TypeScript 检查

## 注意事项

1. **渐进迁移**：不要一次性替换所有文件，按页面逐步迁移
2. **保持一致性**：同一文件内的同类颜色应统一使用 token
3. **特殊颜色**：不在 token 系统中的颜色（如 `#eb2f96` 品红）可保留硬编码
4. **CSS 变量 vs antd token**：
   - 自定义组件（inline style）→ 使用 CSS 变量
   - antd 组件 → 使用 antd token（`useToken()`）
5. **Less 文件**：在 `.less` 文件中使用 `var(--color-xxx)` 而非 `@xxx`

## 当前迁移进度

- ✅ token 系统建立（color-tokens.less + themeConfig.ts）
- ✅ dashboard 页面（样本替换）
- ✅ doctor/list.tsx
- ✅ appointment/list.tsx
- ⏳ 其他页面（逐步迁移）

## 统计

- 总硬编码颜色：约 1164 处
- 已迁移：约 50 处（dashboard + doctor/list + appointment/list）
- 待迁移：约 1114 处
