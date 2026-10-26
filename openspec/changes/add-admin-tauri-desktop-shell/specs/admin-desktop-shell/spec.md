# Spec Delta: admin-desktop-shell

## ADDED Requirements

### Requirement: 桌面壳必须复用 admin 单一代码库

Tauri 桌面壳是 `apps/admin` 的一种发布形态，不是独立前端。桌面分支必须以 `TAURI_DESKTOP` 构建变量或 `isTauriDesktop()` 运行时守卫；web 构建（不注入变量、无 `window.__TAURI__`）的行为必须与引入桌面壳之前完全一致。

#### Scenario: web 构建不受桌面分支影响

- WHEN 以普通 `pnpm build` 构建 `apps/admin`（未注入 TAURI_DESKTOP）
- THEN 路由为 browser history，且产物中不存在任何桌面分支被激活的路径

#### Scenario: web 运行时调用桌面 API

- WHEN 在浏览器中调用 `isTauriDesktop()`、`isTauriPackaged()`、`applyDesktopBaseUrl()`
- THEN 分别返回 false、false、resolve(null)，且不发起任何 Tauri invoke

### Requirement: 桌面壳后端地址必须可按机构配置且无需重新打包

桌面壳必须从应用数据目录的 `desktop-config.json` 读取 `desktop.baseUrl`（顶层扁平键，容错嵌套对象）覆盖构建期 baseURL；键未设置时回落构建期 `API_BASE_URL`。配置读取必须收敛在 Rust 自定义命令 `get_desktop_config` 内，前端不得持有 store 插件的 IPC 权限。

#### Scenario: 机构配置自定义后端地址

- WHEN 机构在应用数据目录 `desktop-config.json` 写入 `{"desktop.baseUrl": "http://<server>:9000/api/v1"}` 并重启应用
- THEN 桌面壳内所有 API 请求发往该绝对地址

#### Scenario: 配置缺失或键名错误时不得静默失败

- WHEN 打包态下 `desktop-config.json` 不存在、为空或缺少 `desktop.baseUrl` 键
- THEN 应用启动时给出可见告警，说明配置文件路径与 JSON 形状；同时 console.warn 区分「文件未建」与「键不对」
- AND 不 crash、不阻塞应用启动

#### Scenario: tauri dev 形态不受配置缺失影响

- WHEN 以 `pnpm desktop:dev` 运行（前端在 http devUrl 上、经 Umi 代理访问后端）且未配置 desktop.baseUrl
- THEN 请求正常经代理发出，不出现配置缺失弹窗

### Requirement: 桌面壳内的整页跳转必须落到预期路由

桌面壳为 hash 路由且运行在自定义协议上。admin 内所有 `window.location.href` 整页跳转必须经由 `hardNavigate`（桌面壳下写 `/#<path>`），保证整页刷新语义保留且 hash 路由落到目标页；页面路径记录（性能、会话录制）必须 hash 感知。

#### Scenario: 登录成功回跳原业务页

- WHEN 用户在桌面壳内从业务页被登出后重新登录成功
- THEN 整页跳转后落在原业务页（safeLastPath），而不是被资产协议回退重置到默认路由

#### Scenario: 403 租户暂停跳转

- WHEN 桌面壳内收到租户暂停 403
- THEN 整页跳转后落在 /tenant-suspended 页面

### Requirement: 桌面壳必须防多开并具备最小权限

桌面壳必须注册 single-instance（重复启动时聚焦已有窗口）；capabilities 必须仅授予核心能力，未使用的插件 IPC 权限不得授予。

#### Scenario: 重复启动

- WHEN 应用已在运行时再次双击启动
- THEN 第二个进程退出，已有窗口被显示并聚焦

#### Scenario: 权限最小化

- WHEN 审查 `src-tauri/capabilities/default.json`
- THEN 仅包含 `core:default`，不包含 store 等未被前端 IPC 调用的插件权限
