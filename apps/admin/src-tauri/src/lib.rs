use tauri::{Emitter, Manager};
use tauri_plugin_autostart::{MacosLauncher, ManagerExt};
use tauri_plugin_log::{log, Target, TargetKind};
use tauri_plugin_store::StoreExt;

/// 桌面配置命令：读取应用数据目录下 desktop-config.json（tauri-plugin-store，相对路径
/// 按 BaseDirectory::AppData 解析），返回 { baseUrl: string | null, storeLoaded: bool }
/// 供前端覆盖 API baseURL。
///
/// 机构部署切换环境：无需重新打包，直接编辑应用数据目录中的 desktop-config.json
/// （macOS: ~/Library/Application Support/online.aicm.hospital.admin/
///  Windows: %APPDATA%\online.aicm.hospital.admin\），写入：
///
///   {"desktop.baseUrl": "http://<server>:9000/api/v1"}
///
/// 键必须是上面这种「顶层扁平键」——tauri-plugin-store 的 get 是顶层字面键查找
/// （HashMap.get，不拆点路径），嵌套写法会查不到。为容错，此处同时接受嵌套对象
/// {"desktop": {"baseUrl": "..."}}。保存后重启应用生效。
///
/// baseUrl 为 null 时前端回落构建期 API_BASE_URL；打包态（tauri://localhost）下相对
/// 路径无法访问后端，前端会给出可见告警（见 packages/api/src/desktop.ts 与 app.tsx）。
///
/// storeLoaded：配置文件是否加载到了任何键。插件内部对 load 失败（文件缺失 / 非法
/// JSON）静默吞错并以空缓存创建 store，此标记让前端能区分「文件没配」与「配了但
/// 格式不对」，告警文案据此给出针对性指引。
#[tauri::command]
fn get_desktop_config(app: tauri::AppHandle) -> Result<serde_json::Value, String> {
    let store = app
        .store("desktop-config.json")
        .map_err(|e| format!("读取桌面配置失败: {e}"))?;
    // 顶层扁平键优先（插件原生语义），其次容错嵌套对象
    let base_url = store
        .get("desktop.baseUrl")
        .and_then(|value| value.as_str().map(str::to_string))
        .or_else(|| {
            store.get("desktop").and_then(|desktop| {
                desktop
                    .get("baseUrl")
                    .and_then(|value| value.as_str().map(str::to_string))
            })
        });
    let store_loaded = !store.keys().is_empty();
    Ok(serde_json::json!({ "baseUrl": base_url, "storeLoaded": store_loaded }))
}

/// 首次启动配置引导写入命令（前端向导 apps/admin/src/utils/desktopSetup.tsx 调用）：
/// 校验 base_url 以 http:// 或 https:// 开头后，写入 desktop-config.json 的顶层扁平键
/// desktop.baseUrl（与 get_desktop_config 同一 store），随即 save() 落盘——插件的 set
/// 只改内存缓存，不落盘的话重启就丢。成功返回 Ok(())，失败返回 Err(中文说明)，前端
/// 向导据此保持弹窗让用户重试。
///
/// 机构后端地址逐机构可变（云托管 / 自建内网），不能打进安装包：要么首启向导配置，
/// 要么照 get_desktop_config 文档手工编辑 desktop-config.json。
#[tauri::command]
fn set_desktop_config(app: tauri::AppHandle, base_url: String) -> Result<(), String> {
    let base_url = base_url.trim();
    if !(base_url.starts_with("http://") || base_url.starts_with("https://")) {
        return Err("地址必须以 http:// 或 https:// 开头".to_string());
    }
    let store = app
        .store("desktop-config.json")
        .map_err(|e| format!("打开桌面配置失败: {e}"))?;
    store.set("desktop.baseUrl", base_url);
    store
        .save()
        .map_err(|e| format!("保存桌面配置失败: {e}"))?;
    Ok(())
}

/// 唤起主窗口（show + 取消最小化 + 聚焦）：托盘单击、托盘菜单「显示主窗口」、
/// 重复启动（single-instance）、macOS Dock 重开共用。show() 是 hide() 的逆操作，
/// 窗口被关窗隐藏到托盘后靠这里唤回。
fn show_main_window<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    if let Some(window) = app.get_webview_window("main") {
        let _ = window.show();
        let _ = window.unminimize();
        let _ = window.set_focus();
    }
}

