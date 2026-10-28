/**
 * Tauri 桌面壳系统通知（仅打包态生效；web 端与 tauri dev 直接返回）
 *
 * 背景：桌面端已支持关窗隐藏到托盘常驻（src-tauri lib.rs on_window_event），医生切走
 * 或关窗后应用内 antd 通知看不见，患者签到 / 新预约 / 停诊这类消息需要系统级兜底提醒。
 *
 * 零 npm 依赖：壳已开 app.withGlobalTauri，Rust 侧注册 notification 插件后，JS API 挂在
 * window.__TAURI__.notification 上（isPermissionGranted / requestPermission /
 * sendNotification，与官方 @tauri-apps/plugin-notification 同一签名）。与 desktopUpdater /
 * @hospital/api desktop.ts 同一兼容承诺：仅打包态（isTauriPackaged）生效；拿不到全局对象
 * 立即返回；权限查询/申请、发送的任何失败只 console.warn，绝不影响业务消息处理。
 *
 * 权限时序说明：首次尝试发送时才走 isPermissionGranted → requestPermission（macOS 会弹
 * 系统授权框，Windows 一般无需申请）。授权框出现前的那条通知可能丢失，属预期——下次
 * 授权通过后恢复。
 */

import { isTauriPackaged } from '@hospital/api';

/** window.__TAURI__.notification（notification 插件 withGlobalTauri 注入）的最小类型描述 */
interface TauriNotificationGlobal {
  notification?: {
    isPermissionGranted: () => Promise<boolean>;
    requestPermission: () => Promise<'granted' | 'denied' | 'default' | 'prompt'>;
    sendNotification: (options: { title?: string; body?: string; icon?: string }) => Promise<string>;
  };
}

// 不与 @hospital/api 的 Window.__TAURI__ 声明合并（重复声明类型冲突），走局部断言
const tauriGlobal = (): TauriNotificationGlobal | undefined =>
  typeof window === 'undefined'
    ? undefined
    : (window as unknown as { __TAURI__?: TauriNotificationGlobal }).__TAURI__;

/**
 * 窗口是否「看不到」：整窗隐藏（关窗进托盘 / 最小化 / 切走）或未聚焦。
 * 两者任一成立才值得发系统通知——窗口在前台时应用内通知已可见，重复提醒是噪音。
 */
export const isWindowInactive = (): boolean =>
  typeof document !== 'undefined' && (document.hidden || !document.hasFocus());

/**
 * 发送系统通知。调用方自行决定时机（本模块不做窗口状态判断）；非打包态、全局 API
 * 缺失、权限未授予、发送失败均静默（console.warn）返回。
 */
export const sendDesktopNotification = async (options: {
  title: string;
  body?: string;
}): Promise<void> => {
  if (!isTauriPackaged()) return;

  const api = tauriGlobal()?.notification;
  if (!api) {
    console.warn('[desktop-notify] window.__TAURI__.notification 不可用（壳未注册 notification 插件？）');
    return;
  }

  try {
    let permissionGranted = await api.isPermissionGranted();
    if (!permissionGranted) {
      const permission = await api.requestPermission();
      permissionGranted = permission === 'granted';
    }
    if (!permissionGranted) {
      console.warn('[desktop-notify] 系统通知权限未授予，跳过本次提醒');
      return;
    }
    await api.sendNotification({ title: options.title, body: options.body });
  } catch (error) {
    console.warn('[desktop-notify] 发送系统通知失败', error);
  }
};
