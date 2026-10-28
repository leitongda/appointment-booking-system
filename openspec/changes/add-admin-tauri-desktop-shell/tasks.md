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
- [x] 6.2 updater 自动更新（两端对称）：Cargo 加 `tauri-plugin-updater`/`tauri-plugin-process` 并在 lib.rs 注册；capabilities 加 `updater:default`/`process:default`；`tauri.conf.json` 开 `createUpdaterArtifacts`、公钥、`.invalid` 占位更新源（真实 https 域名走 secret `DESKTOP_UPDATE_BASE_URL`，CI 用 `--config` 覆盖层注入）、`version` 改指向 `../package.json`（版本唯一来源，两端 bump 到 1.1.0）、targets 砍 msi 只留 nsis（避免机构混装两种安装器）；前端 `utils/desktopUpdater.tsx`（零 npm 依赖走 `window.__TAURI__.updater/process`，启动后 5s 静默检查 → 弹窗展示版本+公告 → 下载进度 → 不自动重启），挂在 `getInitialState` 桌面 baseURL 把关之后；CI 新增 secrets fail-fast、tag==两端 package.json 版本门禁、CHANGELOG 段落提取为 Release 正文、签名 env、`includeUpdaterJson:false`；`desktop-release/`：`CHANGELOG.md`（用户向公告，唯一来源）、`extract-notes.sh`、`publish-updates.sh`（下载 Release 产物 → 按端生成 latest.json（universal 包同时登记 darwin-aarch64/x86_64）→ scp 到生产 nginx、latest.json 原子替换）、`README.md` 运维手册。门禁 cargo check 两端通过。密钥对已生成在 `~/.tauri/hospital-desktop.key(.password/.pub)`，私钥不入库。**待用户**：配置 3 个 secrets、nginx 加 `/desktop/updates/` location、自托管 Mac 装 python3（CLT 自带）、首次发版实测产物命名与 `--config` 路径解析
- [x] 6.3 doctor 端复制壳：`apps/doctor/src-tauri/`（identifier `online.aicm.hospital.doctor`，devUrl 9103）、`.umirc.ts` hash 分支、`app.tsx`（baseURL 把关 + initMonitoring 延迟 + SW 禁用）、`utils/hardNavigate.ts` + 2 处整页跳转、`package.json` 脚本/devDep；门禁 cargo check + umi build 通过；release 包 .app 12.3 MiB / DMG 4.5 MiB
- [x] 6.4 上报组件打包态修复（admin+doctor）：tracker/perf/sessionRecorder 裸 fetch 固化相对 URL 绕过 setBaseURL——改为等桌面 baseURL 覆盖后用 getBaseURL() 绝对地址初始化；实测资产协议回退清零
- [x] 6.5 顺手修 doctor 既有缺陷：`/logo.svg` 引用但 public/ 无文件（web 端 404 静默，Tauri 日志暴露），从 admin 复制
- [ ] 6.6 共享包 tracker page_path 的 hash 感知统一（可选）
- [x] 6.7 人工 GUI 冒烟（admin）：登录 → 仪表盘（真实数据）→ 医生列表（5/5 姓名）全通过；过程中修复 CORS 白名单（服务端）
- [x] 6.8 GUI 冒烟（doctor，真机 .app）：登录 → 工作台（姓名/职称、全部菜单、三组卡片）通过；登录态跨重启持久化；过程中修复桌面端 WebSocket 基址（原按页面 origin 推断得到 ws://localhost，现随机构 baseURL 派生），右上角「实时」绿标 + 服务端握手日志确认
- [x] 6.9 修复 doctor 登录既有缺陷（web 与桌面均受影响）：服务端 `/doctors/login` snake_case → camelCase 对齐；登录页 refresh() 早退 → 改整页跳转
- [x] 6.10 Windows 脚本兼容：desktop:dev/build 改 cross-env；CI pnpm 由 packageManager 决定（lockfile v9）
- [~] 6.11 CI 实跑：推 tag `desktop-v0.1.0-rc1`，workflow 已通过解析并创建作业；但作业无法启动——GitHub 账户 Actions 计费/支出限额问题（账户级，需在 Billing & plans 处理后重推 tag）

## 阶段 7：P0 增强（托盘常驻/通知/安全/发版工程）

- [x] 7.1 托盘常驻 + 关窗最小化 + 开机自启（两端对称，f58ed712）：关闭窗口隐藏到托盘不退出进程；托盘菜单「显示主窗口 / 开机自启 / 检查更新 / 退出」
- [x] 7.2 开机自启收敛：仅首次启动自动注册一次 + 托盘 CheckMenuItem「开机自启」开关持久化（3ca814c2）
- [x] 7.3 医生端系统通知兜底：WS 消息转系统级提醒，窗口在后台/最小化也不漏（48af1a4d）
- [x] 7.4 首次启动配置引导向导（缺 desktop-config.json 时逐步引导填后端地址）+ 托盘「检查更新」菜单项（125c07bf）
- [x] 7.5 CSP 收紧：两端 webview 从无 CSP 改为白名单（454dbea3），随后按实测补齐——connect-src 放行自建机构任意 origin http/https/ws/wss（a52c4eb7）、img-src 补 http:（21550f89）、admin 端补 worker-src blob: 与 restapi.amap.com 修复地图选点（dbf3e539）
- [x] 7.6 医生端独立图标 + 机构安装配置指南（d78514d0）
- [x] 7.7 上传文件公网基址 PUBLIC_MEDIA_BASE_URL（服务端）：桌面壳下 `<img>` 相对路径 `/uploads/...` 打向资产协议导致头像/图片不显示，由服务端返回绝对 URL 根治（9389ac00，对应下方已知待办第 1 条，已闭环）
- [x] 7.8 发版工程：publish-updates 支持 -rcN 预发布后缀（8cc7c4a5）、作业 contents 权限 write（9244c3c3）、下载产物加重试（67df65d7）、允许缺 Windows 产物并告警（47be3f8f）、自托管 runner 生产运维 workflow prod-ops.yml（28be5fe3 + 15556098 按巡检修正生产路径）

## 已知待办（桌面端特有，不阻塞）

- ~~后端返回的上传文件为相对路径 `/uploads/...`，打包态 `<img src>` 打向资产协议，头像/上传图片不显示~~ 已闭环：服务端新增 PUBLIC_MEDIA_BASE_URL 返回绝对 URL（9389ac00，见 7.7）
- 本地开发库 schema 漂移：`appointments.assistant_confirm_status` 列缺失（alembic 已在 head），`/statistics/overview` 与 `/statistics/revenue/trend` 500——与桌面壳无关，web 同样复现
- 拉取本批改动后，各端 umi dev 需清一次 MFSU 缓存（`rm -rf node_modules/.cache src/.umi`），否则报 `isTauriDesktop is not a function`
