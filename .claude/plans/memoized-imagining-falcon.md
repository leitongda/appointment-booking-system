# 通知设置页样式统一：Tailwind → Ant Design

## Context

`apps/doctor/src/pages/settings/notification-settings.tsx` 使用了 Tailwind CSS 工具类（`flex`, `grid grid-cols-2`, `p-6 bg-gray-50`, `max-w-3xl mx-auto` 等），但医生端项目没有安装 Tailwind CSS（无 tailwind.config、无 postcss.config、package.json 无 tailwindcss 依赖）。这些 className 实际不生效，页面布局依赖浏览器默认样式，表现不一致。

需要将所有 Tailwind 工具类替换为 Ant Design 组件 + 行内样式，与其他页面保持一致。

## 修改文件

- `apps/doctor/src/pages/settings/notification-settings.tsx`（唯一需要改的文件）

## 替换方案

| Tailwind 类 | 替换为 |
|---|---|
| `className="flex items-center justify-center h-96"` | `<Spin>` 包裹在 `<div style={{ textAlign: 'center', paddingTop: 200 }}>` |
| `className="p-6 bg-gray-50 min-h-screen"` | `PageContainer`（与其他页面一致） |
| `className="max-w-3xl mx-auto"` | `<div style={{ maxWidth: 720, margin: '0 auto' }}>` |
| `className="mb-6"` / `className="mb-4"` | `<div style={{ marginBottom: 24 }}>` / `style={{ marginBottom: 16 }}` |
| `className="text-sm"` | `style={{ fontSize: 14 }}` |
| `className="ml-2 text-sm"` | `style={{ marginLeft: 8, fontSize: 14 }}` |
| `className="my-4"` (Divider) | `<Divider style={{ margin: '16px 0' }}>` |
| `className="grid grid-cols-2 gap-4"` | `<Row gutter={16}>` + `<Col span={12}>` |
| `className="w-full"` (TimePicker) | `style={{ width: '100%' }}` |
| `className="flex justify-end gap-3"` | `<div style={{ textAlign: 'right' }}>` + `<Space>` |

## 具体改动

1. 新增 imports：`PageContainer`, `Row`, `Col`（antd）
2. 移除 `Typography.Title`/`Typography.Text` 的独立引用，改用 antd 的 `Typography` 导出
3. loading 状态：用居中 `Spin` + 内联样式
4. 外层容器：用 `PageContainer` 包裹，去掉 `className="p-6 bg-gray-50 min-h-screen"`
5. 内容区：`<div style={{ maxWidth: 720, margin: '0 auto' }}>` 替代 `max-w-3xl mx-auto`
6. 免打扰时段的两列布局：`<Row gutter={16}><Col span={12}>...</Col><Col span={12}>...</Col></Row>`
7. 底部按钮：`<div style={{ textAlign: 'right' }}><Space>...</Space></div>`

## 验证

```bash
pnpm build:doctor
```

构建通过即可，页面无功能性改动，仅样式层替换。
