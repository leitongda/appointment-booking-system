# Change: 新增机构端（apps/admin）Tauri 桌面客户端壳

## Why
机构后台目前只能通过浏览器访问。部分机构的电脑为固定办公场景，需要：
- 桌面图标直达、独立窗口（不与浏览器标签页混用）、防误关；
- 内网/机构电脑环境复杂（老系统、精简浏览器），桌面客户端由系统 WebView 渲染，不依赖机构浏览器版本；
- 后端地址可按机构部署调整而无需重新打包。

选型结论（2026-10-25 定案）：**Tauri 2.x 壳 + 现有 React 构建产物直接进系统 WebView**。UI 100% 复用 `apps/admin`，Rust 仅做窗口与系统能力；Electron（150MB 包体）、Wails（无 Go 资产/生态薄）、纯 Rust GUI（antd 生态无等价物）均否决。本变更不是新业务端——`apps/admin` 代码零分叉，桌面是一种发布形态（类比 patient-miniapp 一套代码多端产物）。

## What Changes
- 新增 `apps/admin/src-tauri/`：Tauri 2 壳工程（tauri + store/single-instance/log 三个官方插件，identifier `online.aicm.hospital.admin`，window `HospitalAdmin` 1440×900，`withGlobalTauri`）。
- 新增自定义命令 `get_desktop_config`：Rust 侧经 tauri-plugin-store 读取应用数据目录 `desktop-config.json` 的 `desktop.baseUrl`（顶层扁平键，容错嵌套对象），返回 `{ baseUrl, storeLoaded }`。
- 新增 `packages/api/src/desktop.ts`：`isTauriDesktop` / `isTauriPackaged` / `applyDesktopBaseUrl`。仅 `window.__TAURI__` 存在时生效，web 端行为零变化；baseURL 覆盖采用「启动预取 + getInitialState 把关」两段式时序。
- 路由适配：Umi 配置加 `TAURI_DESKTOP=1 → hash` 环境分支；新增 `utils/hardNavigate.ts`（`hardNavigate` 整页跳转 + `currentRoutePath` hash 感知取路径），admin 内全部 `window.location.href` 整页跳转（登录落地、401/403、跨标签页登出、租户暂停）与 pathname 直用点（路由性能记录、会话录制）切换到 hash 感知实现。
- 部署体验：打包态下若未配置 `desktop.baseUrl`，控制台告警 + 启动时可见弹窗给出配置文件路径与 JSON 形状指引；`tauri dev`（http devUrl）不受影响、不弹窗。
- 权限最小化：capabilities 仅授 `core:default`，不授 `store:default`（前端从不经 IPC 访问 store 插件，配置读取全部走 Rust 侧）。
- 新增脚本 `desktop:dev` / `desktop:build`（`@tauri-apps/cli` devDep）。

## Design Principles
- **不是新端**：壳工程放 `apps/admin/src-tauri/`，业务代码零复制；web 构建不注入 `TAURI_DESKTOP`，所有桌面分支在 web 下恒为关闭。
- **配置即部署**：机构切环境 = 编辑应用数据目录一个 JSON 文件 + 重启，不重新打包、不依赖环境变量注入。
- **权限最小**：前端不持有任何 store 插件 IPC 权限，配置读取收敛在 Rust 自定义命令内。
- **web 零影响**：桌面分支全部以 `isTauriDesktop()`/`TAURI_DESKTOP` 守卫，现有 web 行为逐字节不变。

## Scope

### In Scope
- `apps/admin/src-tauri/`（Cargo.toml、build.rs、tauri.conf.json、capabilities、main.rs/lib.rs、图标）。
- `packages/api/src/desktop.ts`（new）+ `index.ts` 导出。
- `apps/admin`：`config/config.ts` 路由分支、`src/utils/hardNavigate.ts`（new）、7 处整页跳转调用点、`app.tsx`（baseURL 把关 + 打包态告警 + 初始路径归一化）、`utils/request.ts`、`utils/crossTab.tsx`、`utils/visibilityAuth.ts`、`utils/sessionRecorder.ts`、`pages/login/index.tsx`、`pages/tenant-suspended/index.tsx`、`package.json`（脚本 + devDep）。
- `apps/admin/src/utils/initApp.ts` 启动预取。

### Out of Scope
- doctor / patient-h5 / temp-registration / website / patient-miniapp 各端不动（doctor 壳复制留待 admin 验收后）。
- `apps/server` 后端零改动。
- DMG/NSIS 打包流水线、代码签名与公证、自动更新（updater 插件未启用）：下一阶段。
- 共享包 tracker 的 page_path 仍用 `window.location.pathname`（桌面 hash 态记录为 '/'，属已知限制，待后续统一）。

## Impact
- Affected specs: `admin-desktop-shell` (new)
- Affected code:
  - `apps/admin/src-tauri/**` (new)
  - `apps/admin/package.json`、`apps/admin/config/config.ts`
  - `apps/admin/src/app.tsx`、`apps/admin/src/utils/{initApp,request,crossTab,visibilityAuth,sessionRecorder,hardNavigate}.ts(x)`
  - `apps/admin/src/pages/login/index.tsx`、`apps/admin/src/pages/tenant-suspended/index.tsx`
  - `packages/api/src/desktop.ts` (new)、`packages/api/src/index.ts`

## Verification
- `pnpm --filter @hospital/api run test`（vitest）
- `pnpm --filter @hospital/admin run build`（max build，web 产物回归）
- `cargo check --manifest-path apps/admin/src-tauri/Cargo.toml`（Rust 侧编译）
- 人工 GUI 冒烟：`cd apps/admin && pnpm desktop:dev` 目验窗口/登录/列表/上传（需真机，不在 CI 内）。
