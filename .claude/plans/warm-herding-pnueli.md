# PWA 最小安装支持 -- Chrome "在应用中打开" 功能

## Context

Chrome 浏览器的 "在应用中打开" / "安装应用" 功能要求网站满足 PWA 安装条件：HTTPS + Web App Manifest + Service Worker（带 fetch 处理器）。当前所有 Web 应用均无 PWA 基础设施（无 manifest、无 SW、无 PWA 图标）。本次仅为满足 Chrome 安装条件，不做离线缓存。

## 影响范围

5 个 Web 应用：admin、doctor、patient-h5、temp-registration、website

每个应用 4 个新文件 + 2 个修改文件 = 共 20 个新文件 + 10 个修改。

## 实施步骤

### Step 1: 生成 PWA 图标

从 `apps/admin/public/logo.svg`（蓝色渐变圆角矩形 + 医疗十字 logo）渲染出 192x192 和 512x512 PNG，复制到各应用。

- 安装临时依赖 `sharp`，运行 Node 脚本生成，完成后卸载
- 输出路径：各应用 `public/icons/icon-192.png` + `public/icons/icon-512.png`
- temp-registration 需先创建 `public/` 目录

### Step 2: 创建 manifest.json（每个应用 `public/manifest.json`）

各应用 manifest 内容不同（name/short_name/description），其余字段相同：

```json
{
  "name": "<应用全名>",
  "short_name": "<短名>",
  "description": "<描述>",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#1677ff",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

| 应用 | name | short_name | theme_color |
|------|------|------------|-------------|
| admin | 医院挂号管理系统 | 管理系统 | #1677ff |
| doctor | 医生工作台 | 医生台 | #1677ff |
| patient-h5 | 医院预约挂号 | 预约挂号 | #1677ff |
| temp-registration | 现场临时挂号 | 临时挂号 | #1677ff |
| website | 医院挂号系统 | 挂号系统 | #0052FF |

### Step 3: 创建最小 Service Worker（每个应用 `public/sw.js`）

所有应用内容相同 -- 仅透传 fetch，满足 Chrome 安装条件：

```js
self.addEventListener('fetch', (event) => {
  event.respondWith(fetch(event.request));
});
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()));
```

### Step 4: 配置文件修改 -- 添加 manifest link 和 theme-color

**Umi 4 应用** -- 在 `defineConfig({})` 中添加 `links` 和 `metas`：

- `apps/admin/config/config.ts` (第 88 行现有 `links` 数组中追加 manifest 条目)
- `apps/doctor/.umirc.ts` (在 `proxy` 后添加 `links` + `metas`)
- `apps/patient-h5/.umirc.ts` (在 `proxy` 后添加 `links` + `metas`)
- `apps/temp-registration/.umirc.ts` (在 `proxy` 后添加 `links` + `metas`)

```ts
links: [{ rel: 'manifest', href: '/manifest.json' }],
metas: [{ name: 'theme-color', content: '#1677ff' }],
```

**Vite 应用** -- 直接修改 `apps/website/index.html` `<head>` 内添加：

```html
<link rel="manifest" href="/manifest.json" />
<meta name="theme-color" content="#0052FF" />
```

### Step 5: Service Worker 注册 -- 各应用入口文件

在所有应用的入口文件顶部（import 之后，业务逻辑之前）添加：

```ts
// PWA Service Worker 注册
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {});
  });
}
```

修改文件：
- `apps/admin/src/app.tsx` -- 在 `initApp()` 之前
- `apps/doctor/src/app.tsx` -- 在 `initTracker(...)` 之前
- `apps/patient-h5/src/app.tsx` -- 在 import 之后
- `apps/temp-registration/src/app.tsx` -- 在 import 之后
- `apps/website/src/main.tsx` -- 在 `createRoot` 之前

## 文件清单

| 文件 | 操作 |
|------|------|
| `apps/*/public/icons/icon-192.png` | 创建 x5 |
| `apps/*/public/icons/icon-512.png` | 创建 x5 |
| `apps/*/public/manifest.json` | 创建 x5 |
| `apps/*/public/sw.js` | 创建 x5 |
| `apps/admin/config/config.ts` | 修改 -- links 中加 manifest |
| `apps/doctor/.umirc.ts` | 修改 -- 加 links + metas |
| `apps/patient-h5/.umirc.ts` | 修改 -- 加 links + metas |
| `apps/temp-registration/.umirc.ts` | 修改 -- 加 links + metas |
| `apps/website/index.html` | 修改 -- 加 link + meta |
| `apps/admin/src/app.tsx` | 修改 -- 加 SW 注册 |
| `apps/doctor/src/app.tsx` | 修改 -- 加 SW 注册 |
| `apps/patient-h5/src/app.tsx` | 修改 -- 加 SW 注册 |
| `apps/temp-registration/src/app.tsx` | 修改 -- 加 SW 注册 |
| `apps/website/src/main.tsx` | 修改 -- 加 SW 注册 |

## 验证

1. 启动任意应用 `pnpm dev:admin`，打开 Chrome DevTools > Application 面板
2. 检查 Manifest 子面板：应显示 manifest 内容，无错误
3. 检查 Service Workers 子面板：应显示 "activated and is running"
4. 生产环境 HTTPS 部署后，Chrome 地址栏右侧应出现安装图标，或地址栏下方出现安装横幅
5. 可选：运行 Lighthouse > PWA 审计，确认基础安装条件通过
