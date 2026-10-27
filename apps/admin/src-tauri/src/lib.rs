use tauri::Manager;
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
        // Run 键。仅 Rust 直调不经 IPC，无需 capabilities 授权。随启动即启用；机构
        // 环境可能禁用自启项，失败仅告警不阻断启动。
        .plugin(tauri_plugin_autostart::init(MacosLauncher::LaunchAgent, None))
        // 自动更新：updater 校验 minisign 签名后下载安装，process 供前端在安装完成后 relaunch。
        // 公钥/更新源在 tauri.conf.json plugins.updater；真实域名不入库，由 CI 用 --config
        // 合并注入（见 desktop-release.yml），仓库内留 .invalid 占位，本地构建检查更新只会静默失败。
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .invoke_handler(tauri::generate_handler![get_desktop_config])
        .setup(|app| {
            // 托盘常驻：应用图标 + 两项菜单；左键单击托盘唤起主窗口，右键弹菜单。
            // 主窗口关闭不再退出而是隐藏到托盘（见 on_window_event），真正退出走
            // 菜单「退出」→ app.exit(0)，不经过窗口 close，不受关窗拦截影响。
            let show_item =
                tauri::menu::MenuItem::with_id(app, "show", "显示主窗口", true, None::<&str>)?;
            let quit_item = tauri::menu::MenuItem::with_id(app, "quit", "退出", true, None::<&str>)?;
            let tray_menu = tauri::menu::Menu::with_items(app, &[&show_item, &quit_item])?;
            tauri::tray::TrayIconBuilder::with_id("main")
                .icon(
                    app.default_window_icon()
                        .expect("bundle.icon 未配置，托盘无图标可用")
                        .clone(),
                )
                .menu(&tray_menu)
                // 左键留给「唤起主窗口」，菜单交给右键
                .show_menu_on_left_click(false)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => show_main_window(app),
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
            // 开机自启：enable 幂等（已注册时重复启用无害）
            if let Err(e) = app.autolaunch().enable() {
                log::warn!("开机自启启用失败，机构可能禁用了自启项，跳过: {e}");
            }
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