/// desktop-shell.json 里标记「本应用已自动注册过开机自启」的键。单独放一个
/// store 文件而不写进 desktop-config.json：后者是机构部署的用户配置（首启向导
/// 依赖其 storeLoaded 语义区分「没配」与「配错」），壳自身的状态不应混入。
const AUTOSTART_FLAG_FILE: &str = "desktop-shell.json";
const AUTOSTART_FLAG_KEY: &str = "autostartEverEnabled";

/// 是否已自动注册过开机自启（痕记存在即 true；store 打不开按未注册处理，
/// 允许下次启动重试自动注册）。
fn autostart_ever_enabled<R: tauri::Runtime>(app: &tauri::AppHandle<R>) -> bool {
    app.store(AUTOSTART_FLAG_FILE)
        .ok()
        .and_then(|store| store.get(AUTOSTART_FLAG_KEY).and_then(|v| v.as_bool()))
        .unwrap_or(false)
}

/// 写入「已自动注册过」痕记并落盘（插件的 set 只改内存缓存，不 save 重启就丢）。
fn mark_autostart_registered<R: tauri::Runtime>(app: &tauri::AppHandle<R>) {
    if let Ok(store) = app.store(AUTOSTART_FLAG_FILE) {
        store.set(AUTOSTART_FLAG_KEY, true);
        let _ = store.save();
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // single-instance 需尽早注册：重复启动时直接退出并唤起已有窗口
        // （窗口可能已随关窗隐藏到托盘，show() 兼具取消隐藏，仍能唤回）
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            show_main_window(app);
        }))
        // 日志：应用日志目录（LogDir，如 macOS ~/Library/Logs/online.aicm.hospital.admin/）
        // + 开发期 stdout，便于 PoC 排查
        .plugin(
            tauri_plugin_log::Builder::new()
                .targets([
                    Target::new(TargetKind::LogDir { file_name: None }),
                    Target::new(TargetKind::Stdout),
                ])
                .build(),
        )
        .plugin(tauri_plugin_store::Builder::new().build())
        // 开机自启：macOS 装 LaunchAgent（~/Library/LaunchAgents），Windows 写注册表
        // Run 键。仅 Rust 直调不经 IPC，无需 capabilities 授权。是否注册不再无条件
        // 重开：仅首次启动自动注册一次，此后由托盘「开机自启」开关或系统设置决定
        // （见 setup 与 autostart_ever_enabled 注释）；机构环境可能禁用自启项，失败
        // 仅告警不阻断启动。
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, None))
        // 自动更新：updater 校验 minisign 签名后下载安装，process 供前端在安装完成后 relaunch。
        // 公钥/更新源在 tauri.conf.json plugins.updater；真实域名不入库，由 CI 用 --config
        // 合并注入（见 desktop-release.yml），仓库内留 .invalid 占位，本地构建检查更新只会静默失败。
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        // 系统通知：本期管理端前端未接（页面内已有通知铃），与医生端保持壳能力一致，
        // 仅注册插件备用；前端经 window.__TAURI__.notification 即可调用（零 npm 依赖），
        // 需 capabilities 的 notification:default 授权。
        .plugin(tauri_plugin_notification::init())
        .invoke_handler(tauri::generate_handler![
            get_desktop_config,
            set_desktop_config
        ])
        .setup(|app| {
            // 开机自启：仅首次启动自动注册一次（成功后写 autostartEverEnabled 痕记），
            // 此后启动不再无条件 enable——用户经托盘「开机自启」开关或系统设置
            // （macOS 登录项 / Windows Run 键）移除后，重启不会被静默恢复。
            let mut autostart_on = app.autolaunch().is_enabled().unwrap_or(false);
            if !autostart_on && !autostart_ever_enabled(app.handle()) {
                match app.autolaunch().enable() {
                    Ok(()) => {
                        mark_autostart_registered(app.handle());
                        autostart_on = true;
                    }
                    // 机构环境可能禁用自启项，失败仅告警不阻断启动（不写痕记，
                    // 下次启动可重试）
                    Err(e) => log::warn!("开机自启启用失败，机构可能禁用了自启项，跳过: {e}"),
                }
            }
            // 托盘常驻：应用图标 + 四项菜单；左键单击托盘唤起主窗口，右键弹菜单。
            // 主窗口关闭不再退出而是隐藏到托盘（见 on_window_event），真正退出走
            // 菜单「退出」→ app.exit(0)，不经过窗口 close，不受关窗拦截影响。
            let show_item =
                tauri::menu::MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
            // 「开机自启」复选开关：勾选态取当前系统注册状态，点击即切换（见
            // on_menu_event 的 toggle-autostart 分支）——应用内关闭自启的入口。
            let autostart_item = tauri::menu::CheckMenuItem::with_id(
                app,
                "toggle-autostart",
                "开机自启",
                true,
                autostart_on,
                None::<&str>,
            )?;
            let check_updates_item =
                tauri::menu::MenuItem::with_id(app, "check-updates", "检查更新", true, None::<&str>)?;
            let quit_item = tauri::menu::MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let tray_menu = tauri::menu::Menu::with_items(
                app,
                &[&show_item, &autostart_item, &check_updates_item, &quit_item],
            )?;
            tauri::tray::TrayIconBuilder::with_id("main")
                .icon(
                    app.default_window_icon()
                        .expect("bundle.icon 未配置，托盘无图标可用")
                        .clone(),
                )
                .menu(&tray_menu)
                // 左键留给「唤起主窗口」，菜单交给右键
                .show_menu_on_left_click(false)
                .on_menu_event(move |app, event| match event.id.as_ref() {
                    "show" => show_main_window(app),
                    // 开机自启开关：按当前系统注册状态取反并同步勾选态；开启成功补写
                    // autostartEverEnabled 痕记，维持「移除后不被静默恢复」的语义。
                    // 失败（机构禁用自启项等）按真实注册态回弹勾选框。
                    "toggle-autostart" => {
                        let manager = app.autolaunch();
                        let next = !manager.is_enabled().unwrap_or(false);
                        let result = if next {
                            manager.enable()
                        } else {
                            manager.disable()
                        };
                        match result {
                            Ok(()) => {
                                if next {
                                    mark_autostart_registered(app);
                                }
                                let _ = autostart_item.set_checked(next);
                            }
                            Err(e) => {
                                log::warn!("切换开机自启失败: {e}");
                                let _ = autostart_item
                                    .set_checked(manager.is_enabled().unwrap_or(false));
                            }
                        }
                    }
                    // 检查更新：先唤起主窗口（手动检查的结果反馈弹在 webview 里，窗口
                    // 隐藏到托盘时用户看不见），再向主窗口发事件；前端 desktopSetup.tsx
                    // 监听后调用 checkDesktopUpdate({ manual: true })。
                    "check-updates" => {
                        show_main_window(app);
                        let _ = app.emit_to("main", "desktop-check-updates", ());
                    }
                    "quit" => app.exit(0),
                    _ => {}
                })
                .on_tray_icon_event(|tray, event| {
                    if let tauri::tray::TrayIconEvent::Click {
                        button: tauri::tray::MouseButton::Left,
                        button_state: tauri::tray::MouseButtonState::Up,
                        ..
                    } = event
                    {
                        show_main_window(tray.app_handle());
                    }
                })
                .build(app)?;
            Ok(())
        })
        // 关窗最小化：拦截主窗口关闭请求，隐藏到托盘常驻；菜单「退出」走
        // app.exit(0)，不经过窗口 close，不受此拦截影响
        .on_window_event(|window, event| {
            if window.label() == "main" {
                if let tauri::WindowEvent::CloseRequested { api, .. } = event {
                    api.prevent_close();
                    let _ = window.hide();
                }
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application")
        // macOS：窗口隐藏到托盘后点 Dock 图标只激活应用、不会还原窗口，这里补一次
        // 唤起（Reopen 是 macOS 专属事件，臂上加 cfg 以免 Windows 构建编译不过）
        .run(|app, event| match event {
            #[cfg(target_os = "macos")]
            tauri::RunEvent::Reopen { .. } => show_main_window(app),
            _ => {}
        });
}
