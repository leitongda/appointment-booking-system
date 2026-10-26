/**
 * Tauri 桌面壳分支（PoC，仅 apps/admin 桌面壳使用）
 *
 * 背景：web 端 baseURL 是构建期注入的相对路径（apps/admin/.env 的 API_BASE_URL=/api/v1，
 * 经 config/config.ts define 编译进产物），浏览器下与后端同源、由网关/代理转发。打包进
 * Tauri 桌面壳后，前端运行在自定义协议（tauri://localhost）上，相对路径无同源后端可打，
 * 需要一个可按机构配置的绝对地址。
 *
 * 方案：桌面壳（apps/admin/src-tauri）用 tauri-plugin-store 在应用数据目录维护
 * desktop-config.json，机构部署时直接编辑该文件即可切换环境，无需重新打包。
 * 文件形状（注意是「顶层扁平键」，插件的 get 不拆点路径；嵌套写法 Rust 侧也容错）：
 *
 *   {"desktop.baseUrl": "http://<server>:9000/api/v1"}
 *
 * 文件位置：macOS ~/Library/Application Support/online.aicm.hospital.admin/
 *           Windows %APPDATA%\online.aicm.hospital.admin\（identifier 决定目录名）
 * 前端通过 window.__TAURI__.core.invoke('get_desktop_config') 读取
 * （桌面壳已开启 app.withGlobalTauri，无需额外 npm 依赖）。
 *
 * 兼容性承诺：仅当 window.__TAURI__ 存在时本模块才生效；web 端所有函数立即返回、
 * 不触碰任何状态，现有行为零变化。拿不到配置（插件缺失、命令失败、键未设置）时
 * 返回 null，调用方回落到现有逻辑（构建期 API_BASE_URL），并 console.warn 说明
 * 原因（文件未建 / 已建但键不对）。
 */
import { setBaseURL } from './request';

/** window.__TAURI__（app.withGlobalTauri = true 注入）的最小类型描述 */
interface TauriDesktopGlobal {
  core?: {
    invoke?: <T = unknown>(cmd: string, args?: Record<string, unknown>) => Promise<T>;
  };
}

declare global {
  interface Window {
    __TAURI__?: TauriDesktopGlobal;
  }
}

/** get_desktop_config 命令返回结构 */
export interface DesktopConfig {
  baseUrl?: string | null;
  /** 配置文件是否加载到了任何键（false = 文件缺失 / 空 JSON / 非法 JSON，插件内部静默吞错） */
  storeLoaded?: boolean;
}

/**
 * 是否运行在 Tauri 桌面壳内
 * （withGlobalTauri 注入的 window.__TAURI__ 存在且 core.invoke 可用）
 */
export const isTauriDesktop = (): boolean =>
  typeof window !== 'undefined'
  && !!(window as Window & { __TAURI__?: TauriDesktopGlobal }).__TAURI__?.core?.invoke;

/**
 * 是否运行在 Tauri 打包态（而非 tauri dev）。
 * 打包态前端运行在自定义协议上（macOS/Linux: tauri://localhost，
 * Windows: http://tauri.localhost），相对路径 baseURL 无同源后端可打；
 * tauri dev 走 devUrl（http://127.0.0.1:9105），相对路径经 Umi 代理可正常工作。
 */
export const isTauriPackaged = (): boolean =>
  typeof window !== 'undefined'
  && (window.location.protocol === 'tauri:' || window.location.hostname === 'tauri.localhost');

/**
 * 读取桌面配置（invoke get_desktop_config）。
 * 任何失败（命令不存在、插件未就绪等）都吞掉并返回 null —— 拿不到配置就回落现有逻辑。
 */
const invokeDesktopConfig = async (): Promise<DesktopConfig | null> => {
  const tauri = (window as Window & { __TAURI__?: TauriDesktopGlobal }).__TAURI__;
  try {
    const config = await tauri!.core!.invoke!<DesktopConfig>('get_desktop_config');
    return config && typeof config === 'object' ? config : null;
  } catch {
    return null;
  }
};

/**
 * 应用桌面 baseUrl 覆盖（单飞 + 幂等）。
 *
 * 成功拿到非空 desktop.baseUrl 时调用 setBaseURL 覆盖默认实例并返回该值；
 * 否则返回 null，调用方维持构建期 baseURL 不变。
 *
 * 初始化时序说明：invoke 是异步的，而各端 setBaseURL 是同步调用。稳妥方案为
 * 「启动时预取 + 首请求前把关」，两处调用命中本函数缓存的同一次 invoke：
 *   1) initApp（app.tsx 模块初始化时）fire-and-forget 调用，尽早完成预取；
 *   2) getInitialState（Umi 首个业务请求前的最后一道关口）await 本函数，
 *      保证 fetchUserInfo 等首个业务请求发出前 baseURL 已定稿。
 */
let desktopBaseUrlPromise: Promise<string | null> | null = null;

export const applyDesktopBaseUrl = (): Promise<string | null> => {
  if (!isTauriDesktop()) return Promise.resolve(null);
  if (!desktopBaseUrlPromise) {
    desktopBaseUrlPromise = invokeDesktopConfig().then((config) => {
      const baseUrl = config?.baseUrl;
      if (typeof baseUrl === 'string' && baseUrl.trim() !== '') {
        setBaseURL(baseUrl);
        return baseUrl;
      }
      // 配置缺失不是静默场景：打包态下相对路径 baseURL 无法访问后端，
      // 控制台给出定位信息（打包态的可见弹窗由 app.tsx getInitialState 负责）
      console.warn(
        '[desktop] 未读到 desktop.baseUrl，回落构建期 API_BASE_URL。'
        + (config?.storeLoaded
          ? 'desktop-config.json 已存在但缺少键——请确认写入的是顶层扁平键 '
            + '"desktop.baseUrl"（嵌套 {"desktop":{"baseUrl":…}} 也支持），保存后重启应用。'
          : 'desktop-config.json 不存在或为空/非法 JSON——请在应用数据目录创建它：'
            + 'macOS ~/Library/Application Support/online.aicm.hospital.admin/、'
            + 'Windows %APPDATA%\\online.aicm.hospital.admin\\，内容形如 '
            + '{"desktop.baseUrl": "http://<server>:9000/api/v1"}，保存后重启应用。'),
      );
      return null;
    });
  }
  return desktopBaseUrlPromise;
};
