use tauri::Manager;
use tauri_plugin_log::{Target, TargetKind};
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

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        // single-instance 需尽早注册：重复启动时直接退出并聚焦已有窗口
        .plugin(tauri_plugin_single_instance::init(|app, _args, _cwd| {
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.show();
                let _ = window.unminimize();
                let _ = window.set_focus();
            }
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
        .invoke_handler(tauri::generate_handler![get_desktop_config])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
