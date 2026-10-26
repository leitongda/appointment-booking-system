# Implementation Tasks: add-admin-tauri-desktop-shell

## 阶段 1：Tauri 壳工程

- [x] 1.1 新建 `apps/admin/src-tauri/`（Cargo.toml：tauri 2 + store/single-instance/log 插件；build.rs；main.rs；lib.rs）
- [x] 1.2 `tauri.conf.json`：identifier `online.aicm.hospital.admin`、productName `HospitalAdmin`、withGlobalTauri、devUrl 127.0.0.1:9105、frontendDist `../dist`、窗口 1440×900
- [x] 1.3 `capabilities/default.json` 仅授 `core:default`（不授 store 插件 IPC 权限）
- [x] 1.4 `lib.rs` 实现 `get_desktop_config`：读 `desktop.baseUrl`（顶层扁平键优先、容错嵌套对象），返回 `{ baseUrl, storeLoaded }`；注册三插件（single-instance 防多开聚焦、log 落 LogDir+stdout）
- [x] 1.5 由仓库内 logo 生成 `src-tauri/icons/`（`tauri icon`）

## 阶段 2：前端接入（packages/api）

- [x] 2.1 新建 `packages/api/src/desktop.ts`：`isTauriDesktop` / `isTauriPackaged` / `applyDesktopBaseUrl`（单飞 Promise；web 端立即返回 null）
- [x] 2.2 `index.ts` 导出 desktop 模块
- [x] 2.3 baseURL 覆盖时序：`initApp` fire-and-forget 预取 + `app.tsx getInitialState` await 把关（首业务请求前定稿）
- [x] 2.4 配置缺失告警：console.warn（区分「文件未建」与「键不对」，storeLoaded 驱动）+ 打包态启动弹窗指引（app.tsx）

## 阶段 3：路由与导航适配（apps/admin）

- [x] 3.1 `config/config.ts`：`TAURI_DESKTOP=1 → history hash` 环境分支（web 不注入，模式不变）
- [x] 3.2 新建 `src/utils/hardNavigate.ts`：`hardNavigate`（桌面壳写 `/#<path>` 保留整页刷新语义）+ `currentRoutePath`（hash 感知取当前路由路径）
- [x] 3.3 七处整页跳转切换 hardNavigate：login 落地、request.ts 401/403、app.tsx 租户暂停订阅、crossTab 登出、visibilityAuth 过期、tenant-suspended 退出
- [x] 3.4 pathname 直用点归一化：app.tsx 初始路由性能记录、sessionRecorder `getPagePath`
- [x] 3.5 `rememberReturnPath` 显式传 umi 路由 location（crossTab / visibilityAuth，避免 hash 态默认值取到 '/'）

## 阶段 4：构建脚本与依赖

- [x] 4.1 `apps/admin/package.json`：`desktop:dev`（TAURI_DESKTOP=1 tauri dev）/ `desktop:build`（TAURI_DESKTOP=1 tauri build）+ `@tauri-apps/cli` devDep
- [x] 4.2 按仓库约定执行 `CI=true pnpm install --no-frozen-lockfile`

## 阶段 5：验证

- [x] 5.1 `pnpm --filter @hospital/api run test`（15 用例通过）
- [x] 5.2 `pnpm --filter @hospital/admin run build`（web 产物回归通过）
- [x] 5.3 `cargo check --manifest-path apps/admin/src-tauri/Cargo.toml`（通过）
- [ ] 5.4 人工 GUI 冒烟：`cd apps/admin && pnpm desktop:dev` 目验窗口/登录/列表/上传/401 跳转回登录（需真机，用户执行）

## 阶段 6：发布与第二端

- [x] 6.1 CI：`.github/workflows/desktop-release.yml`（tauri-action；admin+doctor × macOS arm64/x64 + Windows x64；推 `desktop-v*` tag 挂 Release 草稿，手动触发走 artifact；签名/公证 secrets 可选）
- [ ] 6.2 updater 自动更新（签名密钥对 + 更新源；需先在 Cargo/conf 启用 tauri-plugin-updater）
- [x] 6.3 doctor 端复制壳：`apps/doctor/src-tauri/`（identifier `online.aicm.hospital.doctor`，devUrl 9103）、`.umirc.ts` hash 分支、`app.tsx`（baseURL 把关 + initMonitoring 延迟 + SW 禁用）、`utils/hardNavigate.ts` + 2 处整页跳转、`package.json` 脚本/devDep；门禁 cargo check + umi build 通过；release 包 .app 12.3 MiB / DMG 4.5 MiB
- [x] 6.4 上报组件打包态修复（admin+doctor）：tracker/perf/sessionRecorder 裸 fetch 固化相对 URL 绕过 setBaseURL——改为等桌面 baseURL 覆盖后用 getBaseURL() 绝对地址初始化；实测资产协议回退清零
- [x] 6.5 顺手修 doctor 既有缺陷：`/logo.svg` 引用但 public/ 无文件（web 端 404 静默，Tauri 日志暴露），从 admin 复制
- [ ] 6.6 共享包 tracker page_path 的 hash 感知统一（可选）
- [x] 6.7 人工 GUI 冒烟（admin）：登录 → 仪表盘（真实数据）→ 医生列表（5/5 姓名）全通过；过程中修复 CORS 白名单（服务端）
- [x] 6.8 GUI 冒烟（doctor，真机 .app）：登录 → 工作台（姓名/职称、全部菜单、三组卡片）通过；登录态跨重启持久化；过程中修复桌面端 WebSocket 基址（原按页面 origin 推断得到 ws://localhost，现随机构 baseURL 派生），右上角「实时」绿标 + 服务端握手日志确认
- [x] 6.9 修复 doctor 登录既有缺陷（web 与桌面均受影响）：服务端 `/doctors/login` snake_case → camelCase 对齐；登录页 refresh() 早退 → 改整页跳转
- [x] 6.10 Windows 脚本兼容：desktop:dev/build 改 cross-env；CI pnpm 由 packageManager 决定（lockfile v9）
- [~] 6.11 CI 实跑：推 tag `desktop-v0.1.0-rc1`，workflow 已通过解析并创建作业；但作业无法启动——GitHub 账户 Actions 计费/支出限额问题（账户级，需在 Billing & plans 处理后重推 tag）

## 已知待办（桌面端特有，不阻塞）

- 后端返回的上传文件为相对路径 `/uploads/...`，打包态 `<img src>` 打向资产协议，头像/上传图片不显示；需在前端加统一 `resolveMediaUrl`（桌面壳下拼后端 origin）或后端返回绝对 URL
- 本地开发库 schema 漂移：`appointments.assistant_confirm_status` 列缺失（alembic 已在 head），`/statistics/overview` 与 `/statistics/revenue/trend` 500——与桌面壳无关，web 同样复现
- 拉取本批改动后，各端 umi dev 需清一次 MFSU 缓存（`rm -rf node_modules/.cache src/.umi`），否则报 `isTauriDesktop is not a function`
