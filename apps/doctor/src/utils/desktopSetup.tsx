/**
 * Tauri 桌面壳首次启动配置引导 + 托盘「检查更新」事件（仅打包态生效；web 端与
 * tauri dev 直接返回）——与 apps/admin/src/utils/desktopSetup.tsx 同构（每端副本
 * 模式，同 hardNavigate.ts）。
 *
 * 背景：打包态运行在自定义协议（tauri://localhost / http://tauri.localhost）上，
 * 相对路径 baseURL 无同源后端可打，必须先配置 desktop.baseUrl（desktop-config.json
 * 的顶层扁平键）。此前只能手工编辑应用数据目录里的 JSON（见 packages/api/src/
 * desktop.ts 头注释），对非技术用户不友好——本模块在「打包态 + 未配置」时弹 antd
 * 向导：输入地址 → 自定义命令 set_desktop_config 校验并写盘 → 成功后整页刷新，
 * 刷新后 applyDesktopBaseUrl 读到新值，应用按机构后端正常启动。
 *
 * 托盘「检查更新」：Rust 托盘菜单点击后 emit_to 主窗口 desktop-check-updates
 * （见 src-tauri lib.rs on_menu_event），这里监听并转调 desktopUpdater 的手动检查
 * ——与启动时的静默检查不同，无新版本 / 更新源不可达也给出可见反馈。
 *
 * 文件是 .tsx 而非 .ts：向导 content 含 JSX（同 desktopUpdater.tsx 的缘故）。
 *
 * 零 npm 依赖：壳已开 app.withGlobalTauri，自定义命令不经 ACL 直接 invoke。与
 * desktopNotify / desktopUpdater 同一兼容承诺：仅打包态生效，拿不到全局对象立即
 * 返回，失败只 console.warn / message 提示，不影响业务。
 */

import { Input, Modal, message } from 'antd';
import { applyDesktopBaseUrl, isTauriPackaged } from '@hospital/api';
import { checkDesktopUpdate } from './desktopUpdater';

/** window.__TAURI__（withGlobalTauri 注入）本模块用到的最小类型描述 */
interface TauriSetupGlobal {
  core?: { invoke?: <T = unknown>(cmd: string, args?: Record<string, unknown>) => Promise<T> };
  event?: {
    listen?: (
      event: string,
      handler: (event: { payload?: unknown }) => void,
    ) => Promise<() => void>;
  };
}

// 不与 @hospital/api 的 Window.__TAURI__ 声明合并（重复声明类型冲突），走局部断言
const tauriGlobal = (): TauriSetupGlobal | undefined =>
  typeof window === 'undefined'
    ? undefined
    : (window as unknown as { __TAURI__?: TauriSetupGlobal }).__TAURI__;

/** 向导默认示例地址（云托管默认入口；机构自建服务器由管理员另行提供） */
const EXAMPLE_BASE_URL = 'https://yy.aicm.online/api/v1';

/** 托盘菜单「检查更新」点击后由 Rust 侧 emit_to 主窗口的事件名（src-tauri lib.rs） */
const TRAY_CHECK_UPDATES_EVENT = 'desktop-check-updates';

const isValidHttpUrl = (value: string): boolean => {
  try {
    const url = new URL(value);
    return url.protocol === 'http:' || url.protocol === 'https:';
  } catch {
    return false;
  }
};

/**
 * 首次启动配置向导：打包态且 desktop.baseUrl 未配置时弹窗收集机构后端地址。
 * applyDesktopBaseUrl 单飞幂等（getInitialState 已 await 过时命中同一次 invoke），
 * 已配置则立即返回，不打扰正常启动。
 */
export const showSetupWizardIfMissing = async (): Promise<void> => {
  if (!isTauriPackaged()) return;
  const configured = await applyDesktopBaseUrl();
  if (configured) return;

  // Modal.confirm 的 content 不是组件实例，用闭包变量承接输入值
  // （desktopUpdater.tsx promptUpdate 同款命令式风格）
  let value = EXAMPLE_BASE_URL;
  Modal.confirm({
    title: '首次使用，请配置机构后端地址',
    width: 560,
    content: (
      <div>
        <p style={{ color: 'rgba(0, 0, 0, 0.65)', margin: '0 0 4px' }}>
          桌面应用需要连接你们机构的预约系统服务（地址由机构管理员提供）才能登录使用，
          配置保存在本机，之后无需重复输入。
        </p>
        <p style={{ color: 'rgba(0, 0, 0, 0.45)', margin: '0 0 12px' }}>
          云托管默认地址 https://yy.aicm.online/api/v1；机构自建服务器形如
          http://&lt;服务器IP&gt;:9000/api/v1（含 /api/v1 后缀）。配错时可编辑本机
          desktop-config.json 修正。
        </p>
        <Input
          defaultValue={EXAMPLE_BASE_URL}
          placeholder={`例如：${EXAMPLE_BASE_URL}`}
          onChange={(e) => { value = e.target.value; }}
        />
      </div>
    ),
    okText: '保存并重启',
    cancelText: '暂不配置',
    onOk: async () => {
      const baseUrl = value.trim();
      if (!isValidHttpUrl(baseUrl)) {
        message.error('地址格式不正确：请输入以 http:// 或 https:// 开头的完整地址');
        // 抛错让 antd 保持弹窗不关闭，用户修正后可重试
        throw new Error(`invalid base url: ${baseUrl}`);
      }
      const invoke = tauriGlobal()?.core?.invoke;
      if (!invoke) {
        message.error('桌面壳接口不可用，请重启应用后重试');
        throw new Error('window.__TAURI__.core.invoke unavailable');
      }
      try {
        await invoke('set_desktop_config', { baseUrl });
      } catch (error) {
        console.warn('[desktop-setup] 写入 desktop-config.json 失败', error);
        message.error(`保存失败：${error instanceof Error ? error.message : String(error)}`);
        throw error;
      }
      // 写盘成功：整页刷新让配置生效（重启后 applyDesktopBaseUrl 读到新值，业务照常
      // 启动）。单页面应用没有可靠的「软重载」，location.reload() 即最直接的生效方式。
      window.location.reload();
    },
  });
};

/**
 * 注册托盘「检查更新」事件监听：收到壳 emit 的 desktop-check-updates 后执行一次
 * 手动检查（manual=true：无新版本 / 更新源不可达也弹反馈，见 desktopUpdater.tsx）。
 *
 * 无需反注册的理由：监听在应用启动时注册一次（getInitialState，非 React 组件生命
 * 周期），单页面应用整页只加载一次、没有会重复注册的挂载点；页面销毁（关窗 /
 * location.reload() / 升级重启）时 webview 上下文整体回收，监听随之消失，不会累积。
 */
export const listenTrayCheckUpdates = (): void => {
  if (!isTauriPackaged()) return;
  const listen = tauriGlobal()?.event?.listen;
  if (!listen) {
    console.warn('[desktop-setup] window.__TAURI__.event.listen 不可用（桌面壳版本过旧？）');
    return;
  }
  void listen(TRAY_CHECK_UPDATES_EVENT, () => {
    void checkDesktopUpdate({ manual: true });
  });
};
